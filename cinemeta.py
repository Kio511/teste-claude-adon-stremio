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
    meta = get_full_meta(imdb_id, content_type)
    return meta.get("name") if meta else None


def get_full_meta(imdb_id: str, content_type: str) -> dict | None:
    """
    Busca o objeto `meta` completo do Cinemeta (nome, descrição, poster,
    gêneros, lista de episódios no caso de série, etc). Vamos usar isso
    como base e só adicionar/alterar alguns campos antes de devolver pro
    Stremio.
    """
    url = f"{CINEMETA_BASE}/{content_type}/{imdb_id}.json"
    try:
        resp = httpx.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("meta")
    except (httpx.HTTPError, ValueError):
        return None
