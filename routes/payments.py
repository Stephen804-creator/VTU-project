from flask import Blueprint, request, session

from services.payment_service import PaymentService
from utils.responses import success_response, error_response


payments_bp = Blueprint(
    "payments",
    __name__,
    url_prefix="/api/v1/payments"
)


@payments_bp.route(
    "/create",
    methods=["POST"]
)
def create_payment():

    user_id = session.get("user_id")

    if not user_id:

        return error_response(
            "You must be logged in.",
            401
        )

    data = request.get_json(
        silent=True
    ) or {}

    amount = data.get("amount")

    if amount is None:

        return error_response(
            "Amount is required.",
            400
        )

    try:

        amount = float(amount)

    except (TypeError, ValueError):

        return error_response(
            "Invalid amount.",
            400
        )

    if amount <= 0:

        return error_response(
            "Amount must be greater than zero.",
            400
        )

    # Convert Naira to kobo.
    amount_kobo = int(
        round(amount * 100)
    )

    try:

        payment = PaymentService.create_payment(
            user_id=user_id,
            amount_kobo=amount_kobo,
            provider="pending",
            payment_method="pending"
        )

        return success_response(
            data={
                "payment": payment
            },
            message=(
                "Payment request created. "
                "Payment provider connection "
                "will be completed next."
            )
        )

    except Exception as error:

        return error_response(
            f"Could not create payment: {str(error)}",
            500
        )
