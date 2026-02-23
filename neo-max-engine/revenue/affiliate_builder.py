"""
affiliate_builder - Genera la estructura /affiliate con páginas por producto (Notion, HubSpot, etc.).
Cada slug tiene un index.html con CTA y enlace de afiliado desde config.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("neo_max.affiliate_builder")

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "saas_loop_config.json"
DEFAULT_AFFILIATE = {
    "notion": {"name": "Notion", "url": "#", "description": "All-in-one workspace."},
    "hubspot": {"name": "HubSpot", "url": "#", "description": "CRM and marketing platform."},
    "monday": {"name": "Monday", "url": "#", "description": "Work OS for teams."},
    "stripe": {"name": "Stripe", "url": "#", "description": "Payments for the internet."},
    "quickbooks": {"name": "QuickBooks", "url": "#", "description": "Accounting software."},
    "paddle": {"name": "Paddle", "url": "#", "description": "SaaS billing and tax."},
    "chartmogul": {"name": "ChartMogul", "url": "#", "description": "SaaS analytics and metrics."},
}


def _load_affiliate_config() -> dict[str, dict[str, str]]:
    if CONFIG_PATH.is_file():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            return data.get("affiliate", DEFAULT_AFFILIATE)
        except Exception as e:
            logger.warning("No se pudo cargar config affiliate: %s. Usando default.", e)
    return DEFAULT_AFFILIATE


def _affiliate_page_html(slug: str, name: str, url: str, description: str, base_url: str) -> str:
    canonical = f"{base_url.rstrip('/')}/affiliate/{slug}/"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{name} – Recommended for SaaS | SaaS Metrics</title>
  <meta name="description" content="{description}">
  <link rel="canonical" href="{canonical}">
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 560px; margin: 0 auto; padding: 2rem; line-height: 1.6; background: #f8fafc; }}
    .card {{ background: #fff; padding: 1.5rem; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
    .cta {{ display: inline-block; margin-top: 1rem; padding: .6rem 1.25rem; background: #2563eb; color: #fff; text-decoration: none; border-radius: 8px; font-weight: 600; }}
    .cta:hover {{ background: #1d4ed8; }}
    a.back {{ color: #64748b; font-size: .875rem; }}
  </style>
</head>
<body>
  <a class="back" href="{base_url.rstrip('/')}/">← Home</a>
  <div class="card">
    <h1>{name}</h1>
    <p>{description}</p>
    <a href="{url}" class="cta">Try {name}</a>
  </div>
</body>
</html>
"""


def build_affiliate_section(portal_root: Path, base_url: str, affiliate_config: dict[str, dict[str, str]] | None = None) -> None:
    """Crea affiliate/<slug>/index.html para cada entrada en config."""
    affiliate = affiliate_config or _load_affiliate_config()
    aff_dir = Path(portal_root) / "affiliate"
    aff_dir.mkdir(parents=True, exist_ok=True)
    for slug, info in affiliate.items():
        if not isinstance(info, dict):
            continue
        name = info.get("name", slug.title())
        url = info.get("url", "#")
        desc = info.get("description", "")
        sub = aff_dir / slug
        sub.mkdir(parents=True, exist_ok=True)
        html = _affiliate_page_html(slug, name, url, desc, base_url)
        (sub / "index.html").write_text(html, encoding="utf-8")
        logger.info("Affiliate page: %s", sub)
