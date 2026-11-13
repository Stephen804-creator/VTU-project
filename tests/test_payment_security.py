"""Security regression tests for wallet funding and provider webhooks.

Run with: python -m unittest discover -s tests -v
"""
import hashlib
import hmac
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from unittest.mock import patch

# Set safe test configuration before importing application modules.
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-that-is-long-enough-123456")
os.environ.setdefault("PAYSTACK_SECRET_KEY", "sk_test_unit_test_secret")
os.environ.setdefault("PAIRGATE_WEBHOOK_SECRET", "pairgate-unit-test-secret")
os.environ.setdefault("PAIRGATE_API_KEY", "pairgate-test-key")
os.environ.setdefault("PAIRGATE_WEBHOOK_VERIFY", "true")

from flask import Flask
from routes.payments import naira_to_kobo
from routes.webhooks import webhooks_bp
from services.payment_service import PaymentService


class NairaToKoboTests(unittest.TestCase):
    def test_exact_integer_and_fractional_naira_conversion(self):
        self.assertEqual(naira_to_kobo("100"), 10000)
        self.assertEqual(naira_to_kobo("100.01"), 10001)
        self.assertEqual(naira_to_kobo(Decimal("0.10")), 10)

    def test_rejects_invalid_or_unsafe_amounts(self):
        for value in (None, True, False, "NaN", "Infinity", "-Infinity", "abc", "", "0", "-1", "1.001", "1000000.01"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    naira_to_kobo(value)

    def test_rejects_float_artifacts_beyond_two_decimal_places(self):
        with self.assertRaises(ValueError):
            naira_to_kobo(0.1 + 0.2)


class ProductionSecretTests(unittest.TestCase):
    def _import_settings(self, secret):
        env = os.environ.copy()
        env.update({
            "APP_ENV": "production",
            "PAYSTACK_SECRET_KEY": "sk_test_configured",
            "PAIRGATE_API_KEY": "pairgate_configured",
            "PAIRGATE_WEBHOOK_SECRET": "pairgate_webhook_configured",
        })
        if secret is None:
            env.pop("SECRET_KEY", None)
        else:
            env["SECRET_KEY"] = secret
        return subprocess.run(
            [sys.executable, "-c", "import config.settings"],
            cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)),
            env=env,
            capture_output=True,
            text=True,
        )

    def test_missing_secret_fails_closed(self):
        result = self._import_settings(None)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SECRET_KEY", result.stderr)

    def test_short_or_placeholder_secret_fails_closed(self):
        for secret in ("short", "replace-with-a-random-secret-of-at-least-32-characters"):
            with self.subTest(secret=secret):
                result = self._import_settings(secret)
                self.assertNotEqual(result.returncode, 0)

    def test_strong_secret_allows_production_configuration(self):
        result = self._import_settings("a" * 64)
        self.assertEqual(result.returncode, 0, result.stderr)


class PaymentDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "payments.sqlite3")
        self._initialize_database()

        def connect():
            connection = sqlite3.connect(self.db_path, timeout=15)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            return connection

        self.connection_factory = connect
        self.patch_connection = patch("services.payment_service.get_connection", side_effect=connect)
        self.patch_connection.start()

    def tearDown(self):
        self.patch_connection.stop()
        self.temp_dir.cleanup()

    def _initialize_database(self):
        connection = sqlite3.connect(self.db_path)
        connection.executescript("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                email TEXT NOT NULL
            );
            CREATE TABLE wallets (
                id INTEGER PRIMARY KEY,
                user_id INTEGER UNIQUE NOT NULL,
                balance_kobo INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE payments (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                reference TEXT UNIQUE NOT NULL,
                provider TEXT NOT NULL,
                provider_reference TEXT,
                amount_kobo INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                payment_method TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE wallet_transactions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                amount_kobo INTEGER NOT NULL,
                reference TEXT UNIQUE NOT NULL,
                description TEXT,
                status TEXT NOT NULL
            );
            INSERT INTO users(id, email) VALUES (1, 'test@example.com');
            INSERT INTO wallets(id, user_id, balance_kobo) VALUES (1, 1, 0);
            INSERT INTO payments(
                id, user_id, reference, provider, amount_kobo, status, payment_method
            ) VALUES (1, 1, 'PAY-TEST-001', 'paystack', 25000, 'PENDING', 'online');
        """)
        connection.commit()
        connection.close()

    def _read_state(self):
        connection = self.connection_factory()
        try:
            balance = connection.execute(
                "SELECT balance_kobo FROM wallets WHERE user_id = 1"
            ).fetchone()[0]
            payment_status = connection.execute(
                "SELECT status FROM payments WHERE reference = 'PAY-TEST-001'"
            ).fetchone()[0]
            ledger = connection.execute(
                "SELECT COUNT(*) FROM wallet_transactions WHERE reference = 'FUND-PAY-TEST-001'"
            ).fetchone()[0]
            return balance, payment_status, ledger
        finally:
            connection.close()

    def test_verified_payment_credits_wallet_once(self):
        first = PaymentService.complete_verified_payment(
            "PAY-TEST-001", "provider-tx-1", 25000
        )
        second = PaymentService.complete_verified_payment(
            "PAY-TEST-001", "provider-tx-1", 25000
        )
        self.assertEqual(first["status"], "success")
        self.assertEqual(second["status"], "already_processed")
        self.assertEqual(self._read_state(), (25000, "SUCCESS", 1))

    def test_amount_mismatch_does_not_credit_wallet(self):
        with self.assertRaises(ValueError):
            PaymentService.complete_verified_payment(
                "PAY-TEST-001", "provider-tx-1", 24999
            )
        self.assertEqual(self._read_state(), (0, "PENDING", 0))

    def test_missing_verified_amount_does_not_credit_wallet(self):
        with self.assertRaises(ValueError):
            PaymentService.complete_verified_payment("PAY-TEST-001")
        self.assertEqual(self._read_state(), (0, "PENDING", 0))

    def test_non_paystack_payment_cannot_use_paystack_completion(self):
        connection = self.connection_factory()
        connection.execute(
            "UPDATE payments SET provider = 'other' WHERE reference = 'PAY-TEST-001'"
        )
        connection.commit()
        connection.close()

        with self.assertRaises(ValueError):
            PaymentService.complete_verified_payment(
                "PAY-TEST-001", "provider-tx-1", 25000
            )
        self.assertEqual(self._read_state(), (0, "PENDING", 0))

    def test_success_state_without_ledger_is_reported_as_inconsistent(self):
        connection = self.connection_factory()
        connection.execute(
            "UPDATE payments SET status = 'SUCCESS' WHERE reference = 'PAY-TEST-001'"
        )
        connection.commit()
        connection.close()

        with self.assertRaises(RuntimeError):
            PaymentService.complete_verified_payment(
                "PAY-TEST-001", "provider-tx-1", 25000
            )
        self.assertEqual(self._read_state(), (0, "SUCCESS", 0))

    def test_concurrent_duplicate_completions_never_double_credit(self):
        barrier = threading.Barrier(2)

        def complete():
            barrier.wait(timeout=5)
            try:
                return PaymentService.complete_verified_payment(
                    "PAY-TEST-001", "provider-tx-1", 25000
                )
            except sqlite3.OperationalError:
                # SQLite can reject a concurrent lock upgrade. The provider retry
                # can safely re-deliver; the invariant under test is no double credit.
                return {"status": "sqlite_contention"}

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: complete(), range(2)))

        self.assertEqual(self._read_state(), (25000, "SUCCESS", 1))
        self.assertEqual(
            sum(result.get("status") == "success" for result in results), 1
        )


class WebhookSignatureTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
        self.app.register_blueprint(webhooks_bp)
        self.client = self.app.test_client()

    def test_paystack_invalid_signature_is_rejected(self):
        body = json.dumps({
            "event": "charge.success",
            "data": {
                "reference": "PAY-TEST-001",
                "amount": 25000,
                "currency": "NGN",
                "status": "success",
            },
        }).encode()
        response = self.client.post(
            "/api/v1/webhooks/paystack",
            data=body,
            content_type="application/json",
            headers={"x-paystack-signature": "invalid"},
        )
        self.assertEqual(response.status_code, 401)

    @patch.object(PaymentService, "complete_verified_payment")
    def test_paystack_valid_signature_calls_completion(self, complete):
        complete.return_value = {"status": "success"}
        body = json.dumps({
            "event": "charge.success",
            "data": {
                "reference": "PAY-TEST-001",
                "amount": 25000,
                "currency": "NGN",
                "status": "success",
                "id": 123,
            },
        }).encode()
        signature = hmac.new(
            os.environ["PAYSTACK_SECRET_KEY"].encode(),
            body,
            hashlib.sha512,
        ).hexdigest()
        response = self.client.post(
            "/api/v1/webhooks/paystack",
            data=body,
            content_type="application/json",
            headers={"x-paystack-signature": signature},
        )
        self.assertEqual(response.status_code, 200)
        complete.assert_called_once_with(
            reference="PAY-TEST-001",
            provider_reference="123",
            provider_amount_kobo=25000,
        )


    def test_pairgate_valid_signature_is_accepted_within_timestamp_window(self):
        from routes.webhooks import order_service
        from unittest.mock import patch
        import time

        body = json.dumps({
            "event": "data.purchase",
            "reference_code": "ORD-TEST-001",
            "status": "successful",
        }).encode()
        timestamp = str(int(time.time()))
        signed_payload = timestamp.encode() + b"." + body
        signature = hmac.new(
            os.environ["PAIRGATE_WEBHOOK_SECRET"].encode(),
            signed_payload,
            hashlib.sha256,
        ).hexdigest()

        with patch.object(
            order_service,
            "process_pairgate_webhook",
            return_value={"status": "success"},
        ) as process:
            response = self.client.post(
                "/api/v1/webhooks/pairgate",
                data=body,
                content_type="application/json",
                headers={
                    "X-Pairgate-Timestamp": timestamp,
                    "X-Pairgate-Signature": signature,
                },
            )

        self.assertEqual(response.status_code, 200)
        process.assert_called_once()

    def test_pairgate_stale_signed_request_is_rejected(self):
        import time

        body = json.dumps({
            "event": "data.purchase",
            "reference_code": "ORD-TEST-001",
            "status": "successful",
        }).encode()
        timestamp = str(int(time.time()) - 3600)
        signature = hmac.new(
            os.environ["PAIRGATE_WEBHOOK_SECRET"].encode(),
            timestamp.encode() + b"." + body,
            hashlib.sha256,
        ).hexdigest()
        response = self.client.post(
            "/api/v1/webhooks/pairgate",
            data=body,
            content_type="application/json",
            headers={
                "X-Pairgate-Timestamp": timestamp,
                "X-Pairgate-Signature": signature,
            },
        )
        self.assertEqual(response.status_code, 401)

    def test_legacy_unsigned_payment_webhook_is_disabled(self):
        response = self.client.post(
            "/api/v1/webhooks/payment",
            json={"reference": "PAY-TEST-001", "status": "SUCCESS"},
        )
        self.assertEqual(response.status_code, 410)


if __name__ == "__main__":
    unittest.main()
