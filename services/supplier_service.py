from suppliers.pairgate import PairgateSupplier


class SupplierService:
    def __init__(self):
        self.suppliers = {}

    def get_supplier(self, supplier_name="pairgate"):
        supplier = self.suppliers.get(supplier_name)

        if supplier is None:
            if supplier_name == "pairgate":
                supplier = PairgateSupplier()
                self.suppliers[supplier_name] = supplier
            else:
                raise ValueError(
                    f"Supplier '{supplier_name}' is not configured."
                )

        return supplier

    def list_suppliers(self):
        return ["pairgate"]
