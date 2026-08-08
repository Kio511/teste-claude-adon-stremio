# Stremio Addon — Dublado PT-BR?

Addon que checa (via JustWatch) se um filme/série/anime tem dublagem em
português do Brasil disponível em algum serviço de streaming (Crunchyroll,
Netflix, Prime Video, etc.), e mostra isso:

- na **tela de detalhes** do título (descrição + tag), antes de abrir a lista de episódios;
- na **lista de streams**;
- num **catálogo próprio** "Animes Dublados PT-BR", navegável, já filtrado.

O addon é **configurável**: em `/configure` a pessoa escolhe se quer
considerar todos os serviços ou só um específico (Crunchyroll, Netflix
ou Prime Video), e isso gera um link de instalação próprio — inclusive
com botão de instalação direta (`stremio://`) pra facilitar compartilhar.

## Como funciona

```
Pessoa acessa /configure
        │
        ▼
  escolhe o serviço (ou "todos") → link de instalação gerado na hora
        │
        ▼
Stremio pede /{config}/manifest.json, depois /{config}/meta/... etc.
        │
        ▼
  addon_config.py decodifica a preferência da URL
        │
        ▼
  cache.get(imdb_id) ──► hit? usa direto (TTL 7 dias)
        │ miss
        ▼
  cinemeta.get_full_meta(imdb_id)  → nome, poster, descrição, episódios
        │
        ▼
  justwatch_client.check_pt_br_dubbing(título, imdb_id)
        │  busca na JustWatch (país=BR), confirma pelo imdb_id,
        │  olha offer.audio_languages procurando "pt"
        ▼
  cache.set(imdb_id, resultado)  ← guarda TODOS os provedores encontrados
        │
        ▼
  addon_config.filter_providers()  ← filtra conforme a config da pessoa
        │
        ▼
  meta / stream / catalog respondem já filtrados
```

Importante: o cache guarda o resultado **sem filtro** (todos os
provedores encontrados), e o filtro por configuração é aplicado só na
hora de responder. Assim, uma única consulta à JustWatch serve pessoas
com configurações diferentes, sem duplicar trabalho.

## Rodar localmente

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 7000
```

Abra `http://127.0.0.1:7000/configure` no navegador, escolha a
configuração e clique em instalar (ou copie o link gerado).

## ⚠️ Passo obrigatório: prioridade do addon

O Stremio já vem com o **Cinemeta** instalado por padrão, que também
serve `meta` pros mesmos títulos. Quando dois addons oferecem `meta`
pro mesmo item, o Stremio usa o de **maior prioridade** — ou seja, se
o Cinemeta estiver antes do nosso addon na lista, o Cinemeta "ganha" e
nossa tag não aparece na descrição.

**Correção:** depois de instalar, vá em `Addons` no Stremio, ache
"Dublado PT-BR?" na lista e **arraste ele pra cima do Cinemeta**. Sem
esse passo, a tag só aparece na lista de streams e no catálogo
próprio, não na descrição do título.

## Sobre o catálogo "Animes Dublados PT-BR"

O arquivo `anime_catalog_seed.json` tem uma lista inicial de ~18 animes
populares (imdb_id) usada pra popular o catálogo. **Os IDs vieram de
memória e podem estar errados** — não consegui verificar cada um numa
chamada real de rede a partir deste ambiente de desenvolvimento. Antes
de divulgar publicamente, confira cada `imdb_id` em imdb.com e corrija
o que precisar. É só editar o JSON e fazer redeploy — sem precisar
mexer em código.

Pra expandir a lista, adicione objetos no formato:
```json
{"imdb_id": "tt1234567", "type": "series", "nome_referencia": "Nome só pra você lembrar"}
```

O catálogo hoje é limitado a essa lista curada porque montar um
catálogo dinâmico de "todo anime que existe" exigiria uma fonte de
dados própria de animes (tipo AniList/MAL) cruzada com a JustWatch —
uma melhoria possível pro futuro.

## Sobre a divulgação pública

Se quiser divulgar pra mais gente (não só você testando):
- **Plano free do Render tem cold start (~1min)** depois de 15 min
  sem uso — pra um público maior, considere o plano pago mais barato
  do Render (elimina o "acordar"), ou pelo menos avise isso na
  descrição do addon/README.
- A página `/configure` já serve como "landing page" de instalação —
  esse é o link que você compartilha, não a URL do manifest direto.
- Pra aparecer na busca de addons dentro do próprio Stremio (sem
  precisar do usuário colar link), dá pra submeter em
  https://stremio-addons.net — eles pedem o manifest público e passam
  por uma revisão.

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
