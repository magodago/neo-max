"""
portal_engine - Orquesta la generación y publicación del portal vertical.
Vertical: "SaaS Metrics & Startup Finance".
Si cualquier herramienta falla en generación IA, se aborta todo y no se publica.
"""

import logging
import time

from revenue.portal_builder import build_portal, PORTAL_OUTPUT
from revenue.microtool_generator import OllamaGenerationError
from tools.github_publisher import publish_portal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("neo_max.portal")


def main() -> None:
    """Genera el portal completo y lo publica. Aborta si alguna herramienta falla."""
    logger.info("Portal engine iniciado – Vertical: SaaS Metrics & Startup Finance")
    t_start = time.perf_counter()
    estado = "FAILED"

    try:
        # 1. Generar portal (todas las herramientas + landing)
        portal_path, t_generacion = build_portal(output_dir=PORTAL_OUTPUT)
        logger.info("Tiempo generación portal: %.1fs | Ruta: %s", t_generacion, portal_path)

        # 2. Publicar
        t_pub_start = time.perf_counter()
        url = publish_portal(portal_path)
        t_pub = time.perf_counter() - t_pub_start
        logger.info("Tiempo publicación: %.1fs", t_pub)

        if url:
            estado = "SUCCESS"
            logger.info("Portal publicado: %s", url)
        else:
            logger.warning("Publicación fallida o rechazada")

    except OllamaGenerationError as e:
        logger.error("Generación IA falló. Portal incompleto. No se publica. %s", e)
        estado = "ABORTED"
    except Exception as e:
        logger.exception("Error inesperado: %s", e)
        estado = "FAILED"

    t_total = time.perf_counter() - t_start
    logger.info("Tiempo total: %.1fs | Estado final: %s", t_total, estado)


if __name__ == "__main__":
    main()
