from flask import Blueprint, request, session

from services.auth_service import AuthService
from utils.responses import success_response, error_response
from utils.csrf import (
    get_csrf_token,
    csrf_required
)


auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/api/v1/auth"
)


@auth_bp.route("/register", methods=["POST"])
@csrf_required
def register():

    data = request.get_json(silent=True) or {}

    email = data.get("email")
    password = data.get("password")

    first_name = data.get("first_name")
    last_name = data.get("last_name")
    phone = data.get("phone")

    if not email:
        return error_response(
            "Email address is required.",
            400
        )

    if not password:
        return error_response(
            "Password is required.",
            400
        )

    if len(password) < 8:
        return error_response(
            "Password must contain at least 8 characters.",
            400
        )

    existing_user = AuthService.get_user_by_email(email)

    if existing_user:
        return error_response(
            "An account with this email already exists.",
            409
        )

    try:

        user = AuthService.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone=phone
        )

        session["user_id"] = user["id"]

        return success_response(
            data={
                "user": user
            },
            message="Account created successfully."
        )

    except Exception as error:

        return error_response(
            f"Could not create account: {str(error)}",
            500
        )


@auth_bp.route("/login", methods=["POST"])
@csrf_required
def login():

    data = request.get_json(silent=True) or {}

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return error_response(
            "Email and password are required.",
            400
        )

    user = AuthService.authenticate(
        email,
        password
    )

    if not user:
        return error_response(
            "Invalid email or password.",
            401
        )

    session["user_id"] = user["id"]

    return success_response(
        data={
            "user": user
        },
        message="Login successful."
    )


@auth_bp.route("/logout", methods=["POST"])
@csrf_required
def logout():

    session.clear()

    return success_response(
        message="Logged out successfully."
    )


@auth_bp.route("/me", methods=["GET"])
def current_user():

    user_id = session.get("user_id")

    if not user_id:
        return error_response(
            "You are not logged in.",
            401
        )

    user = AuthService.get_user_by_id(user_id)

    if not user:
        session.clear()

        return error_response(
            "User account no longer exists.",
            401
        )

    return success_response(
        data={
            "user": user
        }
    )


@auth_bp.route("/csrf", methods=["GET"])
def csrf_token():

    token = get_csrf_token()

    return success_response(
        data={
            "csrf_token": token
        }
    )
