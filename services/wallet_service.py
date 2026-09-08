from database.database import get_connection
from utils.references import generate_reference


class WalletService:

    @staticmethod
    def get_wallet(user_id):

        connection = get_connection()

        try:
            cursor = connection.cursor()

            cursor.execute("""
                SELECT
                    id,
                    user_id,
                    balance_kobo,
                    currency,
                    created_at,
                    updated_at
                FROM wallets
                WHERE user_id = ?
            """, (user_id,))

            wallet = cursor.fetchone()

            if not wallet:
                return None

            return dict(wallet)

        finally:
            connection.close()

    @staticmethod
    def get_balance_kobo(user_id):

        wallet = WalletService.get_wallet(user_id)

        if not wallet:
            raise ValueError("Wallet not found.")

        return wallet["balance_kobo"]

    @staticmethod
    def credit_wallet(
        user_id,
        amount_kobo,
        reference=None,
        description="Wallet funding"
    ):

        if amount_kobo <= 0:
            raise ValueError(
                "Wallet credit amount must be greater than zero."
            )

        if not reference:
            reference = generate_reference("WAL")

        connection = get_connection()

        try:
            cursor = connection.cursor()

            # Increase wallet balance.
            cursor.execute("""
                UPDATE wallets
                SET
                    balance_kobo = balance_kobo + ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (
                amount_kobo,
                user_id
            ))

            if cursor.rowcount == 0:
                raise ValueError("Wallet not found.")

            # Record ledger transaction.
            cursor.execute("""
                INSERT INTO wallet_transactions (
                    user_id,
                    type,
                    amount_kobo,
                    reference,
                    description,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                "CREDIT",
                amount_kobo,
                reference,
                description,
                "SUCCESS"
            ))

            connection.commit()

            return {
                "reference": reference,
                "amount_kobo": amount_kobo,
                "type": "CREDIT"
            }

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

    @staticmethod
    def debit_wallet(
        user_id,
        amount_kobo,
        reference=None,
        description="Data purchase"
    ):

        if amount_kobo <= 0:
            raise ValueError(
                "Wallet debit amount must be greater than zero."
            )

        if not reference:
            reference = generate_reference("WAL")

        connection = get_connection()

        try:
            cursor = connection.cursor()

            # IMPORTANT:
            # Only debit if enough balance exists.
            cursor.execute("""
                UPDATE wallets
                SET
                    balance_kobo = balance_kobo - ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE
                    user_id = ?
                    AND balance_kobo >= ?
            """, (
                amount_kobo,
                user_id,
                amount_kobo
            ))

            if cursor.rowcount == 0:
                raise ValueError(
                    "Insufficient wallet balance."
                )

            cursor.execute("""
                INSERT INTO wallet_transactions (
                    user_id,
                    type,
                    amount_kobo,
                    reference,
                    description,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                "DEBIT",
                amount_kobo,
                reference,
                description,
                "SUCCESS"
            ))

            connection.commit()

            return {
                "reference": reference,
                "amount_kobo": amount_kobo,
                "type": "DEBIT"
            }

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

    @staticmethod
    def get_transactions(user_id, limit=50):

        connection = get_connection()

        try:
            cursor = connection.cursor()

            cursor.execute("""
                SELECT
                    id,
                    type,
                    amount_kobo,
                    reference,
                    description,
                    status,
                    created_at
                FROM wallet_transactions
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
            """, (
                user_id,
                limit
            ))

            transactions = cursor.fetchall()

            return [
                dict(transaction)
                for transaction in transactions
            ]

        finally:
            connection.close()
