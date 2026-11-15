import os
from pathlib import Path

from dotenv import load_dotenv


# Load .env when running locally.
# Render and other hosting platforms can provide
# environment variables directly.
load_dotenv()


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings:

    APP_NAME = os.getenv(
        "APP_NAME",
        "Subscribe Me"
    )

    APP_ENV = os.getenv(
        "APP_ENV",
        "development"
    ).strip().lower()

    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        if APP_ENV == "production":
            raise RuntimeError(
                "SECRET_KEY must be configured in production."
            )
        SECRET_KEY = "development-only-insecure-secret"

    PAIRGATE_WEBHOOK_SECRET = os.getenv(
        "PAIRGATE_WEBHOOK_SECRET"
    )

    PAIRGATE_WEBHOOK_VERIFY = (
        os.getenv("PAIRGATE_WEBHOOK_VERIFY", "true").strip().lower()
        == "true"
    )

    try:
        PAIRGATE_WEBHOOK_TOLERANCE_SECONDS = int(
            os.getenv("PAIRGATE_WEBHOOK_TOLERANCE_SECONDS", "300")
        )
    except ValueError as error:
        raise RuntimeError(
            "PAIRGATE_WEBHOOK_TOLERANCE_SECONDS must be an integer."
        ) from error

    if not 30 <= PAIRGATE_WEBHOOK_TOLERANCE_SECONDS <= 900:
        raise RuntimeError(
            "PAIRGATE_WEBHOOK_TOLERANCE_SECONDS must be between 30 and 900."
        )


    DATABASE_PATH = os.getenv(
        "DATABASE_PATH",
        "data/subscribe_me.db"
    )

    PAIRGATE_API_KEY = os.getenv(
        "PAIRGATE_API_KEY"
    )

    PAIRGATE_BASE_URL = os.getenv(
        "PAIRGATE_BASE_URL",
        "https://pairgate.com/api/v1"
    )

    PAIRGATE_TEST_MODE = (
        os.getenv(
            "PAIRGATE_TEST_MODE",
            "false" if APP_ENV == "production" else "true"
        ).strip().lower()
        == "true"
    )

    if (
        APP_ENV == "production"
        and PAIRGATE_API_KEY
        and not PAIRGATE_WEBHOOK_SECRET
    ):
        raise RuntimeError(
            "PAIRGATE_WEBHOOK_SECRET is required when Pairgate is enabled."
        )

    PAYSTACK_SECRET_KEY = os.getenv(
        "PAYSTACK_SECRET_KEY"
    )

    PAYSTACK_BASE_URL = os.getenv(
        "PAYSTACK_BASE_URL",
        "https://api.paystack.co"
    )

    PAYSTACK_TEST_MODE = (
        os.getenv(
            "PAYSTACK_TEST_MODE",
            "false" if APP_ENV == "production" else "true"
        ).strip().lower() == "true"
    )
    if APP_ENV == "production" and PAIRGATE_TEST_MODE:
        raise RuntimeError(
            "PAIRGATE_TEST_MODE must be false in production."
        )

    if APP_ENV == "production" and PAYSTACK_TEST_MODE:
        raise RuntimeError(
            "PAYSTACK_TEST_MODE must be false in production."
        )

    PORT = int(
        os.getenv(
            "PORT",
            "5000"
        )
    )


settings = Settings()
