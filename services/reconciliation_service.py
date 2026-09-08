from services.order_service import OrderService
from services.supplier_service import SupplierService


class ReconciliationService:

    def __init__(self):

        self.order_service = (
            OrderService()
        )

        self.supplier_service = (
            SupplierService()
        )


    def check_order(
        self,
        reference
    ):

        order = (
            self.order_service
            .get_order_by_reference(
                reference
            )
        )

        if not order:

            raise ValueError(
                "Order not found."
            )

        supplier = (
            self.supplier_service
            .get_supplier(
                order["supplier"]
            )
        )

        response = (
            supplier.check_transaction(
                reference
            )
        )

        status = self._extract_status(
            response
        )

        message = self._extract_message(
            response
        )

        supplier_reference = (
            self._extract_reference(
                response
            )
        )

        if status == "successful":

            result = (
                self.order_service
                .process_pairgate_webhook(
                    reference=reference,
                    status="successful",
                    message=message,
                    supplier_reference=
                        supplier_reference
                )
            )

            return {
                "supplier_response":
                    response,
                "result":
                    result
            }

        if status == "failed":

            result = (
                self.order_service
                .process_pairgate_webhook(
                    reference=reference,
                    status="failed",
                    message=message,
                    supplier_reference=
                        supplier_reference
                )
            )

            return {
                "supplier_response":
                    response,
                "result":
                    result
            }

        return {
            "supplier_response":
                response,
            "result": {
                "status":
                    "processing",
                "reference":
                    reference,
                "message":
                    message
                    or
                    "Transaction is still processing."
            }
        }


    @staticmethod
    def _extract_status(
        response
    ):

        if not isinstance(
            response,
            dict
        ):

            return ""

        status = response.get(
            "status"
        )

        if isinstance(
            status,
            str
        ):

            normalized = (
                status
                .strip()
                .lower()
            )

            if normalized in {
                "successful",
                "success",
                "completed"
            }:

                return "successful"

            if normalized in {
                "failed",
                "failure",
                "cancelled"
            }:

                return "failed"


        data = response.get(
            "data"
        )

        if isinstance(
            data,
            dict
        ):

            nested_status = data.get(
                "status"
            )

            if isinstance(
                nested_status,
                str
            ):

                normalized = (
                    nested_status
                    .strip()
                    .lower()
                )

                if normalized in {
                    "successful",
                    "success",
                    "completed"
                }:

                    return "successful"

                if normalized in {
                    "failed",
                    "failure",
                    "cancelled"
                }:

                    return "failed"

        return ""


    @staticmethod
    def _extract_message(
        response
    ):

        if not isinstance(
            response,
            dict
        ):

            return None

        message = response.get(
            "message"
        )

        if message:

            return str(message)

        data = response.get(
            "data"
        )

        if isinstance(
            data,
            dict
        ):

            message = data.get(
                "message"
            )

            if message:

                return str(message)

        return None


    @staticmethod
    def _extract_reference(
        response
    ):

        if not isinstance(
            response,
            dict
        ):

            return None

        reference = (
            response.get(
                "reference_code"
            )
            or
            response.get(
                "reference"
            )
            or
            response.get(
                "transaction_id"
            )
        )

        if reference:

            return str(reference)

        data = response.get(
            "data"
        )

        if isinstance(
            data,
            dict
        ):

            reference = (
                data.get(
                    "reference_code"
                )
                or
                data.get(
                    "reference"
                )
                or
                data.get(
                    "transaction_id"
                )
            )

            if reference:

                return str(reference)

        return None
