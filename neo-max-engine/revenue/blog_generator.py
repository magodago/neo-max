"""
blog_generator - Genera posts de blog SEO con Ollama: 1200+ palabras, H1/H2/H3, internal links, Schema Article, CTA.
"""

import json
import logging
import re
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from revenue.seo_utils import article_head_seo

logger = logging.getLogger("neo_max.blog_generator")

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:7b-instruct"
TIMEOUT_SECONDS = 600
MAX_TOKENS_BLOG = 4000
OLLAMA_MAX_RETRIES = 3
OLLAMA_RETRY_DELAYS = (2, 4, 8)

MARKER_TITLE = "===TITLE==="
MARKER_META = "===META==="
MARKER_BODY = "===BODY==="


class BlogGenerationError(Exception):
    """Error al generar el post (Ollama o parse)."""
    pass


def _call_ollama(prompt: str, max_tokens: int = MAX_TOKENS_BLOG) -> str | None:
    payload = {"model": MODEL, "prompt": prompt, "stream": False, "options": {"num_predict": max_tokens}}
    last_err = None
    for attempt in range(OLLAMA_MAX_RETRIES):
        req = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return (data.get("response") or "").strip()
        except Exception as e:
            last_err = e
            logger.warning("Ollama blog attempt %d/%d failed: %s", attempt + 1, OLLAMA_MAX_RETRIES, e)
            if attempt < OLLAMA_MAX_RETRIES - 1 and attempt < len(OLLAMA_RETRY_DELAYS):
                time.sleep(OLLAMA_RETRY_DELAYS[attempt])
    if last_err:
        logger.warning("Ollama blog failed after %d attempts: %s", OLLAMA_MAX_RETRIES, last_err)
    return None


def _build_blog_prompt(topic: str, keyword_long_tail: str, tool_slugs: list[str]) -> str:
    tools_links = " ".join(f"[TOOL:{s}]" for s in tool_slugs[:5])
    return f"""Escribe un artículo de blog SEO largo (1200+ palabras) para un sitio de métricas SaaS / finanzas para startups.
IMPORTANTE: Todo el artículo debe estar en ESPAÑOL (título, meta descripción y cuerpo).

Tema: {topic}
Keyword principal a usar con naturalidad: {keyword_long_tail}

Output ONLY the following three blocks, with no other text or markdown:

{MARKER_TITLE}
(one line: the H1 title of the post)

{MARKER_META}
(one or two sentences for meta description, under 160 chars)

{MARKER_BODY}
(Cuerpo del artículo completo en HTML, en español. Usa <h2> y <h3> para secciones. Párrafos cortos. Inserta enlaces internos con estos placeholders: {tools_links} y [LINK:url] para enlaces genéricos. Ejemplo: "Usa nuestra [TOOL:cac-calculator] para calcular." Solo HTML, sin markdown. Termina con conclusión y CTA tipo "Prueba nuestras calculadoras gratis arriba".)
"""


def _parse_blog_response(raw: str) -> dict[str, str] | None:
    raw = raw.strip()
    title_match = re.search(rf"{re.escape(MARKER_TITLE)}\s*\n(.+?)(?=\n|$)", raw, re.IGNORECASE)
    meta_match = re.search(rf"{re.escape(MARKER_META)}\s*\n(.+?)(?=\s*{re.escape(MARKER_BODY)}|$)", raw, re.DOTALL | re.IGNORECASE)
    body_match = re.search(rf"{re.escape(MARKER_BODY)}\s*\n(.*)$", raw, re.DOTALL | re.IGNORECASE)
    if not title_match or not body_match:
        return None
    title = title_match.group(1).strip()
    meta = meta_match.group(1).strip() if meta_match else title[:160]
    meta = re.sub(r"\s+", " ", meta)[:160]
    body = body_match.group(1).strip()
    return {"title": title, "meta": meta, "body": body}


def _slug_from_title(title: str) -> str:
    s = title.lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return s.strip("-")[:80]


def _replace_internal_links(body: str, base_url: str, tool_slugs: list[str]) -> str:
    base = base_url.rstrip("/")
    for slug in tool_slugs:
        body = re.sub(
            rf"\[TOOL:{re.escape(slug)}\]",
            f'<a href="{base}/tools/{slug}/">{slug.replace("-", " ").title()}</a>',
            body,
            flags=re.IGNORECASE,
        )
    body = re.sub(r"\[LINK:([^\]]+)\]", r'<a href="\1">aquí</a>', body)
    return body


def generate_blog_post(
    topic: str,
    keyword_long_tail: str,
    base_url: str,
    tool_slugs: list[str],
) -> tuple[str, str, str] | None:
    """
    Genera un post completo. Retorna (slug, title, html_full) o None si falla.
    """
    prompt = _build_blog_prompt(topic, keyword_long_tail, tool_slugs)
    raw = _call_ollama(prompt)
    if not raw:
        raise BlogGenerationError("Ollama did not return content")
    parsed = _parse_blog_response(raw)
    if not parsed:
        raise BlogGenerationError("Could not parse title/meta/body from response")
    title = parsed["title"]
    meta = parsed["meta"]
    body = parsed["body"]
    body = _replace_internal_links(body, base_url, tool_slugs)
    slug = _slug_from_title(title)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    canonical = f"{base_url.rstrip('/')}/blog/{slug}.html"
    head = article_head_seo(title, meta, canonical, now, now)
    cta = f'<p><a href="{base_url.rstrip("/")}/#tools" style="display:inline-block;padding:.6rem 1.25rem;background:#2563eb;color:#fff;text-decoration:none;border-radius:8px;font-weight:600;">Use free calculators</a></p>'
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
{head}
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    body {{ font-family: 'Inter', system-ui, sans-serif; max-width: 720px; margin: 0 auto; padding: 2rem 1.5rem; line-height: 1.6; background: #f8fafc; }}
    article {{ background: #fff; padding: 2rem; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
    h1 {{ font-size: 1.75rem; margin-bottom: 0.5rem; }}
    h2 {{ font-size: 1.25rem; margin: 1.5rem 0 0.75rem; }}
    h3 {{ font-size: 1.0625rem; margin: 1.25rem 0 0.5rem; }}
    p {{ margin-bottom: 0.75rem; }}
    a {{ color: #2563eb; }}
  </style>
</head>
<body>
  <a href="{base_url.rstrip("/")}/" style="color:#64748b;font-size:.875rem;">← Home</a>
  <article>
    <h1>{title}</h1>
    {body}
    {cta}
  </article>
</body>
</html>
"""
    return (slug, title, html)


def write_blog_post(portal_root: Path, slug: str, html: str, title: str) -> Path:
    """Escribe blog/<slug>.html y devuelve la ruta."""
    blog_dir = Path(portal_root) / "blog"
    blog_dir.mkdir(parents=True, exist_ok=True)
    path = blog_dir / f"{slug}.html"
    path.write_text(html, encoding="utf-8")
    logger.info("Blog post written: %s", path)
    return path
