"""
NEO: Memoria persistente tipo OpenClaw.
Workspace con USER.md, IDENTITY.md, SOUL.md, AGENTS.md, TOOLS.md inyectados cada sesión.
Sesiones estables en JSONL por session_id (ej. chat_id de Telegram).
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger("neo_desktop.memory")

BOOTSTRAP_FILES = ("USER.md", "IDENTITY.md", "SOUL.md", "AGENTS.md", "TOOLS.md", "LEARNED.md")
MAX_FILE_CHARS = 4000
LEARNED_MAX_LINES = 200
SESSION_TAIL_LINES = 50


def get_workspace_dir(config: dict) -> Path:
    """Ruta del workspace (config o por defecto junto al agente)."""
    base = Path(__file__).resolve().parent
    ws = config.get("workspace_dir") or ""
    if ws:
        return Path(ws).expanduser().resolve()
    return base / "workspace"


def ensure_workspace(workspace_dir: Path) -> None:
    """Crea workspace y archivos bootstrap si no existen."""
    workspace_dir.mkdir(parents=True, exist_ok=True)
    (workspace_dir / "sessions").mkdir(exist_ok=True)
    (workspace_dir / "skills").mkdir(exist_ok=True)
    for name in BOOTSTRAP_FILES:
        p = workspace_dir / name
        if not p.is_file():
            p.write_text(_template(name), encoding="utf-8")
            logger.info("Creado %s", p)


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
        return "# Notas de herramientas\n\nConvenciones: BROWSER para web, SCRIPT:python para lógica, COMMAND para PowerShell.\n"
    if name == "LEARNED.md":
        return "# Autoaprendizaje\n\nHechos que NEO ha aprendido sobre el usuario (gustos, preferencias, reacciones) para ser más útil y proactivo.\n"
    return ""


def load_bootstrap_memory(workspace_dir: Path, skip_if_missing: bool = False) -> str:
    """
    Carga el contenido de USER, IDENTITY, SOUL, AGENTS, TOOLS.
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
