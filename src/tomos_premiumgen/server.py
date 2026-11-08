"""Minimal FastAPI redemption API for pre-issued TomOS Premium licences.

This service is a starter deployment. Put it behind HTTPS and a production
reverse proxy; never expose its SQLite file or admin import command.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .storage import connect_licence_db

DB_PATH = Path(os.environ.get("TOMOS_LICENCE_DB", "tomos-licences.sqlite3"))
_CODE_PATTERN = re.compile(r"TOMOS-PREM-(?:[A-Z2-7]{4}-){3}[A-Z2-7]{4}")

app = FastAPI(title="TomOS Premium Licence API", version="0.1.0")


def connect() -> sqlite3.Connection:
    return connect_licence_db(DB_PATH)


class RedeemRequest(BaseModel):
    activation_code: str = Field(min_length=10, max_length=64)
    device_id: str = Field(min_length=16, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")


class RedeemResponse(BaseModel):
    licence: dict


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/v1/redeem", response_model=RedeemResponse)
def redeem(request: RedeemRequest) -> RedeemResponse:
    code = "".join(request.activation_code.split()).upper()
    if not _CODE_PATTERN.fullmatch(code):
        raise HTTPException(status_code=400, detail="Activation code format is invalid.")
    digest = hashlib.sha256(code.encode("ascii")).hexdigest()

    # Acquire the SQLite write reservation before reading so two devices cannot
    # both observe an unused code and race to claim it.
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM licences WHERE code_hash = ?", (digest,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Activation code not recognised.")
        if row["device_id"] is not None and row["device_id"] != request.device_id:
            raise HTTPException(status_code=409, detail="This activation code has already been redeemed on another device.")
        if row["device_id"] is None:
            db.execute(
                "UPDATE licences SET device_id = ?, redeemed_at = CURRENT_TIMESTAMP WHERE code_hash = ? AND device_id IS NULL",
                (request.device_id, digest),
            )
            row = db.execute("SELECT * FROM licences WHERE code_hash = ?", (digest,)).fetchone()
        if row["device_id"] != request.device_id:
            raise HTTPException(status_code=409, detail="This activation code has already been redeemed on another device.")
        licence = json.loads(row["licence_json"])
    return RedeemResponse(licence=licence)


@app.post("/admin/import")
def import_licence() -> dict:
    # Intentionally disabled: importing licence bundles is an offline admin CLI task.
    raise HTTPException(status_code=405, detail="Use the offline admin import command; this endpoint is disabled.")



def main() -> int:
    """Start the redemption API, bound to loopback unless explicitly overridden."""
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="Run the TomOS Premium redemption API.")
    parser.add_argument(
        "--host",
        default=os.environ.get("TOMOS_SERVER_HOST", "127.0.0.1"),
        help="Bind address (default: 127.0.0.1; use a reverse proxy for public HTTPS).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("TOMOS_SERVER_PORT", "8000")),
        help="TCP port (default: 8000).",
    )
    parser.add_argument("--log-level", choices=("critical", "error", "warning", "info", "debug"), default="info")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    uvicorn.run("tomos_premiumgen.server:app", host=args.host, port=args.port, log_level=args.log_level)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
