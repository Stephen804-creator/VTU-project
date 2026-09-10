from flask import Blueprint, request, session

from services.order_service import OrderService
from utils.responses import success_response, error_response
from utils.csrf import csrf_required


orders_bp = Blueprint(
    "orders",
    __name__,
    url_prefix="/api/v1/orders"
)


order_service = OrderService()


@orders_bp.route(
    "",
    methods=["POST"]
)
@csrf_required
def create_order():

    user_id = session.get("user_id")

    if not user_id:

        return error_response(
            "You must be logged in to purchase data.",
            401
        )

    data = request.get_json(
        silent=True
    ) or {}

    plan_id = data.get("plan_id")
    phone = data.get("phone")

    if not plan_id:

        return error_response(
            "plan_id is required.",
            400
        )

    if not phone:

        return error_response(
            "Phone number is required.",
            400
        )

    try:

        plan_id = int(plan_id)

    except (TypeError, ValueError):

        return error_response(
            "Invalid plan ID.",
            400
        )

    try:

        result = order_service.create_order(
            user_id=user_id,
            plan_id=plan_id,
            phone=phone
        )

        if result["status"] == "success":

            return success_response(
                data=result,
                message=result["message"]
            )

        if result["status"] == "processing":

            return success_response(
                data=result,
                message=result["message"]
            )

        if result["status"] == "refunded":

            return success_response(
                data=result,
                message=result["message"]
            )

        return error_response(
            result.get(
                "message",
                "Order could not be completed."
            ),
            400
        )

    except ValueError as error:

        return error_response(
            str(error),
            400
        )

    except Exception as error:

        return error_response(
            f"Order processing error: {str(error)}",
            500
        )


@orders_bp.route(
    "/<reference>",
    methods=["GET"]
)
def get_order(reference):

    user_id = session.get("user_id")

    if not user_id:

        return error_response(
            "You must be logged in.",
            401
        )

    order = order_service.get_order(
        user_id=user_id,
        reference=reference
    )

    if not order:

        return error_response(
            "Order not found.",
            404
        )

    return success_response(
        data={
            "order": order
        }
    )


@orders_bp.route(
    "",
    methods=["GET"]
)
def list_orders():

    user_id = session.get("user_id")

    if not user_id:

        return error_response(
            "You must be logged in.",
            401
        )

    orders = order_service.get_orders(
        user_id=user_id
    )

    return success_response(
        data={
            "orders": orders
        }
    )
