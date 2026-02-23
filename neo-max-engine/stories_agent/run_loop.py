"""
Loop autónomo del agente de historias: cada día a las 9:00 genera 1 capítulo + 1 imagen y publica en GitHub Pages.
Requisitos: Ollama corriendo, GEMINI_API_KEY o OPENAI_API_KEY en .env para imágenes, GITHUB_TOKEN en .env.
"""
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Anadir padre (tools) y esta carpeta (build_site, generate_*) al path
_root = Path(__file__).resolve().parent.parent
_agent_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(_root))
sys.path.insert(0, str(_agent_dir))
# Cargar .env del engine (igual que NEO MAX), pero NO GITHUB_TOKEN: lo carga solo el publisher al publicar
_env = _root / ".env"
if _env.is_file():
    for line in _env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip("'\"")
            if k and k not in os.environ and k != "GITHUB_TOKEN":
                os.environ[k] = v

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("stories_agent")

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"
OUTPUT_DIR = Path(__file__).resolve().parent / "output" / "site"


def _load_config() -> dict:
    if not CONFIG_PATH.is_file():
        return {}
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _save_next_chapter_backup(data: dict) -> None:
    """Guarda backup del capítulo por delante (por si se pierde el estado)."""
    backup_path = Path(__file__).resolve().parent / "output" / "next_chapter_backup.json"
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    safe = {k: v for k, v in data.items() if k != "body"}
    safe["_backup_note"] = "Capítulo por delante. El body está en serial_state.json next_chapter.body"
    try:
        backup_path.write_text(json.dumps(safe, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        logger.debug("Backup next_chapter failed: %s", e)


def run_one_cycle() -> bool:
    """
    Un capítulo por delante: si hay next_chapter guardado, ese se publica a las 9:00.
    Luego se genera uno nuevo y se guarda como próximo (y backup). Así siempre tienes uno
    listo para vender y como respaldo.
    """
    from build_site import _slug, add_story_to_site
    from generate_image import generate_and_save_image
    from generate_story import generate_one_story, generate_next_chapter
    from serial_state import load_state, publish_next_chapter, set_next_chapter
    from tools.github_publisher import publish_portal

    config = _load_config()
    base_url = config.get("base_url", "").rstrip("/")
    repo_name = config.get("repo_name", "daily-heartwarming-stories")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    state = load_state()
    story = None
    if state.get("next_chapter"):
        story = publish_next_chapter(state)
        if story:
            logger.info("Publishing saved chapter (one ahead): %s", story.get("title"))
    if not story:
        story = generate_one_story()
        if not story:
            logger.warning("No story generated; skipping cycle")
            return False
        logger.info("Story generated: %s", story["title"])

    slug = story.get("slug") or _slug(story["title"])
    image_rel = story.get("image_rel")
    if not image_rel:
        image_rel = generate_and_save_image(
            story["prompt_for_image"],
            slug,
            OUTPUT_DIR,
            size=config.get("image_size", "1024x1024"),
            model=config.get("image_model", "dall-e-3"),
            image_provider=config.get("image_provider", "openai"),
        )
        if not image_rel:
            logger.info("No image (set GEMINI_API_KEY or OPENAI_API_KEY in .env); publishing without image")

    add_story_to_site(
        OUTPUT_DIR,
        title=story["title"],
        body_html=story["body"],
        image_rel=image_rel,
        base_url=base_url,
        serial_title=story.get("serial_title"),
        theme=story.get("theme"),
        chapter_num=story.get("chapter_num"),
    )
    logger.info("Site updated with new story")

    orig_cwd = os.getcwd()
    try:
        os.chdir(_root)
        url = publish_portal(str(OUTPUT_DIR), repo_name_override=repo_name)
    finally:
        os.chdir(orig_cwd)
    if not url:
        logger.warning("Publish failed")
        return False
    logger.info("Published: %s", url)

    # Generar y guardar el siguiente (el que se publicará mañana y que se puede vender)
    state = load_state()
    next_story = generate_next_chapter(append_to_state=False)
    if next_story:
        next_slug = _slug(next_story["title"])
        next_image_rel = generate_and_save_image(
            next_story["prompt_for_image"],
            next_slug,
            OUTPUT_DIR,
            size=config.get("image_size", "1024x1024"),
            model=config.get("image_model", "dall-e-3"),
            image_provider=config.get("image_provider", "openai"),
        )
        next_data = {
            "title": next_story["title"],
            "body": next_story["body"],
            "summary": next_story.get("summary", ""),
            "prompt_for_image": next_story["prompt_for_image"],
            "slug": next_slug,
            "image_rel": next_image_rel,
            "serial_title": next_story.get("serial_title"),
            "theme": next_story.get("theme"),
            "chapter_num": len(state.get("chapters", [])) + 1,
        }
        set_next_chapter(state, next_data)
        _save_next_chapter_backup(next_data)
        logger.info("Next chapter saved (will publish at next 9:00): %s", next_story["title"])
    else:
        logger.warning("Could not generate next chapter for backup")

    return True


def main() -> None:
    config = _load_config()
    interval_hours = float(config.get("interval_hours", 24))
    interval_sec = max(60, int(interval_hours * 3600))
    if not os.environ.get("GITHUB_TOKEN"):
        logger.warning("GITHUB_TOKEN not set; publish will fail")
    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("OPENAI_API_KEY"):
        logger.warning("No GEMINI_API_KEY nor OPENAI_API_KEY; stories will have no image")

    run_once = len(sys.argv) > 1 and sys.argv[1].lower() in ("once", "1", "--once")
    fresh = len(sys.argv) > 2 and sys.argv[2].lower() in ("fresh", "--fresh") or (
        len(sys.argv) == 2 and sys.argv[1].lower() in ("fresh", "--fresh")
    )
    if fresh:
        logger.info("Modo FRESH: borrar estado local, sitio local y contenido del repo en GitHub; luego un ciclo.")
        config = _load_config()
        repo_name = config.get("repo_name", "daily-heartwarming-stories")
        state_path = Path(__file__).resolve().parent / "output" / "serial_state.json"
        if state_path.is_file():
            state_path.unlink()
            logger.info("Borrado serial_state.json")
        if OUTPUT_DIR.is_dir():
            import shutil
            for f in OUTPUT_DIR.rglob("*"):
                if f.is_file():
                    f.unlink()
            for d in sorted(OUTPUT_DIR.rglob("*"), key=lambda x: -len(str(x))):
                if d.is_dir() and d != OUTPUT_DIR:
                    try:
                        d.rmdir()
                    except OSError:
                        pass
            logger.info("Vaciada carpeta output/site")
        try:
            from tools.github_publisher import clear_repo_contents
            clear_repo_contents(repo_name)
        except Exception as e:
            logger.warning("No se pudo vaciar el repo en GitHub: %s. Publicación sobrescribirá archivos.", e)
        run_one_cycle()
        return
    if run_once:
        logger.info("Modo prueba: un solo ciclo y salir.")
        run_one_cycle()
        return

    publish_hour = int(config.get("publish_hour", 9))
    publish_minute = int(config.get("publish_minute", 0))
    logger.info(
        "Stories agent started. Un capítulo cada día a las %02d:%02d (hora local). Ctrl+C to stop.",
        publish_hour,
        publish_minute,
    )

    def seconds_until_next_run() -> float:
        now = datetime.now()
        next_run = now.replace(hour=publish_hour, minute=publish_minute, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        return (next_run - now).total_seconds()

    while True:
        try:
            wait_sec = seconds_until_next_run()
            if wait_sec > 60:
                logger.info("Próxima publicación en %.0f min (a las %02d:%02d)", wait_sec / 60, publish_hour, publish_minute)
            time.sleep(wait_sec)
            run_one_cycle()
        except KeyboardInterrupt:
            logger.info("Stopped by user")
            sys.exit(0)
        except Exception as e:
            logger.exception("Cycle error: %s. Retry in 10 min.", e)
            time.sleep(600)


if __name__ == "__main__":
    main()
