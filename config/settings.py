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
    )

    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "development-secret-change-me"
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
            "true"
        ).lower()
        == "true"
    )

    PORT = int(
        os.getenv(
            "PORT",
            "5000"
        )
    )


settings = Settings()
