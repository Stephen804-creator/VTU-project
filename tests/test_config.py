import os
import subprocess
import sys


def test_production_rejects_short_secret_key():
    environment = os.environ.copy()
    environment["APP_ENV"] = "production"
    environment["SECRET_KEY"] = "too-short"
    environment.pop("PAIRGATE_API_KEY", None)
    environment.pop("PAIRGATE_WEBHOOK_SECRET", None)
    environment.pop("PAYSTACK_SECRET_KEY", None)

    result = subprocess.run(
        [sys.executable, "-c", "import config.settings"],
        env=environment,
        capture_output=True,
        text=True,
        check=False
    )

    assert result.returncode != 0
    assert "SECRET_KEY must be a non-placeholder value" in result.stderr


def test_production_rejects_placeholder_secret_key():
    environment = os.environ.copy()
    environment["APP_ENV"] = "production"
    environment["SECRET_KEY"] = "change-this-secret-key"
    environment.pop("PAIRGATE_API_KEY", None)
    environment.pop("PAIRGATE_WEBHOOK_SECRET", None)
    environment.pop("PAYSTACK_SECRET_KEY", None)

    result = subprocess.run(
        [sys.executable, "-c", "import config.settings"],
        env=environment,
        capture_output=True,
        text=True,
        check=False
    )

    assert result.returncode != 0
    assert "SECRET_KEY must be a non-placeholder value" in result.stderr
