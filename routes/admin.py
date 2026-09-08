from flask import Blueprint, request

from services.plan_service import PlanService
from services.transaction_service import TransactionService
from utils.auth import admin_required
from utils.responses import success_response, error_response
from services.reconciliation_service import (
    ReconciliationService
)

admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/api/v1/admin"
)


plan_service = PlanService()


@admin_bp.route(
    "/orders",
    methods=["GET"]
)
@admin_required
def admin_orders():

    limit = request.args.get(
        "limit",
        100
    )

    try:

        limit = int(limit)

    except (
        TypeError,
        ValueError
    ):

        return error_response(
            "Invalid limit.",
            400
        )

    limit = max(
        1,
        min(
            limit,
            500
        )
    )

    orders = (
        TransactionService
        .get_all_orders(
            limit=limit
        )
    )

    return success_response(
        data={
            "orders": orders
        }
    )


@admin_bp.route(
    "/wallet-transactions",
    methods=["GET"]
)
@admin_required
def admin_wallet_transactions():

    limit = request.args.get(
        "limit",
        100
    )

    try:

        limit = int(limit)

    except (
        TypeError,
        ValueError
    ):

        return error_response(
            "Invalid limit.",
            400
        )

    limit = max(
        1,
        min(
            limit,
            500
        )
    )

    transactions = (
        TransactionService
        .get_all_wallet_transactions(
            limit=limit
        )
    )

    return success_response(
        data={
            "transactions":
                transactions
        }
    )


@admin_bp.route(
    "/sync-plans",
    methods=["POST"]
)
@admin_required
def admin_sync_plans():

    networks = [
        "mtn",
        "airtel",
        "glo",
        "9mobile"
    ]

    plan_types = [
        "CG",
        "CG_LITE",
        "SME",
        "GIFTING",
        "AWOOF"
    ]

    synced = []

    errors = []

    for network in networks:

        for plan_type in plan_types:

            try:

                result = (
                    plan_service
                    .sync_pairgate_plans(
                        provider=network,
                        plan_type=plan_type
                    )
                )

                synced.extend(
                    result
                )

            except Exception as error:

                errors.append({
                    "network": network,
                    "plan_type": plan_type,
                    "error": str(error)
                })

    return success_response(
        data={
            "synced_count":
                len(synced),
            "errors":
                errors
        },
        message=(
            "Administrative plan "
            "synchronization completed."
        )
    )
reconciliation_service = (
    ReconciliationService()
)


@admin_bp.route(
    "/orders/<reference>/reconcile",
    methods=["POST"]
)
@admin_required
def reconcile_order(reference):

    try:

        result = (
            reconciliation_service
            .check_order(
                reference
            )
        )

        return success_response(
            data=result,
            message=(
                "Order reconciliation completed."
            )
        )

    except ValueError as error:

        return error_response(
            str(error),
            404
        )

    except Exception as error:

        return error_response(
            f"Reconciliation failed: {str(error)}",
            500
        )
