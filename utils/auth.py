from functools import wraps

from flask import session

from database.database import get_connection
from utils.responses import error_response


def get_current_user():

    user_id = session.get(
        "user_id"
    )

    if not user_id:
        return None

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                id,
                email,
                first_name,
                last_name,
                phone,
                role,
                is_active
            FROM users
            WHERE id = ?
        """, (
            user_id,
        ))

        user = cursor.fetchone()

        if not user:
            return None

        return dict(user)

    finally:

        connection.close()


def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        user = get_current_user()

        if not user:

            return error_response(
                "You must be logged in.",
                401
            )

        if not user["is_active"]:

            session.clear()

            return error_response(
                "Your account is disabled.",
                403
            )

        return function(
            *args,
            **kwargs
        )

    return wrapper


def admin_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        user = get_current_user()

        if not user:

            return error_response(
                "You must be logged in.",
                401
            )

        if not user["is_active"]:

            session.clear()

            return error_response(
                "Your account is disabled.",
                403
            )

        if user["role"] != "admin":

            return error_response(
                "Administrator access required.",
                403
            )

        return function(
            *args,
            **kwargs
        )

    return wrapper
