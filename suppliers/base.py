from abc import ABC, abstractmethod


class DataSupplier(ABC):

    @abstractmethod
    def get_plans(
        self,
        provider,
        plan_type
    ):
        """
        Retrieve data plans from supplier.
        """
        raise NotImplementedError


    @abstractmethod
    def purchase_data(
        self,
        provider,
        plan_id,
        recipient,
        reference
    ):
        """
        Purchase a data bundle.
        """
        raise NotImplementedError


    @abstractmethod
    def check_transaction(
        self,
        reference
    ):
        """
        Check transaction status.
        """
        raise NotImplementedError
