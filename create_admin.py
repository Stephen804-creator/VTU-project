import getpass

from database.models import initialize_database
from services.auth_service import AuthService


def main():

    initialize_database()

    print()
    print("================================")
    print(" Subscribe Me Admin Setup")
    print("================================")
    print()

    email = input(
        "Admin email: "
    ).strip().lower()

    if not email:

        print(
            "Email is required."
        )

        return

    password = getpass.getpass(
        "Admin password: "
    )

    confirm_password = getpass.getpass(
        "Confirm password: "
    )

    if password != confirm_password:

        print(
            "Passwords do not match."
        )

        return

    if len(password) < 8:

        print(
            "Password must contain at least 8 characters."
        )

        return

    existing = (
        AuthService
        .get_user_by_email(
            email
        )
    )

    if existing:

        print(
            "A user with this email already exists."
        )

        print(
            "Use the database administration process "
            "to promote the existing user."
        )

        return

    first_name = input(
        "First name: "
    ).strip()

    last_name = input(
        "Last name: "
    ).strip()

    try:

        user = (
            AuthService.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
        )

    except Exception as error:

        print(
            f"Could not create admin: {error}"
        )

        return

    from database.database import get_connection

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute("""
            UPDATE users
            SET role = 'admin'
            WHERE id = ?
        """, (
            user["id"],
        ))

        connection.commit()

    finally:

        connection.close()

    print()
    print(
        "Administrator account created successfully."
    )
    print(
        f"Admin email: {email}"
    )
    print()


if __name__ == "__main__":

    main()
