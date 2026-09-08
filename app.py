from flask import Flask, render_template

from config.settings import settings
from database.models import initialize_database

from routes.health import health_bp
from routes.auth import auth_bp
from routes.wallet import wallet_bp


app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)

app.config["SECRET_KEY"] = settings.SECRET_KEY

# Required for browser login sessions.
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Enable this when deployed behind HTTPS.
if settings.APP_ENV == "production":
    app.config["SESSION_COOKIE_SECURE"] = True


# =========================
# DATABASE
# =========================

initialize_database()


# =========================
# API ROUTES
# =========================

app.register_blueprint(health_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(wallet_bp)


# =========================
# FRONTEND
# =========================

@app.route("/")
def home():
    return render_template("index.html")


# =========================
# APPLICATION START
# =========================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=settings.PORT,
        debug=False
    )
