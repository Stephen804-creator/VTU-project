from flask import (
    Flask,
    render_template,
    jsonify
)

from config.settings import settings

from database.models import (
    initialize_database
)

from routes.health import health_bp
from routes.auth import auth_bp
from routes.wallet import wallet_bp
from routes.data import data_bp
from routes.orders import orders_bp
from routes.payments import payments_bp
from routes.transactions import transactions_bp
from routes.admin import admin_bp
from routes.webhooks import webhooks_bp

from utils.security import (
    apply_security_headers
)

from utils.logging_config import (
    configure_logging
)


app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)


app.config["SECRET_KEY"] = (
    settings.SECRET_KEY
)

app.config[
    "SESSION_COOKIE_HTTPONLY"
] = True

app.config[
    "SESSION_COOKIE_SAMESITE"
] = "Lax"

app.config[
    "MAX_CONTENT_LENGTH"
] = 1 * 1024 * 1024


if settings.APP_ENV == "production":

    app.config[
        "SESSION_COOKIE_SECURE"
    ] = True


logger = configure_logging()


app.after_request(
    apply_security_headers
)


initialize_database()


app.register_blueprint(
    health_bp
)

app.register_blueprint(
    auth_bp
)

app.register_blueprint(
    wallet_bp
)

app.register_blueprint(
    data_bp
)

app.register_blueprint(
    orders_bp
)

app.register_blueprint(
    payments_bp
)

app.register_blueprint(
    transactions_bp
)

app.register_blueprint(
    admin_bp
)

app.register_blueprint(
    webhooks_bp
)


@app.route("/")
def home():

    return render_template(
        "index.html"
    )


@app.errorhandler(413)
def request_too_large(error):

    return jsonify({
        "status": "error",
        "message": "Request is too large."
    }), 413


@app.errorhandler(404)
def not_found(error):

    return jsonify({
        "status": "error",
        "message": "Resource not found."
    }), 404


@app.errorhandler(500)
def internal_server_error(error):

    logger.exception(
        "Unhandled application error."
    )

    return jsonify({
        "status": "error",
        "message": "Internal server error."
    }), 500


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=settings.PORT,
        debug=False
    )
