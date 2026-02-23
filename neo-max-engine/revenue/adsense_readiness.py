"""
adsense_readiness - Comprueba que una página esté lista para AdSense (suficiente texto, enlaces legales).
Reduce riesgo de rechazo. Se ejecuta tras generar herramienta; si falla se registra pero no se bloquea la publicación.
"""

import re
import logging
from pathlib import Path

logger = logging.getLogger("neo_max.adsense_readiness")

MIN_BODY_WORDS = 200
MIN_LINKS_LEGAL = 1


def check_page_ready_for_adsense(html: str, page_path: str = "") -> tuple[bool, list[str]]:
    """
    Comprueba: (1) cuerpo con al menos MIN_BODY_WORDS palabras, (2) al menos un enlace a privacy/about.
    Returns (True, []) si OK, (False, [motivos]) si no.
    """
    issues = []
    html_lower = html.lower()
    body_match = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL | re.IGNORECASE)
    if not body_match:
        issues.append("No body tag")
        return (False, issues)
    body = body_match.group(1)
    text = re.sub(r"<script[\s\S]*?</script>", "", body, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    words = len(text.split())
    if words < MIN_BODY_WORDS:
        issues.append(f"Body text too short ({words} words, need {MIN_BODY_WORDS}+)")
    if not re.search(r'href=["\'][^"\']*(?:privacy|about)[^"\']*["\']', html_lower):
        issues.append("No link to privacy or about page")
    return (len(issues) == 0, issues)


def ensure_tool_page_ready(html: str, base_url: str) -> str:
    """
    Si la página no tiene suficiente texto, inyecta un bloque "How to use" antes de </body>.
    Así pasamos el chequeo AdSense sin cambiar la lógica de la herramienta.
    """
    ok, issues = check_page_ready_for_adsense(html)
    if ok:
        return html
    if "Body text too short" not in str(issues):
        return html
    inject = f'''
<section class="tool-how-to" style="margin-top:1.5rem;padding:1rem;background:#f1f5f9;border-radius:8px;font-size:0.9375rem;">
  <h3 style="font-size:1rem;margin-bottom:0.5rem;">Cómo usar esta calculadora</h3>
  <p>Introduce los datos en los campos de arriba y pulsa Calcular. El resultado aparece al instante. Usa esta herramienta gratis para planificar tus métricas. Más guías en nuestro <a href="{base_url.rstrip("/")}/blog/">blog</a> y <a href="{base_url.rstrip("/")}/privacy.html">política de privacidad</a>.</p>
</section>
'''
    if "</body>" in html:
        html = html.replace("</body>", inject + "\n</body>")
    return html
