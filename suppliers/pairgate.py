import requests

from config.settings import settings
from suppliers.base import DataSupplier


class PairgateSupplier(DataSupplier):

    def __init__(self):

        if not settings.PAIRGATE_API_KEY:

            raise RuntimeError(
                "PAIRGATE_API_KEY is not configured."
            )

        self.api_key = (
            settings.PAIRGATE_API_KEY
        )

        self.base_url = (
            settings.PAIRGATE_BASE_URL
        ).rstrip("/")


    @property
    def headers(self):

        return {

            "Authorization":
                f"Bearer {self.api_key}",

            "Accept":
                "application/json",

            "Content-Type":
                "application/json"
        }


    def get_plans(
        self,
        provider,
        plan_type
    ):

        url = (
            f"{self.base_url}/data-plans"
        )

        params = {

            "provider_id":
                provider,

            "plan_type":
                plan_type
        }

        response = requests.get(

            url,

            headers=self.headers,

            params=params,

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

        if settings.PAIRGATE_TEST_MODE:

            endpoint = (
                "/test/data/purchase"
            )

        else:

            endpoint = (
                "/data/purchase"
            )


        url = (
            f"{self.base_url}{endpoint}"
        )


        payload = {

            "provider_id":
                provider,

            "plan_id":
                str(plan_id),

            "recipient":
                recipient,

            "reference":
                reference
        }


        response = requests.post(

            url,

            headers=self.headers,

            json=payload,

            timeout=30
        )


        response.raise_for_status()

        return response.json()


    def check_transaction(
        self,
        reference
    ):

        url = (
            f"{self.base_url}"
            f"/data/transaction/{reference}"
        )


        response = requests.get(

            url,

            headers=self.headers,

            timeout=20
        )


        response.raise_for_status()

        return response.json()
