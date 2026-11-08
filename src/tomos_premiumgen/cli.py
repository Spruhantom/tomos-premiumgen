"""Command line interface for the TomOS Premium licence generator."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .licence import activation_code_matches, generate_keypair, issue_licence, read_json, verify_licence, write_activation_qr, write_offline_licence_qr, write_json
from .offline import issue_offline_licence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tomos-premiumgen", description="Generate TomOS SIP Premium lifetime licences.")
    commands = parser.add_subparsers(dest="command", required=True)

    keygen = commands.add_parser("keygen", help="Generate Ed25519 signing and verification keys.")
    keygen.add_argument("--private-key", type=Path, required=True)
    keygen.add_argument("--public-key", type=Path, required=True)
    keygen.add_argument("--force", action="store_true", help="Explicitly allow replacing existing key files.")

    generate = commands.add_parser("generate", help="Generate an online activation code, signed licence and QR image.")
    generate.add_argument("--private-key", type=Path, required=True)
    generate.add_argument("--customer", default="", help="Optional internal customer reference; avoid personal data.")
    generate.add_argument("--output", type=Path, required=True)
    generate.add_argument("--qr-output", type=Path, help="QR PNG output path (default: <licence-output>.qr.png).")

    offline = commands.add_parser("issue-offline", help="Issue a signed lifetime licence for one device without a server.")
    offline.add_argument("--private-key", type=Path, required=True)
    offline.add_argument("--device-id", required=True, help="UUID displayed by TomOS SIP on the customer's device.")
    offline.add_argument("--customer", default="", help="Optional internal customer reference; avoid personal data.")
    offline.add_argument("--output", type=Path, required=True)
    offline.add_argument("--qr-output", type=Path, help="QR PNG output path (default: <licence-output>.qr.png).")

    register = commands.add_parser("register", help="Import a generated code and signed licence into the optional redemption database.")
    register.add_argument("--public-key", type=Path, required=True)
    register.add_argument("--licence", type=Path, required=True)
    register.add_argument("--activation-code", required=True)
    register.add_argument("--database", type=Path, default=Path("tomos-licences.sqlite3"))

    commands.add_parser("tui", help="Open the interactive terminal interface.")

    verify = commands.add_parser("verify", help="Verify a signed licence file.")
    verify.add_argument("--public-key", type=Path, required=True)
    verify.add_argument("--licence", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "tui":
        from .tui import run_tui
        run_tui()
        return 0
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
            qr_output = args.qr_output or args.output.with_suffix(".qr.png")
            write_activation_qr(code, qr_output)
            print("Premium lifetime activation code (deliver privately; shown only once):")
            print(code)
            print(f"Signed licence document: {args.output}")
            print(f"Activation QR image: {qr_output} (keep private; it grants redemption access).")
            print("Never commit activation codes, QR images or the private signing key.")
            return 0
        if args.command == "issue-offline":
            if not args.private_key.is_file():
                raise FileNotFoundError(f"Private key not found: {args.private_key}")
            document = issue_offline_licence(args.private_key, args.device_id, args.customer)
            write_json(args.output, document)
            qr_output = args.qr_output or args.output.with_suffix(".qr.png")
            write_offline_licence_qr(document, qr_output)
            print(f"Offline lifetime licence issued for device {document['payload']['device_id']}.")
            print(f"Signed licence document: {args.output}")
            print(f"Offline licence QR image: {qr_output} (contains the signed licence; keep private).")
            print("The QR contains the complete signed licence; the receiving app must support scanning/import.")
            return 0
        if args.command == "register":
            import hashlib
            import json
            import sqlite3
            document = read_json(args.licence)
            if not verify_licence(args.public_key, document):
                raise ValueError("Licence signature or contents are invalid.")
            if not activation_code_matches(args.activation_code, document):
                raise ValueError("Activation code does not match this signed licence.")
            args.database.parent.mkdir(parents=True, exist_ok=True)
            normalized = "".join(args.activation_code.split()).upper()
            digest = hashlib.sha256(normalized.encode("ascii")).hexdigest()
            try:
                with sqlite3.connect(args.database) as db:
                    db.execute("CREATE TABLE IF NOT EXISTS licences (code_hash TEXT PRIMARY KEY, licence_id TEXT NOT NULL UNIQUE, licence_json TEXT NOT NULL, device_id TEXT, redeemed_at TEXT)")
                    db.execute("INSERT INTO licences (code_hash, licence_id, licence_json) VALUES (?, ?, ?)", (digest, document["payload"]["licence_id"], json.dumps(document, separators=(",", ":"))))
            except sqlite3.IntegrityError as error:
                raise ValueError("This activation code or licence has already been registered.") from error
            print(f"Registered licence {document['payload']['licence_id']} in {args.database}")
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
