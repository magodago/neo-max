"""
Búsqueda en internet sin abrir el navegador (evita CAPTCHA de Google).
Primero intenta duckduckgo-search (API fiable); si falla, DuckDuckGo HTML.
"""
import logging
import re
import urllib.parse
import urllib.request

logger = logging.getLogger("neo_desktop.search")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
MAX_RESULTS = 8
TIMEOUT = 15


def _search_via_package(query: str, max_results: int) -> str | None:
    """Usa el paquete duckduckgo-search (DDGS). Devuelve texto con resultados o None si falla."""
    try:
        from duckduckgo_search import DDGS
        # API: DDGS().text(keywords, ...) devuelve lista (v8) o iterable; sin context manager
        ddgs = DDGS()
        items = ddgs.text(query, region="es-es", max_results=max_results)
        items = list(items) if items is not None else []
        if not items:
            return None
        lines = []
        for r in items:
            title = (r.get("title") or "").strip()
            body = (r.get("body") or "").strip()
            href = (r.get("href") or "").strip()
            if not title and not body:
                continue
            line = f"- {title}" if title else "- (sin título)"
            if body:
                line += "\n  " + (body[:300] + "…" if len(body) > 300 else body)
            if href:
                line += f"\n  {href}"
            lines.append(line)
        if not lines:
            return None
        return "Resultados de búsqueda (DuckDuckGo):\n\n" + "\n\n".join(lines[:max_results])
    except Exception as e:
        logger.warning("duckduckgo_search package failed: %s", e)
        return None


def _search_via_html(query: str, max_results: int) -> str | None:
    """Fallback: scrape de DuckDuckGo HTML. Devuelve texto o None."""
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        logger.warning("DuckDuckGo HTML falló: %s", e)
        return None
    results = []
    for m in re.finditer(
        r'<a[^>]+href="[^"]*uddg=[^"]*"[^>]*>([^<]+)</a>',
        html,
        re.IGNORECASE,
    ):
        text = re.sub(r"\s+", " ", m.group(1).strip())
        if len(text) < 5 or text.lower() in ("feedback", "next", "previous", "all regions", "any time"):
            continue
        if len(text) > 250:
            text = text[:247] + "…"
        results.append("- " + text)
        if len(results) >= max_results:
            break
    if not results:
        for m in re.finditer(r'<h2[^>]*>([^<]+)</h2>\s*<a[^>]*>([^<]{20,400})</a>', html, re.IGNORECASE | re.DOTALL):
            title = re.sub(r"\s+", " ", m.group(1).strip())
            snippet = re.sub(r"\s+", " ", m.group(2).strip())
            results.append(f"- {title}\n  {snippet[:280]}" + ("…" if len(snippet) > 280 else ""))
            if len(results) >= max_results:
                break
    if not results:
        return None
    return "Resultados de búsqueda (DuckDuckGo):\n\n" + "\n\n".join(results[:max_results])


def web_search(query: str, max_results: int = MAX_RESULTS) -> str:
    """
    Busca en internet (DuckDuckGo). Primero usa el paquete duckduckgo-search; si falla, HTML.
    Sin navegador, sin CAPTCHA.
    """
    query = (query or "").strip()[:500]
    if not query:
        return "Búsqueda vacía. Usa SEARCH: <tu consulta>."
    out = _search_via_package(query, max_results)
    if out:
        return out
    out = _search_via_html(query, max_results)
    if out:
        return out
    return "No se encontraron resultados para esa búsqueda. Prueba otras palabras o BROWSER:go a una URL concreta (ej. expansion.com para IBEX)."
