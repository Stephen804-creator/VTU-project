import hashlib
import hmac
import time

from flask import Blueprint, request

from config.settings import settings
from services.order_service import OrderService
from services.payment_service import PaymentService
from utils.responses import success_response, error_response


webhooks_bp = Blueprint(
    "webhooks",
    __name__,
    url_prefix="/api/v1/webhooks"
)


order_service = OrderService()


# ==========================================================
# PAIRGATE SIGNATURE VERIFICATION
# ==========================================================

def verify_pairgate_signature():

    # Production must always verify signatures.
    if settings.APP_ENV == "production":

        verify_signature = True

    else:

        verify_signature = (
            settings.PAIRGATE_WEBHOOK_VERIFY
        )

    if not verify_signature:

        return True

    secret = (
        settings.PAIRGATE_WEBHOOK_SECRET
    )

    if not secret:

        return False

    # ------------------------------------------------------
    # Development override
    # ------------------------------------------------------

    if not settings.PAIRGATE_WEBHOOK_VERIFY:

        return True

    # ------------------------------------------------------
    # Secret must exist when verification is enabled
    # ------------------------------------------------------

    secret = settings.PAIRGATE_WEBHOOK_SECRET

    if not secret:

        return False

    # ------------------------------------------------------
    # Read Pairgate security headers
    # ------------------------------------------------------

    timestamp = request.headers.get(
        "X-Pairgate-Timestamp"
    )

    provided_signature = request.headers.get(
        "X-Pairgate-Signature"
    )

    if not timestamp or not provided_signature:

        return False

    # ------------------------------------------------------
    # Validate timestamp
    # ------------------------------------------------------

    try:

        timestamp_integer = int(
            timestamp
        )

    except (TypeError, ValueError):

        return False

    current_time = int(
        time.time()
    )

    if abs(
        current_time - timestamp_integer
    ) > settings.PAIRGATE_WEBHOOK_TOLERANCE_SECONDS:

        return False

    # ------------------------------------------------------
    # IMPORTANT:
    #
    # Use the RAW JSON request body.
    #
    # Do not use request.json here because Pairgate signs
    # the exact raw JSON payload.
    # ------------------------------------------------------

    raw_payload = request.get_data()

    signed_payload = (
        timestamp.encode("utf-8")
        + b"."
        + raw_payload
    )

    # ------------------------------------------------------
    # Calculate expected HMAC SHA-256 signature
    # ------------------------------------------------------

    expected_signature = hmac.new(
        secret.encode("utf-8"),
        signed_payload,
        hashlib.sha256
    ).hexdigest()

    # ------------------------------------------------------
    # Constant-time comparison
    # ------------------------------------------------------

    return hmac.compare_digest(
        expected_signature,
        provided_signature
    )


# ==========================================================
# PAIRGATE WEBHOOK
# ==========================================================

@webhooks_bp.route(
    "/pairgate",
    methods=["POST"]
)
def pairgate_webhook():

    # ------------------------------------------------------
    # Verify Pairgate signature BEFORE processing data
    # ------------------------------------------------------

    if not verify_pairgate_signature():

        return error_response(
            "Invalid Pairgate webhook signature.",
            401
        )

    # ------------------------------------------------------
    # Parse JSON
    # ------------------------------------------------------

    data = request.get_json(
        silent=True
    )

    if not isinstance(
        data,
        dict
    ):

        return error_response(
            "Invalid webhook payload.",
            400
        )

    # ------------------------------------------------------
    # Confirm this is a data purchase event
    # ------------------------------------------------------

    event = str(
        data.get("event", "")
    ).strip().lower()

    if event != "data.purchase":

        return error_response(
            "Unsupported Pairgate event.",
            400
        )

    # ------------------------------------------------------
    # Pairgate calls this reference_code
    # ------------------------------------------------------

    reference = data.get(
        "reference_code"
    )

    if not reference:

        return error_response(
            "Pairgate reference_code is required.",
            400
        )

    # ------------------------------------------------------
    # Final status
    # ------------------------------------------------------

    status = str(
        data.get("status", "")
    ).strip().lower()

    if status not in {
        "successful",
        "failed"
    }:

        return error_response(
            "Unsupported Pairgate transaction status.",
            400
        )

    message = data.get(
        "message"
    )

    # Pairgate's reference_code is retained as the
    # supplier reference in our order record.
    supplier_reference = str(
        reference
    )

    # ------------------------------------------------------
    # Process the order
    # ------------------------------------------------------

    try:

        result = (
            order_service
            .process_pairgate_webhook(
                reference=reference,
                status=status,
                message=message,
                supplier_reference=
                    supplier_reference
            )
        )

        return success_response(
            data=result,
            message="Pairgate webhook processed."
        )

    except ValueError as error:

        # An unknown reference is not a valid Subscribe Me
        # order. We return 404 so it is visible in logs and
        # Pairgate can retry if appropriate.
        return error_response(
            str(error),
            404
        )

    except Exception:

        # Do not expose internal database/payment details
        # to the external supplier.
        return error_response(
            "Could not process Pairgate webhook.",
            500
        )


# ==========================================================
# PAYMENT PROVIDER WEBHOOK
# ==========================================================
#
# This is NOT Pairgate.
#
# This endpoint is reserved for the provider we will use
# later for customer wallet funding.
# ==========================================================

@webhooks_bp.route(
    "/payment",
    methods=["POST"]
)
def payment_webhook():

    data = request.get_json(
        silent=True
    ) or {}

    reference = data.get(
        "reference"
    )

    status = str(
        data.get(
            "status",
            ""
        )
    ).upper()

    provider_reference = data.get(
        "provider_reference"
    )

    if not reference:

        return error_response(
            "Payment reference is required.",
            400
        )

    if status == "SUCCESS":

        try:

            result = (
                PaymentService
                .mark_successful_payment(
                    reference=reference,
                    provider_reference=
                        provider_reference
                )
            )

            return success_response(
                data=result,
                message="Payment processed."
            )

        except ValueError as error:

            return error_response(
                str(error),
                400
            )

        except Exception:

            return error_response(
                "Payment processing failed.",
                500
            )

    if status == "FAILED":

        result = (
            PaymentService.mark_failed_payment(
                reference=reference
            )
        )

        return success_response(
            data=result,
            message="Payment marked as failed."
        )

    return error_response(
        "Unsupported payment status.",
        400
    )
    
payment_provider_service = (
    PaymentProviderService()
)

@webhooks_bp.route(
    "/paystack",
    methods=["POST"]
)
def paystack_webhook():

    raw_payload = request.get_data()

    signature = request.headers.get(
        "x-paystack-signature"
    )

    try:

        provider = (
            payment_provider_service
            .get_provider("paystack")
        )

    except Exception:

        return error_response(
            "Payment provider is not configured.",
            500
        )

    if not provider.verify_webhook_signature(
        raw_payload,
        signature
    ):

        return error_response(
            "Invalid Paystack webhook signature.",
            401
        )

    data = request.get_json(
        silent=True
    )

    if not isinstance(
        data,
        dict
    ):

        return error_response(
            "Invalid webhook payload.",
            400
        )

    event = str(
        data.get(
            "event",
            ""
        )
    ).strip().lower()

    if event != "charge.success":

        return success_response(
            message=(
                "Webhook received but no wallet "
                "funding action was required."
            )
        )

    transaction = data.get(
        "data"
    )

    if not isinstance(
        transaction,
        dict
    ):

        return error_response(
            "Invalid transaction payload.",
            400
        )

    reference = transaction.get(
        "reference"
    )

    amount = transaction.get(
        "amount"
    )

    if not reference:

        return error_response(
            "Payment reference is missing.",
            400
        )

    if amount is None:

        return error_response(
            "Payment amount is missing.",
            400
        )

    try:

        result = (
            PaymentService
            .complete_verified_payment(
                reference=reference,
                provider_reference=
                    str(
                        transaction.get(
                            "id"
                        )
                    )
                    if transaction.get("id")
                    else None,
                provider_amount_kobo=
                    int(amount)
            )
        )

        return success_response(
            data=result,
            message=(
                "Paystack payment webhook processed."
            )
        )

    except ValueError as error:

        return error_response(
            str(error),
            400
        )

    except Exception:

        return error_response(
            "Could not process Paystack webhook.",
            500
        )
