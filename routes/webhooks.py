import logging
import hashlib
import hmac
import time

from flask import Blueprint, request

from config.settings import settings
from services.order_service import OrderService
from services.payment_service import PaymentService
from utils.responses import success_response, error_response


logger = logging.getLogger(__name__)

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

    if settings.APP_ENV == "production":

        verify_signature = True

    else:

        verify_signature = (
            settings.PAIRGATE_WEBHOOK_VERIFY
        )

    if not verify_signature:

        return True

    secret = settings.PAIRGATE_WEBHOOK_SECRET

    if not secret:

        return False

    timestamp = request.headers.get(
        "X-Pairgate-Timestamp"
    )

    provided_signature = request.headers.get(
        "X-Pairgate-Signature"
    )

    if not timestamp or not provided_signature:

        return False

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

    raw_payload = request.get_data()

    signed_payload = (
        timestamp.encode("utf-8")
        + b"."
        + raw_payload
    )

    expected_signature = hmac.new(
        secret.encode("utf-8"),
        signed_payload,
        hashlib.sha256
    ).hexdigest()

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

    if not verify_pairgate_signature():

        return error_response(
            "Invalid Pairgate webhook signature.",
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

    if event != "data.purchase":

        return error_response(
            "Unsupported Pairgate event.",
            400
        )

    reference = data.get(
        "reference_code"
    )

    if not reference:

        return error_response(
            "Pairgate reference_code is required.",
            400
        )

    status = str(
        data.get(
            "status",
            ""
        )
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

    supplier_reference = str(
        reference
    )

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

    except ValueError:
        return error_response("Webhook could not be applied to the referenced order.", 404)

    except Exception:
        logger.exception("Pairgate webhook processing failed.")
        return error_response("Could not process Pairgate webhook.", 500)


# ==========================================================
# GENERIC PAYMENT WEBHOOK
# ==========================================================

@webhooks_bp.route(
    "/payment",
    methods=["POST"]
)
def payment_webhook():
    # No provider authentication contract exists for this legacy generic route.
    return error_response("This payment webhook endpoint is disabled.", 410)


# ==========================================================
# PAYSTACK WEBHOOK
# ==========================================================

@webhooks_bp.route(
    "/paystack",
    methods=["POST"]
)
def paystack_webhook():

    raw_payload = request.get_data()

    signature = request.headers.get(
        "x-paystack-signature"
    )

    secret_key = settings.PAYSTACK_SECRET_KEY
    if not secret_key:
        logger.error("Paystack webhook received without configured secret.")
        return error_response("Payment webhook is not configured.", 503)
    if not signature:
        return error_response("Paystack webhook signature is missing.", 401)

    expected_signature = hmac.new(
        secret_key.encode("utf-8"),
        raw_payload,
        hashlib.sha512
    ).hexdigest()

    if not hmac.compare_digest(
        expected_signature,
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

    # ------------------------------------------------------
    # We currently only need successful Paystack charges
    # for wallet funding.
    #
    # Other Paystack events can safely be acknowledged
    # without changing the wallet.
    # ------------------------------------------------------

    if event != "charge.success":

        return success_response(
            message=(
                "Webhook received. "
                "No wallet funding action was required."
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
            "Invalid Paystack transaction payload.",
            400
        )

    reference = transaction.get(
        "reference"
    )

    amount = transaction.get(
        "amount"
    )

    provider_transaction_id = transaction.get(
        "id"
    )

    if not isinstance(reference, str) or not reference.strip():
        return error_response("Payment reference is missing.", 400)

    if amount is None:

        return error_response(
            "Payment amount is missing.",
            400
        )

    if isinstance(amount, bool):
        return error_response("Invalid Paystack payment amount.", 400)

    try:
        amount_kobo = int(amount)

    except (
        TypeError,
        ValueError
    ):

        return error_response(
            "Invalid Paystack payment amount.",
            400
        )

    if str(amount).strip() != str(amount_kobo) or amount_kobo <= 0:
        return error_response("Invalid Paystack payment amount.", 400)

    if (
        str(transaction.get("currency", "")).upper() != "NGN"
        or str(transaction.get("status", "")).lower() != "success"
    ):
        return error_response("Paystack transaction is not a successful NGN payment.", 400)

    try:

        result = (
            PaymentService
            .complete_verified_payment(
                reference=reference,
                provider_reference=(
                    str(provider_transaction_id)
                    if provider_transaction_id
                    else None
                ),
                provider_amount_kobo=
                    amount_kobo
            )
        )

        return success_response(
            data=result,
            message=(
                "Paystack payment webhook processed."
            )
        )

    except ValueError:
        return error_response("Payment could not be verified against the payment record.", 400)

    except Exception:

        return error_response(
            "Could not process Paystack webhook.",
            500
    )
