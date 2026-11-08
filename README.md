# TomOS Premium Generator

TomOS Premium Generator is an **offline-only** tool for creating and verifying Ed25519-signed, device-bound lifetime licences for TomOS SIP. It includes GTK 4, Textual and command-line interfaces.

There is no activation server, redemption API, account service, online licence check, or internet requirement for issuing or activating a licence. The Android app verifies the signature locally and checks the signed installation UUID before saving the licence encrypted with Android Keystore.

## Install (Arch, Ubuntu, Debian and Fedora)

```bash
curl -fsSL https://raw.githubusercontent.com/Spruhantom/tomos-premiumgen/main/install.sh | bash
```

Launch **TomOS Premium Code Generator** from the desktop menu, or run `tomos-premiumgen-gui`. The CLI and TUI are also available. Uninstall with:

```bash
curl -fsSL https://raw.githubusercontent.com/Spruhantom/tomos-premiumgen/main/install.sh | bash -s -- --uninstall
```

## Offline workflow

1. On the phone, open Premium and copy its installation UUID.
2. Transfer that UUID to the administrator using a trusted offline or out-of-band method.
3. Generate a device-bound licence and QR image on the administrator's computer:

```bash
tomos-premiumgen keygen --private-key ~/.config/tomos-premiumgen/private.pem --public-key ~/.config/tomos-premiumgen/public.pem

tomos-premiumgen issue-offline \
  --private-key ~/.config/tomos-premiumgen/private.pem \
  --device-id 123e4567-e89b-12d3-a456-426614174000 \
  --customer "Order reference" \
  --output ./licences/customer.json
```

4. Transfer the JSON file or companion PNG QR image to the matching phone.
5. Scan/import it in TomOS SIP. The app verifies the Ed25519 signature and device UUID locally, then stores the signed document encrypted with Android Keystore.

Verify a licence on the administrator's computer:

```bash
tomos-premiumgen verify --public-key ~/.config/tomos-premiumgen/public.pem --licence ./licences/customer.json
```

## Security

- The private Ed25519 signing key stays on the administrator's computer and must never be included in the app or repository.
- Android builds contain only the public verification key.
- The licence payload includes the installation UUID and is cryptographically signed; changing either invalidates the signature.
- The Android app re-verifies the stored licence after restart. Invalid, tampered, malformed, or wrong-device licences do not unlock Premium.
- Offline licences do not depend on servers, network access, accounts, or remote checks. They cannot be remotely revoked. Refunds and replacement-device reissues must be handled by the licence administrator.
- Keep licence files and QR images private, and back up the signing key securely.

## Tests

```bash
python -m unittest discover -s tests -v
```
