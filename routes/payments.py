import logging
from decimal import Decimal, InvalidOperation

from flask import Blueprint, request, session, url_for

from services.auth_service import AuthService
from services.payment_service import PaymentService
from utils.responses import success_response, error_response
from utils.csrf import csrf_required


logger = logging.getLogger(__name__)

payments_bp = Blueprint(
    "payments",
    __name__,
    url_prefix="/api/v1/payments"
)


def naira_to_kobo(value):
    """Convert a user-supplied naira amount without binary float arithmetic."""
    if isinstance(value, bool) or value is None:
        raise ValueError("Invalid amount.")

    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Invalid amount.") from None

    if not amount.is_finite():
        raise ValueError("Invalid amount.")

    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")
    if amount > Decimal("1000000"):
        raise ValueError("Maximum wallet funding amount is ₦1,000,000.")

    # Enforce the input scale, including trailing fractional zeroes.
    if amount.as_tuple().exponent < -2:
        raise ValueError("Amount cannot have more than two decimal places.")

    return int(amount * 100)


@payments_bp.route("/create", methods=["POST"])
@csrf_required
def create_payment():
    user_id = session.get("user_id")
    if not user_id:
        return error_response("You must be logged in.", 401)

    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict) or data.get("amount") is None:
        return error_response("Amount is required.", 400)

    try:
        amount_kobo = naira_to_kobo(data["amount"])
    except ValueError as error:
        return error_response(str(error), 400)

    user = AuthService.get_user_by_id(user_id)
    if not user:
        return error_response("User account not found.", 404)

    try:
        callback_url = url_for("payments.payment_callback", _external=True)
        result = PaymentService.initialize_paystack_payment(
            user_id=user_id,
            amount_kobo=amount_kobo,
            email=user["email"],
            callback_url=callback_url
        )
        return success_response(
            data=result,
            message="Payment initialized successfully."
        )
    except Exception:
        logger.exception("Could not initialize Paystack payment.")
        return error_response("Could not initialize payment. Please try again.", 500)


@payments_bp.route("/callback", methods=["GET"])
def payment_callback():
    reference = request.args.get("reference")
    if not reference:
        return error_response("Payment reference is missing.", 400)

    try:
        result = PaymentService.verify_paystack_payment(reference)
        provider_data = result["provider_response"].get("data", {})
        if not isinstance(provider_data, dict):
            raise ValueError("Invalid payment verification response.")

        status = str(provider_data.get("status", "")).lower()

        if status == "success":
            if (
                provider_data.get("reference") != reference
                or str(provider_data.get("currency", "")).upper() != "NGN"
            ):
                raise ValueError("Payment details do not match the expected transaction.")
            completed = PaymentService.complete_verified_payment(
                reference=reference,
                provider_reference=provider_data.get("reference"),
                provider_amount_kobo=provider_data.get("amount")
            )
            return success_response(
                data=completed,
                message="Payment verified and wallet credited successfully."
            )

        return success_response(
            data={"reference": reference, "status": status or "unknown"},
            message="Payment has not been confirmed as successful."
        )
    except ValueError as error:
        return error_response(str(error), 400)
    except Exception:
        logger.exception("Could not verify Paystack payment callback.")
        return error_response("Could not verify payment. Please try again.", 500)
