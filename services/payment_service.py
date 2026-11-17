from database.database import get_connection
from services.payment_provider_service import (
    PaymentProviderService
)
from utils.references import generate_reference


class PaymentService:

    provider_service = None

    @staticmethod
    def get_provider(provider_name="paystack"):
        # Defer provider construction until a payment operation is requested.
        # This lets the application and non-payment routes start without
        # payment credentials configured.
        if PaymentService.provider_service is None:
            PaymentService.provider_service = PaymentProviderService()

        return PaymentService.provider_service.get_provider(provider_name)

    @staticmethod
    def create_payment(
        user_id,
        amount_kobo,
        provider="paystack",
        payment_method="online"
    ):

        if amount_kobo <= 0:

            raise ValueError(
                "Payment amount must be greater than zero."
            )

        reference = generate_reference(
            "PAY"
        )

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
                "reference":
                    reference,

                "amount_kobo":
                    amount_kobo,

                "status":
                    "PENDING",

                "provider":
                    provider
            }

        except Exception:

            connection.rollback()

            raise

        finally:

            connection.close()

    @staticmethod
    def get_payment(
        reference
    ):

        connection = get_connection()

        try:

            cursor = connection.cursor()

            cursor.execute("""
                SELECT *
                FROM payments
                WHERE reference = ?
            """, (
                reference,
            ))

            payment = cursor.fetchone()

            if not payment:

                return None

            return dict(payment)

        finally:

            connection.close()

    @staticmethod
    def initialize_paystack_payment(
        user_id,
        amount_kobo,
        email,
        callback_url
    ):

        payment = (
            PaymentService.create_payment(
                user_id=user_id,
                amount_kobo=amount_kobo,
                provider="paystack",
                payment_method="online"
            )
        )

        try:
            provider = (
                PaymentService.get_provider("paystack")
            )

            result = provider.initialize_transaction(
                email=email,
                amount_kobo=amount_kobo,
                reference=payment["reference"],
                callback_url=callback_url,
                metadata={
                    "user_id": user_id,
                    "payment_reference": payment["reference"]
                }
            )
        except Exception:
            PaymentService.mark_failed_payment(
                payment["reference"],
                message="Provider initialization failed."
            )
            raise

        data = result.get(
            "data",
            {}
        )

        return {
            "payment": payment,

            "authorization_url":
                data.get(
                    "authorization_url"
                ),

            "access_code":
                data.get(
                    "access_code"
                ),

            "provider_reference":
                data.get(
                    "reference"
                )
        }

    @staticmethod
    def verify_paystack_payment(
        reference
    ):

        payment = PaymentService.get_payment(reference)

        if not payment:
            raise ValueError("Payment record not found.")

        if payment["provider"] != "paystack":
            raise ValueError("Payment provider does not match Paystack.")

        provider = PaymentService.get_provider("paystack")
        result = provider.verify_transaction(reference)
        provider_data = result.get("data") if isinstance(result, dict) else None

        if not result.get("status") or not isinstance(provider_data, dict):
            raise ValueError("Paystack could not verify this payment.")

        if str(provider_data.get("reference", "")) != str(reference):
            raise ValueError("Paystack payment reference does not match.")

        if str(provider_data.get("currency", "")).upper() != "NGN":
            raise ValueError("Paystack payment currency is not NGN.")

        return {
            "payment": payment,
            "provider_response": result
        }

    @staticmethod
    def complete_verified_payment(
        reference,
        provider_reference=None,
        provider_amount_kobo=None
    ):

        connection = get_connection()

        try:

            cursor = connection.cursor()

            cursor.execute("""
                SELECT *
                FROM payments
                WHERE reference = ?
            """, (
                reference,
            ))

            payment = cursor.fetchone()

            if not payment:

                raise ValueError(
                    "Payment record not found."
                )

            payment = dict(payment)

            if payment["status"] == "SUCCESS":

                connection.commit()

                return {
                    "status":
                        "already_processed",

                    "reference":
                        reference
                }

            if payment["status"] == "FAILED":
                raise ValueError(
                    "This payment has already failed."
                )

            if payment["provider"] != "paystack":
                raise ValueError("Payment provider does not match Paystack.")

            if provider_reference in (None, ""):
                raise ValueError("Paystack transaction ID is required.")

            if provider_amount_kobo is None:
                raise ValueError("Verified Paystack amount is required.")

            try:
                verified_amount = int(provider_amount_kobo)
            except (TypeError, ValueError):
                raise ValueError("Invalid verified Paystack amount.")

            if verified_amount != int(payment["amount_kobo"]):

                raise ValueError(
                    "Payment amount does not match "
                    "the expected wallet funding amount."
                )

            cursor.execute("""
                SELECT reference
                FROM payments
                WHERE provider = 'paystack'
                  AND provider_reference = ?
                  AND reference != ?
            """, (str(provider_reference), reference))

            if cursor.fetchone():
                raise ValueError(
                    "Paystack transaction ID has already been used."
                )

            cursor.execute("""
                UPDATE payments
                SET
                    status = 'SUCCESS',
                    provider_reference = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE
                    reference = ?
                    AND status = 'PENDING'
            """, (
                provider_reference,
                reference
            ))

            if cursor.rowcount == 0:

                cursor.execute("""
                    SELECT status
                    FROM payments
                    WHERE reference = ?
                """, (
                    reference,
                ))

                current = cursor.fetchone()

                if current and current["status"] == "SUCCESS":

                    connection.commit()

                    return {
                        "status":
                            "already_processed",

                        "reference":
                            reference
                    }

                raise ValueError(
                    "Payment could not be completed."
                )

            wallet_reference = (
                f"FUND-{reference}"
            )

            cursor.execute("""
                SELECT id
                FROM wallet_transactions
                WHERE reference = ?
            """, (
                wallet_reference,
            ))

            existing_transaction = (
                cursor.fetchone()
            )

            if not existing_transaction:

                cursor.execute("""
                    UPDATE wallets
                    SET
                        balance_kobo =
                            balance_kobo + ?,
                        updated_at =
                            CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (
                    payment["amount_kobo"],
                    payment["user_id"]
                ))

                if cursor.rowcount == 0:

                    raise ValueError(
                        "Wallet not found."
                    )

                cursor.execute("""
                    INSERT INTO wallet_transactions (
                        user_id,
                        type,
                        amount_kobo,
                        reference,
                        description,
                        status
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    payment["user_id"],
                    "CREDIT",
                    payment["amount_kobo"],
                    wallet_reference,
                    (
                        "Wallet funding via "
                        f"{payment['provider']}"
                    ),
                    "SUCCESS"
                ))

            connection.commit()

            return {
                "status":
                    "success",

                "payment_reference":
                    reference,

                "provider_reference":
                    provider_reference,

                "amount_kobo":
                    payment["amount_kobo"],

                "wallet_transaction_reference":
                    wallet_reference
            }

        except Exception:

            connection.rollback()

            raise

        finally:

            connection.close()

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
                "status":
                    "failed",

                "reference":
                    reference,

                "message":
                    message
            }

        except Exception:

            connection.rollback()

            raise

        finally:

            connection.close()
