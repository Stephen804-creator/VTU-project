# Subscribe Me (VTU Project)

Subscribe Me is a Flask-based VTU application for account registration, wallet funding, data-plan browsing, data purchases, transaction history, and administrative plan/order operations.

## Technology

- Python 3 and Flask
- SQLite for the current persistence implementation
- Paystack for online wallet funding
- Pairgate for data-plan supply and purchase fulfilment
- Server-rendered HTML with browser-side JavaScript

## Local setup

1. Create and activate a Python virtual environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and set the provider credentials you intend to use.
4. Start the application:

   ```bash
   python app.py
   ```

The default local database path is `data/subscribe_me.db`. The application creates its tables on startup.

## Configuration

Important environment variables:

| Variable | Purpose |
| --- | --- |
| `APP_ENV` | Use `development` locally and `production` for deployment. |
| `SECRET_KEY` | Required in production; used to sign Flask sessions. |
| `DATABASE_PATH` | SQLite database file path. Must point to persistent storage in a deployment. |
| `PAIRGATE_API_KEY` | Pairgate API credential. |
| `PAIRGATE_BASE_URL` | Pairgate API base URL. |
| `PAIRGATE_TEST_MODE` | Uses Pairgate test endpoints when `true`; must be `false` in production. |
| `PAIRGATE_WEBHOOK_SECRET` | Shared secret used to authenticate Pairgate webhooks. |
| `PAIRGATE_WEBHOOK_VERIFY` | Controls Pairgate signature verification; keep enabled. |
| `PAIRGATE_WEBHOOK_TOLERANCE_SECONDS` | Accepted timestamp window (30–900 seconds; default 300). |
| `PAYSTACK_SECRET_KEY` | Paystack secret key used for API verification and webhook signatures. |
| `PAYSTACK_TEST_MODE` | Configuration guard; must be `false` in production. |
| `PAYSTACK_BASE_URL` | Paystack API base URL. |
| `PORT` | Local/server listening port. |

Never commit real credentials. Configure production secrets in the hosting provider's secret/environment-variable settings, not in source control. Production startup fails if `SECRET_KEY` is absent, if Pairgate is enabled without its webhook secret, or if either provider's test-mode flag is enabled.

## Payment and order safety

- Paystack webhook requests are authenticated using the HMAC-SHA512 signature over the raw request body.
- The Paystack callback independently verifies the transaction with Paystack before crediting the wallet.
- Paystack reference, NGN currency, success status, transaction ID, and expected amount are checked before wallet funding.
- Payment state changes and wallet-ledger credit are committed in one database transaction.
- Wallet funding uses a stable ledger reference so a repeated verified event cannot credit the wallet twice.
- Pairgate webhook signatures include a timestamp and raw payload; stale signatures are rejected.
- Pairgate order status transitions and refunds are processed atomically. Duplicate failed callbacks cannot create a second refund.
- Data-purchase requests accept an `Idempotency-Key` header. The browser client sends a key and reuses it when retrying the same submission.
- The former generic `/api/v1/webhooks/payment` endpoint is disabled because it accepted unverified payment statuses. It returns HTTP 410. Use the verified Paystack endpoint instead.

## Database and deployment limitations

The current application uses SQLite, not PostgreSQL. SQLite is suitable for local development and a carefully configured single-instance deployment with a persistent disk. It is not a safe assumption for horizontally scaled or multi-instance wallet/payment workloads.

Before operating a real-money service at scale, plan and test a migration to a managed transactional database such as PostgreSQL, including schema migrations, concurrency tests, backups, restore drills, monitoring, and payment reconciliation. Do not deploy multiple application instances against an ephemeral or shared SQLite file.

Provider credentials, webhook delivery, supplier purchase semantics, refund/reconciliation behaviour, hosting persistence, and live transactions must be tested in the respective provider sandbox and then in a controlled production rollout. Passing the repository's automated tests does not replace those checks.

## Checks

The GitHub Actions workflow compiles the Python modules and runs the regression tests:

```bash
python -m compileall -q .
pytest -q
```

The tests cover unsigned webhook rejection, Pairgate signature freshness, Paystack wallet-credit idempotency and amount validation, Pairgate refund idempotency, and order-request idempotency.

## Current status

This repository is an educational/portfolio project with payment and supplier integrations. It should not be described as a fully production-ready financial service until the remaining deployment, database, provider-sandbox, operational, and security checks have been completed.
