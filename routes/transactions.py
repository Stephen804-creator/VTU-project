from flask import Blueprint, session

from services.transaction_service import TransactionService
from utils.responses import success_response, error_response


transactions_bp = Blueprint(
    "transactions",
    __name__,
    url_prefix="/api/v1/transactions"
)


@transactions_bp.route(
    "",
    methods=["GET"]
)
def transactions():

    user_id = session.get(
        "user_id"
    )

    if not user_id:

        return error_response(
            "You must be logged in.",
            401
        )

    wallet_transactions = (
        TransactionService
        .get_wallet_transactions(
            user_id=user_id
        )
    )

    orders = (
        TransactionService
        .get_orders(
            user_id=user_id
        )
    )

    return success_response(
        data={
            "wallet_transactions":
                wallet_transactions,
            "orders":
                orders
        }
    )
