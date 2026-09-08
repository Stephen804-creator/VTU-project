import hashlib
import hmac

import requests

from config.settings import settings


class PaystackProvider:

    def __init__(self):

        if not settings.PAYSTACK_SECRET_KEY:
            raise RuntimeError(
                "PAYSTACK_SECRET_KEY is not configured."
            )

        self.secret_key = (
            settings.PAYSTACK_SECRET_KEY
        )

        self.base_url = (
            settings.PAYSTACK_BASE_URL
            .rstrip("/")
        )

    @property
    def headers(self):

        return {
            "Authorization":
                f"Bearer {self.secret_key}",

            "Content-Type":
                "application/json",

            "Accept":
                "application/json"
        }

    def initialize_transaction(
        self,
        email,
        amount_kobo,
        reference,
        callback_url=None,
        metadata=None
    ):

        payload = {
            "email": email,
            "amount": str(amount_kobo),
            "currency": "NGN",
            "reference": reference
        }

        if callback_url:

            payload["callback_url"] = (
                callback_url
            )

        if metadata is not None:

            payload["metadata"] = metadata

        response = requests.post(
            f"{self.base_url}/transaction/initialize",
            headers=self.headers,
            json=payload,
            timeout=30
        )

        response.raise_for_status()

        result = response.json()

        if not result.get("status"):

            raise RuntimeError(
                result.get(
                    "message",
                    "Paystack initialization failed."
                )
            )

        return result

    def verify_transaction(
        self,
        reference
    ):

        response = requests.get(
            (
                f"{self.base_url}/transaction/"
                f"verify/{reference}"
            ),
            headers=self.headers,
            timeout=30
        )

        response.raise_for_status()

        result = response.json()

        if not result.get("status"):

            raise RuntimeError(
                result.get(
                    "message",
                    "Paystack verification failed."
                )
            )

        return result

    def verify_webhook_signature(
        self,
        raw_payload,
        signature
    ):

        if not signature:

            return False

        expected_signature = hmac.new(
            self.secret_key.encode("utf-8"),
            raw_payload,
            hashlib.sha512
        ).hexdigest()

        return hmac.compare_digest(
            expected_signature,
            signature
        )
