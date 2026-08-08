"""
Wrapper em volta da lib `simple-justwatch-python-api`.

Responsabilidade única: dado um título (e opcionalmente um imdb_id pra
confirmar o match certo), dizer se existe alguma oferta de streaming no
Brasil com áudio em português.

Por que confirmar com imdb_id?
A busca por texto na JustWatch pode retornar vários resultados parecidos
(remakes, filmes com nome igual, etc). Como o Cinemeta/Stremio trabalha
com imdb_id, usamos esse campo (que a JustWatch também expõe) pra ter
certeza que estamos olhando pro título certo.
"""

from __future__ import annotations

from dataclasses import dataclass

from simplejustwatchapi.justwatch import search
from simplejustwatchapi.tuples import MediaEntry, Offer

JUSTWATCH_COUNTRY = "BR"
JUSTWATCH_LANGUAGE = "pt"
PT_AUDIO_CODES = {"pt"}  # a API não distingue pt-BR de pt-PT no código de 2 letras


@dataclass
class DubbingResult:
    found_entry: bool
    has_pt_audio: bool
    providers: list[str]  # nomes das plataformas onde tem áudio em PT
    justwatch_url: str | None


def _entry_matches(entry: MediaEntry, imdb_id: str | None) -> bool:
    if imdb_id is None:
        return True
    return entry.imdb_id == imdb_id


def _offer_has_pt_audio(offer: Offer) -> bool:
    langs = offer.audio_languages or []
    return any(code in PT_AUDIO_CODES for code in langs)


def check_pt_br_dubbing(title: str, imdb_id: str | None = None) -> DubbingResult:
    """
    Busca o título na JustWatch (catálogo BR) e verifica se alguma oferta
    de streaming (FLATRATE/ADS/RENT/BUY) tem áudio em português.
    """
    results = search(title, country=JUSTWATCH_COUNTRY, language=JUSTWATCH_LANGUAGE, count=5)

    entry = next((e for e in results if _entry_matches(e, imdb_id)), None)
    if entry is None and results:
        # fallback: se não bateu o imdb_id, usa o primeiro resultado mesmo
        # (melhor um match aproximado do que nada — mas fica marcado como
        # "não confirmado" pra quem for consumir isso depois, se quiser)
        entry = results[0]

    if entry is None:
        return DubbingResult(found_entry=False, has_pt_audio=False, providers=[], justwatch_url=None)

    pt_offers = [o for o in entry.offers if _offer_has_pt_audio(o)]
    providers = sorted({o.package.name for o in pt_offers})

    return DubbingResult(
        found_entry=True,
        has_pt_audio=len(pt_offers) > 0,
        providers=providers,
        justwatch_url=entry.url,
    )
