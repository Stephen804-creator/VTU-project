# Subscribe Me (VTU Project)

Subscribe Me is a Flask-based backend for Nigerian virtual top-up services. It provides account authentication, data-plan discovery, wallet balances and ledger transactions, data-purchase orders, Paystack wallet funding, and Pairgate supplier integration.

## Current architecture

- **Flask application:** `app.py` registers the API blueprints and initializes the SQLite schema.
- **Configuration:** `config/settings.py` reads environment variables (and a local `.env` file).
- **Persistence:** SQLite is used through `database/database.py`; wallet and payment amounts are stored as integer kobo.
- **Payments:** Paystack initializes and verifies wallet-funding transactions.
- **Supplier:** Pairgate supplies data plans and processes data purchases.
- **Business logic:** `services/` contains authentication, payment, wallet, order, plan, and reconciliation services.
- **HTTP routes:** `routes/` exposes authentication, wallet, data, order, payment, admin, health, transaction, and webhook endpoints.

## Requirements

- Python 3.9 or newer
- pip
- A Paystack account and secret key for wallet funding
- Pairgate API credentials for live supplier operations

## Local setup

### 1. Clone and create a virtual environment

```bash
git clone https://github.com/Stephen804-creator/VTU-project.git
cd VTU-project
python -m venv .venv
```

Activate it:

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

### 2. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure environment

Copy `.env.example` to `.env` and replace the placeholders with credentials for the services you intend to use.

```bash
# Windows PowerShell
Copy-Item .env.example .env

# macOS / Linux
cp .env.example .env
```

Generate a strong Flask secret:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Set the generated value as `SECRET_KEY`. Do not commit `.env` or real credentials. For production, set `APP_ENV=production`, provide a unique `SECRET_KEY` of at least 32 characters, and configure `PAYSTACK_SECRET_KEY`, `PAIRGATE_API_KEY`, and `PAIRGATE_WEBHOOK_SECRET`. Production startup fails when these required secrets are absent or invalid.

For a local run, `APP_ENV=development` and the provider test-mode flags can remain enabled. Configure provider credentials before testing provider-backed operations.

### 4. Initialize and run

The application initializes its SQLite tables when it starts. The default database path is `data/subscribe_me.db`; the directory is created automatically.

```bash
python app.py
```

The default local address is `http://127.0.0.1:5000`. For a production WSGI process, use the included Gunicorn dependency, for example:

```bash
gunicorn app:app
```

### 5. Create an administrator

Run the interactive setup script:

```bash
python create_admin.py
```

It creates a user and promotes that account to the administrator role. Use a unique, strong password.

## Configuration reference

| Variable | Purpose |
| --- | --- |
| `APP_NAME` | Application display name |
| `APP_ENV` | `development` or `production` |
| `SECRET_KEY` | Flask session-signing secret; mandatory and strong in production |
| `DATABASE_PATH` | SQLite database file path |
| `PAIRGATE_API_KEY` | Pairgate supplier API credential |
| `PAIRGATE_BASE_URL` | Pairgate API base URL |
| `PAIRGATE_TEST_MODE` | Use Pairgate test endpoints when `true` |
| `PAIRGATE_WEBHOOK_SECRET` | Pairgate webhook HMAC secret; mandatory in production |
| `PAIRGATE_WEBHOOK_VERIFY` | Local development verification toggle; production always verifies |
| `PAIRGATE_WEBHOOK_TOLERANCE_SECONDS` | Allowed Pairgate timestamp drift (default 300 seconds) |
| `PAYSTACK_SECRET_KEY` | Paystack API and webhook secret |
| `PAYSTACK_BASE_URL` | Paystack API base URL |
| `PAYSTACK_TEST_MODE` | Paystack test-mode setting |
| `PORT` | Local application port |

## Payment and wallet integrity

- User-entered naira amounts are parsed with Python `Decimal` and converted to integer kobo. Amounts with more than two decimal places are rejected; they are never silently rounded.
- Payment and wallet balances are persisted in integer kobo. Provider-reported Paystack amounts are compared with the stored payment amount before crediting.
- A Paystack webhook must have a valid HMAC-SHA512 signature over the exact raw request body. The webhook endpoint does not trust a client-supplied payment status.
- Paystack's webhook contract does not provide a signed timestamp header for this flow. Replay safety therefore relies on the atomic pending-to-success payment transition and the unique `FUND-{payment_reference}` wallet-ledger reference. A callback and a webhook racing for the same payment cannot both credit it.
- Pairgate webhooks use HMAC-SHA256 over `timestamp + "." + raw request body`, with a default 300-second timestamp tolerance. Signature verification is mandatory in production. Duplicate terminal order notifications are handled by order-state checks; refund credits use a deterministic `REFUND-{order_reference}` ledger reference.
- The legacy generic `/api/v1/webhooks/payment` endpoint is disabled because it has no provider-authentication contract. Use the signed provider-specific endpoints.

## Important routes

| Route | Purpose |
| --- | --- |
| `GET /` | Web application entry page |
| `GET /api/v1/health` | Health endpoint |
| `/api/v1/auth/*` | Registration, login, logout, current user, CSRF token |
| `/api/v1/data/plans` | Read available data plans |
| `/api/v1/orders` | Create and list data orders |
| `/api/v1/payments/create` | Initialize Paystack wallet funding |
| `GET /api/v1/payments/callback` | Verify a Paystack payment callback |
| `POST /api/v1/webhooks/paystack` | Signed Paystack webhook |
| `POST /api/v1/webhooks/pairgate` | Signed Pairgate supplier webhook |
| `/api/v1/wallet/*` | Wallet and ledger operations |
| `/api/v1/admin/*` | Administrator operations |

## Security and operational notes

- Keep all credentials in deployment environment variables or a secrets manager.
- Use HTTPS in production and configure the deployment's public callback URL correctly.
- Configure the exact webhook URL in each provider dashboard.
- Do not disable webhook verification in production.
- Back up the SQLite database and protect it as financial data. SQLite is suitable for a small single-instance deployment; a multi-instance or higher-throughput deployment should move to a server database with transaction and migration management.
- Provider credentials, live payment processing, and supplier delivery must be tested in their respective sandbox environments before enabling live mode.

## Tests

There is currently no automated test suite or test command declared in `requirements.txt`. Before production use, add and run unit and integration coverage for amount parsing, missing production secrets, invalid signatures, stale Pairgate timestamps, duplicate webhook delivery, callback/webhook races, wallet-credit idempotency, and supplier refund races.

## License

No license file is currently included. Unless a license is added by the project owner, the source should be treated as all rights reserved.
