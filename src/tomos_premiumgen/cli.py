"""Command line interface for the TomOS Premium licence generator."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .licence import generate_keypair, issue_licence, read_json, verify_licence, write_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tomos-premiumgen", description="Generate TomOS SIP Premium lifetime licences.")
    commands = parser.add_subparsers(dest="command", required=True)

    keygen = commands.add_parser("keygen", help="Generate Ed25519 signing and verification keys.")
    keygen.add_argument("--private-key", type=Path, required=True)
    keygen.add_argument("--public-key", type=Path, required=True)
    keygen.add_argument("--force", action="store_true", help="Explicitly allow replacing existing key files.")

    generate = commands.add_parser("generate", help="Generate a one-time activation code and signed licence.")
    generate.add_argument("--private-key", type=Path, required=True)
    generate.add_argument("--customer", default="", help="Optional internal customer reference; avoid personal data.")
    generate.add_argument("--output", type=Path, required=True)

    verify = commands.add_parser("verify", help="Verify a signed licence file.")
    verify.add_argument("--public-key", type=Path, required=True)
    verify.add_argument("--licence", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "keygen":
            generate_keypair(args.private_key, args.public_key, args.force)
            print(f"Private key written to {args.private_key} (keep secret; permissions 0600).")
            print(f"Public key written to {args.public_key} (safe to distribute).")
            return 0
        if args.command == "generate":
            if not args.private_key.is_file():
                raise FileNotFoundError(f"Private key not found: {args.private_key}")
            code, document = issue_licence(args.private_key, args.customer)
            write_json(args.output, document)
            print("Premium lifetime activation code (deliver privately; shown only once):")
            print(code)
            print(f"Signed licence document: {args.output}")
            print("Never commit activation codes or the private signing key.")
            return 0
        if args.command == "verify":
            valid = verify_licence(args.public_key, read_json(args.licence))
            print("VALID: signed TomOS SIP Premium lifetime licence." if valid else "INVALID: signature or licence contents did not validate.")
            return 0 if valid else 2
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
