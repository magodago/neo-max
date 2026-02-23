"""
loop_saas - Loop autónomo SaaS: revisar herramientas (score, 70/50/descartar), añadir nuevas, publicar.
Registra decisiones en metrics_store y opcionalmente exporta log CSV.
"""

import csv
import json
import logging
import os
import time
from pathlib import Path

from revenue.metrics_store import (
    DEFAULT_DB_PATH,
    export_dashboard_json,
    list_tools,
    record_decision,
    update_tool_metrics,
    upsert_tool,
)
from revenue.tool_evaluator import evaluate_tool
from tools.github_publisher import publish_portal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("neo_max.loop_saas")

CONFIG_PATH = Path(__file__).resolve().parent / "config" / "saas_loop_config.json"
PORTAL_OUTPUT = "output/saas-metrics-portal"
LOG_CSV_PATH = Path(__file__).resolve().parent / "data" / "loop_decisions.csv"


def _load_config() -> dict:
    if not CONFIG_PATH.is_file():
        return {}
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _engagement_to_score(visits: int, clicks: int) -> float:
    """Convierte visitas/clicks en score 0–100 (normalizado simple)."""
    raw = visits + clicks * 2
    if raw >= 100:
        return 100.0
    return min(100.0, float(raw))


def review_portal(portal_root: str | Path, db_path: Path | None = None) -> None:
    """
    Revisa todas las herramientas en la DB: recalcula quality (si existe path),
    engagement desde visits/clicks, score_final. Aplica reglas 70/50/<50 y registra decisiones.
    """
    config = _load_config()
    scoring = config.get("scoring", {})
    keep_threshold = int(scoring.get("keep_threshold", 70))
    improve_threshold = int(scoring.get("improve_threshold", 50))
    qw = float(scoring.get("quality_weight", 0.5))
    ew = float(scoring.get("engagement_weight", 0.5))

    portal_root = Path(portal_root)
    tools = list_tools(db_path=db_path)
    for t in tools:
        slug = t["slug"]
        path_rel = t.get("path_rel", "")
        if path_rel:
            tool_path = portal_root / path_rel.rstrip("/")
        else:
            tool_path = portal_root / "tools" / slug
        quality = t.get("quality_score")
        if quality is None and tool_path.is_dir():
            quality = evaluate_tool(str(tool_path), t.get("problem") or slug)
        if quality is None:
            quality = 0
        visits = int(t.get("visits") or 0)
        clicks = int(t.get("clicks") or 0)
        engagement = _engagement_to_score(visits, clicks)
        score_final = qw * quality + ew * (engagement / 100.0) * 100
        score_final = round(min(100, score_final), 1)

        if score_final >= keep_threshold:
            new_status = "active"
            reason = f"score {score_final} >= {keep_threshold}"
        elif score_final >= improve_threshold:
            new_status = "improve"
            reason = f"score {score_final} in [{improve_threshold},{keep_threshold})"
        else:
            new_status = "discarded"
            reason = f"score {score_final} < {improve_threshold}"

        update_tool_metrics(
            slug,
            quality_score=quality,
            engagement_score=engagement,
            score_final=score_final,
            status=new_status,
            db_path=db_path,
        )
        record_decision(
            t["id"],
            new_status,
            score_final=score_final,
            reason=reason,
            db_path=db_path,
        )
        append_decision_log_csv({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
            "slug": slug,
            "action": new_status,
            "score_final": str(score_final),
            "reason": reason,
        })
        logger.info("Tool %s: quality=%s engagement=%.0f final=%.1f -> %s", slug, quality, engagement, score_final, new_status)


def append_decision_log_csv(row: dict, path: Path = LOG_CSV_PATH) -> None:
    """Añade una fila al CSV de decisiones (para historial)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = path.is_file()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["timestamp", "slug", "action", "score_final", "reason"])
        if not file_exists:
            w.writeheader()
        w.writerow(row)


def _build_portals_list(portal_root: str | Path) -> list[dict]:
    """Lista de portales (sitios) con name y base_url para el dashboard."""
    config = _load_config()
    portals = []
    base = config.get("base_url", "").rstrip("/")
    main_repo = config.get("portal_repo_name") or "saas-metrics-tools"
    if base:
        portals.append({"name": main_repo, "base_url": base, "label": "Portal principal"})
    gh_user = config.get("github_user") or "magodago"
    portals_dir = Path(portal_root).parent / "portals"
    if portals_dir.is_dir():
        for d in sorted(portals_dir.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                portals.append({
                    "name": d.name,
                    "base_url": f"https://{gh_user}.github.io/{d.name}",
                    "label": d.name.replace("-", " ").title(),
                })
    return portals


def run_review_and_export(portal_root: str = PORTAL_OUTPUT, dashboard_path: str | Path | None = None) -> None:
    """Ejecuta review_portal y exporta JSON del dashboard (por defecto output/dashboard/dashboard_data.json)."""
    review_portal(portal_root)
    if dashboard_path is not None:
        out = Path(dashboard_path)
    else:
        out = Path(__file__).resolve().parent / "output" / "dashboard" / "dashboard_data.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    export_dashboard_json(out, DEFAULT_DB_PATH)
    data = json.loads(out.read_text(encoding="utf-8"))
    data["portals"] = _build_portals_list(portal_root)
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    template = Path(__file__).resolve().parent / "dashboard" / "index.html"
    if template.is_file():
        import shutil
        shutil.copy(template, out.parent / "index.html")
    dashboard_repo = _load_config().get("dashboard_repo_name")
    if dashboard_repo:
        from tools.github_publisher import publish_portal
        dash_url = publish_portal(str(out.parent), repo_name_override=dashboard_repo)
        if dash_url:
            logger.info("Dashboard published (visible desde fuera): %s", dash_url)
    logger.info("Dashboard data exported to %s", out)


def main() -> None:
    """CLI: python -m loop_saas [review|build]"""
    import sys
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "review").lower()
    if cmd == "review":
        run_review_and_export()
        return
    if cmd == "build":
        from revenue.portal_builder_v2 import build_portal_v2
        from tools.sitemap_ping import ping_sitemap
        portal_path, _ = build_portal_v2(generate_blog_count=0, register_in_db=True)
        config = _load_config()
        url = publish_portal(portal_path, repo_name_override=config.get("portal_repo_name"))
        if url:
            logger.info("Portal published: %s", url)
            if config.get("base_url"):
                ping_sitemap(config["base_url"].rstrip("/") + "/sitemap.xml")
        run_review_and_export(portal_root=portal_path)
        return
    logger.info("Usage: python -m loop_saas review | build")


if __name__ == "__main__":
    main()
