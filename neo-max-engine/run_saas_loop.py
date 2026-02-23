"""
run_saas_loop - Ejecuta el loop autónomo en bucle para un PC siempre encendido.
Cada CYCLE_HOURS: crea un SaaS (tema + 5 herramientas + 2 posts) y publica.
Cada REVIEW_HOURS: revisa scores y exporta el dashboard.
Pon GITHUB_TOKEN y SERPAPI_KEY en .env. AdSense y afiliados los añades cuando los tengas.
"""

import json
import logging
import os
import sys
import time
from pathlib import Path

# Cargar .env
_env = Path(__file__).resolve().parent / ".env"
if _env.is_file():
    for line in _env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip("'\"")
            if k and k not in os.environ:
                os.environ[k] = v

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("neo_max.run_loop")

PORTAL_OUTPUT = "output/saas-metrics-portal"
CONFIG_PATH = Path(__file__).resolve().parent / "config" / "saas_loop_config.json"


def _load_config() -> dict:
    if not CONFIG_PATH.is_file():
        return {}
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def main() -> None:
    from autonomous_loop import run_autonomous_cycle
    from loop_saas import run_review_and_export

    config = _load_config()
    cycle_hours = int(config.get("cycle_hours", 6))
    review_hours = int(config.get("review_hours", 24))
    min_market_score = int(config.get("min_market_score", 65))

    logger.info("NEO MAX loop started. Cycle every %sh, review every %sh. Ctrl+C to stop.", cycle_hours, review_hours)
    if not os.environ.get("GITHUB_TOKEN"):
        logger.warning("GITHUB_TOKEN not set in .env – publish will fail")
    if not os.environ.get("SERPAPI_KEY"):
        logger.warning("SERPAPI_KEY not set in .env – idea discovery will use fallback only")

    cycle_sec = cycle_hours * 3600
    review_sec = review_hours * 3600
    last_review = 0.0
    cycles = 0

    while True:
        try:
            t0 = time.time()
            run_autonomous_cycle(
                portal_root=PORTAL_OUTPUT,
                use_theme_mode=True,
                publish=True,
                min_market_score=min_market_score,
            )
            cycles += 1
            logger.info("Cycle %d done. Next in %sh.", cycles, cycle_hours)

            if t0 - last_review >= review_sec:
                run_review_and_export(portal_root=PORTAL_OUTPUT)
                last_review = t0
                logger.info("Dashboard exported.")
                from autonomous_loop import run_scale_step
                from pathlib import Path
                if run_scale_step(portals_dir=Path(PORTAL_OUTPUT).parent / "portals"):
                    logger.info("Scaled a portal with good data.")

            elapsed = time.time() - t0
            sleep = max(0, cycle_sec - elapsed)
            if sleep > 0:
                logger.info("Sleeping %.0f min until next cycle.", sleep / 60)
                time.sleep(sleep)
        except KeyboardInterrupt:
            logger.info("Stopped by user.")
            sys.exit(0)
        except Exception as e:
            logger.exception("Cycle error: %s. Retrying in 5 min.", e)
            time.sleep(300)


if __name__ == "__main__":
    main()
