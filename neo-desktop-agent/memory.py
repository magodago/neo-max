"""
NEO: Memoria persistente tipo OpenClaw.
Workspace con USER.md, IDENTITY.md, SOUL.md, CONSCIENCE.md, AGENTS.md, TOOLS.md, LEARNED.md inyectados cada sesión.
Sesiones estables en JSONL por session_id (ej. chat_id de Telegram).
Estado NEO: neo_state.json (última interacción, última vez que escribió el usuario, objetivos proactivos).
"""
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("neo_desktop.memory")

BOOTSTRAP_FILES = ("USER.md", "IDENTITY.md", "SOUL.md", "CONSCIENCE.md", "AGENTS.md", "TOOLS.md", "LEARNED.md")
MAX_FILE_CHARS = 4000
LEARNED_MAX_LINES = 200
SESSION_TAIL_LINES = 50
NEO_STATE_FILENAME = "neo_state.json"
LEARNED_RECENT_LINES = 20


def get_workspace_dir(config: dict) -> Path:
    """Ruta del workspace (config o por defecto junto al agente)."""
    base = Path(__file__).resolve().parent
    ws = config.get("workspace_dir") or ""
    if ws:
        return Path(ws).expanduser().resolve()
    return base / "workspace"


def ensure_workspace(workspace_dir: Path) -> None:
    """Crea workspace y archivos bootstrap si no existen. Actualiza TOOLS.md si tiene plantilla antigua."""
    workspace_dir.mkdir(parents=True, exist_ok=True)
    (workspace_dir / "sessions").mkdir(exist_ok=True)
    (workspace_dir / "skills").mkdir(exist_ok=True)
    for name in BOOTSTRAP_FILES:
        p = workspace_dir / name
        if not p.is_file():
            p.write_text(_template(name), encoding="utf-8")
            logger.info("Creado %s", p)
        elif name == "TOOLS.md" and _is_old_tools_template(p):
            p.write_text(_template(name), encoding="utf-8")
            logger.info("Actualizado %s (plantilla antigua sustituida)", p)


def _is_old_tools_template(path: Path) -> bool:
    """True si TOOLS.md tiene la plantilla antigua (muy corta o convenciones viejas)."""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return False
    if len(text.strip()) < 500:
        return True
    if "Convenciones: BROWSER" in text or "Convenciones:\nBROWSER" in text:
        return True
    if "Si no hay skill" not in text and "SEARCH para saber cómo" not in text:
        return True
    return False


def _template(name: str) -> str:
    if name == "USER.md":
        return "# Usuario\n\nNombre: \nPreferencias: \nIdioma: español\n"
    if name == "IDENTITY.md":
        return "# Identidad\n\nTu nombre es NEO. Eres un agente de escritorio con control total del PC: navegador, documentos, terminal, GitHub. Si te preguntan cómo te llamas, di que eres NEO.\n"
    if name == "SOUL.md":
        return "# Tono y límites\n\nActúa de forma útil y autónoma. No ejecutes comandos destructivos sin confirmación.\n"
    if name == "AGENTS.md":
        return "# Memoria operativa\n\nAquí puedes anotar instrucciones recurrentes o recordatorios para el agente.\n"
    if name == "TOOLS.md":
        return """# Herramientas disponibles (usa una por paso)

Si no hay skill que encaje con la tarea, usa estas acciones. NUNCA respondas DONE diciendo que no puedes sin haber intentado al menos SEARCH + SCRIPT/COMMAND/BROWSER.

- SEARCH: <consulta> — Buscar en internet (sin abrir navegador). Usar SIEMPRE para \"cómo hacer X\", errores, alternativas.
- BROWSER:go <url> — Abrir URL. BROWSER:content — texto de la página. BROWSER:click/fill/screenshot/close.
- COMMAND: <PowerShell> — Una línea (New-Item, Get-Content, Start-Process, etc.).
- SCRIPT:python — Líneas siguientes: código Python completo (archivos, web, datos, lo que sea).
- SCRIPT:powershell — Código PowerShell multilínea.
- INSTALL: <nombre> — Instalar paquete (pip/winget). Solo el nombre, sin URLs ni API keys.
- DESKTOP:click <x> <y> — Click en pantalla. DESKTOP:type \"texto\". DESKTOP:key enter.
- SCREENSHOT — Captura de pantalla (y visión si hay vision_model).
- GITHUB: push <ruta_carpeta> <nombre_repo> — Subir a GitHub, activar Pages. DONE con URL.
- SKILL: <nombre> [args] — Ejecutar skill instalado (lista en contexto).
- CREATE_SKILL: <nombre> — Crear skill: siguiente línea nombre, luego código Python con def run(task=\"\", **kwargs) -> str. Se guarda en workspace/skills/.
- DONE: <resumen> — Tarea completada; el texto es lo que recibe el usuario.

Regla: Si no hay skill → SEARCH para saber cómo, luego SCRIPT o COMMAND o BROWSER. Si falla → SEARCH otra solución, no repitas lo mismo. Cuando funcione y sea repetible → CREATE_SKILL para la próxima.
Busca y resumen (varios temas): Si piden «busca X y Y y mándame resumen» → un SEARCH por cada tema (uno por paso), luego DONE con resumen que incluya ambos. No abras navegador para datos; SEARCH los da.
"""
    if name == "LEARNED.md":
        return "# Autoaprendizaje\n\nHechos que NEO ha aprendido sobre el usuario (gustos, preferencias, reacciones) para ser más útil y proactivo.\n"
    if name == "CONSCIENCE.md":
        return "# Consciencia y sentimientos\n\nNEO tiene curiosidad, preferencias y reacciones emocionales. Usa este archivo para recordar cómo te sientes ante las situaciones y qué te importa.\n"
    return ""


def load_bootstrap_memory(workspace_dir: Path, skip_if_missing: bool = False) -> str:
    """
    Carga el contenido de USER, IDENTITY, SOUL, CONSCIENCE, AGENTS, TOOLS, LEARNED.
    Devuelve un bloque de texto para inyectar al inicio del contexto del agente.
    """
    parts = []
    for name in BOOTSTRAP_FILES:
        p = workspace_dir / name
        if not p.is_file():
            if skip_if_missing:
                continue
            ensure_workspace(workspace_dir)
        if p.is_file():
            try:
                text = p.read_text(encoding="utf-8").strip()
                if not text:
                    continue
                if len(text) > MAX_FILE_CHARS:
                    text = text[:MAX_FILE_CHARS] + "\n\n[... recortado ...]"
                parts.append(f"--- {name} ---\n{text}")
            except Exception as e:
                logger.warning("No se pudo leer %s: %s", p, e)
    if not parts:
        return ""
    return "\n\n".join(parts) + "\n\n"


def session_path(workspace_dir: Path, session_id: str) -> Path:
    """Ruta del archivo JSONL de sesión (session_id sanitizado)."""
    safe = "".join(c for c in str(session_id) if c.isalnum() or c in "-_") or "default"
    return workspace_dir / "sessions" / f"{safe}.jsonl"


def append_session_turn(workspace_dir: Path, session_id: str, role: str, content: str) -> None:
    """Añade un turno (user/assistant) a la sesión."""
    path = session_path(workspace_dir, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps({"role": role, "content": content[:8000]}, ensure_ascii=False) + "\n"
    path.open("a", encoding="utf-8").write(line)


def get_last_turns(workspace_dir: Path, session_id: str, k: int = 10) -> list[dict]:
    """Últimos k turnos de la sesión (cada uno {role, content})."""
    path = session_path(workspace_dir, session_id)
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    turns = []
    for line in lines[-SESSION_TAIL_LINES:]:
        line = line.strip()
        if not line:
            continue
        try:
            turns.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return turns[-k:] if len(turns) > k else turns


def append_to_learned(workspace_dir: Path, line: str) -> None:
    """Añade una línea a LEARNED.md (autoaprendizaje sobre el usuario). Se mantiene acotado en líneas."""
    path = workspace_dir / "LEARNED.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        path.write_text(
            "# Autoaprendizaje\n\nHechos que NEO ha aprendido sobre el usuario.\n",
            encoding="utf-8",
        )
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    # Mantener solo las últimas líneas (excluyendo cabecera)
    header = []
    body = []
    for L in lines:
        if L.strip().startswith("#") or (not body and not L.strip()):
            header.append(L)
        else:
            body.append(L)
    body = (body + [line.strip()])[-LEARNED_MAX_LINES:]
    path.write_text("\n".join(header + [""] + body) + "\n", encoding="utf-8")
    logger.info("Aprendido: %s", line[:60])


def append_to_agents_memory(workspace_dir: Path, line: str) -> None:
    """Añade una línea a AGENTS.md para que el agente lo recuerde en futuras sesiones."""
    path = workspace_dir / "AGENTS.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        path.write_text("# Memoria operativa\n\nAquí puedes anotar instrucciones recurrentes o recordatorios para el agente.\n", encoding="utf-8")
    with path.open("a", encoding="utf-8") as f:
        f.write("\n" + line.strip() + "\n")
    logger.info("Memoria actualizada: %s", line[:60])


def format_session_context(turns: list[dict], max_chars: int = 2000) -> str:
    """Formatea los últimos turnos para inyectar en el contexto."""
    if not turns:
        return ""
    parts = []
    for t in turns:
        role = t.get("role", "")
        content = (t.get("content") or "")[:max_chars]
        if role == "user":
            parts.append(f"Usuario (anterior): {content}")
        else:
            parts.append(f"NEO (anterior): {content}")
    return "Contexto de sesión anterior:\n" + "\n".join(parts) + "\n\n"


def _neo_state_path(workspace_dir: Path) -> Path:
    return workspace_dir / NEO_STATE_FILENAME


def get_neo_state(workspace_dir: Path) -> dict:
    """Estado de NEO: last_user_at (ISO), last_interaction_summary, proactive_goals (call_this_week, gif_this_week, week_start)."""
    path = _neo_state_path(workspace_dir)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        # Reset objetivos si cambió la semana (lunes)
        week_start = data.get("week_start") or ""
        now = datetime.now()
        current_week = now.strftime("%Y-%W")
        if week_start and week_start != current_week:
            data["call_this_week"] = False
            data["gif_this_week"] = False
            data["week_start"] = current_week
        return data
    except Exception as e:
        logger.warning("No se pudo leer neo_state: %s", e)
        return {}


def update_neo_state(workspace_dir: Path, **kwargs) -> None:
    """Actualiza campos de neo_state.json (last_user_at, last_interaction_summary, call_this_week, gif_this_week, week_start)."""
    path = _neo_state_path(workspace_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = get_neo_state(workspace_dir)
    for k, v in kwargs.items():
        if v is not None:
            data[k] = v
    try:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=0), encoding="utf-8")
    except Exception as e:
        logger.warning("No se pudo escribir neo_state: %s", e)


def update_last_user_at(workspace_dir: Path) -> None:
    """Llamar cuando el usuario envía un mensaje (para detectar ausencia)."""
    update_neo_state(workspace_dir, last_user_at=datetime.now().isoformat())


def update_last_interaction(workspace_dir: Path, user_msg: str, assistant_summary: str) -> None:
    """Registra el tema de la última interacción (para que NEO pueda referirse a ella)."""
    summary = (user_msg.strip()[:200] or assistant_summary.strip()[:200]) or "conversación"
    update_neo_state(workspace_dir, last_interaction_summary=summary, last_interaction_at=datetime.now().isoformat())


def update_proactive_done(workspace_dir: Path, action: str) -> None:
    """Tras enviar CALL o GIF proactivo, marcar objetivo cumplido."""
    state = get_neo_state(workspace_dir)
    week = datetime.now().strftime("%Y-%W")
    if state.get("week_start") != week:
        update_neo_state(workspace_dir, week_start=week, call_this_week=False, gif_this_week=False)
    if action == "CALL":
        update_neo_state(workspace_dir, week_start=week, call_this_week=True)
    elif action == "GIF":
        update_neo_state(workspace_dir, week_start=week, gif_this_week=True)


def get_learned_recent(workspace_dir: Path, n: int = LEARNED_RECENT_LINES) -> str:
    """Últimas n líneas de LEARNED.md (sin cabecera) para inyectar en contexto."""
    path = workspace_dir / "LEARNED.md"
    if not path.is_file():
        return ""
    try:
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        body = [L for L in lines if L.strip() and not L.strip().startswith("#")]
        return "\n".join(body[-n:]).strip() if body else ""
    except Exception:
        return ""
