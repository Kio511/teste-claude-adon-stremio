"""
Addon Stremio: "Dublado PT-BR?"

Resources oferecidos:
  - meta:    tela de detalhes do título (descrição + tag de gênero)
  - stream:  entrada informativa na lista de streams
  - catalog: "Animes Dublados PT-BR" — lista navegável já filtrada

Configurável: usuário escolhe em /configure qual serviço considerar
(todos / só Crunchyroll / só Netflix / só Prime Video). Essa escolha
vira um trecho extra na URL (ver addon_config.py) que o Stremio repassa
automaticamente em toda chamada — por isso quase toda rota abaixo tem
duas versões: com e sem o prefixo "{config}/".

Rodar localmente:
    pip install -r requirements.txt
    uvicorn main:app --reload --port 7000
Depois abra http://127.0.0.1:7000/configure pra gerar o link de instalação.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

import cache
import cinemeta
from addon_config import AddonConfig, filter_providers, parse_config
from configure_page import render_configure_page
from justwatch_client import check_pt_br_dubbing

app = FastAPI(title="Stremio Addon - Dublado PT-BR")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)  # evita crash no boot se a pasta não veio no deploy
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

CATALOG_ID = "dublado-ptbr-animes"
SEED_PATH = Path(__file__).parent / "anime_catalog_seed.json"

MANIFEST = {
    "id": "community.dublado-ptbr",
    "version": "0.3.0",
    "name": "Dublado PT-BR?",
    "description": "Mostra se um anime/série/filme tem dublagem em português do Brasil disponível (via JustWatch: Crunchyroll, Netflix, Prime Video), na tela de detalhes e em um catálogo próprio.",
    "logo": "/static/logo.svg",
    "resources": ["meta", "stream", "catalog"],
    "types": ["movie", "series"],
    "catalogs": [
        {
            "type": "series",
            "id": CATALOG_ID,
            "name": "Animes Dublados PT-BR",
        }
    ],
    "idPrefixes": ["tt"],
    "behaviorHints": {
        "configurable": True,
        "configurationRequired": False,
    },
    "config": [
        {
            "key": "providers",
            "type": "select",
            "title": "Serviço a considerar",
            "options": ["all", "crunchyroll", "netflix", "primevideo"],
            "default": "all",
        }
    ],
}


def _base_url(request: Request) -> str:
    # Render fica atrás de proxy HTTPS; força https no link gerado.
    scheme = "https" if request.url.hostname != "127.0.0.1" and request.url.hostname != "localhost" else request.url.scheme
    return f"{scheme}://{request.url.netloc}"


@app.get("/")
def root():
    return {"status": "ok", "manifest": "/manifest.json", "configure": "/configure"}


@app.get("/configure", response_class=HTMLResponse)
@app.get("/{config}/configure", response_class=HTMLResponse)
def configure(request: Request, config: str | None = None):
    current = parse_config(config)
    return render_configure_page(_base_url(request), current)


@app.get("/manifest.json")
@app.get("/{config}/manifest.json")
def manifest(request: Request, config: str | None = None):
    dynamic_manifest = copy.deepcopy(MANIFEST)
    dynamic_manifest["logo"] = f"{_base_url(request)}/static/logo.svg"
    return dynamic_manifest


def _get_dubbing_result(imdb_id: str, title: str) -> dict:
    cached = cache.get(imdb_id)
    if cached is not None:
        return cached

    result = check_pt_br_dubbing(title, imdb_id=imdb_id)
    result_dict = {
        "found_entry": result.found_entry,
        "has_pt_audio": result.has_pt_audio,
        "providers": result.providers,
        "justwatch_url": result.justwatch_url,
    }
    cache.set(imdb_id, result_dict)
    return result_dict


def _dubbing_tag_text(result_dict: dict, cfg: AddonConfig) -> tuple[str, list[str], bool]:
    """Retorna (texto_da_tag, provedores_filtrados, tem_audio_pt_considerando_filtro)."""
    if not result_dict["found_entry"]:
        return "❔ Dublagem PT-BR: não encontrado na JustWatch", [], False

    filtered = filter_providers(result_dict["providers"], cfg)
    has_pt = len(filtered) > 0

    if has_pt:
        providers_txt = ", ".join(filtered)
        return f"🇧🇷 Dublado PT-BR ({providers_txt})", filtered, True
    return "🔇 Sem dublagem PT-BR (no serviço escolhido)", [], False


@app.get("/meta/{content_type}/{video_id}.json")
@app.get("/{config}/meta/{content_type}/{video_id}.json")
def meta(content_type: str, video_id: str, config: str | None = None):
    cfg = parse_config(config)
    imdb_id = video_id.split(":")[0]

    base_meta = cinemeta.get_full_meta(imdb_id, content_type)
    if base_meta is None:
        return {"meta": {}}

    result_dict = _get_dubbing_result(imdb_id, base_meta.get("name", ""))
    tag_text, _, _ = _dubbing_tag_text(result_dict, cfg)

    enriched = copy.deepcopy(base_meta)
    original_description = enriched.get("description") or ""
    enriched["description"] = f"{tag_text}\n\n{original_description}".strip()
    genres = enriched.get("genres") or []
    enriched["genres"] = [tag_text] + genres

    return {"meta": enriched}


@app.get("/stream/{content_type}/{video_id}.json")
@app.get("/{config}/stream/{content_type}/{video_id}.json")
def stream(content_type: str, video_id: str, config: str | None = None):
    cfg = parse_config(config)
    imdb_id = video_id.split(":")[0]

    title = cinemeta.get_title(imdb_id, content_type)
    if title is None:
        return {"streams": []}

    result_dict = _get_dubbing_result(imdb_id, title)
    if not result_dict["found_entry"]:
        return {"streams": []}

    tag_text, filtered_providers, has_pt = _dubbing_tag_text(result_dict, cfg)
    if has_pt:
        description = f"Áudio em português disponível em: {', '.join(filtered_providers)}"
    else:
        description = "Nenhum serviço (dentre os escolhidos na configuração) tem áudio em português para este título ainda."

    tag_entry = {
        "name": tag_text,
        "description": description,
        "externalUrl": result_dict["justwatch_url"] or "https://www.justwatch.com/br",
    }

    return {"streams": [tag_entry]}


def _load_seed() -> list[dict]:
    try:
        data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
        return data.get("titulos", [])
    except (OSError, json.JSONDecodeError):
        return []


@app.get("/catalog/{content_type}/{catalog_id}.json")
@app.get("/{config}/catalog/{content_type}/{catalog_id}.json")
def catalog(content_type: str, catalog_id: str, config: str | None = None):
    if catalog_id != CATALOG_ID:
        return {"metas": []}

    cfg = parse_config(config)
    metas = []

    for item in _load_seed():
        imdb_id = item["imdb_id"]
        item_type = item.get("type", "series")
        if item_type != content_type:
            continue

        base_meta = cinemeta.get_full_meta(imdb_id, item_type)
        if base_meta is None:
            continue

        result_dict = _get_dubbing_result(imdb_id, base_meta.get("name", ""))
        _, _, has_pt = _dubbing_tag_text(result_dict, cfg)
        if not has_pt:
            continue

        metas.append(
            {
                "id": imdb_id,
                "type": item_type,
                "name": base_meta.get("name"),
                "poster": base_meta.get("poster"),
                "description": base_meta.get("description"),
            }
        )

    return {"metas": metas}
