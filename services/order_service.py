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
        phone
    ):

        # ---------------------------------
        # 1. Validate phone number
        # ---------------------------------

        phone = str(phone).strip()

        if not validate_phone(phone):

            raise ValueError(
                "Invalid Nigerian phone number. "
                "Use 11 digits beginning with 0."
            )

        # ---------------------------------
        # 2. Find the selected plan
        # ---------------------------------

        plan = self.plan_service.get_plan_by_id(
            plan_id
        )

        if not plan:

            raise ValueError(
                "The selected data plan is no longer available."
            )

        # ---------------------------------
        # 3. Determine price
        # ---------------------------------

        amount_kobo = int(
            plan["selling_price_kobo"]
        )

        if amount_kobo <= 0:

            raise ValueError(
                "This data plan has an invalid price."
            )

        # ---------------------------------
        # 4. Generate our reference
        # ---------------------------------

        reference = generate_reference(
            "ORD"
        )

        # ---------------------------------
        # 5. Create local order
        # ---------------------------------

        connection = get_connection()

        try:

            cursor = connection.cursor()

            cursor.execute("""
                INSERT INTO orders (
                    reference,
                    user_id,
                    phone,
                    network,
                    plan_id,
                    supplier,
                    supplier_plan_id,
                    amount_kobo,
                    status,
                    message
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                reference,
                user_id,
                phone,
                plan["network"],
                plan["id"],
                plan["supplier"],
                plan["supplier_plan_id"],
                amount_kobo,
                "PENDING",
                "Order created."
            ))

            connection.commit()

        except Exception:

            connection.rollback()
            raise

        finally:

            connection.close()

        # ---------------------------------
        # 6. Debit customer wallet
        # ---------------------------------

        try:

            WalletService.debit_wallet(
                user_id=user_id,
                amount_kobo=amount_kobo,
                reference=reference,
                description=(
                    f"Data purchase - "
                    f"{plan['name']}"
                )
            )

        except Exception as error:

            self._update_order(
                reference,
                "FAILED",
                str(error)
            )

            raise

        # ---------------------------------
        # 7. Mark order PROCESSING
        # ---------------------------------

        self._update_order(
            reference,
            "PROCESSING",
            "Sending data order to supplier."
        )

        # ---------------------------------
        # 8. Send to supplier
        # ---------------------------------

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

            # ---------------------------------
            # 9. Save supplier response
            # ---------------------------------

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

            # ---------------------------------
            # 10. Interpret supplier response
            # ---------------------------------

            supplier_status = str(
                supplier_response.get(
                    "status",
                    ""
                )
            ).lower()

            supplier_reference = (
                supplier_response.get(
                    "reference"
                )
                or supplier_response.get(
                    "transaction_id"
                )
                or supplier_response.get(
                    "data", {}
                ).get(
                    "reference"
                )
            )

            if supplier_status in {
                "success",
                "successful",
                "true"
            }:

                self._update_order(
                    reference=reference,
                    status="SUCCESS",
                    message=(
                        supplier_response.get(
                            "message"
                        )
                        or
                        "Data purchase successful."
                    ),
                    supplier_reference=
                        supplier_reference
                )

                return {
                    "status": "success",
                    "reference": reference,
                    "supplier_reference":
                        supplier_reference,
                    "message": (
                        supplier_response.get(
                            "message"
                        )
                        or
                        "Data purchase successful."
                    )
                }

            # If supplier says processing/pending,
            # DON'T refund yet.

            if supplier_status in {
                "pending",
                "processing"
            }:

                self._update_order(
                    reference=reference,
                    status="PROCESSING",
                    message=(
                        supplier_response.get(
                            "message"
                        )
                        or
                        "Supplier is processing the order."
                    ),
                    supplier_reference=
                        supplier_reference
                )

                return {
                    "status": "processing",
                    "reference": reference,
                    "supplier_reference":
                        supplier_reference,
                    "message": (
                        supplier_response.get(
                            "message"
                        )
                        or
                        "Order is being processed."
                    )
                }

            # ---------------------------------
            # Supplier explicitly rejected it
            # ---------------------------------

            reason = (
                supplier_response.get(
                    "message"
                )
                or
                "Supplier rejected the order."
            )

            self._refund_customer(
                user_id=user_id,
                amount_kobo=amount_kobo,
                order_reference=reference,
                plan_name=plan["name"],
                reason=reason
            )

            self._update_order(
                reference=reference,
                status="REFUNDED",
                message=reason,
                supplier_reference=
                    supplier_reference
            )

            return {
                "status": "refunded",
                "reference": reference,
                "message": (
                    "The supplier rejected the order. "
                    "Your wallet has been refunded."
                )
            }

        except Exception as error:

            # ---------------------------------
            # IMPORTANT:
            #
            # A timeout/network failure does NOT
            # automatically mean the supplier
            # rejected the purchase.
            # ---------------------------------

            self._update_order(
                reference=reference,
                status="PROCESSING",
                message=(
                    "Supplier response could not "
                    "be confirmed. Order requires "
                    "status verification."
                )
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

    def _refund_customer(
        self,
        user_id,
        amount_kobo,
        order_reference,
        plan_name,
        reason
    ):

        refund_reference = (
            f"REFUND-{order_reference}"
        )

        # Prevent duplicate refund.
        connection = get_connection()

        try:

            cursor = connection.cursor()

            cursor.execute("""
                SELECT id
                FROM wallet_transactions
                WHERE reference = ?
            """, (
                refund_reference,
            ))

            existing = cursor.fetchone()

            if existing:

                return

        finally:

            connection.close()

        WalletService.credit_wallet(
            user_id=user_id,
            amount_kobo=amount_kobo,
            reference=refund_reference,
            description=(
                f"Refund for {plan_name}. "
                f"Reason: {reason}"
            )
        )

    def _update_order(
        self,
        reference,
        status,
        message=None,
        supplier_reference=None
    ):

        connection = get_connection()

        try:

            cursor = connection.cursor()

            cursor.execute("""
                UPDATE orders
                SET
                    status = ?,
                    message = ?,
                    supplier_reference = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE reference = ?
            """, (
                status,
                message,
                supplier_reference,
                reference
            ))

            connection.commit()

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
