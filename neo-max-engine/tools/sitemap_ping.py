"""
sitemap_ping - Intenta notificar a buscadores cuando el sitemap se actualiza.
Nota: Google y Bing deprecaron el endpoint de ping (404/410). La indexación se basa en
lastmod en el sitemap y en enviar el sitemap en Search Console / Bing Webmaster Tools.
"""

import logging
import urllib.parse
import urllib.request

logger = logging.getLogger("neo_max.sitemap_ping")

GOOGLE_PING = "https://www.google.com/ping?sitemap="
BING_PING = "https://www.bing.com/ping?sitemap="

# Google/Bing devuelven 404/410 desde que deprecaron el ping; no loguear como error
DEPRECATED_STATUSES = (404, 410)


def ping_sitemap(sitemap_url: str, timeout: int = 10) -> dict[str, bool]:
    """
    Intenta notificar a Google y Bing la URL del sitemap.
    Si recibe 404/410 (endpoints deprecados), no se considera error.
    Para indexación óptima: añade lastmod al sitemap y envía la URL en Search Console.
    """
    encoded = urllib.parse.quote(sitemap_url, safe="")
    result = {"google": False, "bing": False}
    for name, base in [("google", GOOGLE_PING), ("bing", BING_PING)]:
        url = base + encoded
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status in (200, 204):
                    result[name] = True
                    logger.info("Sitemap ping %s OK", name)
                elif resp.status in DEPRECATED_STATUSES:
                    logger.debug(
                        "Sitemap ping %s: endpoint deprecated (status %s). Submit sitemap in Search Console.",
                        name, resp.status,
                    )
                else:
                    logger.warning("Sitemap ping %s status %s", name, resp.status)
        except Exception as e:
            err_str = str(e).lower()
            if "404" in err_str or "410" in err_str or "deprecated" in err_str:
                logger.debug("Sitemap ping %s: endpoint deprecated. Submit sitemap in Search Console.", name)
            else:
                logger.warning("Sitemap ping %s failed: %s", name, e)
    return result
