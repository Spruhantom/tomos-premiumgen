"""Secure SQLite storage shared by the admin CLI and redemption API."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path


def connect_licence_db(path: Path) -> sqlite3.Connection:
    """Open the licence database with restrictive permissions and a busy timeout."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    try:
        os.fchmod(fd, 0o600)
    finally:
        os.close(fd)

    db = sqlite3.connect(path, timeout=10)
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
