import hashlib
import hmac
import time

import pytest
from flask import Flask

from config.settings import settings
from database.database import get_connection
from database.models import initialize_database
from routes.webhooks import verify_pairgate_signature, webhooks_bp
from services.order_service import OrderService
from services.payment_service import PaymentService


@pytest.fixture
def database(tmp_path, monkeypatch):
    monkeypatch.setattr(
        settings,
        "DATABASE_PATH",
        str(tmp_path / "subscribe_me_test.db")
    )
    initialize_database()

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO users (email, password_hash) VALUES (?, ?)",
        ("test@example.com", "test-hash")
    )
    user_id = cursor.lastrowid
    cursor.execute(
        "INSERT INTO wallets (user_id, balance_kobo) VALUES (?, ?)",
        (user_id, 0)
    )
    cursor.execute("""
        INSERT INTO data_plans (
            supplier, supplier_plan_id, network, plan_type, name,
            supplier_price_kobo, selling_price_kobo
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ("pairgate", "plan-1", "mtn", "SME", "Test Plan", 500, 700))
    plan_id = cursor.lastrowid
    connection.commit()
    connection.close()

    return user_id, plan_id


def test_legacy_unsigned_payment_webhook_is_disabled():
    app = Flask(__name__)
    app.register_blueprint(webhooks_bp)

    response = app.test_client().post(
        "/api/v1/webhooks/payment",
        json={"reference": "PAY-123", "status": "SUCCESS"}
    )

    assert response.status_code == 410


def test_pairgate_signature_accepts_fresh_valid_payload(monkeypatch):
    secret = "unit-test-webhook-secret"
    timestamp = str(int(time.time()))
    payload = b'{"event":"data.purchase"}'
    signature = hmac.new(
        secret.encode(),
        timestamp.encode() + b"." + payload,
        hashlib.sha256
    ).hexdigest()

    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "PAIRGATE_WEBHOOK_VERIFY", True)
    monkeypatch.setattr(settings, "PAIRGATE_WEBHOOK_SECRET", secret)
    monkeypatch.setattr(settings, "PAIRGATE_WEBHOOK_TOLERANCE_SECONDS", 300)

    app = Flask(__name__)
    with app.test_request_context(
        "/api/v1/webhooks/pairgate",
        method="POST",
        data=payload,
        headers={
            "X-Pairgate-Timestamp": timestamp,
            "X-Pairgate-Signature": signature
        }
    ):
        assert verify_pairgate_signature() is True


def test_pairgate_signature_rejects_stale_payload(monkeypatch):
    secret = "unit-test-webhook-secret"
    timestamp = str(int(time.time()) - 3600)
    payload = b'{"event":"data.purchase"}'
    signature = hmac.new(
        secret.encode(),
        timestamp.encode() + b"." + payload,
        hashlib.sha256
    ).hexdigest()

    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "PAIRGATE_WEBHOOK_VERIFY", True)
    monkeypatch.setattr(settings, "PAIRGATE_WEBHOOK_SECRET", secret)
    monkeypatch.setattr(settings, "PAIRGATE_WEBHOOK_TOLERANCE_SECONDS", 300)

    app = Flask(__name__)
    with app.test_request_context(
        "/api/v1/webhooks/pairgate",
        method="POST",
        data=payload,
        headers={
            "X-Pairgate-Timestamp": timestamp,
            "X-Pairgate-Signature": signature
        }
    ):
        assert verify_pairgate_signature() is False


def test_paystack_wallet_credit_is_atomic_and_idempotent(database):
    user_id, _ = database
    connection = get_connection()
    connection.execute("""
        INSERT INTO payments (
            user_id, reference, provider, amount_kobo, status, payment_method
        )
        VALUES (?, ?, 'paystack', ?, 'PENDING', 'online')
    """, (user_id, "PAY-TEST-001", 25000))
    connection.commit()
    connection.close()

    first = PaymentService.complete_verified_payment(
        reference="PAY-TEST-001",
        provider_reference="provider-txn-1001",
        provider_amount_kobo=25000
    )
    second = PaymentService.complete_verified_payment(
        reference="PAY-TEST-001",
        provider_reference="provider-txn-1001",
        provider_amount_kobo=25000
    )

    connection = get_connection()
    wallet = connection.execute(
        "SELECT balance_kobo FROM wallets WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    ledger_count = connection.execute(
        "SELECT COUNT(*) FROM wallet_transactions WHERE reference = ?",
        ("FUND-PAY-TEST-001",)
    ).fetchone()[0]
    connection.close()

    assert first["status"] == "success"
    assert second["status"] == "already_processed"
    assert wallet["balance_kobo"] == 25000
    assert ledger_count == 1


def test_paystack_wallet_credit_rejects_amount_mismatch(database):
    user_id, _ = database
    connection = get_connection()
    connection.execute("""
        INSERT INTO payments (
            user_id, reference, provider, amount_kobo, status, payment_method
        )
        VALUES (?, ?, 'paystack', ?, 'PENDING', 'online')
    """, (user_id, "PAY-TEST-002", 25000))
    connection.commit()
    connection.close()

    with pytest.raises(ValueError, match="amount does not match"):
        PaymentService.complete_verified_payment(
            reference="PAY-TEST-002",
            provider_reference="provider-txn-1002",
            provider_amount_kobo=24999
        )

    connection = get_connection()
    wallet = connection.execute(
        "SELECT balance_kobo FROM wallets WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    status = connection.execute(
        "SELECT status FROM payments WHERE reference = ?",
        ("PAY-TEST-002",)
    ).fetchone()
    connection.close()

    assert wallet["balance_kobo"] == 0
    assert status["status"] == "PENDING"


def test_pairgate_failed_callback_refunds_once(database):
    user_id, plan_id = database
    connection = get_connection()
    connection.execute(
        "UPDATE wallets SET balance_kobo = 0 WHERE user_id = ?",
        (user_id,)
    )
    connection.execute("""
        INSERT INTO orders (
            reference, user_id, phone, network, plan_id, supplier,
            supplier_plan_id, amount_kobo, status, message
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PROCESSING', ?)
    """, (
        "ORD-TEST-001", user_id, "08012345678", "mtn", plan_id,
        "pairgate", "plan-1", 700, "Processing"
    ))
    connection.commit()
    connection.close()

    service = OrderService()
    first = service.process_pairgate_webhook(
        reference="ORD-TEST-001",
        status="failed",
        message="Supplier rejected transaction"
    )
    second = service.process_pairgate_webhook(
        reference="ORD-TEST-001",
        status="failed",
        message="Duplicate callback"
    )

    connection = get_connection()
    wallet = connection.execute(
        "SELECT balance_kobo FROM wallets WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    ledger_count = connection.execute(
        "SELECT COUNT(*) FROM wallet_transactions WHERE reference = ?",
        ("REFUND-ORD-TEST-001",)
    ).fetchone()[0]
    order = connection.execute(
        "SELECT status FROM orders WHERE reference = ?",
        ("ORD-TEST-001",)
    ).fetchone()
    connection.close()

    assert first["status"] == "refunded"
    assert second["status"] == "already_processed"
    assert wallet["balance_kobo"] == 700
    assert ledger_count == 1
    assert order["status"] == "REFUNDED"


def test_order_idempotency_key_returns_existing_order(database):
    user_id, plan_id = database
    connection = get_connection()
    connection.execute("""
        INSERT INTO orders (
            reference, user_id, phone, network, plan_id, supplier,
            supplier_plan_id, amount_kobo, status, message, idempotency_key
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PROCESSING', ?, ?)
    """, (
        "ORD-EXISTING-001", user_id, "08012345678", "mtn", plan_id,
        "pairgate", "plan-1", 700, "Processing", "same-order-key-123456"
    ))
    connection.commit()
    connection.close()

    result = OrderService().create_order(
        user_id=user_id,
        plan_id=plan_id,
        phone="08012345678",
        idempotency_key="same-order-key-123456"
    )

    assert result["status"] == "processing"
    assert result["reference"] == "ORD-EXISTING-001"


def test_order_idempotency_key_cannot_be_reused_for_different_payload(database):
    user_id, plan_id = database
    connection = get_connection()
    connection.execute("""
        INSERT INTO orders (
            reference, user_id, phone, network, plan_id, supplier,
            supplier_plan_id, amount_kobo, status, message, idempotency_key
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PROCESSING', ?, ?)
    """, (
        "ORD-EXISTING-002", user_id, "08012345678", "mtn", plan_id,
        "pairgate", "plan-1", 700, "Processing", "same-order-key-654321"
    ))
    connection.commit()
    connection.close()

    with pytest.raises(ValueError, match="different order"):
        OrderService().create_order(
            user_id=user_id,
            plan_id=plan_id,
            phone="08099999999",
            idempotency_key="same-order-key-654321"
        )


def test_pending_idempotent_order_retry_reuses_existing_wallet_debit(database):
    user_id, plan_id = database
    reference = "ORD-PENDING-RECOVERY"
    key = "retry-existing-pending-order-123"

    connection = get_connection()
    connection.execute(
        "UPDATE wallets SET balance_kobo = 300 WHERE user_id = ?",
        (user_id,)
    )
    connection.execute("""
        INSERT INTO orders (
            reference, user_id, phone, network, plan_id, supplier,
            supplier_plan_id, amount_kobo, status, message, idempotency_key
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, ?)
    """, (
        reference, user_id, "08012345678", "mtn", plan_id,
        "pairgate", "plan-1", 700, "Order created.", key
    ))
    connection.execute("""
        INSERT INTO wallet_transactions (
            user_id, type, amount_kobo, reference, description, status
        )
        VALUES (?, 'DEBIT', ?, ?, ?, 'SUCCESS')
    """, (
        user_id, 700, reference, "Data purchase - Test Plan"
    ))
    connection.commit()
    connection.close()

    service = OrderService()
    calls = []

    class SuccessfulSupplier:
        def purchase_data(self, **kwargs):
            calls.append(kwargs)
            return {"status": "success", "message": "Delivered"}

    service.supplier_service.get_supplier = lambda _name: SuccessfulSupplier()

    result = service.create_order(
        user_id=user_id,
        plan_id=plan_id,
        phone="08012345678",
        idempotency_key=key
    )

    connection = get_connection()
    wallet = connection.execute(
        "SELECT balance_kobo FROM wallets WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    debit_count = connection.execute(
        "SELECT COUNT(*) FROM wallet_transactions WHERE reference = ?",
        (reference,)
    ).fetchone()[0]
    order = connection.execute(
        "SELECT status FROM orders WHERE reference = ?",
        (reference,)
    ).fetchone()
    connection.close()

    assert result["status"] == "success"
    assert len(calls) == 1
    assert wallet["balance_kobo"] == 300
    assert debit_count == 1
    assert order["status"] == "SUCCESS"


def test_supplier_pending_response_cannot_overwrite_concurrent_success(database):
    user_id, plan_id = database
    connection = get_connection()
    connection.execute(
        "UPDATE wallets SET balance_kobo = 1000 WHERE user_id = ?",
        (user_id,)
    )
    connection.commit()
    connection.close()
    service = OrderService()

    class SupplierWithConcurrentWebhook:
        def purchase_data(self, **kwargs):
            service.process_pairgate_webhook(
                reference=kwargs["reference"],
                status="successful",
                message="Webhook confirmed delivery",
                supplier_reference="PAIRGATE-TXN-1"
            )
            return {"status": "pending", "message": "Still processing"}

    service.supplier_service.get_supplier = lambda _name: SupplierWithConcurrentWebhook()

    result = service.create_order(
        user_id=user_id,
        plan_id=plan_id,
        phone="08012345678",
        idempotency_key="concurrent-success-test-123"
    )

    connection = get_connection()
    order = connection.execute(
        "SELECT status FROM orders WHERE reference = ?",
        (result["reference"],)
    ).fetchone()
    connection.close()

    assert result["status"] == "success"
    assert order["status"] == "SUCCESS"
