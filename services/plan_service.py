from database.database import get_connection
from services.supplier_service import SupplierService


class PlanService:

    def __init__(self):
        self.supplier_service = SupplierService()

    def sync_pairgate_plans(
        self,
        provider,
        plan_type
    ):

        supplier = self.supplier_service.get_supplier(
            "pairgate"
        )

        response = supplier.get_plans(
            provider,
            plan_type
        )

        provider_data = response.get("data", {})

        plans = []

        for provider_name, provider_plans in provider_data.items():

            for plan in provider_plans:

                supplier_plan_id = str(
                    plan.get("plan_id")
                )

                name = str(
                    plan.get("name", "Unnamed Plan")
                )

                price_naira = float(
                    plan.get("price", 0)
                )

                duration = plan.get(
                    "duration"
                )

                supplier_price_kobo = int(
                    round(price_naira * 100)
                )

                # Initially our selling price equals
                # supplier price.
                #
                # Later we can add our markup.
                selling_price_kobo = supplier_price_kobo

                plans.append({
                    "supplier": "pairgate",
                    "supplier_plan_id": supplier_plan_id,
                    "network": provider.lower(),
                    "plan_type": plan_type.upper(),
                    "name": name,
                    "data_amount": name,
                    "validity": (
                        f"{duration} Days"
                        if duration is not None
                        else None
                    ),
                    "supplier_price_kobo":
                        supplier_price_kobo,
                    "selling_price_kobo":
                        selling_price_kobo
                })

        self._save_plans(plans)

        return plans

    def _save_plans(self, plans):

        connection = get_connection()

        try:

            cursor = connection.cursor()

            for plan in plans:

                cursor.execute("""
                    INSERT INTO data_plans (
                        supplier,
                        supplier_plan_id,
                        network,
                        plan_type,
                        name,
                        data_amount,
                        validity,
                        supplier_price_kobo,
                        selling_price_kobo,
                        is_active,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)

                    ON CONFLICT(
                        supplier,
                        supplier_plan_id
                    )
                    DO UPDATE SET
                        network = excluded.network,
                        plan_type = excluded.plan_type,
                        name = excluded.name,
                        data_amount = excluded.data_amount,
                        validity = excluded.validity,
                        supplier_price_kobo =
                            excluded.supplier_price_kobo,
                        selling_price_kobo =
                            excluded.selling_price_kobo,
                        is_active = 1,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    plan["supplier"],
                    plan["supplier_plan_id"],
                    plan["network"],
                    plan["plan_type"],
                    plan["name"],
                    plan["data_amount"],
                    plan["validity"],
                    plan["supplier_price_kobo"],
                    plan["selling_price_kobo"]
                ))

            connection.commit()

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

    def get_plans(
        self,
        network=None,
        plan_type=None
    ):

        connection = get_connection()

        try:

            cursor = connection.cursor()

            query = """
                SELECT
                    id,
                    supplier,
                    supplier_plan_id,
                    network,
                    plan_type,
                    name,
                    data_amount,
                    validity,
                    supplier_price_kobo,
                    selling_price_kobo
                FROM data_plans
                WHERE is_active = 1
            """

            parameters = []

            if network:
                query += """
                    AND network = ?
                """
                parameters.append(
                    network.lower()
                )

            if plan_type:
                query += """
                    AND plan_type = ?
                """
                parameters.append(
                    plan_type.upper()
                )

            query += """
                ORDER BY
                    network ASC,
                    plan_type ASC,
                    selling_price_kobo ASC
            """

            cursor.execute(
                query,
                parameters
            )

            return [
                dict(row)
                for row in cursor.fetchall()
            ]

        finally:
            connection.close()

    def get_plan_by_id(self, plan_id):

        connection = get_connection()

        try:

            cursor = connection.cursor()

            cursor.execute("""
                SELECT *
                FROM data_plans
                WHERE id = ?
                AND is_active = 1
            """, (plan_id,))

            plan = cursor.fetchone()

            if not plan:
                return None

            return dict(plan)

        finally:
            connection.close()
