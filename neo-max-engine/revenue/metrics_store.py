"""
metrics_store - Persistencia de herramientas, blog, métricas y decisiones del loop SaaS.
SQLite local para historial, scoring y dashboard.
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("neo_max.metrics_store")

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "neo_saas_loop.db"
SCHEMA = """
CREATE TABLE IF NOT EXISTS tools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    problem TEXT,
    path_rel TEXT,
    portal_repo TEXT,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    quality_score INTEGER,
    engagement_score REAL,
    score_final REAL,
    visits INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    last_metrics_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS blog_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    path_rel TEXT,
    created_at TEXT NOT NULL,
    word_count INTEGER,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS metrics_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url_path TEXT NOT NULL,
    date TEXT NOT NULL,
    visits INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    UNIQUE(url_path, date)
);

CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    score_final REAL,
    reason TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (tool_id) REFERENCES tools(id)
);

CREATE INDEX IF NOT EXISTS idx_tools_slug ON tools(slug);
CREATE INDEX IF NOT EXISTS idx_tools_status ON tools(status);
CREATE INDEX IF NOT EXISTS idx_metrics_path_date ON metrics_daily(url_path, date);
"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    try:
        conn.execute("ALTER TABLE tools ADD COLUMN portal_repo TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        conn.rollback()
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tools_portal_repo ON tools(portal_repo)")
        conn.commit()
    except sqlite3.OperationalError:
        conn.rollback()
    return conn


def upsert_tool(
    slug: str,
    title: str,
    path_rel: str,
    problem: str | None = None,
    quality_score: int | None = None,
    portal_repo: str | None = None,
    db_path: Path | None = None,
) -> int:
    conn = get_connection(db_path)
    try:
        now = _utc_now()
        cur = conn.execute(
            """INSERT INTO tools (slug, title, problem, path_rel, portal_repo, created_at, status, quality_score, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?)
               ON CONFLICT(slug) DO UPDATE SET
                 title=excluded.title, path_rel=excluded.path_rel, portal_repo=excluded.portal_repo,
                 quality_score=excluded.quality_score, updated_at=excluded.updated_at""",
            (slug, title, problem or "", path_rel, portal_repo or "", now, quality_score, now),
        )
        conn.commit()
        return cur.lastrowid or _tool_id_by_slug(conn, slug)
    finally:
        conn.close()


def _tool_id_by_slug(conn: sqlite3.Connection, slug: str) -> int:
    row = conn.execute("SELECT id FROM tools WHERE slug = ?", (slug,)).fetchone()
    return row["id"] if row else 0


def update_tool_metrics(
    slug: str,
    visits: int | None = None,
    clicks: int | None = None,
    quality_score: int | None = None,
    engagement_score: float | None = None,
    score_final: float | None = None,
    status: str | None = None,
    db_path: Path | None = None,
) -> None:
    conn = get_connection(db_path)
    try:
        now = _utc_now()
        updates = ["updated_at = ?"]
        args = [now]
        if visits is not None:
            updates.append("visits = ?")
            args.append(visits)
        if clicks is not None:
            updates.append("clicks = ?")
            args.append(clicks)
        if quality_score is not None:
            updates.append("quality_score = ?")
            args.append(quality_score)
        if engagement_score is not None:
            updates.append("engagement_score = ?")
            args.append(engagement_score)
        if score_final is not None:
            updates.append("score_final = ?")
            args.append(score_final)
        if status is not None:
            updates.append("status = ?")
            args.append(status)
        updates.append("last_metrics_at = ?")
        args.append(now)
        args.append(slug)
        conn.execute(
            f"UPDATE tools SET {', '.join(updates)} WHERE slug = ?",
            args,
        )
        conn.commit()
    finally:
        conn.close()


def record_decision(
    tool_id: int,
    action: str,
    score_final: float | None = None,
    reason: str | None = None,
    db_path: Path | None = None,
) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            "INSERT INTO decisions (tool_id, action, score_final, reason, created_at) VALUES (?, ?, ?, ?, ?)",
            (tool_id, action, score_final, reason or "", _utc_now()),
        )
        conn.commit()
    finally:
        conn.close()


def get_portal_engagement(db_path: Path | None = None) -> list[dict[str, Any]]:
    """Agregado por portal_repo: total visits, clicks, avg score_final. Solo portales con portal_repo no vacío."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """SELECT portal_repo,
                      SUM(visits) AS total_visits,
                      SUM(clicks) AS total_clicks,
                      AVG(score_final) AS avg_score,
                      COUNT(*) AS tool_count
               FROM tools
               WHERE COALESCE(portal_repo, '') != ''
               GROUP BY portal_repo
               ORDER BY total_visits DESC, total_clicks DESC"""
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def list_tools_by_portal(portal_repo: str, db_path: Path | None = None) -> list[dict[str, Any]]:
    """Herramientas de un portal (por portal_repo)."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM tools WHERE portal_repo = ? ORDER BY created_at ASC",
            (portal_repo,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def list_tools(
    status: str | None = None,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        if status:
            rows = conn.execute(
                "SELECT * FROM tools WHERE status = ? ORDER BY created_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM tools ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_blog_post(
    slug: str,
    title: str,
    path_rel: str,
    word_count: int | None = None,
    db_path: Path | None = None,
) -> int:
    conn = get_connection(db_path)
    try:
        now = _utc_now()
        cur = conn.execute(
            """INSERT INTO blog_posts (slug, title, path_rel, created_at, word_count, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (slug, title, path_rel, now, word_count, now),
        )
        conn.commit()
        return cur.lastrowid or 0
    finally:
        conn.close()


def record_metrics_daily(
    url_path: str,
    date: str,
    visits: int = 0,
    clicks: int = 0,
    db_path: Path | None = None,
) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            """INSERT INTO metrics_daily (url_path, date, visits, clicks)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(url_path, date) DO UPDATE SET
                 visits = visits + excluded.visits,
                 clicks = clicks + excluded.clicks""",
            (url_path, date, visits, clicks),
        )
        conn.commit()
    finally:
        conn.close()


def delete_tool(slug: str, db_path: Path | None = None) -> bool:
    """Elimina una herramienta de la DB por slug. Devuelve True si se eliminó."""
    conn = get_connection(db_path)
    try:
        cur = conn.execute("DELETE FROM tools WHERE slug = ?", (slug,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def clear_all_tools(db_path: Path | None = None) -> None:
    """Borra todas las herramientas y decisiones (y opcionalmente blog_posts). Para empezar de cero."""
    conn = get_connection(db_path)
    try:
        conn.execute("DELETE FROM decisions")
        conn.execute("DELETE FROM tools")
        conn.commit()
        logger.info("Cleared all tools and decisions from DB")
    finally:
        conn.close()


def export_for_dashboard(db_path: Path | None = None) -> dict[str, Any]:
    """Exporta herramientas, posts y últimas decisiones para el dashboard (JSON)."""
    conn = get_connection(db_path)
    try:
        tools = [dict(r) for r in conn.execute("SELECT * FROM tools ORDER BY created_at DESC").fetchall()]
        posts = [dict(r) for r in conn.execute("SELECT * FROM blog_posts ORDER BY created_at DESC").fetchall()]
        decisions = [
            dict(r)
            for r in conn.execute(
                "SELECT d.*, t.slug as tool_slug FROM decisions d JOIN tools t ON d.tool_id = t.id ORDER BY d.created_at DESC LIMIT 100"
            ).fetchall()
        ]
        total_visits = sum(int(t.get("visits") or 0) for t in tools)
        total_clicks = sum(int(t.get("clicks") or 0) for t in tools)
        rpm_placeholder = 2.0
        estimated_revenue = round(total_visits * (rpm_placeholder / 1000), 2)
        active = sum(1 for t in tools if t.get("status") == "active")
        return {
            "generated_at": _utc_now(),
            "summary": {
                "total_tools": len(tools),
                "active_tools": active,
                "total_visits": total_visits,
                "total_clicks": total_clicks,
                "estimated_revenue_usd": estimated_revenue,
                "rpm_note": "Estimate at $2 RPM; replace with real when AdSense connected",
            },
            "tools": tools,
            "blog_posts": posts,
            "decisions": decisions,
        }
    finally:
        conn.close()


def export_dashboard_json(output_path: Path | str, db_path: Path | None = None) -> Path:
    """Escribe el JSON del dashboard en output_path."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    data = export_for_dashboard(db_path)
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return out
