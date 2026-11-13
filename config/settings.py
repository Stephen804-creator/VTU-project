import os
from pathlib import Path

from dotenv import load_dotenv


# Load .env when running locally. Hosting platforms can inject variables.
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings:
    APP_NAME = os.getenv("APP_NAME", "Subscribe Me")
    APP_ENV = os.getenv("APP_ENV", "development").strip().lower()

    _secret_key = os.getenv("SECRET_KEY", "").strip()
    _insecure_secret_values = {
        "",
        "change-this-secret-key",
        "development-secret-change-me",
        "your-secret-key",
        "secret",
    }

    if APP_ENV == "production":
        if (
            len(_secret_key) < 32
            or _secret_key.lower() in _insecure_secret_values
            or "replace-with-" in _secret_key.lower()
            or "change-this" in _secret_key.lower()
        ):
            raise RuntimeError(
                "A strong SECRET_KEY (at least 32 characters) "
                "must be configured in production."
            )
        SECRET_KEY = _secret_key
    else:
        # Convenience fallback is deliberately restricted to local development.
        SECRET_KEY = _secret_key or "development-only-secret-do-not-use-in-production"

    DATABASE_PATH = os.getenv("DATABASE_PATH", "data/subscribe_me.db")

    PAIRGATE_API_KEY = os.getenv("PAIRGATE_API_KEY")
    PAIRGATE_BASE_URL = os.getenv(
        "PAIRGATE_BASE_URL", "https://pairgate.com/api/v1"
    )
    PAIRGATE_TEST_MODE = os.getenv("PAIRGATE_TEST_MODE", "true").lower() == "true"

    PAIRGATE_WEBHOOK_SECRET = os.getenv("PAIRGATE_WEBHOOK_SECRET")
    PAIRGATE_WEBHOOK_VERIFY = (
        os.getenv("PAIRGATE_WEBHOOK_VERIFY", "true").lower() == "true"
    )
    PAIRGATE_WEBHOOK_TOLERANCE_SECONDS = int(
        os.getenv("PAIRGATE_WEBHOOK_TOLERANCE_SECONDS", "300")
    )

    PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
    PAYSTACK_BASE_URL = os.getenv("PAYSTACK_BASE_URL", "https://api.paystack.co")
    PAYSTACK_TEST_MODE = os.getenv("PAYSTACK_TEST_MODE", "true").lower() == "true"

    if APP_ENV == "production":
        if not PAYSTACK_SECRET_KEY:
            raise RuntimeError("PAYSTACK_SECRET_KEY must be configured in production.")
        if not PAIRGATE_API_KEY:
            raise RuntimeError("PAIRGATE_API_KEY must be configured in production.")
        if not PAIRGATE_WEBHOOK_SECRET:
            raise RuntimeError("PAIRGATE_WEBHOOK_SECRET must be configured in production.")
        if PAIRGATE_WEBHOOK_TOLERANCE_SECONDS <= 0:
            raise RuntimeError("PAIRGATE_WEBHOOK_TOLERANCE_SECONDS must be positive.")

    PORT = int(os.getenv("PORT", "5000"))


settings = Settings()
