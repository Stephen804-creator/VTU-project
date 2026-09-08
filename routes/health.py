from flask import Blueprint, jsonify

from config.settings import settings
from database.database import get_connection


health_bp = Blueprint(
    "health",
    __name__
)


@health_bp.route(
    "/health",
    methods=["GET"]
)
def health_check():

    database_status = "ok"

    try:

        connection = (
            get_connection()
        )

        cursor = connection.cursor()

        cursor.execute(
            "SELECT 1"
        )

        cursor.fetchone()

        connection.close()

    except Exception:

        database_status = "error"


    overall_status = (
        "ok"
        if database_status == "ok"
        else "degraded"
    )


    return jsonify({
        "status":
            overall_status,

        "application":
            settings.APP_NAME,

        "environment":
            settings.APP_ENV,

        "dependencies": {
            "database":
                database_status
        }
    })
