# Redemption API (starter)

Install server dependencies with `pip install -e '.[server]'`.

Set environment variables:
- `TOMOS_LICENCE_DB`: SQLite database path.
- `TOMOS_PUBLIC_KEY`: Ed25519 public key path.
- `TOMOS_ADMIN_TOKEN`: reserved for future authenticated admin operations.

Run locally for development:
```bash
uvicorn tomos_premiumgen.server:app --host 127.0.0.1 --port 8080
```

The app provides `GET /health` and `POST /v1/redeem`. Import codes into SQLite only from the trusted admin machine; never expose an unauthenticated import endpoint.

**Deployment warning:** this is a starter API, not production-ready payment infrastructure. Put it behind HTTPS, add authentication/monitoring/backups/rate limits, and define device-transfer and refund procedures before selling licences. Current redemption binds a code to one installation ID; replacing a device requires an administrator reset procedure which is not yet included.
