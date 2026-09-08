from werkzeug.security import generate_password_hash, check_password_hash

from database.database import get_connection


class AuthService:

    @staticmethod
    def create_user(
        email,
        password,
        first_name=None,
        last_name=None,
        phone=None
    ):
        email = str(email).strip().lower()

        password_hash = generate_password_hash(password)

        connection = get_connection()

        try:
            cursor = connection.cursor()

            cursor.execute("""
                INSERT INTO users (
                    email,
                    password_hash,
                    first_name,
                    last_name,
                    phone
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                email,
                password_hash,
                first_name,
                last_name,
                phone
            ))

            user_id = cursor.lastrowid

            # Every customer automatically gets a wallet.
            cursor.execute("""
                INSERT INTO wallets (
                    user_id,
                    balance_kobo
                )
                VALUES (?, 0)
            """, (user_id,))

            connection.commit()

            return AuthService.get_user_by_id(user_id)

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

    @staticmethod
    def get_user_by_id(user_id):
        connection = get_connection()

        try:
            cursor = connection.cursor()

            cursor.execute("""
                SELECT
                    id,
                    email,
                    first_name,
                    last_name,
                    phone,
                    role,
                    is_active,
                    created_at
                FROM users
                WHERE id = ?
            """, (user_id,))

            user = cursor.fetchone()

            if not user:
                return None

            return dict(user)

        finally:
            connection.close()

    @staticmethod
    def get_user_by_email(email):
        connection = get_connection()

        try:
            cursor = connection.cursor()

            cursor.execute("""
                SELECT *
                FROM users
                WHERE email = ?
            """, (str(email).strip().lower(),))

            user = cursor.fetchone()

            if not user:
                return None

            return dict(user)

        finally:
            connection.close()

    @staticmethod
    def authenticate(email, password):
        user = AuthService.get_user_by_email(email)

        if not user:
            return None

        if not user["is_active"]:
            return None

        if not check_password_hash(
            user["password_hash"],
            password
        ):
            return None

        return {
            "id": user["id"],
            "email": user["email"],
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "phone": user["phone"],
            "role": user["role"]
        }
