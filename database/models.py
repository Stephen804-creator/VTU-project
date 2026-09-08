from database.database import get_connection


def initialize_database():
    connection = get_connection()
    cursor = connection.cursor()

    # =========================
    # USERS
    # =========================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            first_name TEXT,
            last_name TEXT,
            phone TEXT,
            role TEXT NOT NULL DEFAULT 'customer',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # =========================
    # WALLETS
    # =========================

    # balance is stored in KOBO.
    #
    # Example:
    # ₦1,000 = 100000 kobo

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wallets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            balance_kobo INTEGER NOT NULL DEFAULT 0,
            currency TEXT NOT NULL DEFAULT 'NGN',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
            REFERENCES users(id)
            ON DELETE CASCADE
        )
    """)

    # =========================
    # DATA PLANS
    # =========================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS data_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            supplier TEXT NOT NULL,
            supplier_plan_id TEXT NOT NULL,

            network TEXT NOT NULL,
            plan_type TEXT NOT NULL,

            name TEXT NOT NULL,
            data_amount TEXT,
            validity TEXT,

            supplier_price_kobo INTEGER,
            selling_price_kobo INTEGER,

            is_active INTEGER NOT NULL DEFAULT 1,

            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(supplier, supplier_plan_id)
        )
    """)

    # =========================
    # ORDERS
    # =========================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            reference TEXT UNIQUE NOT NULL,

            user_id INTEGER,

            phone TEXT NOT NULL,
            network TEXT NOT NULL,

            plan_id INTEGER,

            supplier TEXT NOT NULL,
            supplier_plan_id TEXT NOT NULL,

            amount_kobo INTEGER NOT NULL DEFAULT 0,

            status TEXT NOT NULL DEFAULT 'PENDING',

            supplier_reference TEXT,
            message TEXT,

            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
            REFERENCES users(id)
            ON DELETE SET NULL,

            FOREIGN KEY (plan_id)
            REFERENCES data_plans(id)
            ON DELETE SET NULL
        )
    """)

    # =========================
    # WALLET TRANSACTIONS
    # =========================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wallet_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            type TEXT NOT NULL,

            amount_kobo INTEGER NOT NULL,

            reference TEXT UNIQUE NOT NULL,

            description TEXT,

            status TEXT NOT NULL DEFAULT 'SUCCESS',

            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
            REFERENCES users(id)
            ON DELETE CASCADE
        )
    """)

    # =========================
    # PAYMENTS
    # =========================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER,

            reference TEXT UNIQUE NOT NULL,

            provider TEXT NOT NULL,

            provider_reference TEXT,

            amount_kobo INTEGER NOT NULL,

            status TEXT NOT NULL DEFAULT 'PENDING',

            payment_method TEXT,

            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
            REFERENCES users(id)
            ON DELETE SET NULL
        )
    """)

    # =========================
    # SUPPLIER LOGS
    # =========================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS supplier_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            supplier TEXT NOT NULL,

            operation TEXT NOT NULL,

            reference TEXT,

            request_data TEXT,

            response_data TEXT,

            status_code INTEGER,

            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.commit()
    connection.close()
