from flask import (
    Flask,
    render_template
)

from config.settings import settings

from database.models import (
    initialize_database
)

from routes.health import (
    health_bp
)


app = Flask(

    __name__,

    template_folder="templates",

    static_folder="static"
)


# ==========================================
# APPLICATION CONFIGURATION
# ==========================================

app.config["SECRET_KEY"] = (
    settings.SECRET_KEY
)


# ==========================================
# DATABASE
# ==========================================

initialize_database()


# ==========================================
# ROUTES
# ==========================================

app.register_blueprint(
    health_bp
)


@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ==========================================
# LOCAL DEVELOPMENT
# ==========================================

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=settings.PORT,

        debug=False
    )
