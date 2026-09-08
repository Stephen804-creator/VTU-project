from flask import Flask, render_template

from config.settings import settings
from database.models import initialize_database

from routes.health import health_bp
from routes.auth import auth_bp
from routes.wallet import wallet_bp
from routes.data import data_bp
from routes.orders import orders_bp
from routes.payments import payments_bp
from routes.transactions import transactions_bp
from routes.webhooks import webhooks_bp
from routes.admin import admin_bp

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)


app.config["SECRET_KEY"] = settings.SECRET_KEY


# ==========================================
# SESSION SECURITY
# ==========================================

app.config[
    "SESSION_COOKIE_HTTPONLY"
] = True

app.config[
    "SESSION_COOKIE_SAMESITE"
] = "Lax"


if settings.APP_ENV == "production":

    app.config[
        "SESSION_COOKIE_SECURE"
    ] = True


# ==========================================
# DATABASE
# ==========================================

initialize_database()


# ==========================================
# API ROUTES
# ==========================================

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
    webhooks_bp
)

app.register_blueprint(
    admin_bp
)
# ==========================================
# FRONTEND
# ==========================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ==========================================
# APPLICATION START
# ==========================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=settings.PORT,
        debug=False
    )
