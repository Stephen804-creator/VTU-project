from suppliers.pairgate import (
    PairgateSupplier
)


class SupplierService:

    def __init__(self):

        self.suppliers = {

            "pairgate":
                PairgateSupplier()
        }


    def get_supplier(
        self,
        supplier_name="pairgate"
    ):

        supplier = (
            self.suppliers
            .get(supplier_name)
        )


        if not supplier:

            raise ValueError(
                f"Supplier "
                f"'{supplier_name}' "
                f"is not configured."
            )


        return supplier


    def list_suppliers(self):

        return list(
            self.suppliers.keys()
        )
