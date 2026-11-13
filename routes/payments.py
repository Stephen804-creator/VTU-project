import logging
from decimal import Decimal, InvalidOperation

from flask import (
    Blueprint,
    request,
    session,
    url_for
)

from services.auth_service import (
    AuthService
)

from services.payment_service import (
    PaymentService
)

from utils.responses import (
    success_response,
    error_response
)

from utils.csrf import csrf_required


logger = logging.getLogger(__name__)

payments_bp = Blueprint(
    "payments",
    __name__,
    url_prefix="/api/v1/payments"
)


@payments_bp.route(
    "/create",
    methods=["POST"]
)
@csrf_required
def create_payment():

    user_id = session.get(
        "user_id"
    )

    if not user_id:

        return error_response(
            "You must be logged in.",
            401
        )

    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return error_response("Invalid request payload.", 400)

    amount = data.get(
        "amount"
    )

    if amount is None:

        return error_response(
            "Amount is required.",
            400
        )

    try:
        amount_decimal = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError):
        return error_response("Invalid amount.", 400)

    if not amount_decimal.is_finite() or amount_decimal <= 0:
        return error_response("Amount must be greater than zero.", 400)
    if amount_decimal > Decimal("1000000"):
        return error_response("Maximum wallet funding amount is ₦1,000,000.", 400)
    if amount_decimal.as_tuple().exponent < -2:
        return error_response("Amount cannot have more than two decimal places.", 400)

    amount_kobo = int(amount_decimal * 100)

    user = (
        AuthService
        .get_user_by_id(
            user_id
        )
    )

    if not user:

        return error_response(
            "User account not found.",
            404
        )

    try:

        callback_url = url_for(
            "payments.payment_callback",
            _external=True
        )

        result = (
            PaymentService
            .initialize_paystack_payment(
                user_id=user_id,
                amount_kobo=amount_kobo,
                email=user["email"],
                callback_url=callback_url
            )
        )

        return success_response(
            data=result,
            message=(
                "Payment initialized successfully."
            )
        )

    except Exception:
        logger.exception("Could not initialize Paystack payment.")
        return error_response("Could not initialize payment. Please try again.", 500)


@payments_bp.route(
    "/callback",
    methods=["GET"]
)
def payment_callback():

    reference = request.args.get(
        "reference"
    )

    if not reference:

        return error_response(
            "Payment reference is missing.",
            400
        )

    try:

        result = (
            PaymentService
            .verify_paystack_payment(
                reference
            )
        )

        provider_response = (
            result["provider_response"]
        )

        provider_data = provider_response.get("data", {})
        if not isinstance(provider_data, dict):
            return error_response("Invalid payment verification response.", 502)

        status = str(
            provider_data.get(
                "status",
                ""
            )
        ).lower()

        provider_reference = (
            provider_data.get(
                "reference"
            )
        )

        provider_amount = (
            provider_data.get(
                "amount"
            )
        )

        if status == "success":
            if (
                provider_data.get("reference") != reference
                or str(provider_data.get("currency", "")).upper() != "NGN"
            ):
                return error_response("Payment details do not match the expected transaction.", 400)

            completed = (
                PaymentService
                .complete_verified_payment(
                    reference=reference,
                    provider_reference=provider_reference,
                    provider_amount_kobo=provider_amount
                )
            )

            return success_response(
                data=completed,
                message=(
                    "Payment verified and "
                    "wallet credited successfully."
                )
            )

        return success_response(
            data={
                "reference": reference,
                "status": status or "unknown"
            },
            message=(
                "Payment has not been confirmed as successful."
            )
        )

    except ValueError as error:

        return error_response(
            str(error),
            400
        )

    except Exception:
        logger.exception("Could not verify Paystack payment callback.")
        return error_response("Could not verify payment. Please try again.", 500)
