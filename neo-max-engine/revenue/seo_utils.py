"""
seo_utils - Generación de sitemap.xml, robots.txt y fragmentos SEO (head) para herramientas y blog.
"""

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict


class SEOContext(TypedDict):
    title: str
    description: str
    canonical_url: str
    og_type: str
    json_ld_type: str
    json_ld_name: str


def sitemap_xml(urls: list[str], base_url: str, lastmod: str | None = None) -> str:
    """Genera sitemap.xml. urls: rutas relativas. lastmod: fecha ISO (YYYY-MM-DD) para todas las URLs; por defecto hoy (recomendado por Google)."""
    base = base_url.rstrip("/")
    if lastmod is None:
        lastmod = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = ['<?xml version="1.0" encoding="UTF-8"?>']
    out.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for path in urls:
        loc = f"{base}/{path}" if path else base + "/"
        loc = loc.replace("//", "/")
        priority = "1.0" if not path else ("0.9" if path.startswith("tools/") else "0.8")
        changefreq = "weekly" if not path or path.startswith("blog/") else "monthly"
        out.append(f"  <url><loc>{loc}</loc><lastmod>{lastmod}</lastmod><changefreq>{changefreq}</changefreq><priority>{priority}</priority></url>")
    out.append("</urlset>")
    return "\n".join(out)


def robots_txt(base_url: str, sitemap_path: str = "/sitemap.xml") -> str:
    """Genera robots.txt permitiendo todo y enlazando sitemap."""
    base = base_url.rstrip("/")
    return f"""User-agent: *
Allow: /

Sitemap: {base}{sitemap_path}
"""


def tool_head_seo(ctx: SEOContext) -> str:
    """Genera el bloque <head> completo para una página de herramienta (title, meta, canonical, og, JSON-LD)."""
    title = _escape_html(ctx["title"])
    desc = _escape_html(ctx["description"])
    canonical = ctx["canonical_url"]
    og_type = ctx.get("og_type", "website")
    name_ld = ctx.get("json_ld_name", ctx["title"])
    type_ld = ctx.get("json_ld_type", "WebApplication")
    json_ld = f'''  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"{type_ld}","name":"{_escape_json(name_ld)}","description":"{_escape_json(ctx["description"])}","url":"{_escape_json(canonical)}","applicationCategory":"FinanceApplication"}}
  </script>'''
    return f"""  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <meta name="description" content="{desc}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="{_escape_html(canonical)}">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{desc}">
  <meta property="og:type" content="{og_type}">
  <meta property="og:url" content="{_escape_html(canonical)}">
{json_ld}"""


def article_head_seo(title: str, description: str, canonical_url: str, date_published: str, date_modified: str | None = None) -> str:
    """Head para artículo de blog + JSON-LD Article."""
    date_modified = date_modified or date_published
    title_esc = _escape_html(title)
    desc_esc = _escape_html(description)
    json_ld = f'''  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"Article","headline":"{_escape_json(title)}","description":"{_escape_json(description)}","author":{{"@type":"Organization","name":"SaaS Metrics"}},"publisher":{{"@type":"Organization","name":"SaaS Metrics"}},"datePublished":"{date_published}","dateModified":"{date_modified}","mainEntityOfPage":{{"@type":"WebPage","@id":"{_escape_json(canonical_url)}"}}}}
  </script>'''
    return f"""  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title_esc}</title>
  <meta name="description" content="{desc_esc}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="{_escape_html(canonical_url)}">
  <meta property="og:title" content="{title_esc}">
  <meta property="og:description" content="{desc_esc}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{_escape_html(canonical_url)}">
{json_ld}"""


def _escape_html(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _escape_json(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def inject_seo_into_tool_html(html: str, ctx: SEOContext) -> str:
    """
    Reemplaza o inserta <head> en el HTML de una herramienta.
    Si existe <head>, reemplaza su contenido por el SEO completo; si no, inserta <head> después de <html>.
    """
    head_block = tool_head_seo(ctx)
    html_lower = html.lower()
    if "<head>" in html_lower and "</head>" in html_lower:
        pattern = re.compile(r"<head[^>]*>.*?</head>", re.DOTALL | re.IGNORECASE)
        return pattern.sub(f"<head>\n{head_block}\n</head>", html, count=1)
    if "<html" in html_lower:
        return re.sub(r"(<html[^>]*>)", r"\1\n<head>\n" + head_block + "\n</head>", html, count=1, flags=re.IGNORECASE)
    return "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n" + head_block + "\n</head>\n<body>\n" + html + "\n</body>\n</html>"


def collect_urls_for_sitemap(portal_root: Path, base_url: str) -> list[str]:
    """Recorre portal_root y devuelve lista de rutas relativas para sitemap."""
    urls = [""]
    portal_root = Path(portal_root)
    for path in portal_root.rglob("*.html"):
        rel = path.relative_to(portal_root)
        parts = rel.parts
        if parts[0] == "index.html" and len(parts) == 1:
            continue
        if path.name == "index.html":
            folder = str(rel.parent).replace("\\", "/")
            urls.append(folder + "/")
        else:
            urls.append(str(rel).replace("\\", "/"))
    return sorted(set(urls))
