"""
Addon Stremio: "Dublado PT-BR?"

Implementa o protocolo de addon do Stremio na mão (é só HTTP + JSON,
não precisa do SDK oficial em Node). Referência do protocolo:
https://github.com/Stremio/stremio-addon-sdk/blob/master/docs/api/responses/stream.md

Resource usado: `stream`. Em vez de tentar reescrever os metadados do
título (o que exigiria "brigar" com o Cinemeta), o addon injeta uma
entrada extra na lista de streams — não-clicável como vídeo, funciona
como uma "tag" visual: "🇧🇷 Dublado PT-BR" ou "🔇 Sem dublagem PT-BR".

Rodar localmente:
    pip install fastapi uvicorn
    uvicorn main:app --reload --port 7000

Depois instalar no Stremio apontando pra:
    http://127.0.0.1:7000/manifest.json
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import cache
import cinemeta
from justwatch_client import check_pt_br_dubbing

app = FastAPI(title="Stremio Addon - Dublado PT-BR")


@app.get("/")
def root():
    # útil pra confirmar que o serviço está de pé (Render/Stremio checam isso)
    return {"status": "ok", "manifest": "/manifest.json"}

# Stremio roda dentro de um webview/app; CORS liberado é necessário.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MANIFEST = {
    "id": "community.dublado-ptbr",
    "version": "0.1.0",
    "name": "Dublado PT-BR?",
    "description": "Mostra se um anime/série/filme tem dublagem em português do Brasil disponível (via JustWatch: Crunchyroll, Netflix, Prime Video).",
    "resources": ["stream"],
    "types": ["movie", "series"],
    # catalogs vazio: este addon só enriquece itens já existentes,
    # não define um catálogo próprio pra navegar.
    "catalogs": [],
    "idPrefixes": ["tt"],
}


@app.get("/manifest.json")
def manifest():
    return MANIFEST


@app.get("/stream/{content_type}/{video_id}.json")
def stream(content_type: str, video_id: str):
    # video_id pode vir como "tt1234567" (filme) ou "tt1234567:1:3" (série, temporada:episódio)
    imdb_id = video_id.split(":")[0]

    cached = cache.get(imdb_id)
    if cached is not None:
        result_dict = cached
    else:
        title = cinemeta.get_title(imdb_id, content_type)
        if title is None:
            return {"streams": []}

        result = check_pt_br_dubbing(title, imdb_id=imdb_id)
        result_dict = {
            "found_entry": result.found_entry,
            "has_pt_audio": result.has_pt_audio,
            "providers": result.providers,
            "justwatch_url": result.justwatch_url,
        }
        cache.set(imdb_id, result_dict)

    if not result_dict["found_entry"]:
        return {"streams": []}

    if result_dict["has_pt_audio"]:
        providers = ", ".join(result_dict["providers"]) or "streaming"
        name = "🇧🇷 Dublado PT-BR"
        description = f"Áudio em português disponível em: {providers}"
    else:
        name = "🔇 Sem dublagem PT-BR"
        description = "Nenhum serviço rastreado pela JustWatch tem áudio em português para este título ainda."

    tag_entry = {
        "name": name,
        "description": description,
        # sem "url"/"infoHash": não é um stream de vídeo de verdade, é só
        # uma tag informativa na lista. O Stremio mostra mesmo assim.
        "externalUrl": result_dict["justwatch_url"] or "https://www.justwatch.com/br",
    }

    return {"streams": [tag_entry]}
