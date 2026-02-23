"""
portal_builder_v2 - Genera el portal SaaS completo: landing, tools con SEO, blog, affiliate, sitemap, robots.
Registra herramientas y posts en metrics_store. Listo para loop autónomo.
"""

import json
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Any

from revenue.affiliate_builder import build_affiliate_section
from revenue.blog_generator import generate_blog_post, write_blog_post, BlogGenerationError
from revenue.metrics_store import add_blog_post, upsert_tool
from revenue.microtool_generator import generate_tool_code, OllamaGenerationError
from revenue.portal_builder import PORTAL_TOOLS
from revenue.design_system import ensure_design_system_in_portal
from revenue.seo_utils import (
    collect_urls_for_sitemap,
    inject_seo_into_tool_html,
    robots_txt,
    sitemap_xml,
    SEOContext,
)
from revenue.adsense_readiness import ensure_tool_page_ready
from revenue.tool_evaluator import evaluate_tool, verify_tool_logic

logger = logging.getLogger("neo_max.portal_builder_v2")

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "saas_loop_config.json"
PORTAL_OUTPUT = "output/saas-metrics-portal"
MAX_TOKENS_SAAS = 1200

MONETIZATION_BLOCK = """
<section class="monetization" aria-label="Recommended tools">
  <h3>Recommended SaaS Tools</h3>
  <div class="affiliate-grid">
    <div class="affiliate-card"><h4>Notion</h4><p>All-in-one workspace.</p><a href="/affiliate/notion/" class="affiliate-btn">Try Now</a></div>
    <div class="affiliate-card"><h4>ChartMogul</h4><p>SaaS analytics.</p><a href="/affiliate/chartmogul/" class="affiliate-btn">Try Now</a></div>
  </div>
  <div id="adsense"></div>
</section>
"""

BLOG_TOPICS_INITIAL = [
    ("What is CAC and how to calculate it", "CAC calculator free"),
    ("How to calculate LTV for SaaS", "LTV calculator SaaS"),
    ("Reducing churn: strategies that work", "churn rate calculator"),
    ("Startup runway: how many months do you have", "runway calculator startup"),
    ("SaaS metrics benchmarks 2025", "saas metrics calculator"),
]


def _load_config() -> dict[str, Any]:
    if not CONFIG_PATH.is_file():
        config = {"base_url": os.environ.get("BASE_URL", "https://magodago.github.io/saas-metrics-tools")}
        return config
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if os.environ.get("BASE_URL"):
        config["base_url"] = os.environ["BASE_URL"]
    return config


def _inject_monetization(html: str) -> str:
    if "</body>" in html.lower():
        return html.replace("</body>", MONETIZATION_BLOCK + "\n</body>")
    return html + "\n" + MONETIZATION_BLOCK


def _write_tool(
    portal_root: Path,
    slug: str,
    code: dict,
    base_url: str,
    title: str,
    problem: str,
) -> None:
    ensure_design_system_in_portal(portal_root)
    tool_dir = portal_root / "tools" / slug
    tool_dir.mkdir(parents=True, exist_ok=True)
    html = code["index.html"]
    canonical = f"{base_url.rstrip('/')}/tools/{slug}/"
    ctx: SEOContext = {
        "title": f"{title} | Calculadoras SaaS",
        "description": f"Calculadora gratis: {title}. {problem[:120]}.",
        "canonical_url": canonical,
        "og_type": "website",
        "json_ld_type": "WebApplication",
        "json_ld_name": title,
    }
    html = inject_seo_into_tool_html(html, ctx)
    html = ensure_tool_page_ready(html, base_url)
    if "<head>" in html and "_base.css" not in html:
        html = html.replace("<head>", "<head>\n  <link rel=\"stylesheet\" href=\"../_base.css\">\n  <link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">\n  <link href=\"https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap\" rel=\"stylesheet\">")
    html = _inject_monetization(html)
    related = f'<section class="related-tools"><h3>Más herramientas</h3><a href="{base_url.rstrip("/")}/">Todas las calculadoras</a></section>'
    if "</body>" in html and "related-tools" not in html:
        html = html.replace("</body>", related + "\n</body>")
    (tool_dir / "index.html").write_text(html, encoding="utf-8")
    (tool_dir / "style.css").write_text(code["style.css"], encoding="utf-8")
    (tool_dir / "script.js").write_text(code["script.js"], encoding="utf-8")


def _build_landing_v2(
    portal_root: Path,
    tool_links: list[dict],
    base_url: str,
    lead_magnet_action: str = "#",
    newsletter_action: str = "#",
    theme: str | None = None,
) -> str:
    links_html = "\n".join(
        f'        <div class="tool-card"><h3>{t["title"]}</h3><p>Calculadora gratis.</p><a href="tools/{t["name"]}/">Usar herramienta →</a></div>'
        for t in tool_links
    )
    if theme:
        site_name = f"Calculadoras {theme}"
        title = f"Calculadoras {theme} gratis – Herramientas online"
        description = f"Calculadoras online de {theme} gratis. Sin registro."
        hero_p = f"Herramientas y calculadoras de {theme} gratis."
    else:
        site_name = "Métricas SaaS"
        title = "Calculadoras de métricas SaaS – CAC, LTV, MRR, Churn, Runway"
        description = "Calculadoras gratis: CAC, LTV, MRR, churn, runway. Finanzas para startups. Sin registro."
        hero_p = "CAC, LTV, MRR, Churn y Runway – las métricas que importan. Sin registro."
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <meta name="description" content="{description}">
  <link rel="canonical" href="{base_url.rstrip('/')}/">
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header class="site-header">
    <div class="wrap"><a class="logo" href="/">{site_name}</a>
    <nav><a href="#tools">Herramientas</a><a href="blog/">Blog</a></nav></div>
  </header>
  <main>
    <section class="hero">
      <h1>Calculadoras {theme or "métricas SaaS"} gratis</h1>
      <p>{hero_p}</p>
      <div class="cta"><a href="#tools" class="btn btn-primary">Ver todas las herramientas</a></div>
    </section>
    <section id="tools" class="tools-grid-section">
      <h2>Calculadoras</h2>
      <p class="section-intro">Elige una herramienta, introduce los datos y obtén el resultado al instante.</p>
      <div class="tools-grid">
{links_html}
      </div>
    </section>
    <section class="monetization">
      <h3>Herramientas SaaS recomendadas</h3>
      <div class="affiliate-grid">
        <div class="affiliate-card"><h4>ChartMogul</h4><p>Analíticas SaaS.</p><a href="affiliate/chartmogul/" class="affiliate-btn">Probar</a></div>
      </div>
      <div id="adsense"></div>
    </section>
    <section class="lead-section">
      <h3>Descarga la guía de métricas SaaS (PDF gratis)</h3>
      <p>Introduce tu email para recibir la guía.</p>
      <form class="lead-form" action="{lead_magnet_action}" method="post">
        <input type="email" name="email" placeholder="Email" required>
        <button type="submit" class="btn btn-primary">Descargar</button>
      </form>
    </section>
  </main>
  <footer class="site-footer"><div class="wrap"><nav><a href="blog/">Blog</a> <a href="privacy.html">Privacidad</a> <a href="about.html">Quiénes somos</a></nav><p class="copy">Hecho con NEO MAX Engine</p></div></footer>
  <script src="script.js"></script>
</body>
</html>
"""


def _write_blog_index(portal_root: Path, posts: list[dict], base_url: str) -> None:
    """Escribe blog/index.html con lista de posts. En español."""
    items = "\n".join(
        f'    <li><a href="{p["slug"]}.html">{p["title"]}</a></li>' for p in posts
    )
    html = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Blog – Métricas SaaS</title><link rel="canonical" href="{base_url.rstrip("/")}/blog/">
</head>
<body style="font-family:system-ui;max-width:720px;margin:0 auto;padding:2rem;">
<h1>Blog</h1>
<p>Guías sobre métricas SaaS y finanzas para startups.</p>
<ul>
{items}
</ul>
<p><a href="{base_url.rstrip("/")}/">← Inicio</a></p>
</body>
</html>
"""
    (portal_root / "blog" / "index.html").write_text(html, encoding="utf-8")


def build_portal_v2(
    output_dir: str = PORTAL_OUTPUT,
    generate_blog_count: int = 0,
    register_in_db: bool = True,
) -> tuple[str, float]:
    """
    Genera portal completo: landing, tools (con SEO), affiliate, opcionalmente blog, sitemap, robots.
    generate_blog_count: 0 = no blog, 1+ = generar N posts (Ollama). Para 5 inicial usar 5.
    register_in_db: si True, registra herramientas y posts en metrics_store.
    Returns (ruta_portal, tiempo_segundos).
    """
    config = _load_config()
    base_url = config.get("base_url", "https://magodago.github.io/saas-metrics-tools")
    portal_root = Path(output_dir)
    portal_root.mkdir(parents=True, exist_ok=True)
    (portal_root / "tools").mkdir(exist_ok=True)
    t_start = time.perf_counter()
    tool_links = []

    for tool in PORTAL_TOOLS:
        name = tool["name"]
        title = tool["title"]
        problem = tool["problem"]
        logger.info("Generating tool: %s", name)
        try:
            code = generate_tool_code(problem, saas=True, max_tokens=MAX_TOKENS_SAAS)
        except OllamaGenerationError as e:
            logger.error("Tool %s failed: %s", name, e)
            raise
        _write_tool(portal_root, name, code, base_url, title, problem)
        logic_ok, logic_msg = verify_tool_logic(portal_root / "tools" / name, problem)
        if not logic_ok:
            logger.warning("Tool %s failed verification: %s. Removing.", name, logic_msg)
            shutil.rmtree(portal_root / "tools" / name, ignore_errors=True)
            continue
        tool_links.append({"name": name, "title": title})
        if register_in_db:
            quality = evaluate_tool(str(portal_root / "tools" / name), problem)
            upsert_tool(name, title, f"tools/{name}/", problem=problem, quality_score=quality)

    ph = config.get("placeholders", {})
    landing = _build_landing_v2(
        portal_root,
        tool_links,
        base_url,
        lead_magnet_action=ph.get("lead_magnet_action", "#"),
        newsletter_action=ph.get("newsletter_action", "#"),
    )
    portal_root.joinpath("index.html").write_text(landing, encoding="utf-8")
    if (portal_root / "style.css").is_file():
        pass
    else:
        portal_root.joinpath("style.css").write_text(":root{--bg:#f8fafc;--card:#fff;--text:#1e293b;--accent:#2563eb;}\nbody{font-family:system-ui;background:var(--bg);margin:0;padding:2rem;}\n.tools-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:1rem;}\n.tool-card{background:var(--card);padding:1.25rem;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.08);}\n.btn{display:inline-block;padding:.6rem 1.25rem;background:var(--accent);color:#fff;text-decoration:none;border-radius:8px;font-weight:600;}\n", encoding="utf-8")
    if (portal_root / "script.js").is_file():
        pass
    else:
        portal_root.joinpath("script.js").write_text("document.querySelector('.lead-form')?.addEventListener('submit',function(e){e.preventDefault();alert('¡Gracias! (Recibirás la guía por email.)');});", encoding="utf-8")

    build_affiliate_section(portal_root, base_url, config.get("affiliate"))
    _write_legal_pages(portal_root, base_url)

    posts_for_index = []
    if generate_blog_count > 0:
        (portal_root / "blog").mkdir(exist_ok=True)
        slugs = [t["name"] for t in tool_links]
        for i, (topic, keyword) in enumerate(BLOG_TOPICS_INITIAL[:generate_blog_count]):
            try:
                result = generate_blog_post(topic, keyword, base_url, slugs)
                if result:
                    slug, title, html = result
                    write_blog_post(portal_root, slug, html, title)
                    posts_for_index.append({"slug": slug, "title": title})
                    if register_in_db:
                        add_blog_post(slug, title, f"blog/{slug}.html", word_count=1200)
            except BlogGenerationError as e:
                logger.warning("Blog post skipped: %s", e)

        if posts_for_index:
            _write_blog_index(portal_root, posts_for_index, base_url)

    urls = collect_urls_for_sitemap(portal_root, base_url)
    portal_root.joinpath("sitemap.xml").write_text(sitemap_xml(urls, base_url), encoding="utf-8")
    portal_root.joinpath("robots.txt").write_text(robots_txt(base_url), encoding="utf-8")

    elapsed = time.perf_counter() - t_start
    logger.info("Portal v2 built in %.1fs at %s", elapsed, portal_root)
    return (str(portal_root), elapsed)


def _write_legal_pages(portal_root: Path, base_url: str) -> None:
    """Privacy y About para cumplir con AdSense y confianza. Todo en español."""
    base = base_url.rstrip("/")
    privacy = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Política de privacidad – Métricas SaaS</title><link rel="canonical" href="{base}/privacy.html">
<style>body{{font-family:system-ui;max-width:720px;margin:0 auto;padding:2rem;line-height:1.6;background:#f8fafc;}}</style>
</head>
<body>
<h1>Política de privacidad</h1>
<p>Utilizamos cookies y tecnologías similares para mejorar tu experiencia y analizar el tráfico. Al usar este sitio aceptas su uso.</p>
<p>Podemos usar Google AdSense; Google puede usar cookies para mostrar anuncios según tus visitas. Puedes desactivar la publicidad personalizada en la configuración de Google.</p>
<p>No vendemos tus datos personales. Para consultas, contacta al responsable del sitio.</p>
<p><a href="{base}/">Inicio</a></p>
</body>
</html>
"""
    about = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Quiénes somos – Métricas SaaS</title><link rel="canonical" href="{base}/about.html">
<style>body{{font-family:system-ui;max-width:720px;margin:0 auto;padding:2rem;line-height:1.6;background:#f8fafc;}}</style>
</head>
<body>
<h1>Quiénes somos</h1>
<p>Calculadoras gratis de métricas SaaS para startups y equipos: CAC, LTV, MRR, churn, runway y más. Sin registro.</p>
<p><a href="{base}/">Inicio</a></p>
</body>
</html>
"""
    portal_root.joinpath("privacy.html").write_text(privacy, encoding="utf-8")
    portal_root.joinpath("about.html").write_text(about, encoding="utf-8")


# Títulos que corresponden al mismo concepto -> slug canónico. Aliases: otros slugs que cuentan como "ya existe".
_CANONICAL_SLUGS: list[tuple[list[str], str, list[str]]] = [
    (["cac", "customer acquisition cost", "customer acquisition"], "cac-calculator", ["cac-calculator", "customer-acquisition-cost-calculator"]),
    (["ltv", "lifetime value", "cltv", "clv", "customer lifetime value"], "ltv-calculator", ["ltv-calculator"]),
    (["mrr to arr", "mrr to annual", "monthly recurring to annual"], "mrr-to-arr-converter", ["mrr-to-arr-converter"]),
    (["churn rate", "churn calculator"], "churn-calculator", ["churn-calculator", "churn-rate-calculator"]),
    (["conversion rate"], "conversion-rate-calculator", ["conversion-rate-calculator"]),
    (["monthly recurring revenue", "mrr calculator"], "mrr-calculator", ["mrr-calculator"]),
    (["annual recurring revenue", "arr calculator"], "arr-calculator", ["arr-calculator"]),
    (["runway", "runway calculator"], "runway-calculator", ["runway-calculator"]),
    (["customer retention rate"], "customer-retention-rate-calculator", ["customer-retention-rate-calculator"]),
    (["freelancer hourly rate", "hourly rate calculator"], "freelancer-hourly-rate-calculator", ["freelancer-hourly-rate-calculator"]),
    (["marketing roi", "roi calculator for marketing"], "marketing-roi-calculator", ["marketing-roi-calculator"]),
    (["profit margin", "profit margin calculator"], "profit-margin-calculator", ["profit-margin-calculator"]),
]


def _slug_from_title(title: str) -> str:
    import re
    t_lower = title.lower().strip()
    for keywords, canonical, _ in _CANONICAL_SLUGS:
        if any(kw in t_lower for kw in keywords):
            return canonical
    s = t_lower
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return s.strip("-")[:50]


def _existing_slugs_for_canonical(canonical_slug: str) -> list[str]:
    """Slugs que se consideran el mismo concepto que canonical_slug (para no duplicar)."""
    for _keywords, canon, aliases in _CANONICAL_SLUGS:
        if canon == canonical_slug:
            return aliases
    return [canonical_slug]


def _theme_to_repo_slug(theme: str) -> str:
    """Convierte tema a slug para repo: 'SaaS metrics' -> 'saas-metrics-calculators'."""
    slug = _slug_from_title(theme)
    return f"{slug}-calculators" if slug else "calculators"


def build_portal_for_theme(
    theme: str,
    tools_titles: list[str],
    output_dir: str | Path,
    base_url: str,
    repo_name: str | None = None,
    register_in_db: bool = True,
    blog_posts_count: int = 5,
) -> tuple[str, list[str], list[str]]:
    """
    Crea un portal nuevo desde cero para un tema: landing (vacía), 5 tools, blog del tema, legal, sitemap.
    Pensado para modo "un portal por tema". Retorna (ruta_portal, slugs_tools, slugs_blog).
    """
    portal_root = Path(output_dir)
    portal_root.mkdir(parents=True, exist_ok=True)
    (portal_root / "tools").mkdir(exist_ok=True)
    config = _load_config()
    ph = config.get("placeholders", {})
    ensure_design_system_in_portal(portal_root)
    landing = _build_landing_v2(
        portal_root,
        [],
        base_url,
        lead_magnet_action=ph.get("lead_magnet_action", "#"),
        newsletter_action=ph.get("newsletter_action", "#"),
        theme=theme,
    )
    portal_root.joinpath("index.html").write_text(landing, encoding="utf-8")
    if not (portal_root / "style.css").is_file():
        portal_root.joinpath("style.css").write_text(
            ":root{--bg:#f8fafc;--card:#fff;--text:#1e293b;--accent:#2563eb;}\nbody{font-family:system-ui;background:var(--bg);margin:0;padding:2rem;}\n.tools-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:1rem;}\n.tool-card{background:var(--card);padding:1.25rem;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.08);}\n.btn{display:inline-block;padding:.6rem 1.25rem;background:var(--accent);color:#fff;text-decoration:none;border-radius:8px;font-weight:600;}\n",
            encoding="utf-8",
        )
    if not (portal_root / "script.js").is_file():
        portal_root.joinpath("script.js").write_text(
            "document.querySelector('.lead-form')?.addEventListener('submit',function(e){e.preventDefault();alert('¡Gracias!');});",
            encoding="utf-8",
        )
    _write_legal_pages(portal_root, base_url)
    build_affiliate_section(portal_root, base_url, config.get("affiliate"))
    repo_name = repo_name or _theme_to_repo_slug(theme)
    (portal_root / "_theme.txt").write_text(theme.strip(), encoding="utf-8")
    slugs = []
    for title in tools_titles:
        slug = add_single_tool_to_portal(
            portal_root,
            problem=title,
            title=title,
            slug=None,
            base_url=base_url,
            register_in_db=register_in_db,
            portal_repo=repo_name,
        )
        if slug:
            slugs.append(slug)
    blog_slugs = []
    if len(slugs) >= 2:
        blog_slugs = add_blog_posts_for_theme(
            portal_root, theme, slugs, base_url=base_url, count=blog_posts_count, register_in_db=register_in_db
        )
    urls = collect_urls_for_sitemap(portal_root, base_url)
    portal_root.joinpath("sitemap.xml").write_text(sitemap_xml(urls, base_url), encoding="utf-8")
    portal_root.joinpath("robots.txt").write_text(robots_txt(base_url), encoding="utf-8")
    logger.info("Portal for theme %r built at %s: %d tools, %d blog posts", theme, portal_root, len(slugs), len(blog_slugs))
    return (str(portal_root), slugs, blog_slugs)


def _slug_to_display_title(slug: str) -> str:
    """Convierte slug a título legible: marketing-roi-calculator -> Marketing ROI calculator."""
    return slug.replace("-", " ").title()


def _rebuild_tools_grid_in_index(portal_root: Path) -> None:
    """
    Reconstruye la sección tools-grid del index.html leyendo todas las carpetas en tools/.
    Así el index siempre muestra todas las tools (evita que una nueva no aparezca si el insert falló).
    """
    import re
    tools_dir = portal_root / "tools"
    index_path = portal_root / "index.html"
    if not tools_dir.is_dir() or not index_path.is_file():
        return
    slugs = sorted(d.name for d in tools_dir.iterdir() if d.is_dir() and not d.name.startswith("."))
    # Obtener título por tool: del index.html de la tool si tiene <h1> o <h3>, sino del slug (vacío = grid vacío)
    cards = []
    for s in slugs:
        title = _slug_to_display_title(s)
        tool_index = tools_dir / s / "index.html"
        if tool_index.is_file():
            try:
                content = tool_index.read_text(encoding="utf-8")
                for pattern in [r"<h1[^>]*>([^<]+)</h1>", r"<h3[^>]*>([^<]+)</h3>", r"<title[^>]*>([^<]+)</title>"]:
                    m = re.search(pattern, content, re.IGNORECASE)
                    if m:
                        title = m.group(1).strip()
                        if len(title) > 80:
                            title = title[:77] + "..."
                        break
            except Exception:
                pass
        safe_title = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
        cards.append(f'        <div class="tool-card"><h3>{safe_title}</h3><p>Calculadora gratis.</p><a href="tools/{s}/">Usar herramienta →</a></div>')
    new_grid_inner = "\n".join(cards)
    html = index_path.read_text(encoding="utf-8")
    open_markers = ['<div class="tools-grid">', '<div class="tools-grid"']
    start = -1
    for om in open_markers:
        idx = html.find(om)
        if idx != -1:
            start = idx + len(om)
            break
    if start == -1:
        logger.warning("tools-grid not found in index.html; cannot rebuild.")
        return
    close_pattern = "      </div>\n    </section>"
    end = html.find(close_pattern, start)
    if end == -1:
        close_pattern = "</div>\n      </div>\n    </section>"
        end = html.find(close_pattern, start)
    if end == -1:
        logger.warning("tools-grid closing not found in index.html; cannot rebuild.")
        return
    html = html[:start] + "\n" + new_grid_inner + "\n" + html[end:]
    index_path.write_text(html, encoding="utf-8")
    logger.info("Rebuilt index.html tools grid with %d tools.", len(slugs))


def add_single_tool_to_portal(
    portal_root: Path | str,
    problem: str,
    title: str,
    slug: str | None = None,
    base_url: str | None = None,
    register_in_db: bool = True,
    portal_repo: str | None = None,
) -> str | None:
    """
    Añade una sola herramienta al portal existente: genera con Ollama, escribe en tools/<slug>/,
    actualiza index.html (grid) y sitemap. Retorna slug o None si falla.
    Si la herramienta con ese slug ya existe en el portal, no hace nada y retorna None (evita duplicados).
    """
    portal_root = Path(portal_root)
    config = _load_config()
    base_url = base_url or config.get("base_url", "https://magodago.github.io/saas-metrics-tools")
    if slug is None:
        slug = _slug_from_title(title)
    tools_dir = portal_root / "tools"
    if tools_dir.is_dir():
        existing = {d.name for d in tools_dir.iterdir() if d.is_dir()}
        same_concept = _existing_slugs_for_canonical(slug)
        if any(s in existing for s in same_concept):
            logger.info("Tool %s (or equivalent) already exists in portal; skipping (no duplicate).", slug)
            return None
    for attempt in range(2):
        try:
            code = generate_tool_code(problem, saas=True, max_tokens=MAX_TOKENS_SAAS)
        except OllamaGenerationError as e:
            logger.error("Add tool failed: %s", e)
            return None
        _write_tool(portal_root, slug, code, base_url, title, problem)
        logic_ok, logic_msg = verify_tool_logic(portal_root / "tools" / slug, problem)
        if logic_ok:
            break
        logger.warning("Tool %s failed logic check (intento %d): %s.", slug, attempt + 1, logic_msg)
        tool_dir = portal_root / "tools" / slug
        if tool_dir.is_dir():
            shutil.rmtree(tool_dir, ignore_errors=True)
        if attempt == 1:
            return None
    index_path = portal_root / "index.html"
    if index_path.is_file():
        _rebuild_tools_grid_in_index(portal_root)
    urls = collect_urls_for_sitemap(portal_root, base_url)
    portal_root.joinpath("sitemap.xml").write_text(sitemap_xml(urls, base_url), encoding="utf-8")
    if register_in_db:
        quality = evaluate_tool(str(portal_root / "tools" / slug), problem)
        upsert_tool(slug, title, f"tools/{slug}/", problem=problem, quality_score=quality, portal_repo=portal_repo)
    logger.info("Added tool: %s", slug)
    return slug


def remove_tool_from_portal(portal_root: Path | str, slug: str, base_url: str | None = None) -> bool:
    """Elimina una herramienta del portal: carpeta, DB, rehace index y sitemap. Devuelve True si existía."""
    from revenue.metrics_store import delete_tool
    portal_root = Path(portal_root)
    tool_dir = portal_root / "tools" / slug
    if tool_dir.is_dir():
        shutil.rmtree(tool_dir, ignore_errors=True)
    removed = delete_tool(slug)
    if portal_root.joinpath("index.html").is_file():
        _rebuild_tools_grid_in_index(portal_root)
    config = _load_config()
    url = base_url or config.get("base_url", "https://magodago.github.io/saas-metrics-tools")
    urls = collect_urls_for_sitemap(portal_root, url)
    portal_root.joinpath("sitemap.xml").write_text(sitemap_xml(urls, url), encoding="utf-8")
    logger.info("Removed tool from portal: %s", slug)
    return removed


def add_blog_posts_for_theme(
    portal_root: Path | str,
    theme: str,
    tool_slugs: list[str],
    base_url: str | None = None,
    count: int = 2,
    register_in_db: bool = True,
) -> list[str]:
    """
    Genera `count` posts de blog sobre el tema, con enlaces a las herramientas en tool_slugs.
    Actualiza blog/index.html y sitemap. Retorna lista de slugs de posts creados.
    """
    portal_root = Path(portal_root)
    config = _load_config()
    base_url = base_url or config.get("base_url", "https://magodago.github.io/saas-metrics-tools")
    (portal_root / "blog").mkdir(parents=True, exist_ok=True)
    created = []
    topics = [
        (f"Qué es {theme} y cómo usarlo", f"calculadora {theme}"),
        (f"Mejores herramientas y guías de {theme}", f"herramienta {theme} gratis"),
        (f"Cómo calcular {theme} paso a paso", f"calculadora {theme} gratis"),
        (f"Benchmarks y buenas prácticas de {theme}", f"métricas {theme}"),
        (f"Errores comunes con {theme} y cómo evitarlos", f"guía {theme}"),
    ]
    for i in range(min(count, len(topics))):
        topic, keyword = topics[i][0], topics[i][1]
        try:
            result = generate_blog_post(topic, keyword, base_url, tool_slugs)
            if result:
                slug, title, html = result
                write_blog_post(portal_root, slug, html, title)
                created.append(slug)
                if register_in_db:
                    add_blog_post(slug, title, f"blog/{slug}.html", word_count=1200)
        except BlogGenerationError as e:
            logger.warning("Blog post skipped: %s", e)
    if created:
        _refresh_blog_index(portal_root, base_url)
        urls = collect_urls_for_sitemap(portal_root, base_url)
        portal_root.joinpath("sitemap.xml").write_text(sitemap_xml(urls, base_url), encoding="utf-8")
    return created


def _refresh_blog_index(portal_root: Path, base_url: str) -> None:
    """Reconstruye blog/index.html con todos los .html del blog (excepto index)."""
    blog_dir = portal_root / "blog"
    if not blog_dir.is_dir():
        return
    posts = []
    for f in sorted(blog_dir.glob("*.html")):
        if f.name == "index.html":
            continue
        slug = f.stem
        posts.append({"slug": slug, "title": slug.replace("-", " ").title()})
    if not posts:
        return
    _write_blog_index(portal_root, posts, base_url)
