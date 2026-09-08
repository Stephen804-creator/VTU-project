from database.database import get_connection


class TransactionService:

    @staticmethod
    def get_wallet_transactions(
        user_id,
        limit=50
    ):

        connection = get_connection()

        try:

            cursor = connection.cursor()

            cursor.execute("""
                SELECT
                    id,
                    user_id,
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

            return [
                dict(row)
                for row in cursor.fetchall()
            ]

        finally:

            connection.close()


    @staticmethod
    def get_orders(
        user_id,
        limit=50
    ):

        connection = get_connection()

        try:

            cursor = connection.cursor()

            cursor.execute("""
                SELECT
                    o.id,
                    o.reference,
                    o.phone,
                    o.network,
                    o.amount_kobo,
                    o.status,
                    o.supplier,
                    o.supplier_plan_id,
                    o.supplier_reference,
                    o.message,
                    o.created_at,
                    o.updated_at,
                    d.name AS plan_name,
                    d.data_amount,
                    d.validity
                FROM orders o
                LEFT JOIN data_plans d
                    ON o.plan_id = d.id
                WHERE o.user_id = ?
                ORDER BY o.id DESC
                LIMIT ?
            """, (
                user_id,
                limit
            ))

            return [
                dict(row)
                for row in cursor.fetchall()
            ]

        finally:

            connection.close()


    @staticmethod
    def get_all_wallet_transactions(
        limit=100
    ):

        connection = get_connection()

        try:

            cursor = connection.cursor()

            cursor.execute("""
                SELECT
                    wt.*,
                    u.email
                FROM wallet_transactions wt
                JOIN users u
                    ON wt.user_id = u.id
                ORDER BY wt.id DESC
                LIMIT ?
            """, (
                limit,
            ))

            return [
                dict(row)
                for row in cursor.fetchall()
            ]

        finally:

            connection.close()


    @staticmethod
    def get_all_orders(
        limit=100
    ):

        connection = get_connection()

        try:

            cursor = connection.cursor()

            cursor.execute("""
                SELECT
                    o.*,
                    u.email,
                    d.name AS plan_name
                FROM orders o
                LEFT JOIN users u
                    ON o.user_id = u.id
                LEFT JOIN data_plans d
                    ON o.plan_id = d.id
                ORDER BY o.id DESC
                LIMIT ?
            """, (
                limit,
            ))

            return [
                dict(row)
                for row in cursor.fetchall()
            ]

        finally:

            connection.close()
