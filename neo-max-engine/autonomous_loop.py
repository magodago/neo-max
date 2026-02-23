"""
autonomous_loop - Loop 100% autónomo: un SaaS = un tema + 5 herramientas coherentes.
Nunca machaca lo anterior: siempre AÑADE. Genera blog con enlaces. Publica. Ping sitemap. Objetivo: generar ingresos.
"""

import json
import logging
import random
import sys
import time
from pathlib import Path

from revenue.idea_discovery import discover_best_idea, discover_theme_and_5_tools
from revenue.portal_builder_v2 import (
    add_blog_posts_for_theme,
    add_single_tool_to_portal,
    build_portal_for_theme,
    _theme_to_repo_slug,
)
from revenue.niche_finder import PROBLEMAS_COMERCIALES
from tools.github_publisher import publish_portal
from tools.sitemap_ping import ping_sitemap

# Si ni el tema ni las ideas pasan validación SerpAPI, añadimos al menos una tool de esta lista (sin validar).
FALLBACK_TOOL_TITLES = [
    "CAC calculator for startups",
    "LTV calculator",
    "MRR to ARR converter",
    "Churn rate calculator",
    "Runway calculator for startups",
    "Freelancer hourly rate calculator",
    "ROI calculator for marketing campaigns",
    "Conversion rate calculator",
    "Customer acquisition cost calculator",
    "Monthly recurring revenue calculator",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("neo_max.autonomous")

PORTAL_OUTPUT = "output/saas-metrics-portal"
TOOLS_PER_SAAS = 5
CONFIG_PATH = Path(__file__).resolve().parent / "config" / "saas_loop_config.json"


def _load_config() -> dict:
    if not CONFIG_PATH.is_file():
        return {}
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _blog_posts_per_saas() -> int:
    c = _load_config()
    return int(c.get("blog", {}).get("posts_per_saas", 5))


def run_autonomous_cycle(
    portal_root: str = PORTAL_OUTPUT,
    use_theme_mode: bool = True,
    min_market_score: int = 65,
    publish: bool = True,
) -> dict:
    """
    Un ciclo: descubre un TEMA + 5 herramientas coherentes, las AÑADE al portal (no machaca),
    genera 2 posts de blog con enlaces a esas herramientas, publica.
    Si no hay tema válido, fallback: una sola herramienta (discover_best_idea).
    """
    result = {"theme": None, "slugs": [], "blog_slugs": [], "published": False, "error": None}
    portal_path = Path(portal_root)
    if not (portal_path / "index.html").is_file():
        from revenue.portal_builder_v2 import build_portal_v2
        logger.info("Portal missing; creating initial portal (5 base tools)")
        build_portal_v2(output_dir=str(portal_path), generate_blog_count=0, register_in_db=True)
        if publish:
            config = _load_config()
            repo = config.get("portal_repo_name")
            url = publish_portal(str(portal_path), repo_name_override=repo)
            result["published"] = bool(url)
            if url and config.get("base_url"):
                ping_sitemap(config["base_url"].rstrip("/") + "/sitemap.xml")
        result["slugs"] = []
        _append_cycle_summary(result)
        return result

    if use_theme_mode:
        theme_data = discover_theme_and_5_tools(min_market_score=min_market_score, use_ollama=True)
        if theme_data:
            theme = theme_data["theme"]
            tools = theme_data["tools"]
            result["theme"] = theme
            config = _load_config()
            if config.get("portal_per_theme"):
                repo_name = _theme_to_repo_slug(theme)
                base = config.get("base_url", "").rstrip("/")
                gh_user = config.get("github_user") or "magodago"
                if not gh_user and base and "github.io" in base:
                    for p in base.split("/"):
                        if "github.io" in p:
                            gh_user = p.split(".")[0]
                            break
                gh_user = gh_user or "magodago"
                base_url_new = f"https://{gh_user}.github.io/{repo_name}"
                output_dir = portal_path.parent / "portals" / repo_name
                logger.info("Portal per theme: building new site %s at %s", repo_name, output_dir)
                try:
                    _, slugs, blog_slugs = build_portal_for_theme(
                        theme,
                        tools,
                        output_dir,
                        base_url_new,
                        repo_name=repo_name,
                        register_in_db=True,
                        blog_posts_count=_blog_posts_per_saas(),
                    )
                    result["slugs"] = slugs
                    result["blog_slugs"] = blog_slugs
                    if publish and slugs:
                        url = publish_portal(str(output_dir), repo_name_override=repo_name)
                        result["published"] = bool(url)
                        if url:
                            logger.info("Portal published (per theme): %s", url)
                            ping_sitemap(base_url_new.rstrip("/") + "/sitemap.xml")
                except Exception as e:
                    logger.exception("Build portal for theme failed: %s", e)
                    result["error"] = str(e)
                _append_cycle_summary(result)
                return result
            logger.info("New SaaS theme: %s with %d tools", theme, len(tools))
            main_repo = config.get("portal_repo_name")
            slugs = []
            for title in tools:
                slug = add_single_tool_to_portal(
                    portal_path,
                    problem=title,
                    title=title,
                    slug=None,
                    register_in_db=True,
                    portal_repo=main_repo,
                )
                if slug:
                    slugs.append(slug)
                else:
                    logger.warning("Tool failed: %s", title)
            result["slugs"] = slugs
            if len(slugs) >= 2:
                n_posts = _blog_posts_per_saas()
                blog_created = add_blog_posts_for_theme(
                    portal_path, theme, slugs, count=n_posts, register_in_db=True
                )
                result["blog_slugs"] = blog_created
                logger.info("Blog posts for theme: %s", blog_created)
            if publish and slugs:
                config = _load_config()
                repo = config.get("portal_repo_name")
                url = publish_portal(str(portal_path), repo_name_override=repo)
                result["published"] = bool(url)
                if url:
                    logger.info("Portal published: %s", url)
                    base = config.get("base_url", "").rstrip("/")
                    if base:
                        ping_sitemap(base + "/sitemap.xml")
            _append_cycle_summary(result)
            return result

    # Fallback: una sola herramienta validada por SerpAPI
    config = _load_config()
    main_repo = config.get("portal_repo_name")
    idea = discover_best_idea(
        min_market_score=min_market_score,
        use_ollama=True,
        fallback_list=PROBLEMAS_COMERCIALES,
    )
    if idea:
        result["theme"] = idea["problema"]
        slug = add_single_tool_to_portal(
            portal_path,
            problem=idea["problema"],
            title=idea["problema"],
            slug=None,
            register_in_db=True,
            portal_repo=main_repo,
        )
    else:
        # Ninguna idea pasó SerpAPI: probamos hasta 3 títulos de la lista de respaldo que NO existan ya en el portal (mismo concepto = mismo slug o alias)
        from revenue.portal_builder_v2 import _slug_from_title, _existing_slugs_for_canonical
        tools_dir = Path(portal_path) / "tools"
        existing_slugs = {d.name for d in tools_dir.iterdir() if d.is_dir()} if tools_dir.is_dir() else set()

        def _fallback_already_exists(title: str) -> bool:
            canon = _slug_from_title(title)
            return any(a in existing_slugs for a in _existing_slugs_for_canonical(canon))

        tried = []
        slug = None
        for _ in range(3):
            candidates = [t for t in FALLBACK_TOOL_TITLES if t not in tried and not _fallback_already_exists(t)]
            if not candidates:
                break
            fallback_title = random.choice(candidates)
            tried.append(fallback_title)
            logger.info("No idea passed market validation; trying fallback tool: %s", fallback_title)
            result["theme"] = fallback_title
            slug = add_single_tool_to_portal(
                portal_path,
                problem=fallback_title,
                title=fallback_title,
                slug=None,
                register_in_db=True,
                portal_repo=main_repo,
            )
            if slug:
                break
            logger.warning("Fallback tool failed for: %s; trying another.", fallback_title)
    if not slug and idea:
        # La idea pasó SerpAPI pero la generación o el logic check falló; probar un título de respaldo que NO exista ya (por slug o alias)
        from revenue.portal_builder_v2 import _slug_from_title, _existing_slugs_for_canonical
        tools_dir = Path(portal_path) / "tools"
        existing_slugs = {d.name for d in tools_dir.iterdir() if d.is_dir()} if tools_dir.is_dir() else set()

        def _already_exists(title: str) -> bool:
            canon = _slug_from_title(title)
            return any(a in existing_slugs for a in _existing_slugs_for_canonical(canon))

        fallback_candidates = [t for t in FALLBACK_TOOL_TITLES if not _already_exists(t)]
        if not fallback_candidates:
            logger.info("All fallback tools already exist in portal; nothing new to add.")
        for fallback_title in random.sample(fallback_candidates, min(3, len(fallback_candidates))):
            logger.info("Trying fallback after idea tool failed: %s", fallback_title)
            result["theme"] = fallback_title
            slug = add_single_tool_to_portal(
                portal_path,
                problem=fallback_title,
                title=fallback_title,
                slug=None,
                register_in_db=True,
                portal_repo=main_repo,
            )
            if slug:
                break
    if not slug:
        result["error"] = "No idea passed market validation and fallback tool failed" if not idea else "Tool generation failed"
        logger.warning(result["error"])
        _append_cycle_summary(result)
        return result
    result["slugs"] = [slug]
    if publish and result["slugs"]:
        config = _load_config()
        url = publish_portal(str(portal_path), repo_name_override=config.get("portal_repo_name"))
        result["published"] = bool(url)
        if url and config.get("base_url"):
            ping_sitemap(config["base_url"].rstrip("/") + "/sitemap.xml")
    _append_cycle_summary(result)
    return result


def run_scale_step(
    portals_dir: Path | None = None,
    min_visits_to_scale: int = 5,
    extra_blog_posts: int = 2,
    db_path: Path | None = None,
) -> bool:
    """
    Si algún portal (por tema) tiene buenos datos (visits >= min_visits_to_scale),
    añade más contenido (blog posts) y republica. Retorna True si se escaló alguno.
    """
    from revenue.metrics_store import (
        DEFAULT_DB_PATH,
        get_portal_engagement,
        list_tools_by_portal,
    )
    from revenue.portal_builder_v2 import add_blog_posts_for_theme

    config = _load_config()
    main_repo = config.get("portal_repo_name") or "saas-metrics-tools"
    portals_dir = portals_dir or Path(PORTAL_OUTPUT).parent / "portals"
    db_path = db_path or DEFAULT_DB_PATH
    engagement = get_portal_engagement(db_path=db_path)
    for row in engagement:
        repo = (row.get("portal_repo") or "").strip()
        if not repo or repo == main_repo:
            continue
        total_visits = int(row.get("total_visits") or 0)
        if total_visits < min_visits_to_scale:
            continue
        portal_path = portals_dir / repo
        if not portal_path.is_dir():
            continue
        theme_file = portal_path / "_theme.txt"
        if not theme_file.is_file():
            continue
        theme = theme_file.read_text(encoding="utf-8").strip()
        tools = list_tools_by_portal(repo, db_path=db_path)
        slugs = [t["slug"] for t in tools if t.get("slug")]
        if len(slugs) < 2:
            continue
        gh_user = config.get("github_user") or "magodago"
        base_url = f"https://{gh_user}.github.io/{repo}"
        logger.info("Scaling portal %s (visits=%d): adding %d blog posts", repo, total_visits, extra_blog_posts)
        try:
            add_blog_posts_for_theme(
                portal_path, theme, slugs, base_url=base_url, count=extra_blog_posts, register_in_db=True
            )
            url = publish_portal(str(portal_path), repo_name_override=repo)
            if url:
                logger.info("Scaled portal republished: %s", url)
                ping_sitemap(base_url.rstrip("/") + "/sitemap.xml")
            return True
        except Exception as e:
            logger.warning("Scale step failed for %s: %s", repo, e)
    return False


def _append_cycle_summary(result: dict) -> None:
    """Escribe una línea de resumen en output/cycle_summary.log para revisar qué hizo cada ciclo."""
    from datetime import datetime, timezone
    out_dir = Path(PORTAL_OUTPUT).parent  # output/
    log_file = out_dir / "cycle_summary.log"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    mode = "theme" if len(result.get("slugs") or []) > 1 else "single"
    theme = result.get("theme") or "-"
    slugs = ", ".join(result.get("slugs") or [])
    blog = ", ".join(result.get("blog_slugs") or []) or "-"
    pub = "yes" if result.get("published") else "no"
    err = result.get("error") or "-"
    line = f"{ts} | mode={mode} | theme={theme!r} | tools=[{slugs}] | blog=[{blog}] | published={pub} | error={err}\n"
    try:
        if not log_file.is_file():
            log_file.write_text(
                "# NEO MAX cycle summary. One line per cycle: mode (theme=5 tools, single=1 tool), theme/title, tools added, blog slugs, published, error.\n",
                encoding="utf-8",
            )
        with log_file.open("a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        logger.debug("Could not write cycle summary: %s", e)


def reset_all_tools(
    portal_root: str | None = None,
    clear_portals_dir: bool = True,
) -> None:
    """
    Borra todas las tools para empezar de cero: carpetas en portal/tools/, base de datos,
    rehace index (grid vacío), sitemap y dashboard. Si clear_portals_dir, borra también output/portals/*.
    """
    import shutil
    from pathlib import Path
    from revenue.metrics_store import clear_all_tools, DEFAULT_DB_PATH
    from revenue.portal_builder_v2 import _rebuild_tools_grid_in_index
    from revenue.seo_utils import collect_urls_for_sitemap, sitemap_xml, robots_txt

    config = _load_config()
    base_url = (config.get("base_url") or "https://magodago.github.io/saas-metrics-tools").rstrip("/")
    root = Path(portal_root or PORTAL_OUTPUT).resolve()
    if not root.is_dir():
        logger.warning("Portal dir does not exist: %s. Creating.", root)
        root.mkdir(parents=True, exist_ok=True)

    tools_dir = root / "tools"
    if tools_dir.is_dir():
        removed = 0
        for d in list(tools_dir.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                shutil.rmtree(d, ignore_errors=True)
                removed += 1
        logger.info("Removed %d tool folders from %s", removed, tools_dir)

    clear_all_tools(db_path=DEFAULT_DB_PATH)
    (root / "index.html").touch()
    _rebuild_tools_grid_in_index(root)
    urls = collect_urls_for_sitemap(root, base_url)
    root.joinpath("sitemap.xml").write_text(sitemap_xml(urls, base_url), encoding="utf-8")
    root.joinpath("robots.txt").write_text(robots_txt(base_url), encoding="utf-8")
    logger.info("Portal index and sitemap updated (0 tools)")

    out_parent = root.parent
    if clear_portals_dir:
        portals_dir = out_parent / "portals"
        if portals_dir.is_dir():
            for d in list(portals_dir.iterdir()):
                if d.is_dir() and not d.name.startswith("."):
                    shutil.rmtree(d, ignore_errors=True)
            logger.info("Cleared output/portals/ (per-theme sites)")

    from loop_saas import run_review_and_export
    run_review_and_export(portal_root=str(root))
    logger.info("Reset complete. Dashboard updated. Run the loop to create tools from zero.")


def _interval_seconds() -> int:
    """Segundos entre ciclos (config cycle_hours, default 1)."""
    c = _load_config()
    hours = c.get("cycle_hours")
    if hours is not None:
        try:
            return max(60, int(float(hours) * 3600))
        except (TypeError, ValueError):
            pass
    return 3600  # 1 hora por defecto


def main() -> None:
    """
    Loop continuo: ejecuta un ciclo cada N horas (config cycle_hours) y no termina.
    Argumentos:
      reset  — Borrar todas las tools y empezar de cero (luego sale).
      once   — Un solo ciclo y salir (comportamiento anterior).
    """
    if len(sys.argv) > 1:
        arg = sys.argv[1].strip().lower()
        if arg == "reset":
            reset_all_tools(clear_portals_dir=True)
            return
        if arg == "once":
            logger.info("Autonomous cycle started (single run)")
            t0 = time.perf_counter()
            r = run_autonomous_cycle(use_theme_mode=True, publish=True)
            elapsed = time.perf_counter() - t0
            logger.info("Cycle finished in %.1fs | theme=%s slugs=%s published=%s", elapsed, r.get("theme"), r.get("slugs"), r.get("published"))
            if r.get("error"):
                logger.warning("Error: %s", r["error"])
            return

    interval = _interval_seconds()
    logger.info("Autonomous loop started — cycle every %s (Ctrl+C to stop)", _format_interval(interval))
    cycle_num = 0
    while True:
        cycle_num += 1
        logger.info("--- Cycle #%d ---", cycle_num)
        try:
            t0 = time.perf_counter()
            r = run_autonomous_cycle(use_theme_mode=True, publish=True)
            elapsed = time.perf_counter() - t0
            logger.info("Cycle #%d finished in %.1fs | theme=%s slugs=%s published=%s", cycle_num, elapsed, r.get("theme"), r.get("slugs"), r.get("published"))
            if r.get("error"):
                logger.warning("Error: %s", r["error"])
        except KeyboardInterrupt:
            raise
        except Exception as e:
            logger.exception("Cycle #%d failed: %s", cycle_num, e)
        logger.info("Next cycle in %s", _format_interval(interval))
        time.sleep(interval)


def _format_interval(seconds: int) -> str:
    if seconds >= 3600:
        h = seconds // 3600
        return f"{h}h" if h == 1 else f"{h}h"
    m = seconds // 60
    return f"{m}m"


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Stopped by user (Ctrl+C)")
        sys.exit(0)
