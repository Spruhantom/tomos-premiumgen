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

DB_PATH = Path(os.environ.get("TOMOS_LICENCE_DB", "tomos-licences.sqlite3"))
_CODE_PATTERN = re.compile(r"TOMOS-PREM-(?:[A-Z2-7]{4}-){3}[A-Z2-7]{4}")

app = FastAPI(title="TomOS Premium Licence API", version="0.1.0")


def connect() -> sqlite3.Connection:
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout = 10000")
    db.execute("""
        CREATE TABLE IF NOT EXISTS licences (
            code_hash TEXT PRIMARY KEY,
            licence_id TEXT NOT NULL UNIQUE,
            licence_json TEXT NOT NULL,
            device_id TEXT,
            redeemed_at TEXT
        )
    """)
    return db


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
