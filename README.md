# TomOS Premium Generator

TomOS Premium Generator creates and verifies Ed25519-signed lifetime licences for TomOS SIP. It provides a GTK 4 desktop application, a retained Textual TUI and a command-line interface.

## Install on Debian, Ubuntu, Fedora or Arch Linux

Review the installer before running it if you prefer to inspect scripts first:

```bash
curl -fsSL https://raw.githubusercontent.com/Spruhantom/tomos-premiumgen/main/install.sh | bash
```

The installer detects the distribution, installs GTK 4 and its Python bindings using the native package manager, then installs the Python application into an isolated per-user virtual environment. It creates a desktop-menu entry and does not run the application as root. The signing key is not created or copied by the installer. To preview the detected distribution and required system packages without installing anything, run `curl -fsSL https://raw.githubusercontent.com/Spruhantom/tomos-premiumgen/main/install.sh | bash -s -- --check`.

Launch **TomOS Premium Code Generator** from the desktop application menu, or run:

```bash
tomos-premiumgen-gui
```

To uninstall the application:

```bash
curl -fsSL https://raw.githubusercontent.com/Spruhantom/tomos-premiumgen/main/install.sh | bash -s -- --uninstall
```

Uninstall removes the application, command links and desktop entry. It deliberately leaves system GTK/Python dependencies and signing keys untouched.

## GTK desktop workflow

The desktop app now opens with four clear tasks instead of showing every field at once:

1. **Create online activation** — choose the signing key, optionally add a customer reference, and save the signed licence. The activation code is copied to the clipboard and displayed once; the private QR image is saved beside the licence.
2. **Issue offline licence** — enter the device UUID shown in TomOS SIP and save a licence bound to that device.
3. **Verify a licence** — select the public key and licence file to check the signature and supported licence contents.
4. **Signing keys** — create the Ed25519 private/public key pair. The private key stays on the administrator's computer.

Each task displays only the fields it needs, has a Home button, and reports success or a clear error. The command-line and Textual interfaces remain available for automation and terminal users.

## CLI and TUI remain available

The GTK app does not replace the existing automation interfaces:

```bash
tomos-premiumgen --help
tomos-premiumgen tui
tomos-premiumgen-tui
```


## Optional online redemption server

The optional FastAPI service lets TomOS SIP redeem a pre-issued activation code once and bind it to the first device that claims it. Install the server extra:

```bash
python -m pip install '.[server]'
```

Use the same database path for admin imports and the API process. Import a signed licence after checking its public-key signature:

```bash
export TOMOS_LICENCE_DB="$HOME/.local/share/tomos-premiumgen/licences.sqlite3"
read -rsp "Activation code: " TOMOS_ACTIVATION_CODE
printf '\n'
tomos-premiumgen register \
  --public-key ~/.config/tomos-premiumgen/public.pem \
  --licence ./licences/customer.json \
  --activation-code "$TOMOS_ACTIVATION_CODE" \
  --database "$TOMOS_LICENCE_DB"
unset TOMOS_ACTIVATION_CODE
```

Start the API:

```bash
export TOMOS_LICENCE_DB="$HOME/.local/share/tomos-premiumgen/licences.sqlite3"
tomos-premiumgen-server --host 127.0.0.1 --port 8000
```

The server binds to **127.0.0.1 by default**. Put it behind a properly configured HTTPS reverse proxy for remote devices; configure TLS, request-size limits, rate limiting, firewall rules and monitoring at that layer. Do not expose the development server directly to the public internet. The database file is created with owner-only permissions (0600).

- `GET /health` returns a basic health status.
- `POST /v1/redeem` accepts JSON containing `activation_code` and `device_id`, and returns the signed licence document.
- The first device to redeem a code claims it. Repeated redemption from that same device is idempotent; a different device receives HTTP 409.
- `POST /admin/import` is intentionally disabled. Import licences using the local `tomos-premiumgen register` command.

Example request (replace the sample values with the customer's code and TomOS SIP device UUID):

```bash
curl -fsS http://127.0.0.1:8000/v1/redeem \
  -H 'Content-Type: application/json' \
  -d '{"activation_code":"TOMOS-PREM-ABCD-EFGH-IJKL-MNOP","device_id":"123e4567-e89b-12d3-a456-426614174000"}'
```

The Android application must verify the returned Ed25519 signature locally with its embedded public key before enabling Premium features. The API is a starter service, not a complete production licensing platform: it does not provide customer authentication, payment processing, remote revocation or distributed rate limiting.

## Offline activation

The customer shares the device UUID displayed in TomOS SIP. The administrator issues a signed licence file, then transfers it securely to the customer:

```bash
tomos-premiumgen issue-offline \
  --private-key ~/.config/tomos-premiumgen/private.pem \
  --device-id 123e4567-e89b-12d3-a456-426614174000 \
  --customer "Order reference" \
  --output ./licences/customer.json
```

## Security model

- The private Ed25519 signing key stays on the trusted generator machine and outside the repository.
- Android contains only the public verification key.
- Activation codes, QR images and licence files grant activation access and must be delivered privately.
- The GUI creates private key and licence files with restrictive file permissions through the shared core implementation.
- The installer does not create, upload, back up or replace signing keys.
- Offline device-bound licences work without a server and do not support central redemption or revocation.

See [SECURITY.md](SECURITY.md) for signing-key handling.

## Tests

```bash
python -m unittest discover -s tests -v
```
