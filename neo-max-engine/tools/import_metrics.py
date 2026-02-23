"""
import_metrics - Importa visitas/clicks desde CSV (export GA4) para scoring real.
Así NEO puede priorizar lo que genera tráfico e ingresos.
Uso: python -m tools.import_metrics data/ga4_export.csv
CSV: url_path,date,visits,clicks (o page_path,date,sessions,events)
"""

import csv
import logging
import os
import sys
from pathlib import Path

# Cargar .env
_env = Path(__file__).resolve().parent.parent / ".env"
if _env.is_file():
    for line in _env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip("'\"")
            if k and k not in os.environ:
                os.environ[k] = v

from revenue.metrics_store import (
    DEFAULT_DB_PATH,
    list_tools,
    record_metrics_daily,
    update_tool_metrics,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("neo_max.import_metrics")


def _normalize_path(path: str) -> str:
    """Convierte /tools/cac/ o tools/cac a tools/cac/ para matchear path_rel."""
    p = path.strip().strip("/").replace("\\", "/")
    if p.startswith("tools/") or p.startswith("blog/"):
        return p + "/" if not p.endswith("/") else p
    if p == "" or p == "index":
        return ""
    return p + "/" if not p.endswith("/") else p


def import_from_csv(csv_path: str, db_path: Path | None = None) -> int:
    """
    Lee CSV con columnas: url_path (o page_path), date, visits (o sessions), clicks (opcional).
    Actualiza metrics_daily y tools.visits/clicks por slug.
    Returns número de filas importadas.
    """
    path = Path(csv_path)
    if not path.is_file():
        logger.warning("File not found: %s", csv_path)
        return 0
    db_path = db_path or DEFAULT_DB_PATH
    count = 0
    tools_by_path: dict[str, dict] = {}
    for t in list_tools(db_path=db_path):
        rel = (t.get("path_rel") or "").strip().rstrip("/")
        slug = (t.get("slug") or "").strip()
        if rel:
            tools_by_path[rel] = t
        if slug:
            tools_by_path[slug] = t
    slug_totals: dict[str, tuple[int, int]] = {}
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return 0
        fields = [x.lower() for x in reader.fieldnames]
        path_col = "url_path" if "url_path" in fields else ("page_path" if "page_path" in fields else None)
        date_col = "date" if "date" in fields else None
        visits_col = "visits" if "visits" in fields else ("sessions" if "sessions" in fields else None)
        clicks_col = "clicks" if "clicks" in fields else ("events" if "events" in fields else None)
        if not path_col or not date_col:
            path_col = path_col or reader.fieldnames[0]
            date_col = date_col or (reader.fieldnames[1] if len(reader.fieldnames) > 1 else None)
        skipped = 0
        for row in reader:
            path_raw = row.get(path_col or "", "").strip()
            date_raw = row.get(date_col or "", "").strip()[:10]
            try:
                raw_v = row.get(visits_col or "", 0) or 0
                raw_c = row.get(clicks_col or "", 0) or 0
                visits = int(raw_v) if raw_v != "" else 0
                clicks = int(raw_c) if raw_c != "" else 0
            except (ValueError, TypeError):
                skipped += 1
                logger.debug("Skip row: invalid visits/clicks: %s", row)
                continue
            if visits < 0 or clicks < 0:
                skipped += 1
                logger.debug("Skip row: negative visits/clicks: %s", row)
                continue
            if not date_raw:
                continue
            path_norm = _normalize_path(path_raw)
            if len(path_norm) > 512:
                logger.debug("Skip row: path too long: %s", path_norm[:80])
                skipped += 1
                continue
            record_metrics_daily(path_norm or "/", date_raw, visits=visits, clicks=clicks, db_path=db_path)
            count += 1
            if path_norm and path_norm.startswith("tools/"):
                slug = path_norm.replace("tools/", "").rstrip("/")
                if tools_by_path.get(slug):
                    v, c = slug_totals.get(slug, (0, 0))
                    slug_totals[slug] = (v + visits, c + clicks)
        if skipped:
            logger.info("Skipped %d rows (invalid or too long path)", skipped)
    for slug, (v, c) in slug_totals.items():
        update_tool_metrics(slug, visits=v, clicks=c, db_path=db_path)
    logger.info("Imported %d rows from %s", count, csv_path)
    return count


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m tools.import_metrics <path_to_ga4_export.csv>")
        print("CSV columns: url_path (or page_path), date, visits (or sessions), clicks (optional)")
        sys.exit(1)
    import_from_csv(sys.argv[1])
