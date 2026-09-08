from flask import Blueprint, request

from services.payment_service import PaymentService
from utils.responses import success_response, error_response


webhooks_bp = Blueprint(
    "webhooks",
    __name__,
    url_prefix="/api/v1/webhooks"
)


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
        data.get("status", "")
    ).upper()

    provider_reference = data.get(
        "provider_reference"
    )

    if not reference:

        return error_response(
            "Payment reference is required.",
            400
        )

    # --------------------------------
    # SUCCESS
    # --------------------------------

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

    # --------------------------------
    # FAILED
    # --------------------------------

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
