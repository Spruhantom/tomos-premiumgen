# TomOS Premium Generator

A Python command-line utility for generating signed TomOS SIP Premium lifetime licences. Designed for Arch Linux and Omarchy Linux.

## Offline activation (recommended)

Offline activation does not require an activation server or an internet connection on the customer's Android device. The customer shares the device UUID displayed in TomOS SIP with the administrator. The administrator issues a signed licence file, then transfers that file to the customer (USB, local file transfer, or another private channel).

```bash
tomos-premiumgen issue-offline \
  --private-key ~/.config/tomos-premiumgen/private.pem \
  --device-id 123e4567-e89b-12d3-a456-426614174000 \
  --customer "Order reference" \
  --output ./licences/customer.json
```

The licence payload contains the device UUID and is signed with Ed25519. TomOS SIP must verify both the signature and that the embedded UUID matches its own installation ID before enabling Premium. A copied licence must not activate a different installation.

## Security model

- The private Ed25519 signing key stays on the trusted generator machine and outside the repository.
- Android contains only the public verification key.
- Device IDs and licence files should be transferred privately.
- A lifetime licence is device-bound; reinstalling the app or changing its installation identity may require a newly issued licence.
- The offline workflow has no central redemption or revocation service. Protect the signing key and issue replacement licences deliberately.
- The optional online redemption command remains available, but is not required for offline activation.

## Arch Linux / Omarchy Linux

```bash
sudo pacman -S --needed python python-pip python-cryptography
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Generate the signing key

Run on a trusted administrator machine:

```bash
tomos-premiumgen keygen --private-key ~/.config/tomos-premiumgen/private.pem --public-key public.pem
chmod 600 ~/.config/tomos-premiumgen/private.pem
```

Never commit or distribute the private key. Only the public key may be embedded in the Android application.

## Optional online activation code

```bash
tomos-premiumgen generate --private-key ~/.config/tomos-premiumgen/private.pem --customer "Internal reference" --output ./licences/customer.json
```

This generates an activation code, signed licence and private QR image for the optional online redemption service.

## Verify a licence file

```bash
tomos-premiumgen verify --public-key ./public.pem --licence ./licences/customer.json
```

## Tests

```bash
python -m unittest discover -s tests -v
```

See [SECURITY.md](SECURITY.md) for signing-key handling.
