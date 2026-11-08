"""Offline-only command line interface for TomOS Premium licences."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from .licence import generate_keypair, read_json, verify_licence, write_json, write_offline_licence_qr
from .offline import issue_offline_licence

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tomos-premiumgen", description="Issue and verify fully offline TomOS SIP Premium lifetime licences.")
    commands = parser.add_subparsers(dest="command", required=True)
    keygen = commands.add_parser("keygen", help="Generate local Ed25519 signing and verification keys.")
    keygen.add_argument("--private-key", type=Path, required=True)
    keygen.add_argument("--public-key", type=Path, required=True)
    keygen.add_argument("--force", action="store_true")
    offline = commands.add_parser("issue-offline", help="Issue a signed lifetime licence for one device without a server or internet connection.")
    offline.add_argument("--private-key", type=Path, required=True)
    offline.add_argument("--device-id", required=True)
    offline.add_argument("--customer", default="")
    offline.add_argument("--output", type=Path, required=True)
    offline.add_argument("--qr-output", type=Path)
    verify = commands.add_parser("verify", help="Verify a signed offline licence file locally.")
    verify.add_argument("--public-key", type=Path, required=True)
    verify.add_argument("--licence", type=Path, required=True)
    commands.add_parser("tui", help="Open the interactive offline terminal interface.")
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
            print(f"Private key: {args.private_key} (keep secret; permissions 0600).")
            print(f"Public key: {args.public_key} (copy into trusted app builds).")
            return 0
        if args.command == "issue-offline":
            if not args.private_key.is_file():
                raise FileNotFoundError(f"Private key not found: {args.private_key}")
            document = issue_offline_licence(args.private_key, args.device_id, args.customer)
            write_json(args.output, document)
            qr = args.qr_output or args.output.with_suffix(".qr.png")
            write_offline_licence_qr(document, qr)
            print(f"Offline lifetime licence issued for device {document['payload']['device_id']}.")
            print(f"Signed licence: {args.output}")
            print(f"QR image: {qr}")
            print("Transfer either file privately. No activation server or internet connection is used.")
            return 0
        if args.command == "verify":
            valid = verify_licence(args.public_key, read_json(args.licence))
            print("VALID: signed TomOS SIP Premium licence." if valid else "INVALID: signature or licence contents did not validate.")
            return 0 if valid else 2
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
