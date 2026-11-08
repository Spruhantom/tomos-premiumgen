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

## Debian home-server deployment (systemd + HTTPS)

The installer has a separate server mode for a Debian host. It installs the optional
FastAPI service into an isolated system virtual environment, creates a dedicated
unprivileged `tomospremium` account, stores the SQLite database under
`/var/lib/tomos-premiumgen`, and manages the API with a hardened systemd system
service. Caddy is installed as the HTTPS reverse proxy and is configured to request
a Let's Encrypt IP-address certificate using the `shortlived` ACME profile.

The installer is now available on `main`. Run this on the Debian server (replace
the example address and email):

```bash
curl -fsSL https://raw.githubusercontent.com/Spruhantom/tomos-premiumgen/main/install.sh | sudo bash -s -- --install-server --public-ip 203.0.113.10 --email admin@example.com
```

Use your real globally routable public IPv4 address, not the documentation example.
The server installer refuses private, reserved or malformed addresses. It is
Debian-only; the existing desktop installer remains available for Debian, Ubuntu,
Fedora and Arch.

See [the full home-server deployment guide](docs/HOME_SERVER_DEPLOYMENT.md) for operational checks, backups and troubleshooting.

The router must forward **TCP 80 and TCP 443** to the Debian server, and the host
firewall must permit those ports. The router WAN IPv4 must match the supplied
public IP; CGNAT prevents direct inbound port forwarding. Let's Encrypt IP
certificates use a 160-hour lifetime, so Caddy must remain running and able to
renew them automatically. If the ISP changes the public IP, rerun the server
installer with the new address and ensure the router forwards to the host.

The service listens only on `127.0.0.1:8000`; Caddy exposes
`https://YOUR_PUBLIC_IP`. The reverse proxy limits request bodies and blocks
the unused admin/import and interactive API documentation paths. Licence imports
remain a local administrator CLI operation using the same database:

```bash
sudo -u tomospremium /opt/tomos-premiumgen-server/venv/bin/tomos-premiumgen register \
  --public-key /path/to/public.pem \
  --licence /path/to/customer.json \
  --activation-code 'CUSTOMER-ACTIVATION-CODE' \
  --database /var/lib/tomos-premiumgen/licences.sqlite3
```

Check the daemon and logs with:

```bash
sudo systemctl status tomos-premiumgen-server
sudo journalctl -u tomos-premiumgen-server -f
curl -fsS https://YOUR_PUBLIC_IP/health
```

Uninstall the server components (the licence database is deliberately retained):

```bash
curl -fsSL https://raw.githubusercontent.com/Spruhantom/tomos-premiumgen/main/install.sh | sudo bash -s -- --uninstall-server
```

**Deployment limitation:** this API currently has no customer authentication or
distributed rate limiter. The installer does not claim to provide those controls;
monitor the service and restrict inbound traffic as appropriate before a
commercial public launch. Back up `/var/lib/tomos-premiumgen` securely.

## GTK desktop workflow

The desktop app now opens with five clear tasks instead of showing every field at once:

1. **Create online activation** — choose the signing key, optionally add a customer reference, and save the signed licence. The activation code is copied to the clipboard and displayed once; the private QR image is saved beside the licence.
2. **Issue offline licence** — enter the device UUID shown in TomOS SIP and save a licence bound to that device.
3. **Verify a licence** — select the public key and licence file to check the signature and supported licence contents.
4. **Signing keys** — create the Ed25519 private/public key pair. The private key stays on the administrator's computer.
5. **Redemption server setup** — prepare a loopback-only user service and private database directory; the wizard does not start or expose the service.

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

## Guided redemption-server setup

The GTK app includes a **Redemption server setup** task. It prepares a per-user
systemd service and a private SQLite database directory. The generated service
binds only to `127.0.0.1`; it is not enabled or started automatically, and an
existing service file is never overwritten.

After preparing the service, follow the commands shown in the app to install
the optional FastAPI/uvicorn dependencies, enable the user service and check
`/health`. Import each signed licence locally with the `register` command.
For remote devices, place the API behind a correctly configured HTTPS reverse
proxy with request limits, rate limiting, firewall rules and monitoring. Do not
expose the development server directly to the public internet.

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
