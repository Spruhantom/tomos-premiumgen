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

## GTK desktop features

- Generate Ed25519 signing and verification keys.
- Generate online lifetime activation codes, signed licence JSON and a private QR image.
- Issue device-bound offline lifetime licences using the UUID displayed by TomOS SIP.
- Verify signed licence documents.
- Copy newly generated online activation codes to the clipboard.
- Keep private signing keys on the local administrator machine.

## CLI and TUI remain available

The GTK app does not replace the existing automation interfaces:

```bash
tomos-premiumgen --help
tomos-premiumgen tui
tomos-premiumgen-tui
```

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
- The offline workflow has no central redemption or revocation service.

See [SECURITY.md](SECURITY.md) for signing-key handling.

## Tests

```bash
python -m unittest discover -s tests -v
```
