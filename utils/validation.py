import re


SUPPORTED_NETWORKS = {
    "mtn",
    "airtel",
    "glo",
    "9mobile"
}


SUPPORTED_PLAN_TYPES = {
    "SME",
    "GIFTING",
    "CORPORATE",
    "CG",
    "CG_LITE",
    "DG",
    "AWOOF"
}


def validate_phone(phone):

    if not phone:

        return False


    phone = str(phone).strip()


    return bool(
        re.fullmatch(
            r"0\d{10}",
            phone
        )
    )


def normalize_network(network):

    if not network:

        return None

    network = (
        str(network)
        .strip()
        .lower()
    )

    if network not in SUPPORTED_NETWORKS:

        return None

    return network


def normalize_plan_type(plan_type):

    if not plan_type:

        return None

    plan_type = (
        str(plan_type)
        .strip()
        .upper()
    )

    if plan_type not in SUPPORTED_PLAN_TYPES:

        return None

    return plan_type
