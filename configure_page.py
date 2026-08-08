"""
Gera a página HTML de /configure. É a página que:
  1. Deixa o usuário escolher qual serviço de streaming considerar
     (todos, ou só Crunchyroll/Netflix/Prime).
  2. Monta o link de instalação certo (com a config embutida) e mostra
     um botão "Instalar no Stremio" (deep link stremio://) além do link
     comum, pra facilitar compartilhar com outras pessoas.

Fica tudo num HTML simples com um pouco de JS, sem framework — não
precisa de build step, o FastAPI serve como string mesmo.
"""

from __future__ import annotations

from addon_config import AddonConfig


def render_configure_page(base_url: str, current: AddonConfig) -> str:
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Dublado PT-BR? — Configurar</title>
<style>
  :root {{
    --verde: #0d7a3f;
    --amarelo: #f6c700;
    --azul: #1a2a5e;
    --fundo: #0f1115;
    --card: #171a21;
    --texto: #eaeaea;
    --texto-fraco: #9aa0ab;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: var(--fundo);
    color: var(--texto);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
    display: flex;
    justify-content: center;
    padding: 40px 16px;
  }}
  .card {{
    background: var(--card);
    border-radius: 16px;
    padding: 32px;
    max-width: 480px;
    width: 100%;
    box-shadow: 0 8px 30px rgba(0,0,0,0.4);
  }}
  .logo {{
    width: 64px;
    height: 64px;
    margin-bottom: 16px;
  }}
  h1 {{
    font-size: 22px;
    margin: 0 0 4px;
  }}
  p.subtitle {{
    color: var(--texto-fraco);
    margin: 0 0 28px;
    font-size: 14px;
  }}
  fieldset {{
    border: none;
    padding: 0;
    margin: 0 0 28px;
  }}
  legend {{
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 12px;
    color: var(--texto);
  }}
  label.option {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    border-radius: 10px;
    margin-bottom: 8px;
    cursor: pointer;
    border: 1px solid #2a2e38;
    transition: border-color 0.15s;
  }}
  label.option:hover {{ border-color: var(--verde); }}
  label.option input {{ accent-color: var(--verde); }}
  .btn {{
    display: block;
    width: 100%;
    text-align: center;
    padding: 14px;
    border-radius: 10px;
    font-weight: 600;
    font-size: 15px;
    text-decoration: none;
    margin-bottom: 10px;
    border: none;
    cursor: pointer;
  }}
  .btn-primary {{
    background: var(--verde);
    color: white;
  }}
  .btn-secondary {{
    background: transparent;
    color: var(--texto);
    border: 1px solid #2a2e38;
  }}
  .url-box {{
    background: #0b0d11;
    border: 1px solid #2a2e38;
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 12px;
    color: var(--texto-fraco);
    word-break: break-all;
    margin-bottom: 20px;
    font-family: monospace;
  }}
  .footer-note {{
    font-size: 12px;
    color: var(--texto-fraco);
    margin-top: 20px;
    line-height: 1.5;
  }}
</style>
</head>
<body>
  <div class="card">
    <img class="logo" src="/static/logo.svg" alt="logo" />
    <h1>Dublado PT-BR?</h1>
    <p class="subtitle">Mostra se um anime/série/filme tem dublagem em português do Brasil, direto na tela de detalhes do Stremio.</p>

    <form id="config-form">
      <fieldset>
        <legend>Qual serviço considerar?</legend>

        <label class="option">
          <input type="radio" name="providers" value="all" {"checked" if current.providers == "all" else ""} />
          Todos (Crunchyroll, Netflix, Prime Video)
        </label>
        <label class="option">
          <input type="radio" name="providers" value="crunchyroll" {"checked" if current.providers == "crunchyroll" else ""} />
          Somente Crunchyroll
        </label>
        <label class="option">
          <input type="radio" name="providers" value="netflix" {"checked" if current.providers == "netflix" else ""} />
          Somente Netflix
        </label>
        <label class="option">
          <input type="radio" name="providers" value="primevideo" {"checked" if current.providers == "primevideo" else ""} />
          Somente Prime Video
        </label>
      </fieldset>

      <a id="install-btn" class="btn btn-primary" href="#">📲 Instalar no Stremio</a>
      <a id="copy-btn" class="btn btn-secondary" href="#">🔗 Copiar link de instalação</a>
    </form>

    <div class="url-box" id="url-preview"></div>

    <p class="footer-note">
      Depois de instalar: vá em <strong>Addons</strong> no Stremio e arraste
      "Dublado PT-BR?" pra cima do <strong>Cinemeta</strong> na lista, senão
      a tag só aparece na lista de streams, não na descrição do título.
    </p>
  </div>

<script>
  const baseUrl = {base_url!r};

  function b64EncodeUrlSafe(str) {{
    return btoa(str).replace(/\\+/g, '-').replace(/\\//g, '_').replace(/=+$/, '');
  }}

  function buildManifestUrl() {{
    const providers = document.querySelector('input[name="providers"]:checked').value;
    const config = JSON.stringify({{ providers }});
    const segment = b64EncodeUrlSafe(config);
    return `${{baseUrl}}/${{segment}}/manifest.json`;
  }}

  function refresh() {{
    const manifestUrl = buildManifestUrl();
    const httpsUrl = manifestUrl;
    const deepLink = manifestUrl.replace(/^https?:\\/\\//, 'stremio://');

    document.getElementById('install-btn').href = deepLink;
    document.getElementById('copy-btn').onclick = (e) => {{
      e.preventDefault();
      navigator.clipboard.writeText(httpsUrl);
      const btn = document.getElementById('copy-btn');
      const original = btn.textContent;
      btn.textContent = '✅ Copiado!';
      setTimeout(() => btn.textContent = original, 1500);
    }};
    document.getElementById('url-preview').textContent = httpsUrl;
  }}

  document.querySelectorAll('input[name="providers"]').forEach(el => {{
    el.addEventListener('change', refresh);
  }});

  refresh();
</script>
</body>
</html>
"""
