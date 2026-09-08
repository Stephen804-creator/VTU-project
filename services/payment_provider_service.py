from payment_providers.paystack import (
    PaystackProvider
)


class PaymentProviderService:

    def __init__(self):

        self.providers = {
            "paystack":
                PaystackProvider()
        }

    def get_provider(
        self,
        provider_name="paystack"
    ):

        provider = self.providers.get(
            provider_name
        )

        if not provider:

            raise ValueError(
                f"Payment provider "
                f"'{provider_name}' "
                f"is not configured."
            )

        return provider

    def list_providers(self):

        return list(
            self.providers.keys()
        )
