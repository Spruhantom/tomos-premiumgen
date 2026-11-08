# TomOS Premium Generator

A Python command-line utility for generating signed TomOS SIP Premium lifetime licences and private activation QR images. Designed for Arch Linux and other Linux distributions.

## Security model

- Uses Ed25519 public-key signatures.
- The generator keeps the private signing key outside the repository.
- The Android app will embed only the public verification key.
- Generated lifetime licences include an ID, issue timestamp, customer reference and the initial Premium feature list.
- The activation QR contains the one-time activation code only. It does not contain a signing key or an unsigned entitlement.
- Redemption remains online, HTTPS-only and bound to the first device that redeems the code.
- Treat QR images exactly like activation codes: deliver privately and never commit, publish or include them in logs or screenshots.
- This local tool is not a complete purchase, redemption, revocation or activation backend.

## Arch Linux

```bash
sudo pacman -S --needed python python-pip python-cryptography
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Install from PKGBUILD

After creating a tagged release `v0.1.0`, build and install the Arch package:

```bash
makepkg -si
```

The PKGBUILD currently uses a source checksum placeholder. Before publishing an AUR package or using the PKGBUILD for production, replace `sha256sums=('SKIP')` with the verified source archive SHA-256.

## Generate the signing key

Run on a trusted admin machine:

```bash
tomos-premiumgen keygen --private-key ~/.config/tomos-premiumgen/private.pem --public-key public.pem
chmod 600 ~/.config/tomos-premiumgen/private.pem
```

Never commit or distribute the private key. Only the public key may be embedded in the Android application.

## Generate a lifetime code, signed licence and QR image

```bash
tomos-premiumgen generate --private-key ~/.config/tomos-premiumgen/private.pem --customer "Internal reference" --output ./licences/customer.json
```

This creates:
- `customer.json`: the Ed25519-signed lifetime licence.
- `customer.qr.png`: a QR image containing the one-time activation code, saved with owner-only permissions.

Use `--qr-output /secure/path/customer.png` to choose a different QR image path. The activation code is displayed once. Deliver the code and QR image privately; either can be used to redeem the licence.

## Verify a licence file

```bash
tomos-premiumgen verify --public-key ./public.pem --licence ./licences/customer.json
```

## Tests

```bash
python -m unittest discover -s tests -v
```

See [SECURITY.md](SECURITY.md) for handling signing keys and activation codes.
