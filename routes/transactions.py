from flask import Blueprint, session

from services.wallet_service import WalletService
from services.order_service import OrderService
from utils.responses import success_response, error_response


transactions_bp = Blueprint(
    "transactions",
    __name__,
    url_prefix="/api/v1/transactions"
)


order_service = OrderService()


@transactions_bp.route("", methods=["GET"])
def transactions():

    user_id = session.get("user_id")

    if not user_id:
        return error_response(
            "You must be logged in.",
            401
        )

    wallet_transactions = (
        WalletService.get_transactions(
            user_id=user_id
        )
    )

    orders = (
        order_service.get_orders(
            user_id=user_id
        )
    )

    return success_response(
        data={
            "wallet_transactions":
                wallet_transactions,
            "orders": orders
        }
    )
