"""
O Stremio manda pro addon apenas o imdb_id (ex: tt1234567), não o título.
Pra buscar na JustWatch (que trabalha por texto), precisamos do título.

O Cinemeta é o addon oficial de metadados do Stremio e expõe uma API HTTP
pública e simples — usamos ela só pra resolver imdb_id -> título.
"""

from __future__ import annotations

import httpx

CINEMETA_BASE = "https://v3-cinemeta.strem.io/meta"


def get_title(imdb_id: str, content_type: str) -> str | None:
    """
    content_type: "movie" ou "series"
    """
    url = f"{CINEMETA_BASE}/{content_type}/{imdb_id}.json"
    try:
        resp = httpx.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("meta", {}).get("name")
    except (httpx.HTTPError, ValueError):
        return None
