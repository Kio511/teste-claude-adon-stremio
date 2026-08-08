# Stremio Addon — Dublado PT-BR?

Addon que checa (via JustWatch) se um filme/série/anime tem dublagem em
português do Brasil disponível em algum serviço de streaming (Crunchyroll,
Netflix, Prime Video, etc.), e mostra isso como uma tag na lista de streams.

## Como funciona

```
Stremio pede /stream/series/tt1234567.json
        │
        ▼
  cache.get(imdb_id) ──► hit? retorna direto (TTL 7 dias)
        │ miss
        ▼
  cinemeta.get_title(imdb_id)  → resolve o título a partir do imdb_id
        │
        ▼
  justwatch_client.check_pt_br_dubbing(título, imdb_id)
        │  busca na JustWatch (país=BR), confirma pelo imdb_id,
        │  olha offer.audio_languages procurando "pt"
        ▼
  cache.set(imdb_id, resultado)
        │
        ▼
  retorna streams: [{ name: "🇧🇷 Dublado PT-BR", ... }]
```

## Rodar localmente

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 7000
```

Depois, no Stremio: `Addons` → `Community Addons` → cole a URL:

```
http://127.0.0.1:7000/manifest.json
```

## ⚠️ Passo obrigatório: prioridade do addon

A partir da v0.2, o addon usa o resource `meta` pra mostrar a dublagem
**na tela de detalhes** (descrição + tag), antes de abrir a lista de
episódios — não só na lista de streams.

Só que o Stremio já vem com o **Cinemeta** instalado por padrão, que
também serve `meta` pros mesmos títulos. Quando dois addons oferecem
`meta` pro mesmo item, o Stremio usa o de **maior prioridade** — ou
seja, se o Cinemeta estiver antes do nosso addon na lista, o Cinemeta
"ganha" e nossa tag nunca aparece.

**Correção:** depois de instalar, vá em `Addons` no Stremio, ache
"Dublado PT-BR?" na lista e **arraste ele pra cima do Cinemeta**
(ou use o botão de mover, se o app tiver). Sem esse passo, a tag só vai
aparecer na lista de streams (resource `stream`, que continua funcionando
independente disso), não na descrição.

## Limitações conhecidas (importante ler)

1. **JustWatch não é API oficial.** É engenharia reversa do GraphQL que o
   site/app deles usa. Pode quebrar sem aviso se eles mudarem algo — é
   por isso que o `justwatch_client.py` fica isolado num arquivo só,
   pra ser fácil de consertar sem mexer no resto.

2. **`audio_languages: ["pt"]` não distingue PT-BR de PT-PT.** Na prática,
   pra a maioria dos títulos vistos a partir do país `BR`, é dublagem
   brasileira — mas não é garantido. Se isso importar muito pro seu caso
   de uso, um próximo passo é comparar a `price_currency` da oferta
   (BRL é forte sinal de catálogo BR) ou filtrar por `package.technical_name`
   nos provedores que você sabe que só fazem dublagem BR (ex: Crunchyroll BR).

3. **Match por título é impreciso.** O código tenta confirmar via `imdb_id`
   retornado pela JustWatch, mas nem todo título tem esse campo preenchido
   lá. Títulos de anime às vezes aparecem com nome romanizado diferente do
   nome em inglês do Cinemeta — pode dar falso negativo. Se isso for
   frequente, vale manter um dicionário manual de "título Cinemeta → título
   JustWatch" pros casos problemáticos.

4. **Uso não-comercial.** As libs não-oficiais de JustWatch deixam claro
   nos termos delas que uso comercial é proibido. Isso aqui é pra projeto
   pessoal.

5. **Sem testes automatizados ainda** — este é um esqueleto funcional, não
   um addon pronto pra produção. Delay de rede pra usuário final: a
   primeira consulta de cada título é síncrona (pode demorar 1-2s); depois
   fica em cache.

## Próximos passos sugeridos

- [ ] Job separado (cron) que pré-popula o cache pra uma lista de animes
      populares, em vez de esperar o primeiro request do usuário.
- [ ] Endpoint `/catalog` próprio: "Animes Dublados PT-BR" navegável.
- [ ] Deploy em algo grátis tipo Render/Railway/Fly.io pra não depender do
      seu PC ligado.
- [ ] Fallback pra Crunchyroll API não-oficial quando JustWatch não achar
      o título (comum em animes muito recentes ou de nicho).
