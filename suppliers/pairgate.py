import requests

from config.settings import settings
from suppliers.base import DataSupplier


class PairgateSupplier(DataSupplier):

    def __init__(self):
        if not settings.PAIRGATE_API_KEY:
            raise RuntimeError(
                "PAIRGATE_API_KEY is not configured."
            )

        self.api_key = settings.PAIRGATE_API_KEY
        self.base_url = settings.PAIRGATE_BASE_URL.rstrip("/")

    @property
    def headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def get_plans(self, provider, plan_type):

        endpoint = (
            "/test/data-plans"
            if settings.PAIRGATE_TEST_MODE
            else "/data-plans"
        )

        url = f"{self.base_url}{endpoint}"

        response = requests.get(
            url,
            headers=self.headers,
            params={
                "provider_id": provider,
                "plan_type": plan_type
            },
            timeout=20
        )

        response.raise_for_status()

        return response.json()

    def purchase_data(
        self,
        provider,
        plan_id,
        recipient,
        reference
    ):

        endpoint = (
            "/test/data/purchase"
            if settings.PAIRGATE_TEST_MODE
            else "/data/purchase"
        )

        url = f"{self.base_url}{endpoint}"

        payload = {
            "provider_id": provider,
            "plan_id": str(plan_id),
            "recipient": recipient,
            "reference": reference
        }

        response = requests.post(
            url,
            headers=self.headers,
            json=payload,
            timeout=30
        )

        response.raise_for_status()

        return response.json()

    def check_transaction(self, reference):

        endpoint = (
            "/test/transaction/status"
            if settings.PAIRGATE_TEST_MODE
            else "/transaction/status"
        )

        url = f"{self.base_url}{endpoint}"

        response = requests.get(
            url,
            headers=self.headers,
            params={
                "reference_code": reference
            },
            timeout=20
        )

        response.raise_for_status()

        return response.json()
