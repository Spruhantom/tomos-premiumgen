"""Device-bound, fully offline Premium licence issuance."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from .licence import _canonical_json, _private_key, issue_licence


def issue_offline_licence(
    private_path: Path, device_id: str, customer: str = ""
) -> dict[str, Any]:
    """Issue a signed lifetime licence bound to one Android installation UUID."""
    try:
        normalized_device_id = str(uuid.UUID(device_id))
    except (ValueError, TypeError, AttributeError) as error:
        raise ValueError("Device ID must be a valid UUID shown by TomOS SIP.") from error

    document = issue_licence(private_path, customer)
    payload = dict(document["payload"])
    payload["device_id"] = normalized_device_id
    signed_payload = _canonical_json(payload)
    signature = _private_key(private_path).sign(signed_payload)
    document["payload"] = payload
    import base64

    document["signed_payload"] = base64.b64encode(signed_payload).decode("ascii")
    document["signature"] = base64.b64encode(signature).decode("ascii")
    return document
