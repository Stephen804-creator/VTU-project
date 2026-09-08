import secrets

from flask import session, request

from utils.responses import error_response


CSRF_SESSION_KEY = "_csrf_token"

CSRF_HEADER = "X-CSRF-Token"


def get_csrf_token():
    """
    Get the current CSRF token.

    If one does not exist, create it and
    store it inside the user's Flask session.
    """

    token = session.get(
        CSRF_SESSION_KEY
    )

    if not token:

        token = secrets.token_urlsafe(
            32
        )

        session[
            CSRF_SESSION_KEY
        ] = token

    return token


def verify_csrf_token():

    expected_token = session.get(
        CSRF_SESSION_KEY
    )

    provided_token = request.headers.get(
        CSRF_HEADER
    )

    if not expected_token:

        return False

    if not provided_token:

        return False

    return secrets.compare_digest(
        expected_token,
        provided_token
    )


def csrf_required(function):

    def wrapper(*args, **kwargs):

        if not verify_csrf_token():

            return error_response(
                "Invalid or missing CSRF token.",
                403
            )

        return function(
            *args,
            **kwargs
        )

    wrapper.__name__ = function.__name__

    return wrapper
