"""
O Stremio suporta addons "configuráveis": o usuário escolhe opções numa
página HTML que o próprio addon serve, e essa escolha vira um pedaço
extra na URL do manifest — algo como:

    https://seu-addon.onrender.com/eyJwcm92aWRlcnMiOiJuZXRmbGl4In0/manifest.json

Esse trecho no meio (base64 de um JSON) é repassado automaticamente pelo
Stremio em TODAS as chamadas seguintes (meta, stream, catalog), então o
addon sabe a preferência do usuário em cada request sem precisar de
cookies/sessão.

Esse arquivo cuida de: (a) decodificar isso, (b) aplicar o filtro em
cima da lista de provedores encontrados na JustWatch.
"""

from __future__ import annotations

import base64
import binascii
import json
from dataclasses import dataclass

DEFAULT_PROVIDERS = "all"

# chave interna -> como o nome costuma aparecer no campo `package.name` da JustWatch
PROVIDER_MATCH = {
    "crunchyroll": ["crunchyroll"],
    "netflix": ["netflix"],
    "primevideo": ["prime video", "amazon"],
}

PROVIDER_OPTIONS = ["all", "crunchyroll", "netflix", "primevideo"]


@dataclass
class AddonConfig:
    providers: str = DEFAULT_PROVIDERS  # "all" | "crunchyroll" | "netflix" | "primevideo"

    def to_url_segment(self) -> str:
        payload = json.dumps({"providers": self.providers}, separators=(",", ":"))
        encoded = base64.urlsafe_b64encode(payload.encode()).decode()
        return encoded.rstrip("=")


def parse_config(raw_segment: str | None) -> AddonConfig:
    if not raw_segment:
        return AddonConfig()
    try:
        # repõe padding do base64 que a URL costuma cortar
        padded = raw_segment + "=" * (-len(raw_segment) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded))
        providers = data.get("providers", DEFAULT_PROVIDERS)
        if providers not in PROVIDER_OPTIONS:
            providers = DEFAULT_PROVIDERS
        return AddonConfig(providers=providers)
    except (ValueError, binascii.Error, json.JSONDecodeError):
        return AddonConfig()


def filter_providers(all_providers: list[str], config: AddonConfig) -> list[str]:
    """Filtra a lista de provedores (nomes vindos da JustWatch) conforme a config."""
    if config.providers == "all":
        return all_providers

    keywords = PROVIDER_MATCH.get(config.providers, [])
    return [p for p in all_providers if any(k in p.lower() for k in keywords)]
