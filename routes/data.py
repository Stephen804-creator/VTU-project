import logging

from flask import Blueprint, request

from services.plan_service import PlanService
from utils.auth import admin_required
from utils.responses import success_response, error_response
from utils.validation import normalize_network, normalize_plan_type


logger = logging.getLogger(__name__)
data_bp = Blueprint("data", __name__, url_prefix="/api/v1/data")
plan_service = PlanService()


@data_bp.route("/plans", methods=["GET"])
def plans():
    network = request.args.get("network")
    plan_type = request.args.get("plan_type")
    if network:
        network = normalize_network(network)
        if not network:
            return error_response("Unsupported network.", 400)
    if plan_type:
        plan_type = normalize_plan_type(plan_type)
        if not plan_type:
            return error_response("Unsupported plan type.", 400)

    plans = plan_service.get_plans(network=network, plan_type=plan_type)
    formatted_plans = [{
        "id": plan["id"],
        "supplier": plan["supplier"],
        "supplier_plan_id": plan["supplier_plan_id"],
        "network": plan["network"],
        "plan_type": plan["plan_type"],
        "name": plan["name"],
        "data_amount": plan["data_amount"],
        "validity": plan["validity"],
        "price_kobo": plan["selling_price_kobo"],
        "price_naira": plan["selling_price_kobo"] / 100
    } for plan in plans]
    return success_response(
        data={"plans": formatted_plans, "count": len(formatted_plans)}
    )


@data_bp.route("/sync", methods=["POST"])
@admin_required
def sync_plans():
    synced_plans = []
    errors = []
    for network in ["mtn", "airtel", "glo", "9mobile"]:
        for plan_type in ["CG", "CG_LITE", "SME", "GIFTING", "AWOOF"]:
            try:
                synced_plans.extend(
                    plan_service.sync_pairgate_plans(network, plan_type)
                )
            except Exception:
                logger.exception(
                    "Plan synchronization failed for network=%s plan_type=%s",
                    network, plan_type
                )
                errors.append({
                    "network": network,
                    "plan_type": plan_type,
                    "error": "Supplier synchronization failed."
                })

    return success_response(
        data={"synced_count": len(synced_plans), "errors": errors},
        message="Plan synchronization completed."
    )
