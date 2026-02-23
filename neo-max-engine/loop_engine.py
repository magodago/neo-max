"""
loop_engine - Motor de ciclo productivo NEO MAX.
Pipeline: problema -> validación mercado -> generación IA -> evaluación -> publicación.
"""

import logging
import time

from revenue.niche_finder import generate_commercial_micro_problem
from revenue.microtool_generator import generate_tool_structure, OllamaGenerationError
from revenue.tool_evaluator import evaluate_tool
from tools.github_publisher import publish_tool
from tools.market_validator import MarketValidator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("neo_max")

OUTPUT_DIR = "output/tools"
CYCLE_DELAY_SECONDS = 30
PUBLISH_SCORE_THRESHOLD = 60
MIN_NIVEL_MONETIZACION = 3
MARKET_SCORE_THRESHOLD = 65


def run_cycle(cycle_number: int) -> None:
    """Un ciclo completo. Estado final: SUCCESS | SKIPPED | FAILED."""
    t_cycle = time.perf_counter()
    try:
        _run_cycle_impl(cycle_number, t_cycle)
    except Exception as e:
        logger.exception("Ciclo %d falló: %s", cycle_number, e)
        logger.info("Tiempo ciclo: %.1fs | Estado: FAILED", time.perf_counter() - t_cycle)


def _run_cycle_impl(cycle_number: int, t_cycle: float) -> None:
    estado = "SKIPPED"
    logger.info("=== Ciclo %d ===", cycle_number)

    # 1. Problema comercial
    item = generate_commercial_micro_problem()
    problem = item["problema"]
    categoria = item["categoria"]
    nivel = item["nivel_monetizacion"]
    complejidad = item["complejidad"]
    logger.info("Problema: %s | Categoría: %s | Monetización: %d/5 | Complejidad: %d/5",
                problem, categoria, nivel, complejidad)

    if nivel < MIN_NIVEL_MONETIZACION:
        logger.info("Omitido: nivel monetización %d < %d", nivel, MIN_NIVEL_MONETIZACION)
        logger.info("Tiempo ciclo: %.1fs | Estado: SKIPPED", time.perf_counter() - t_cycle)
        return

    # 2. Validación mercado
    t_mercado_start = time.perf_counter()
    validator = MarketValidator()
    problem_data = {"titulo": problem, "categoria": categoria, "nivel_monetizacion": nivel}
    validation = validator.validate_with_serpapi(problem_data)
    t_mercado = time.perf_counter() - t_mercado_start
    logger.info("Validación mercado: %.1fs | total_resultados=%s | ads=%s | organic=%s | market_score=%d",
                t_mercado, validation["total_results"], validation["has_ads"], validation["organic_count"], validation["market_score"])
    if validation["error"]:
        logger.warning("SerpAPI: %s", validation["error"])
    if not validation["should_build"]:
        logger.info("Decisión: descartar (market_score %d < %d)", validation["market_score"], MARKET_SCORE_THRESHOLD)
        logger.info("Tiempo ciclo: %.1fs | Estado: SKIPPED", time.perf_counter() - t_cycle)
        return
    logger.info("Decisión: construir (market_score %d >= %d)", validation["market_score"], MARKET_SCORE_THRESHOLD)

    # 3. Generación IA (sin fallback: excepción si falla)
    tool_path = None
    ai_generation_success = False
    t_generacion = 0.0
    try:
        t_gen_start = time.perf_counter()
        tool_path, ai_generation_success = generate_tool_structure(problem, output_dir=OUTPUT_DIR)
        t_generacion = time.perf_counter() - t_gen_start
        logger.info("Tiempo generación IA: %.1fs | Herramienta: %s", t_generacion, tool_path)
    except OllamaGenerationError as e:
        logger.warning("IA falló. Publicación cancelada. %s", e)
        logger.info("Tiempo ciclo: %.1fs | Estado: SKIPPED", time.perf_counter() - t_cycle)
        return

    if not tool_path or not ai_generation_success:
        logger.info("Tiempo ciclo: %.1fs | Estado: SKIPPED", time.perf_counter() - t_cycle)
        return

    # 4. Evaluar (solo si IA generó código real)
    score = evaluate_tool(tool_path, problem)
    logger.info("Score: %d/100", score)

    # 5. Publicar (solo si score > umbral; github_publisher valida index.html)
    t_pub = 0.0
    if score > PUBLISH_SCORE_THRESHOLD:
        t_pub_start = time.perf_counter()
        url = publish_tool(tool_path)
        t_pub = time.perf_counter() - t_pub_start
        logger.info("Tiempo publicación: %.1fs", t_pub)
        if url:
            logger.info("Publicado: %s", url)
        else:
            logger.warning("Publicación fallida o rechazada (validación index.html / token)")
    else:
        logger.info("No se publica (score <= %d)", PUBLISH_SCORE_THRESHOLD)

    estado = "SUCCESS"
    logger.info("Resultado ciclo %d [%s]: %s -> %s -> %d/100",
                cycle_number, categoria, problem, tool_path, score)
    logger.info("Tiempos: validación_mercado=%.1fs | generación_IA=%.1fs | publicación=%.1fs",
                t_mercado, t_generacion, t_pub)
    logger.info("Tiempo ciclo total: %.1fs | Estado: %s", time.perf_counter() - t_cycle, estado)


def main():
    """Loop principal."""
    logger.info("NEO MAX Engine iniciado")
    logger.info("Output: %s | Intervalo: %ds | Umbral mercado: %d | Umbral publicación: %d",
                OUTPUT_DIR, CYCLE_DELAY_SECONDS, MARKET_SCORE_THRESHOLD, PUBLISH_SCORE_THRESHOLD)
    cycle = 1
    try:
        while True:
            run_cycle(cycle)
            cycle += 1
            if cycle > 1:
                logger.info("Esperando %d segundos...", CYCLE_DELAY_SECONDS)
            time.sleep(CYCLE_DELAY_SECONDS)
    except KeyboardInterrupt:
        logger.info("Engine detenido por usuario")


if __name__ == "__main__":
    main()
