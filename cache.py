"""
Cache local em SQLite. Guarda o resultado da checagem de dublagem por
imdb_id, com um TTL (padrão 7 dias) pra revalidar de vez em quando —
catálogos de streaming mudam.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).parent / "cache.sqlite3"
DEFAULT_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 dias


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS dubbing_cache (
            imdb_id TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            updated_at REAL NOT NULL
        )
        """
    )
    return conn


def get(imdb_id: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> dict | None:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT payload, updated_at FROM dubbing_cache WHERE imdb_id = ?", (imdb_id,)
        ).fetchone()
        if row is None:
            return None
        payload, updated_at = row
        if time.time() - updated_at > ttl_seconds:
            return None  # expirado, precisa revalidar
        return json.loads(payload)
    finally:
        conn.close()


def set(imdb_id: str, payload: dict) -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO dubbing_cache (imdb_id, payload, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(imdb_id) DO UPDATE SET payload = excluded.payload, updated_at = excluded.updated_at
            """,
            (imdb_id, json.dumps(payload), time.time()),
        )
        conn.commit()
    finally:
        conn.close()
