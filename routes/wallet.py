from flask import Blueprint, session

from services.wallet_service import WalletService
from utils.responses import success_response, error_response


wallet_bp = Blueprint(
    "wallet",
    __name__,
    url_prefix="/api/v1/wallet"
)


@wallet_bp.route("", methods=["GET"])
def wallet():

    user_id = session.get("user_id")

    if not user_id:
        return error_response(
            "You must be logged in.",
            401
        )

    wallet = WalletService.get_wallet(user_id)

    if not wallet:
        return error_response(
            "Wallet not found.",
            404
        )

    return success_response(
        data={
            "wallet": {
                "id": wallet["id"],
                "balance_kobo": wallet["balance_kobo"],
                "currency": wallet["currency"]
            }
        }
    )


@wallet_bp.route("/transactions", methods=["GET"])
def wallet_transactions():

    user_id = session.get("user_id")

    if not user_id:
        return error_response(
            "You must be logged in.",
            401
        )

    transactions = WalletService.get_transactions(
        user_id
    )

    return success_response(
        data={
            "transactions": transactions
        }
    )
