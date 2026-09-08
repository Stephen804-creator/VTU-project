from database.database import get_connection
from services.wallet_service import WalletService
from utils.references import generate_reference


class PaymentService:

    @staticmethod
    def create_payment(
        user_id,
        amount_kobo,
        provider="pending",
        payment_method="unknown"
    ):

        if amount_kobo <= 0:
            raise ValueError(
                "Payment amount must be greater than zero."
            )

        reference = generate_reference("PAY")

        connection = get_connection()

        try:
            cursor = connection.cursor()

            cursor.execute("""
                INSERT INTO payments (
                    user_id,
                    reference,
                    provider,
                    amount_kobo,
                    status,
                    payment_method
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                reference,
                provider,
                amount_kobo,
                "PENDING",
                payment_method
            ))

            connection.commit()

            return {
                "reference": reference,
                "amount_kobo": amount_kobo,
                "status": "PENDING"
            }

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

    @staticmethod
    def get_payment(reference):

        connection = get_connection()

        try:
            cursor = connection.cursor()

            cursor.execute("""
                SELECT *
                FROM payments
                WHERE reference = ?
            """, (reference,))

            payment = cursor.fetchone()

            if not payment:
                return None

            return dict(payment)

        finally:
            connection.close()

    @staticmethod
    def mark_successful_payment(
        reference,
        provider_reference=None
    ):

        connection = get_connection()

        try:
            cursor = connection.cursor()

            # --------------------------------
            # Find payment
            # --------------------------------

            cursor.execute("""
                SELECT *
                FROM payments
                WHERE reference = ?
            """, (reference,))

            payment = cursor.fetchone()

            if not payment:
                raise ValueError(
                    "Payment record not found."
                )

            payment = dict(payment)

            # --------------------------------
            # Idempotency protection
            # --------------------------------
            #
            # If the webhook arrives twice,
            # don't credit the wallet twice.
            #

            if payment["status"] == "SUCCESS":

                return {
                    "status": "already_processed",
                    "reference": reference
                }

            if payment["status"] == "FAILED":

                raise ValueError(
                    "This payment has already failed."
                )

            # --------------------------------
            # Mark payment successful
            # --------------------------------

            cursor.execute("""
                UPDATE payments
                SET
                    status = 'SUCCESS',
                    provider_reference = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE reference = ?
            """, (
                provider_reference,
                reference
            ))

            connection.commit()

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

        # --------------------------------
        # Credit customer wallet
        # --------------------------------

        wallet_transaction = (
            WalletService.credit_wallet(
                user_id=payment["user_id"],
                amount_kobo=payment["amount_kobo"],
                reference=f"FUND-{reference}",
                description=(
                    f"Wallet funding via "
                    f"{payment['provider']}"
                )
            )
        )

        return {
            "status": "success",
            "payment_reference": reference,
            "provider_reference":
                provider_reference,
            "wallet_transaction":
                wallet_transaction
        }

    @staticmethod
    def mark_failed_payment(
        reference,
        message="Payment failed."
    ):

        connection = get_connection()

        try:

            cursor = connection.cursor()

            cursor.execute("""
                UPDATE payments
                SET
                    status = 'FAILED',
                    updated_at = CURRENT_TIMESTAMP
                WHERE
                    reference = ?
                    AND status = 'PENDING'
            """, (
                reference,
            ))

            connection.commit()

            return {
                "status": "failed",
                "reference": reference,
                "message": message
            }

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()
