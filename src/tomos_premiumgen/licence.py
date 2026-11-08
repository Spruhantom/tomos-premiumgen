"""Ed25519-signed TomOS SIP lifetime licence format."""

from __future__ import annotations

import base64
import json
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import qrcode
from qrcode.constants import ERROR_CORRECT_M
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

PRODUCT = "tomos-sip"
SCHEMA_VERSION = 1
FEATURES = ("multiple_sip_accounts", "advanced_codec_controls", "encrypted_backup")


def _canonical_json(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def write_offline_licence_qr(document: dict[str, Any], path: Path) -> None:
    """Write the complete signed device-bound licence as a private JSON QR PNG."""
    payload = document.get("payload")
    if not isinstance(payload, dict) or not payload.get("device_id"):
        raise ValueError("Offline QR requires a device-bound licence document.")
    if document.get("signature_algorithm") != "Ed25519" or not document.get("signature") or not document.get("signed_payload"):
        raise ValueError("Offline QR requires a complete Ed25519-signed licence.")
    encoded = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    qr = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_M, box_size=8, border=4)
    qr.add_data(encoded)
    qr.make(fit=True)
    qr.make_image(fill_color="black", back_color="white").save(path, format="PNG")
    path.chmod(0o600)

def generate_keypair(private_path: Path, public_path: Path, overwrite: bool = False) -> None:
    if private_path.resolve() == public_path.resolve():
        raise ValueError("Private and public key paths must be different.")
    if (private_path.exists() or public_path.exists()) and not overwrite:
        raise FileExistsError("Key file already exists; refusing to overwrite without --force.")
    private_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    private_key = Ed25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_bytes = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    private_path.write_bytes(private_bytes)
    private_path.chmod(0o600)
    public_path.write_bytes(public_bytes)
    public_path.chmod(0o644)


def _private_key(path: Path) -> Ed25519PrivateKey:
    key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("Signing key must be Ed25519.")
    return key


def _public_key(path: Path) -> Ed25519PublicKey:
    key = serialization.load_pem_public_key(path.read_bytes())
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError("Verification key must be Ed25519.")
    return key


def issue_licence(private_path: Path, customer: str = "") -> dict[str, Any]:
    customer = customer.strip()
    if len(customer) > 120:
        raise ValueError("Customer reference must be 120 characters or fewer.")
    issued = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    payload: dict[str, Any] = {
        "schema": SCHEMA_VERSION,
        "product": PRODUCT,
        "licence_id": str(uuid.uuid4()),
        "licence_type": "lifetime",
        "issued_at": issued,
        "customer_reference": customer,
        "features": list(FEATURES),
        "activation_code_sha256": secrets.token_hex(32),
    }
    signature = _private_key(private_path).sign(_canonical_json(payload))
    return {
        "payload": payload,
        "signature_algorithm": "Ed25519",
        "signed_payload": base64.b64encode(_canonical_json(payload)).decode("ascii"),
        "signature": base64.b64encode(signature).decode("ascii"),
    }


def verify_licence(public_path: Path, document: dict[str, Any]) -> bool:
    try:
        if set(document) != {"payload", "signature_algorithm", "signed_payload", "signature"}:
            return False
        if document["signature_algorithm"] != "Ed25519":
            return False
        payload = document["payload"]
        if not isinstance(payload, dict):
            return False
        if payload.get("schema") != SCHEMA_VERSION or payload.get("product") != PRODUCT:
            return False
        if payload.get("licence_type") != "lifetime" or payload.get("features") != list(FEATURES):
            return False
        uuid.UUID(payload["licence_id"])
        if not isinstance(payload.get("activation_code_sha256"), str) or len(payload["activation_code_sha256"]) != 64 or any(char not in "0123456789abcdef" for char in payload["activation_code_sha256"]):
            return False
        signed_payload = base64.b64decode(document["signed_payload"], validate=True)
        if signed_payload != _canonical_json(payload):
            return False
        signature = base64.b64decode(document["signature"], validate=True)
        _public_key(public_path).verify(signature, signed_payload)
        return True
    except (KeyError, TypeError, ValueError, OSError):
        return False
    except Exception:
        return False


def write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path.chmod(0o600)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Licence JSON must contain an object.")
    return value
