# TomOS Premium Generator

A Python command-line utility for generating signed TomOS SIP Premium lifetime licences. Designed for Arch Linux and other Linux distributions.

## Security model

- Uses Ed25519 public-key signatures.
- The generator keeps the private signing key outside the repository.
- The Android app will embed only the public verification key.
- Generated lifetime licences include an ID, issue timestamp, customer reference and the initial Premium feature list.
- A future activation service must redeem codes once and bind licences to devices. This local tool is not a complete purchase, redemption, revocation or activation backend.

## Arch Linux

```bash
sudo pacman -S --needed python python-pip python-cryptography
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Generate the signing key

Run on a trusted admin machine:

```bash
tomos-premiumgen keygen --private-key ~/.config/tomos-premiumgen/private.pem --public-key public.pem
chmod 600 ~/.config/tomos-premiumgen/private.pem
```

Never commit or distribute the private key. Only the public key may be embedded in the Android application.

## Generate a lifetime code and signed licence

```bash
tomos-premiumgen generate --private-key ~/.config/tomos-premiumgen/private.pem --customer "Internal reference" --output ./licences/customer.json
```

The activation code is displayed once. Deliver it privately and never put it in GitHub, logs or screenshots.

## Verify a licence file

```bash
tomos-premiumgen verify --public-key ./public.pem --licence ./licences/customer.json
```

## Tests

```bash
python -m unittest discover -s tests -v
```

See [SECURITY.md](SECURITY.md) for handling signing keys and activation codes.
