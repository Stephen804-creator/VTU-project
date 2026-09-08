from flask import Blueprint, jsonify


health_bp = Blueprint(
    "health",
    __name__
)


@health_bp.route(
    "/health",
    methods=["GET"]
)
def health_check():

    return jsonify({

        "status":
            "ok",

        "application":
            "Subscribe Me",

        "message":
            "Subscribe Me backend is running."
    })
