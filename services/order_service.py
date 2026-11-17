import json

from database.database import get_connection
from services.plan_service import PlanService
from services.supplier_service import SupplierService
from services.wallet_service import WalletService
from utils.references import generate_reference
from utils.validation import validate_phone


class OrderService:

    def __init__(self):

        self.plan_service = PlanService()
        self.supplier_service = SupplierService()

    def create_order(
        self,
        user_id,
        plan_id,
        phone,
        idempotency_key=None
    ):

        phone = str(phone).strip()
        existing_order_reference = None

        if idempotency_key is not None:
            idempotency_key = str(idempotency_key).strip()
            if not 16 <= len(idempotency_key) <= 128:
                raise ValueError("Idempotency-Key must be between 16 and 128 characters.")

            connection = get_connection()
            try:
                cursor = connection.cursor()
                cursor.execute("""
                    SELECT reference, plan_id, phone, status, message
                    FROM orders
                    WHERE user_id = ? AND idempotency_key = ?
                """, (user_id, idempotency_key))
                existing = cursor.fetchone()
                if existing:
                    existing = dict(existing)
                    if (
                        int(existing["plan_id"] or 0) != int(plan_id)
                        or existing["phone"] != phone
                    ):
                        raise ValueError(
                            "This Idempotency-Key was already used for a different order."
                        )

                    status = str(existing["status"]).upper()
                    if status != "PENDING":
                        status_map = {
                            "SUCCESS": "success",
                            "PROCESSING": "processing",
                            "REFUNDED": "refunded",
                            "FAILED": "failed"
                        }
                        return {
                            "status": status_map.get(status, "processing"),
                            "reference": existing["reference"],
                            "message": existing["message"] or "This order was already submitted."
                        }

                    # A PENDING order has not yet been submitted to the supplier.
                    # Reuse its reference so wallet debit remains idempotent.
                    existing_order_reference = existing["reference"]
            finally:
                connection.close()

        if not validate_phone(phone):

            raise ValueError(
                "Invalid Nigerian phone number. "
                "Use 11 digits beginning with 0."
            )

        plan = self.plan_service.get_plan_by_id(
            plan_id
        )

        if not plan:

            raise ValueError(
                "The selected data plan is no longer available."
            )

        amount_kobo = int(
            plan["selling_price_kobo"]
        )

        if amount_kobo <= 0:

            raise ValueError(
                "This data plan has an invalid price."
            )

        reference = existing_order_reference or generate_reference(
            "ORD"
        )

        connection = get_connection()

        try:

            cursor = connection.cursor()

            if idempotency_key and not existing_order_reference:
                cursor.execute("""
                    INSERT OR IGNORE INTO orders (
                        reference, user_id, phone, network, plan_id,
                        supplier, supplier_plan_id, amount_kobo,
                        status, message, idempotency_key
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    reference, user_id, phone, plan["network"],
                    plan["id"], plan["supplier"], plan["supplier_plan_id"],
                    amount_kobo, "PENDING", "Order created.", idempotency_key
                ))

                if cursor.rowcount == 0:
                    cursor.execute("""
                        SELECT reference, plan_id, phone, status, message
                        FROM orders
                        WHERE user_id = ? AND idempotency_key = ?
                    """, (user_id, idempotency_key))
                    existing = cursor.fetchone()
                    if not existing:
                        raise RuntimeError("Order idempotency conflict could not be resolved.")
                    existing = dict(existing)
                    if (
                        int(existing["plan_id"] or 0) != int(plan_id)
                        or existing["phone"] != phone
                    ):
                        raise ValueError(
                            "This Idempotency-Key was already used for a different order."
                        )
                    connection.commit()
                    status = str(existing["status"]).upper()
                    status_map = {
                        "SUCCESS": "success",
                        "PENDING": "processing",
                        "PROCESSING": "processing",
                        "REFUNDED": "refunded",
                        "FAILED": "failed"
                    }
                    return {
                        "status": status_map.get(status, "processing"),
                        "reference": existing["reference"],
                        "message": existing["message"] or "This order was already submitted."
                    }
            elif not idempotency_key:
                cursor.execute("""
                    INSERT INTO orders (
                        reference, user_id, phone, network, plan_id,
                        supplier, supplier_plan_id, amount_kobo, status, message
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    reference, user_id, phone, plan["network"], plan["id"],
                    plan["supplier"], plan["supplier_plan_id"], amount_kobo,
                    "PENDING", "Order created."
                ))

            connection.commit()

        except Exception:

            connection.rollback()
            raise

        finally:

            connection.close()

        # The order row is persisted before wallet debit. If a process stops
        # between those operations, an idempotent retry can safely resume it.
        connection = get_connection()
        try:
            existing_debit = connection.execute(
                "SELECT id FROM wallet_transactions WHERE reference = ?",
                (reference,)
            ).fetchone()
        finally:
            connection.close()

        if not existing_debit:
            try:
                WalletService.debit_wallet(
                    user_id=user_id,
                    amount_kobo=amount_kobo,
                    reference=reference,
                    description=f"Data purchase - {plan['name']}"
                )
            except Exception as error:
                # A concurrent retry may have completed the same debit.
                connection = get_connection()
                try:
                    existing_debit = connection.execute(
                        "SELECT id FROM wallet_transactions WHERE reference = ?",
                        (reference,)
                    ).fetchone()
                finally:
                    connection.close()

                if not existing_debit:
                    self._update_order(
                        reference,
                        "FAILED",
                        str(error),
                        expected_status="PENDING"
                    )
                    raise

        # Claim the order before calling the supplier. Only one retry may
        # move PENDING -> PROCESSING and submit the purchase request.
        claimed = self._update_order(
            reference,
            "PROCESSING",
            "Sending data order to supplier.",
            expected_status="PENDING"
        )
        if not claimed:
            current = self.get_order_by_reference(reference)
            current_status = str(current["status"]).upper() if current else "PROCESSING"
            status_map = {
                "SUCCESS": "success",
                "PROCESSING": "processing",
                "REFUNDED": "refunded",
                "FAILED": "failed",
                "PENDING": "processing"
            }
            return {
                "status": status_map.get(current_status, "processing"),
                "reference": reference,
                "message": (
                    current.get("message")
                    if current
                    else "This order is already being processed."
                ) or "This order is already being processed."
            }

        try:

            supplier = (
                self.supplier_service.get_supplier(
                    plan["supplier"]
                )
            )

            supplier_response = (
                supplier.purchase_data(
                    provider=plan["network"],
                    plan_id=plan["supplier_plan_id"],
                    recipient=phone,
                    reference=reference
                )
            )

            self._save_supplier_log(
                supplier=plan["supplier"],
                operation="purchase",
                reference=reference,
                request_data={
                    "provider": plan["network"],
                    "plan_id":
                        plan["supplier_plan_id"],
                    "recipient": phone,
                    "reference": reference
                },
                response_data=supplier_response
            )

            supplier_status = str(
                supplier_response.get(
                    "status",
                    ""
                )
            ).lower()

            supplier_data = supplier_response.get(
                "data",
                {}
            )

            if not isinstance(
                supplier_data,
                dict
            ):
                supplier_data = {}

            supplier_reference = (
                supplier_response.get(
                    "reference_code"
                )
                or
                supplier_response.get(
                    "reference"
                )
                or
                supplier_response.get(
                    "transaction_id"
                )
                or
                supplier_data.get(
                    "reference_code"
                )
                or
                supplier_data.get(
                    "reference"
                )
            )

            if supplier_status in {
                "success",
                "successful",
                "true"
            }:

                success_message = (
                    supplier_response.get("message")
                    or supplier_data.get("message")
                    or "Data purchase successful."
                )
                transition = self.process_pairgate_webhook(
                    reference=reference,
                    status="successful",
                    message=success_message,
                    supplier_reference=supplier_reference
                )
                if transition.get("order_status") == "SUCCESS":
                    return {
                        "status": "success",
                        "reference": reference,
                        "supplier_reference": supplier_reference,
                        "message": success_message
                    }
                return {
                    "status": "processing",
                    "reference": reference,
                    "message": "The order status changed while the supplier response was being processed. It is being reconciled."
                }

            if supplier_status in {
                "pending",
                "processing"
            }:

                pending_message = (
                    supplier_response.get("message")
                    or supplier_data.get("message")
                    or "Supplier is processing the order."
                )
                self._update_order(
                    reference=reference,
                    status="PROCESSING",
                    message=pending_message,
                    supplier_reference=supplier_reference,
                    expected_status="PROCESSING"
                )
                current = self.get_order_by_reference(reference)
                current_status = str(current["status"]).upper() if current else "PROCESSING"
                if current_status == "SUCCESS":
                    return {
                        "status": "success",
                        "reference": reference,
                        "supplier_reference": supplier_reference,
                        "message": "Data purchase successful."
                    }
                if current_status == "REFUNDED":
                    return {
                        "status": "refunded",
                        "reference": reference,
                        "message": "The supplier rejected the order. Your wallet has been refunded."
                    }
                return {
                    "status": "processing",
                    "reference": reference,
                    "supplier_reference": supplier_reference,
                    "message": pending_message
                }

            reason = (
                supplier_response.get(
                    "message"
                )
                or
                supplier_data.get(
                    "message"
                )
                or
                "Supplier rejected the order."
            )

            transition = self.process_pairgate_webhook(
                reference=reference,
                status="failed",
                message=reason,
                supplier_reference=supplier_reference
            )

            if transition.get("order_status") == "SUCCESS":
                return {
                    "status": "success",
                    "reference": reference,
                    "supplier_reference": supplier_reference,
                    "message": "The supplier confirmed the order as successful."
                }

            if transition.get("order_status") == "REFUNDED":
                return {
                    "status": "refunded",
                    "reference": reference,
                    "message": (
                        "The supplier rejected the order. "
                        "Your wallet has been refunded."
                    )
                }

            return {
                "status": "processing",
                "reference": reference,
                "message": (
                    "The supplier response conflicts with a concurrent status update. "
                    "The order is being reconciled."
                )
            }

        except Exception as error:

            self._update_order(
                reference=reference,
                status="PROCESSING",
                message=(
                    "Supplier response could not "
                    "be confirmed. Order requires "
                    "status verification."
                ),
                expected_status="PROCESSING"
            )

            self._save_supplier_log(
                supplier=plan["supplier"],
                operation="purchase_error",
                reference=reference,
                request_data={
                    "provider": plan["network"],
                    "plan_id":
                        plan["supplier_plan_id"],
                    "recipient": phone,
                    "reference": reference
                },
                response_data={
                    "error": str(error)
                }
            )

            return {
                "status": "processing",
                "reference": reference,
                "message": (
                    "Your order was submitted but "
                    "the supplier response could not "
                    "yet be confirmed."
                )
            }

    # ==========================================================
    # PAIRGATE WEBHOOK HANDLER
    # ==========================================================

    def process_pairgate_webhook(
        self,
        reference,
        status,
        message=None,
        supplier_reference=None
    ):
        status = str(status or "").strip().lower()
        if status not in {"successful", "failed"}:
            raise ValueError("Unsupported Pairgate webhook status.")

        connection = get_connection()
        try:
            cursor = connection.cursor()
            cursor.execute("BEGIN IMMEDIATE")

            cursor.execute("""
                SELECT
                    o.*,
                    d.name AS plan_name
                FROM orders o
                LEFT JOIN data_plans d ON o.plan_id = d.id
                WHERE o.reference = ?
            """, (reference,))
            row = cursor.fetchone()

            if not row:
                raise ValueError("Order not found.")

            order = dict(row)
            current_status = str(order["status"]).upper()

            if current_status == "SUCCESS":
                connection.commit()
                return {
                    "status": "already_processed" if status == "successful" else "ignored",
                    "reference": reference,
                    "order_status": "SUCCESS"
                }

            if current_status == "REFUNDED":
                connection.commit()
                return {
                    "status": "already_processed" if status == "failed" else "ignored",
                    "reference": reference,
                    "order_status": "REFUNDED",
                    "message": "Order was already refunded."
                }

            if current_status != "PROCESSING":
                connection.commit()
                return {
                    "status": "ignored",
                    "reference": reference,
                    "order_status": current_status,
                    "message": "Order is not in a state that accepts supplier callbacks."
                }

            if status == "successful":
                cursor.execute("""
                    UPDATE orders
                    SET status = 'SUCCESS',
                        message = ?,
                        supplier_reference = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE reference = ? AND status = 'PROCESSING'
                """, (
                    message or "Data purchase completed.",
                    supplier_reference,
                    reference
                ))

                if cursor.rowcount != 1:
                    raise ValueError("Order status changed before callback processing.")

                connection.commit()
                return {
                    "status": "success",
                    "reference": reference,
                    "order_status": "SUCCESS"
                }

            user_id = order["user_id"]
            amount_kobo = int(order["amount_kobo"])
            if not user_id or amount_kobo <= 0:
                raise ValueError("Order cannot be refunded because its user or amount is invalid.")

            refund_reference = f"REFUND-{reference}"
            cursor.execute("""
                SELECT id
                FROM wallet_transactions
                WHERE reference = ?
            """, (refund_reference,))
            existing_refund = cursor.fetchone()

            if not existing_refund:
                cursor.execute("""
                    UPDATE wallets
                    SET balance_kobo = balance_kobo + ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (amount_kobo, user_id))

                if cursor.rowcount != 1:
                    raise ValueError("Wallet not found for refund.")

                cursor.execute("""
                    INSERT INTO wallet_transactions (
                        user_id, type, amount_kobo, reference,
                        description, status
                    )
                    VALUES (?, 'CREDIT', ?, ?, ?, 'SUCCESS')
                """, (
                    user_id,
                    amount_kobo,
                    refund_reference,
                    (
                        f"Refund for {order.get('plan_name') or 'data purchase'}. "
                        f"Reason: {message or 'Pairgate marked the transaction as failed.'}"
                    )
                ))

            cursor.execute("""
                UPDATE orders
                SET status = 'REFUNDED',
                    message = ?,
                    supplier_reference = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE reference = ? AND status = 'PROCESSING'
            """, (
                message or "Pairgate marked the transaction as failed. Wallet refunded.",
                supplier_reference,
                reference
            ))

            if cursor.rowcount != 1:
                raise ValueError("Order status changed before refund completion.")

            connection.commit()
            return {
                "status": "refunded",
                "reference": reference,
                "order_status": "REFUNDED",
                "refund": {
                    "status": "already_refunded" if existing_refund else "refunded",
                    "reference": refund_reference,
                    "amount_kobo": amount_kobo
                }
            }

        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    # ==========================================================
    # REFUND
    # ==========================================================

    def _refund_customer(
        self,
        user_id,
        amount_kobo,
        order_reference,
        plan_name,
        reason
    ):

        if not user_id or int(amount_kobo) <= 0:
            raise ValueError("A valid user and positive refund amount are required.")

        refund_reference = f"REFUND-{order_reference}"
        connection = get_connection()

        try:
            cursor = connection.cursor()
            cursor.execute("BEGIN IMMEDIATE")

            cursor.execute("""
                SELECT id
                FROM wallet_transactions
                WHERE reference = ?
            """, (refund_reference,))

            if cursor.fetchone():
                connection.commit()
                return {
                    "status": "already_refunded",
                    "reference": refund_reference
                }

            cursor.execute("""
                UPDATE wallets
                SET
                    balance_kobo = balance_kobo + ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (int(amount_kobo), user_id))

            if cursor.rowcount != 1:
                raise ValueError("Wallet not found for refund.")

            cursor.execute("""
                INSERT INTO wallet_transactions (
                    user_id,
                    type,
                    amount_kobo,
                    reference,
                    description,
                    status
                )
                VALUES (?, 'CREDIT', ?, ?, ?, 'SUCCESS')
            """, (
                user_id,
                int(amount_kobo),
                refund_reference,
                f"Refund for {plan_name}. Reason: {reason}"
            ))

            connection.commit()

            return {
                "status": "refunded",
                "reference": refund_reference,
                "amount_kobo": int(amount_kobo)
            }

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

    # ==========================================================
    # DATABASE HELPERS
    # ==========================================================

    def _update_order(
        self,
        reference,
        status,
        message=None,
        supplier_reference=None,
        expected_status=None
    ):

        connection = get_connection()

        try:
            cursor = connection.cursor()
            query = """
                UPDATE orders
                SET
                    status = ?,
                    message = ?,
                    supplier_reference = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE reference = ?
            """
            parameters = [status, message, supplier_reference, reference]
            if expected_status is not None:
                query += " AND status = ?"
                parameters.append(expected_status)

            cursor.execute(query, parameters)
            updated = cursor.rowcount == 1
            connection.commit()
            return updated

        finally:
            connection.close()

    def _save_supplier_log(
        self,
        supplier,
        operation,
        reference,
        request_data,
        response_data
    ):

        connection = get_connection()

        try:

            cursor = connection.cursor()

            cursor.execute("""
                INSERT INTO supplier_logs (
                    supplier,
                    operation,
                    reference,
                    request_data,
                    response_data
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                supplier,
                operation,
                reference,
                json.dumps(request_data),
                json.dumps(response_data)
            ))

            connection.commit()

        finally:

            connection.close()

    def get_order_by_reference(
        self,
        reference
    ):

        connection = get_connection()

        try:

            cursor = connection.cursor()

            cursor.execute("""
                SELECT
                    o.*,
                    d.name AS plan_name,
                    d.data_amount,
                    d.validity
                FROM orders o
                LEFT JOIN data_plans d
                    ON o.plan_id = d.id
                WHERE o.reference = ?
            """, (
                reference,
            ))

            order = cursor.fetchone()

            if not order:
                return None

            return dict(order)

        finally:

            connection.close()

    def get_order(
        self,
        user_id,
        reference
    ):

        connection = get_connection()

        try:

            cursor = connection.cursor()

            cursor.execute("""
                SELECT
                    o.*,
                    d.name AS plan_name,
                    d.data_amount,
                    d.validity
                FROM orders o
                LEFT JOIN data_plans d
                    ON o.plan_id = d.id
                WHERE
                    o.reference = ?
                    AND o.user_id = ?
            """, (
                reference,
                user_id
            ))

            order = cursor.fetchone()

            if not order:
                return None

            return dict(order)

        finally:

            connection.close()

    def get_orders(
        self,
        user_id,
        limit=50
    ):

        connection = get_connection()

        try:

            cursor = connection.cursor()

            cursor.execute("""
                SELECT
                    o.*,
                    d.name AS plan_name,
                    d.data_amount,
                    d.validity
                FROM orders o
                LEFT JOIN data_plans d
                    ON o.plan_id = d.id
                WHERE o.user_id = ?
                ORDER BY o.id DESC
                LIMIT ?
            """, (
                user_id,
                limit
            ))

            return [
                dict(row)
                for row in cursor.fetchall()
            ]

        finally:

            connection.close()
