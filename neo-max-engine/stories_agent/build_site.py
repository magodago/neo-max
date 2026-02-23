"""
Construye la web de historias: serial por capítulos, índice con ganchos sociales, diseño por tema, móvil primero.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path


def _sanitize_chapter_content(title: str, body_html: str) -> tuple[str, str]:
    """Si body_html contiene '### TITLE ... ### BODY', extrae título y cuerpo reales (evita mostrarlos crudos)."""
    if not body_html or "### TITLE" not in body_html or "### BODY" not in body_html:
        return title, body_html
    m = re.search(r"#+\s*TITLE\s*(.*?)\s*#+\s*BODY\s*(.*)", body_html, re.DOTALL | re.IGNORECASE)
    if m:
        title_part = m.group(1).strip()
        body_part = m.group(2).strip()
        if title_part and len(title_part) < 200:
            title = title_part.split("\n")[0].strip()
        if body_part and len(body_part) > 50:
            body_html = body_part
    return title, body_html

# Temas visuales: colores, fuentes, fondos (móvil primero, aspecto profesional)
THEMES = {
    "heartwarming": {
        "bg": "#fef7ed",
        "card": "#ffffff",
        "text": "#1c1917",
        "muted": "#78716c",
        "accent": "#c2410c",
        "font_heading": "Georgia, 'Times New Roman', serif",
        "font_body": "'Segoe UI', system-ui, sans-serif",
        "gradient": "linear-gradient(180deg, #fef7ed 0%, #ffedd5 100%)",
    },
    "mystery": {
        "bg": "#1c1917",
        "card": "#292524",
        "text": "#fafaf9",
        "muted": "#a8a29e",
        "accent": "#f59e0b",
        "font_heading": "'Crimson Pro', 'Georgia', serif",
        "font_body": "'Segoe UI', system-ui, sans-serif",
        "gradient": "linear-gradient(180deg, #1c1917 0%, #292524 50%)",
    },
    "thriller": {
        "bg": "#0f172a",
        "card": "#1e293b",
        "text": "#f1f5f9",
        "muted": "#94a3b8",
        "accent": "#e2e8f0",
        "font_heading": "'Crimson Pro', 'Georgia', serif",
        "font_body": "'Segoe UI', system-ui, sans-serif",
        "gradient": "linear-gradient(180deg, #0f172a 0%, #1e293b 40%, #0f172a 100%)",
    },
    "terror": {
        "bg": "#0c0a0f",
        "card": "#1a161f",
        "text": "#f5f3f7",
        "muted": "#8b8499",
        "accent": "#c4b5fd",
        "font_heading": "'Crimson Pro', 'Georgia', serif",
        "font_body": "'DM Sans', 'Segoe UI', system-ui, sans-serif",
        "gradient": "linear-gradient(180deg, #0c0a0f 0%, #1a161f 35%, #0f0d14 100%)",
    },
    "fantasy": {
        "bg": "#1e1b4b",
        "card": "#312e81",
        "text": "#e0e7ff",
        "muted": "#a5b4fc",
        "accent": "#c4b5fd",
        "font_heading": "'Crimson Pro', Georgia, serif",
        "font_body": "'Segoe UI', system-ui, sans-serif",
        "gradient": "linear-gradient(180deg, #1e1b4b 0%, #312e81 100%)",
    },
}


def _load_config() -> dict:
    config_path = Path(__file__).resolve().parent / "config.json"
    if not config_path.is_file():
        return {}
    return json.loads(config_path.read_text(encoding="utf-8"))


def _slug(title: str) -> str:
    import re
    s = title.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return s.strip("-")[:60] or "chapter"


def _theme_css(theme_key: str) -> str:
    t = THEMES.get(theme_key, THEMES["terror"])
    return f"""
  @import url('https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,400;0,600;0,700;1,400&family=DM+Sans:wght@400;500;600&display=swap');
  :root {{
    --bg: {t['bg']};
    --card: {t['card']};
    --text: {t['text']};
    --muted: {t['muted']};
    --accent: {t['accent']};
    --font-heading: {t['font_heading']};
    --font-body: {t['font_body']};
    --gradient: {t['gradient']};
  }}
  * {{ box-sizing: border-box; }}
  html {{ -webkit-text-size-adjust: 100%; scroll-behavior: smooth; }}
  body {{
    font-family: var(--font-body);
    background: var(--gradient);
    color: var(--text);
    margin: 0;
    padding: max(1.25rem, env(safe-area-inset-top)) max(1.25rem, env(safe-area-inset-right)) max(4rem, env(safe-area-inset-bottom)) max(1.25rem, env(safe-area-inset-left));
    min-height: 100vh;
    line-height: 1.8;
    font-size: clamp(1.05rem, 2.5vw + 0.5rem, 1.2rem);
    position: relative;
  }}
  body::before {{
    content: '';
    position: fixed;
    inset: 0;
    background: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E");
    pointer-events: none;
    z-index: 0;
  }}
  h1, h2, h3 {{ font-family: var(--font-heading); font-weight: 600; letter-spacing: 0.02em; }}
  h1 {{ letter-spacing: 0.03em; text-shadow: 0 0 40px rgba(0,0,0,.3); }}
  a {{ color: var(--accent); text-decoration: none; -webkit-tap-highlight-color: transparent; }}
  a:hover {{ text-decoration: underline; }}
  .card {{
    background: var(--card);
    border-radius: 16px;
    padding: max(1.5rem, 6vw);
    box-shadow: 0 12px 48px rgba(0,0,0,.35), 0 1px 0 rgba(255,255,255,.06) inset;
    margin-bottom: 1.75rem;
    border: 1px solid rgba(255,255,255,.08);
    position: relative;
    z-index: 1;
  }}
  article.card .body {{ max-width: 70ch; }}
  article.card .body p {{ margin-bottom: 1.25em; }}
  .muted {{ color: var(--muted); font-size: 0.9rem; }}
  .btn {{
    display: inline-block;
    min-height: 48px;
    min-width: 48px;
    padding: 14px 24px;
    background: var(--accent);
    color: #0f172a;
    border-radius: 12px;
    font-weight: 600;
    text-align: center;
    line-height: 1.3;
    border: none;
    cursor: pointer;
    box-shadow: 0 4px 14px rgba(0,0,0,.2);
  }}
  .btn:hover {{ opacity: 0.95; transform: translateY(-1px); }}
  .btn-whatsapp {{ background: #25D366; color: #fff; }}
  .advance-cta {{ background: linear-gradient(135deg, rgba(196,181,253,.15) 0%, rgba(139,92,246,.1) 100%); border: 1px solid rgba(196,181,253,.3); border-radius: 14px; padding: 1.25rem 1.5rem; margin-top: 1.5rem; }}
  @media (min-width: 600px) {{
    body {{ padding: 2.5rem max(2.5rem, 12vw); }}
    .card {{ padding: 2.5rem 3rem; border-radius: 18px; box-shadow: 0 16px 56px rgba(0,0,0,.4), 0 1px 0 rgba(255,255,255,.06) inset; }}
  }}
"""


def _fake_comments(theme: str) -> str:
    comments = [
        ("María G.", "Vuelvo cada día. Engancha de verdad."),
        ("Carlos R.", "El gancho del final me tiene enganchado."),
        ("Laura M.", "Ya lo he recomendado. Muy bien escrito."),
    ]
    t = THEMES.get(theme, THEMES["terror"])
    lines = ['<section class="comments card" style="margin-top:2rem;"><h3 style="font-size:1.1rem;margin-bottom:1rem;">Lo que dicen los lectores</h3>']
    for name, text in comments:
        lines.append(
            f'<div class="comment" style="border-left:3px solid var(--accent);padding-left:1rem;margin-bottom:1rem;">'
            f'<strong>{name}</strong><span class="muted" style="margin-left:.5rem;">· ahora</span><br>'
            f'<span style="color:var(--text);">{text}</span></div>'
        )
    lines.append("</section>")
    return "\n".join(lines)


def _advance_chapter_and_contact_html(config: dict) -> str:
    """CTA 'Pide un capítulo por adelantado' (1€) + contacto por email y WhatsApp."""
    import urllib.parse
    price = config.get("advance_chapter_price_eur", 1)
    whatsapp = (config.get("whatsapp_number") or "").strip().replace(" ", "").replace("+", "")
    if not whatsapp:
        whatsapp = "34658237988"  # fallback
    author_email = config.get("author_email", "")
    form_id = (config.get("formspree_form_id") or "").strip()
    wa_msg = urllib.parse.quote("Hola, quiero pedir un capítulo por adelantado ({}€).".format(price))
    wa_url = f"https://wa.me/{whatsapp}?text={wa_msg}" if whatsapp else ""
    parts = []
    parts.append(f"""
  <section class="card advance-cta">
    <h3 style="font-size:1.1rem;margin:0 0 0.5rem;">¿Quieres el próximo capítulo antes que nadie?</h3>
    <p class="muted" style="margin:0 0 1rem;">Pide un capítulo por adelantado por solo <strong>{price}€</strong>. Escríbeme por email o por WhatsApp y te lo envío.</p>
    <p style="margin:0;display:flex;flex-wrap:wrap;gap:0.75rem;align-items:center;">""")
    if wa_url:
        parts.append(f'<a href="{wa_url}" target="_blank" rel="noopener" class="btn btn-whatsapp">💬 Pedir por WhatsApp</a>')
    if author_email:
        parts.append(f'<a href="mailto:{author_email}?subject=Capítulo por adelantado ({price}€)" class="btn">✉ Pedir por email</a>')
    parts.append("</p></section>")
    return "\n".join(parts)


def _whatsapp_bubble_html(config: dict) -> str:
    """Burbuja flotante de WhatsApp (esquina inferior derecha)."""
    whatsapp = (config.get("whatsapp_number") or "").strip().replace(" ", "").replace("+", "")
    if not whatsapp:
        whatsapp = "34658237988"
    return f'''
  <a href="https://wa.me/{whatsapp}" target="_blank" rel="noopener" class="whatsapp-bubble" aria-label="Escribir por WhatsApp" style="position:fixed;bottom:1.25rem;right:1.25rem;width:56px;height:56px;background:#25D366;color:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:28px;text-decoration:none;box-shadow:0 4px 20px rgba(37,211,102,.5);z-index:9999;transition:transform .2s, box-shadow .2s;">💬</a>
  <style>.whatsapp-bubble:hover{{transform:scale(1.08);box-shadow:0 6px 24px rgba(37,211,102,.6);}}</style>'''


def _contact_form_html(config: dict) -> str:
    """Formulario de contacto: escribe y al pulsar enviar te llega por email (sin mostrar tu correo). Si no hay formspree_form_id, fallback a mailto."""
    form_id = (config.get("formspree_form_id") or "").strip()
    author_email = config.get("author_email", "dortizs76@gmail.com")
    advance = _advance_chapter_and_contact_html(config)
    if form_id:
        return advance + f"""
  <section class="card" style="margin-top:1.5rem;">
    <p style="margin:0 0 0.5rem;"><strong>Escribir al autor</strong></p>
    <p class="muted" style="margin:0 0 1rem;">Envíame tu mensaje; lo leo todo. Tu correo no se muestra en la web.</p>
    <form action="https://formspree.io/f/{form_id}" method="POST" style="display:flex;flex-direction:column;gap:0.75rem;">
      <input type="text" name="name" placeholder="Tu nombre (opcional)" style="padding:12px;border-radius:8px;border:1px solid var(--muted);background:var(--card);color:var(--text);font-size:1rem;min-height:44px;">
      <input type="email" name="email" placeholder="Tu email (opcional, para responder)" style="padding:12px;border-radius:8px;border:1px solid var(--muted);background:var(--card);color:var(--text);font-size:1rem;min-height:44px;">
      <textarea name="message" required placeholder="Tu mensaje..." rows="4" style="padding:12px;border-radius:8px;border:1px solid var(--muted);background:var(--card);color:var(--text);font-size:1rem;resize:vertical;min-height:100px;"></textarea>
      <input type="hidden" name="_subject" value="Mensaje de un lector">
      <button type="submit" class="btn" style="border:none;cursor:pointer;">Enviar al autor</button>
    </form>
  </section>"""
    return advance + f"""
  <section class="card" style="margin-top:1.5rem;">
    <p style="margin:0 0 0.5rem;"><strong>Escribir al autor</strong></p>
    <p class="muted" style="margin:0;">Cuéntame qué te parece; lo leo todo.</p>
    <p style="margin:0.75rem 0 0;"><a href="mailto:{author_email}" class="btn">✉ Enviar email</a></p>
  </section>"""


def _escape_attr(s: str, max_len: int = 160) -> str:
    """Escapa para atributos HTML (meta content) y trunca."""
    if not s:
        return ""
    s = s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
    return s.strip()[:max_len]


def _seo_head_chapter(
    title: str,
    serial_title: str,
    chapter_num: int,
    base_url: str,
    slug: str,
    image_rel: str | None,
    theme: str,
    config: dict,
) -> str:
    """Meta + Open Graph + Twitter Card + JSON-LD para una página de capítulo (SEO fuerte)."""
    url = f"{base_url.rstrip('/')}/story/{slug}.html"
    desc_plain = f"{title}. {serial_title} — Capítulo {chapter_num}. Novela serial de misterio y terror. Lee gratis, un capítulo nuevo cada día."[:160]
    desc = _escape_attr(desc_plain, 160)
    title_attr = _escape_attr(f"{title} · {serial_title}", 80)
    og_image = f"{base_url.rstrip('/')}/{image_rel}" if image_rel else ""
    genre = config.get("serial_theme", "terror") or config.get("genre", "misterio")
    json_ld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "name": title,
        "description": desc_plain,
        "url": url,
        "isPartOf": {"@type": "Book", "name": serial_title},
        "articleSection": f"Capítulo {chapter_num}",
        "genre": genre,
    }
    if og_image:
        json_ld["image"] = og_image
    import json as _json
    json_ld_str = _json.dumps(json_ld, ensure_ascii=False)
    json_ld_str = json_ld_str.replace("<", "\\u003c").replace(">", "\\u003e")
    lines = [
        f'  <meta name="description" content="{desc}">',
        f'  <link rel="canonical" href="{url}">',
        f'  <meta property="og:type" content="article">',
        f'  <meta property="og:title" content="{title_attr}">',
        f'  <meta property="og:description" content="{desc}">',
        f'  <meta property="og:url" content="{url}">',
        f'  <meta property="og:locale" content="es_ES">',
    ]
    if og_image:
        lines.append(f'  <meta property="og:image" content="{og_image}">')
        lines.append(f'  <meta name="twitter:card" content="summary_large_image">')
    else:
        lines.append('  <meta name="twitter:card" content="summary">')
    lines.append(f'  <meta name="twitter:title" content="{title_attr}">')
    lines.append(f'  <meta name="twitter:description" content="{desc}">')
    if og_image:
        lines.append(f'  <meta name="twitter:image" content="{og_image}">')
    lines.append(f'  <script type="application/ld+json">\n{json_ld_str}\n  </script>')
    return "\n".join(lines)


def _seo_head_index(serial_title: str, base_url: str, theme: str, config: dict) -> str:
    """Meta + Open Graph + Twitter + JSON-LD WebSite para la portada del serial."""
    url = base_url.rstrip("/") + "/"
    desc_plain = f"{serial_title}. Novela serial de misterio y terror. Un capítulo nuevo cada día. Lee gratis online."[:160]
    desc = _escape_attr(desc_plain, 160)
    title_attr = _escape_attr(serial_title, 80)
    json_ld = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": serial_title,
        "description": desc_plain,
        "url": url,
        "inLanguage": "es",
        "publisher": {"@type": "Organization", "name": serial_title},
    }
    import json as _json
    json_ld_str = _json.dumps(json_ld, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e")
    lines = [
        f'  <meta name="description" content="{desc}">',
        f'  <link rel="canonical" href="{url}">',
        f'  <meta property="og:type" content="website">',
        f'  <meta property="og:title" content="{title_attr}">',
        f'  <meta property="og:description" content="{desc}">',
        f'  <meta property="og:url" content="{url}">',
        f'  <meta property="og:locale" content="es_ES">',
        '  <meta name="twitter:card" content="summary">',
        f'  <meta name="twitter:title" content="{title_attr}">',
        f'  <meta name="twitter:description" content="{desc}">',
        f'  <script type="application/ld+json">\n{json_ld_str}\n  </script>',
    ]
    return "\n".join(lines)


def add_chapter_to_serial_site(
    output_dir: Path,
    title: str,
    body_html: str,
    image_rel: str | None,
    base_url: str,
    serial_title: str,
    theme: str,
    chapter_num: int,
) -> str:
    """Añade un capítulo al sitio serial: página del capítulo (tema + móvil) y actualiza índice + sitemap."""
    title, body_html = _sanitize_chapter_content(title, body_html)
    slug = _slug(title)
    config = _load_config()
    base_url = (base_url or config.get("base_url", "")).rstrip("/")
    output_dir = Path(output_dir)
    (output_dir / "story").mkdir(parents=True, exist_ok=True)
    (output_dir / "images").mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    img_tag = f'<img src="../{image_rel}" alt="" style="width:100%;height:auto;border-radius:12px;margin:1rem 0;" loading="lazy">' if image_rel else ""

    try:
        from serial_state import load_state
        state = load_state()
        chapters = state.get("chapters", [])
    except Exception:
        chapters = [{"title": title, "slug": slug}]

    def _chap_link(c: dict) -> str:
        s = c.get("slug") or _slug(c.get("title", ""))
        t = c.get("title", "Chapter")
        return f'<li><a href="story/{s}.html">{t}</a></li>'
    nav_chapters = "".join(_chap_link(c) for c in chapters)
    next_txt = "Mañana, nuevo capítulo." if chapter_num == len(chapters) else ""

    seo_chapter = _seo_head_chapter(title, serial_title, chapter_num, base_url, slug, image_rel, theme, config)
    chapter_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <title>{_escape_attr(title + " · " + serial_title, 80)}</title>
{seo_chapter}
  <style>{_theme_css(theme)}</style>
</head>
<body>
  <nav class="muted" style="margin-bottom:1rem;font-size:0.85rem;">
    <a href="{base_url}/">← {serial_title}</a> · Capítulo {chapter_num}
  </nav>
  <article class="card">
    <h1 style="font-size:clamp(1.4rem, 4vw, 1.9rem);margin:0 0 0.5rem;">{title}</h1>
    <p class="muted" style="margin:0 0 1rem;">{now}</p>
    {img_tag}
    <div class="body">{body_html}</div>
    <p class="muted" style="margin-top:1.5rem;">{next_txt}</p>
  </article>
  {_fake_comments(theme)}
  {_contact_form_html(config)}
  <nav style="margin-top:1.5rem;">
    <a href="{base_url}/" class="btn">← Todos los capítulos</a>
  </nav>
  {_whatsapp_bubble_html(config)}
</body>
</html>"""
    (output_dir / "story" / f"{slug}.html").write_text(chapter_html, encoding="utf-8")

    # Índice: serial + suscriptores + lista de capítulos
    try:
        from serial_state import load_state
        state = load_state()
        subscriber_count = state.get("subscriber_count", 0)
    except Exception:
        subscriber_count = 0

    seo_index = _seo_head_index(serial_title, base_url, theme, config)
    index_path = output_dir / "index.html"
    index_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <title>{_escape_attr(serial_title, 80)}</title>
{seo_index}
  <style>{_theme_css(theme)}</style>
</head>
<body>
  <header class="card" style="text-align:center;">
    <h1 style="font-size:clamp(1.6rem, 5vw, 2.2rem);margin:0 0 0.5rem;">{serial_title}</h1>
    <p class="muted" style="margin:0 0 0.75rem;">Un nuevo capítulo cada día</p>
    <p style="margin:0;font-weight:600;color:var(--accent);">{subscriber_count:,} lectores</p>
  </header>
  <section class="card">
    <h2 style="font-size:1.2rem;margin:0 0 1rem;">Último</h2>
    <p style="margin:0 0 0.5rem;"><a href="story/{slug}.html"><strong>{title}</strong></a></p>
    <p class="muted" style="margin:0;">Capítulo {chapter_num} · {now}</p>
  </section>
  <section class="card">
    <h2 style="font-size:1.2rem;margin:0 0 1rem;">Capítulos</h2>
    <ul style="list-style:none;padding:0;margin:0;">
      {nav_chapters}
    </ul>
  </section>
  {_contact_form_html(config)}
  {_whatsapp_bubble_html(config)}
</body>
</html>"""
    index_path.write_text(index_html, encoding="utf-8")

    # Sitemap
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls = [base_url + "/"]
    for c in chapters:
        s = c.get("slug", _slug(c.get("title", "")))
        urls.append(base_url + f"/story/{s}.html")
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for u in urls:
        sitemap += f"  <url><loc>{u}</loc><lastmod>{now_iso}</lastmod></url>\n"
    sitemap += "</urlset>"
    (output_dir / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    robots = f"User-agent: *\nAllow: /\n\nSitemap: {base_url}/sitemap.xml\n"
    (output_dir / "robots.txt").write_text(robots, encoding="utf-8")
    return slug


def rebuild_serial_index(output_dir: Path) -> None:
    """Regenera solo index.html y sitemap.xml desde serial_state (útil tras corregir títulos en state)."""
    try:
        from serial_state import load_state
        state = load_state()
    except Exception:
        return
    chapters = state.get("chapters", [])
    if not chapters:
        return
    config = _load_config()
    base_url = (config.get("base_url") or "").rstrip("/")
    serial_title = state.get("serial_title", "Serie")
    theme = state.get("theme", "terror")
    subscriber_count = state.get("subscriber_count", 0)
    last = chapters[-1]
    slug = last.get("slug") or _slug(last.get("title", ""))
    title = last.get("title", "Último capítulo")
    chapter_num = len(chapters)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _chap_link(c: dict) -> str:
        s = c.get("slug") or _slug(c.get("title", ""))
        t = c.get("title", "Chapter")
        return f'<li><a href="story/{s}.html">{t}</a></li>'
    nav_chapters = "".join(_chap_link(c) for c in chapters)

    seo_index = _seo_head_index(serial_title, base_url, theme, config)
    index_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <title>{_escape_attr(serial_title, 80)}</title>
{seo_index}
  <style>{_theme_css(theme)}</style>
</head>
<body>
  <header class="card" style="text-align:center;">
    <h1 style="font-size:clamp(1.6rem, 5vw, 2.2rem);margin:0 0 0.5rem;">{serial_title}</h1>
    <p class="muted" style="margin:0 0 0.75rem;">Un nuevo capítulo cada día</p>
    <p style="margin:0;font-weight:600;color:var(--accent);">{subscriber_count:,} lectores</p>
  </header>
  <section class="card">
    <h2 style="font-size:1.2rem;margin:0 0 1rem;">Último</h2>
    <p style="margin:0 0 0.5rem;"><a href="story/{slug}.html"><strong>{title}</strong></a></p>
    <p class="muted" style="margin:0;">Capítulo {chapter_num} · {now}</p>
  </section>
  <section class="card">
    <h2 style="font-size:1.2rem;margin:0 0 1rem;">Capítulos</h2>
    <ul style="list-style:none;padding:0;margin:0;">
      {nav_chapters}
    </ul>
  </section>
  {_contact_form_html(config)}
  {_whatsapp_bubble_html(config)}
</body>
</html>"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "index.html").write_text(index_html, encoding="utf-8")
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls = [base_url + "/"] + [base_url + f"/story/{(c.get('slug') or _slug(c.get('title', '')))}.html" for c in chapters]
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for u in urls:
        sitemap += f"  <url><loc>{u}</loc><lastmod>{now_iso}</lastmod></url>\n"
    sitemap += "</urlset>"
    (output_dir / "sitemap.xml").write_text(sitemap, encoding="utf-8")


def add_story_to_site(
    output_dir: Path,
    title: str,
    body_html: str,
    image_rel: str | None,
    base_url: str,
    serial_title: str | None = None,
    theme: str | None = None,
    chapter_num: int | None = None,
) -> str:
    """
    Añade una historia. Si serial_title/theme/chapter_num están presentes, usa serial (capítulos + tema + móvil).
    image_rel: ruta relativa tipo "images/xxx.jpg" o None.
    """
    if serial_title and theme is not None and chapter_num is not None:
        return add_chapter_to_serial_site(
            output_dir, title, body_html, image_rel, base_url,
            serial_title, theme, chapter_num,
        )

    config = _load_config()
    if config.get("serial_mode", True):
        try:
            from serial_state import load_state
            state = load_state()
            if state and state.get("chapters"):
                last = state["chapters"][-1]
                if last.get("title") == title:
                    return add_chapter_to_serial_site(
                        output_dir, title, body_html, image_rel, base_url,
                        state.get("serial_title", "Serie diaria"),
                        state.get("theme", "thriller"),
                        len(state["chapters"]),
                    )
        except Exception:
            pass

    # Legacy: una página por historia, sin serial
    slug = _slug(title)
    base_url = (base_url or config.get("base_url", "")).rstrip("/")
    output_dir = Path(output_dir)
    (output_dir / "story").mkdir(parents=True, exist_ok=True)
    (output_dir / "images").mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    img_tag = f'<img src="../{image_rel}" alt="" style="width:100%;height:auto;border-radius:12px;margin:1rem 0;" loading="lazy">' if image_rel else ""
    story_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <title>{title}</title>
  <meta name="description" content="{title}. Una historia.">
  <link rel="canonical" href="{base_url}/story/{slug}.html">
  <style>{_theme_css("thriller")}</style>
</head>
<body>
  <a href="{base_url}/" class="muted" style="display:inline-block;margin-bottom:1rem;">← Todas las historias</a>
  <article class="card">
    <h1 style="font-size:clamp(1.35rem, 4vw, 1.75rem);">{title}</h1>
    <p class="muted">{now}</p>
    {img_tag}
    <div class="body">{body_html}</div>
  </article>
  {_contact_form_html(config)}
</body>
</html>"""
    (output_dir / "story" / f"{slug}.html").write_text(story_html, encoding="utf-8")

    index_path = output_dir / "index.html"
    if index_path.is_file():
        index_html = index_path.read_text(encoding="utf-8")
        if "</ul>" in index_html:
            new_item = f'    <li><a href="story/{slug}.html">{title}</a></li>\n  </ul>'
            index_html = index_html.replace("  </ul>", new_item, 1)
            index_path.write_text(index_html, encoding="utf-8")
    else:
        index_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <title>Historias</title>
  <link rel="canonical" href="{base_url}/">
  <style>{_theme_css("thriller")}</style>
</head>
<body>
  <h1 class="card">Historias</h1>
  <ul style="list-style:none;padding:0;">
    <li><a href="story/{slug}.html">{title}</a></li>
  </ul>
</body>
</html>"""
        index_path.write_text(index_html, encoding="utf-8")

    story_dir = output_dir / "story"
    urls = [base_url + "/"] + [base_url + "/story/" + f.name for f in sorted(story_dir.glob("*.html"))]
    if (base_url + f"/story/{slug}.html") not in urls:
        urls.append(base_url + f"/story/{slug}.html")
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for u in urls:
        sitemap += f"  <url><loc>{u}</loc><lastmod>{now}</lastmod></url>\n"
    sitemap += "</urlset>"
    (output_dir / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    return slug
