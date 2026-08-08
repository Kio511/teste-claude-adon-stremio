"""
Addon Stremio: "Dublado PT-BR?"

Agora usando o resource `meta`, além do `stream`:
  - `meta`: reescreve a tela de detalhes do título, adicionando a
    informação de dublagem NA DESCRIÇÃO e como um gênero/tag extra
    (aparece antes de você abrir a lista de episódios).
  - `stream`: mantido como bônus, mostra a mesma info na lista de
    streams também.

IMPORTANTE sobre prioridade de addons:
Quando dois addons oferecem `meta` pro mesmo item (aqui: o nosso e o
Cinemeta, que já vem instalado por padrão no Stremio), o Stremio usa o
que tiver prioridade mais alta na lista de addons do usuário. Ou seja:
pra essa tag aparecer, o usuário PRECISA arrastar "Dublado PT-BR?" pra
cima do Cinemeta em Addons > (ordem da lista). Isso está documentado
no README.

Rodar localmente:
    pip install -r requirements.txt
    uvicorn main:app --reload --port 7000
"""

from __future__ import annotations

import copy

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import cache
import cinemeta
from justwatch_client import check_pt_br_dubbing

app = FastAPI(title="Stremio Addon - Dublado PT-BR")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MANIFEST = {
    "id": "community.dublado-ptbr",
    "version": "0.2.0",
    "name": "Dublado PT-BR?",
    "description": "Mostra se um anime/série/filme tem dublagem em português do Brasil disponível (via JustWatch: Crunchyroll, Netflix, Prime Video), direto na tela de detalhes.",
    "resources": ["meta", "stream"],
    "types": ["movie", "series"],
    "catalogs": [],
    "idPrefixes": ["tt"],
}


@app.get("/")
def root():
    return {"status": "ok", "manifest": "/manifest.json"}


@app.get("/manifest.json")
def manifest():
    return MANIFEST


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


def _dubbing_tag_text(result_dict: dict) -> str:
    if not result_dict["found_entry"]:
        return "❔ Dublagem PT-BR: não encontrado na JustWatch"
    if result_dict["has_pt_audio"]:
        providers = ", ".join(result_dict["providers"]) or "streaming"
        return f"🇧🇷 Dublado PT-BR ({providers})"
    return "🔇 Sem dublagem PT-BR (apenas legendado)"


@app.get("/meta/{content_type}/{video_id}.json")
def meta(content_type: str, video_id: str):
    imdb_id = video_id.split(":")[0]

    base_meta = cinemeta.get_full_meta(imdb_id, content_type)
    if base_meta is None:
        return {"meta": {}}

    result_dict = _get_dubbing_result(imdb_id, base_meta.get("name", ""))
    tag_text = _dubbing_tag_text(result_dict)

    # cópia pra não mutar nada inesperado
    enriched = copy.deepcopy(base_meta)

    # 1) Tag no começo da descrição — é a primeira coisa que a pessoa lê
    #    antes de rolar pra baixo até a lista de episódios.
    original_description = enriched.get("description") or ""
    enriched["description"] = f"{tag_text}\n\n{original_description}".strip()

    # 2) Também como "gênero" extra — em várias skins do Stremio os
    #    gêneros aparecem como badges logo abaixo do título, ainda mais
    #    visível que a descrição.
    genres = enriched.get("genres") or []
    enriched["genres"] = [tag_text] + genres

    return {"meta": enriched}


@app.get("/stream/{content_type}/{video_id}.json")
def stream(content_type: str, video_id: str):
    imdb_id = video_id.split(":")[0]

    title = cinemeta.get_title(imdb_id, content_type)
    if title is None:
        return {"streams": []}

    result_dict = _get_dubbing_result(imdb_id, title)
    if not result_dict["found_entry"]:
        return {"streams": []}

    tag_text = _dubbing_tag_text(result_dict)
    if result_dict["has_pt_audio"]:
        providers = ", ".join(result_dict["providers"]) or "streaming"
        description = f"Áudio em português disponível em: {providers}"
    else:
        description = "Nenhum serviço rastreado pela JustWatch tem áudio em português para este título ainda."

    tag_entry = {
        "name": tag_text,
        "description": description,
        "externalUrl": result_dict["justwatch_url"] or "https://www.justwatch.com/br",
    }

    return {"streams": [tag_entry]}
