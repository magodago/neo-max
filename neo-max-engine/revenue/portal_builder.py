"""
portal_builder - Genera el portal vertical "SaaS Metrics & Startup Finance".
Un micro-portal temático con landing y herramientas. Si alguna herramienta falla, se aborta todo.
"""

import logging
import time
from pathlib import Path

from revenue.microtool_generator import generate_tool_code, OllamaGenerationError

logger = logging.getLogger("neo_max.portal_builder")

PORTAL_OUTPUT = "output/saas-metrics-portal"
PORTAL_REPO_NAME = "saas-metrics-tools"
MAX_TOKENS_SAAS = 1200

# Bloque preparado para monetización (afiliación futura)
MONETIZATION_BLOCK_HTML = """
<!-- MONETIZATION_BLOCK -->
<section class="monetization-block" aria-label="Recomendación">
  <p>Need help optimizing your SaaS metrics? We recommend using professional analytics tools.</p>
  <a href="#" class="monetization-cta">Explore tools</a>
</section>
"""

# Herramientas del vertical inicial. add_new_saas_tool() amplía esta lista.
PORTAL_TOOLS = [
    {"name": "cac-calculator", "title": "CAC Calculator", "problem": "Calculadora de CAC (Customer Acquisition Cost) para SaaS: inputs coste marketing y ventas, número de clientes nuevos; mostrar CAC por cliente."},
    {"name": "ltv-calculator", "title": "LTV Calculator", "problem": "Calculadora de LTV (Lifetime Value) para SaaS: ingresos medios por cliente, retención o churn; mostrar LTV."},
    {"name": "mrr-calculator", "title": "MRR Calculator", "problem": "Calculadora de MRR (Monthly Recurring Revenue): número de clientes por plan y precio por plan; mostrar MRR total."},
    {"name": "churn-calculator", "title": "Churn Calculator", "problem": "Calculadora de Churn rate para SaaS: clientes al inicio del periodo, clientes perdidos; mostrar porcentaje de churn."},
    {"name": "runway-calculator", "title": "Runway Calculator", "problem": "Calculadora de Runway para startup: cash actual, burn rate mensual; mostrar meses de runway restantes."},
]


def add_new_saas_tool(name: str, description: str, problem: str | None = None) -> None:
    """
    Añade una nueva herramienta al portal (para evolución futura).
    name: slug (ej. 'arr-calculator')
    description: título legible (ej. 'ARR Calculator')
    problem: enunciado para la IA (opcional; si no se pasa, se usa description)
    """
    PORTAL_TOOLS.append({
        "name": name,
        "title": description,
        "problem": problem or f"Calculadora SaaS: {description}",
    })
    logger.info("Herramienta añadida al portal: %s", name)


def _inject_monetization(html: str) -> str:
    """Inserta MONETIZATION_BLOCK antes de </body>."""
    if "</body>" in html.lower():
        return html.replace("</body>", MONETIZATION_BLOCK_HTML + "\n</body>")
    return html + "\n" + MONETIZATION_BLOCK_HTML


def _write_tool(portal_root: Path, tool_name: str, code: dict) -> None:
    """Escribe index.html, style.css, script.js en portal_root/tools/tool_name/ e inyecta monetización."""
    tool_dir = portal_root / "tools" / tool_name
    tool_dir.mkdir(parents=True, exist_ok=True)
    html = _inject_monetization(code["index.html"])
    (tool_dir / "index.html").write_text(html, encoding="utf-8")
    (tool_dir / "style.css").write_text(code["style.css"], encoding="utf-8")
    (tool_dir / "script.js").write_text(code["script.js"], encoding="utf-8")


def _build_landing(portal_root: Path, tool_links: list[dict]) -> str:
    """Genera el HTML de la landing principal con SEO, intro CAC/LTV/MRR y lista de herramientas."""
    links_html = "\n".join(
        f'      <li><a href="tools/{t["name"]}/">{t["title"]}</a></li>' for t in tool_links
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Free SaaS Metrics Calculators – CAC, LTV, MRR & More</title>
  <meta name="description" content="Free online calculators for SaaS metrics: CAC, LTV, MRR, Churn, Runway. Essential startup finance and unit economics tools.">
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 720px; margin: 0 auto; padding: 2rem; line-height: 1.6; }}
    h1 {{ font-size: 1.5rem; }}
    ul {{ list-style: none; padding: 0; }}
    ul a {{ display: block; padding: 0.5rem 0; color: #0066cc; }}
    .monetization-block {{ margin-top: 2rem; padding: 1rem; background: #f5f5f5; border-radius: 8px; }}
    .monetization-cta {{ display: inline-block; margin-top: 0.5rem; padding: 0.5rem 1rem; background: #333; color: #fff; text-decoration: none; border-radius: 4px; }}
    footer {{ margin-top: 2rem; font-size: 0.9rem; color: #666; }}
  </style>
</head>
<body>
  <h1>Free SaaS Metrics Calculators</h1>
  <p>CAC, LTV, MRR, Churn & Runway – essential tools for startup finance.</p>

  <h2>Key metrics</h2>
  <p><strong>CAC</strong> (Customer Acquisition Cost) is the cost to acquire one customer. <strong>LTV</strong> (Lifetime Value) is the total revenue you expect from a customer. <strong>MRR</strong> (Monthly Recurring Revenue) is your predictable monthly revenue from subscriptions.</p>

  <h2>Tools</h2>
  <ul>
{links_html}
  </ul>

  <!-- MONETIZATION_BLOCK -->
  <section class="monetization-block" aria-label="Recomendación">
    <p>Need help optimizing your SaaS metrics? We recommend using professional analytics tools.</p>
    <a href="#" class="monetization-cta">Explore tools</a>
  </section>

  <footer>Built by NEO MAX Engine</footer>
</body>
</html>
"""


def build_portal(output_dir: str = PORTAL_OUTPUT) -> tuple[str, float]:
    """
    Genera el portal completo: landing + todas las herramientas.
    Si cualquier herramienta falla (OllamaGenerationError), aborta y relanza la excepción.
    Returns:
        (ruta del portal, tiempo total generación en segundos)
    """
    portal_root = Path(output_dir)
    portal_root.mkdir(parents=True, exist_ok=True)
    (portal_root / "tools").mkdir(exist_ok=True)

    t_total_start = time.perf_counter()
    tool_times: list[tuple[str, float]] = []

    for tool in PORTAL_TOOLS:
        name = tool["name"]
        problem = tool["problem"]
        logger.info("Generando herramienta: %s", name)
        t_start = time.perf_counter()
        try:
            code = generate_tool_code(problem, saas=True, max_tokens=MAX_TOKENS_SAAS)
        except OllamaGenerationError:
            logger.error("Abortando portal: fallo en herramienta %s. No se publica portal incompleto.", name)
            raise
        elapsed = time.perf_counter() - t_start
        tool_times.append((name, elapsed))
        logger.info("Tiempo generación %s: %.1fs", name, elapsed)
        _write_tool(portal_root, name, code)

    # Landing
    landing_html = _build_landing(portal_root, PORTAL_TOOLS)
    (portal_root / "index.html").write_text(landing_html, encoding="utf-8")

    t_total = time.perf_counter() - t_total_start
    logger.info("Tiempo total generación portal: %.1fs", t_total)
    return (str(portal_root), t_total)
