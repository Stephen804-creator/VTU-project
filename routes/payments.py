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

    data = request.get_json(
        silent=True
    ) or {}

    amount = data.get(
        "amount"
    )

    if amount is None:

        return error_response(
            "Amount is required.",
            400
        )

    try:

        amount = float(amount)

    except (
        TypeError,
        ValueError
    ):

        return error_response(
            "Invalid amount.",
            400
        )

    if amount <= 0:

        return error_response(
            "Amount must be greater than zero.",
            400
        )

    if amount > 1000000:

        return error_response(
            "Maximum wallet funding amount is ₦1,000,000.",
            400
        )

    amount_kobo = int(
        round(amount * 100)
    )

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

    except Exception as error:

        return error_response(
            f"Could not initialize payment: {str(error)}",
            500
        )


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

        provider_data = (
            provider_response.get(
                "data",
                {}
            )
        )

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

        return error_response(
            "Could not verify payment.",
            500
    )
