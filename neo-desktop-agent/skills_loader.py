"""
NEO: Skills dinámicos (el agente puede crear los que necesite).
Cada skill es un .py en workspace/skills/ con: def run(task="", **kwargs) -> str
y opcionalmente DESCRIPTION = "descripción".
"""
import importlib.util
import logging
import sys
from pathlib import Path

logger = logging.getLogger("neo_desktop.skills")

SKILLS_DIR_NAME = "skills"


def get_skills_dir(workspace_dir: Path) -> Path:
    return workspace_dir / SKILLS_DIR_NAME


def load_skills(workspace_dir: Path) -> dict:
    """
    Carga todos los .py en workspace/skills/.
    Returns: { "skill_name": {"run": callable, "description": str}, ... }
    """
    skills_dir = get_skills_dir(workspace_dir)
    if not skills_dir.is_dir():
        return {}
    registry = {}
    for path in sorted(skills_dir.glob("*.py")):
        if path.name.startswith("_"):
            continue
        name = path.stem
        try:
            # Ruta absoluta en str para evitar fallos en Windows/threads
            path_abs = str(path.resolve())
            spec = importlib.util.spec_from_file_location(f"neo_skill_{name}", path_abs)
            if spec is None or spec.loader is None:
                logger.debug("Skill %s: spec/loader None (path=%s)", name, path_abs)
                continue
            if spec.name in sys.modules:
                importlib.reload(sys.modules[spec.name])
                mod = sys.modules[spec.name]
            else:
                mod = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = mod
                spec.loader.exec_module(mod)
            if not hasattr(mod, "run"):
                logger.warning("Skill %s no tiene función run()", name)
                continue
            desc = getattr(mod, "DESCRIPTION", None) or getattr(mod, "description", "") or f"Skill {name}"
            registry[name] = {"run": mod.run, "description": str(desc).strip()[:200]}
        except Exception as e:
            logger.warning("No se pudo cargar skill %s: %s", name, e)
    return registry


def run_skill(registry: dict, skill_name: str, task: str = "", **kwargs) -> tuple[bool, str]:
    """Ejecuta un skill por nombre. Returns (success, output)."""
    skill_name = (skill_name or "").strip().lower()
    if not skill_name or skill_name not in registry:
        return (False, f"Skill desconocido: {skill_name}. Disponibles: {', '.join(registry.keys()) or 'ninguno'}")
    try:
        out = registry[skill_name]["run"](task=task, **kwargs)
        return (True, str(out) if out is not None else "OK")
    except Exception as e:
        return (False, str(e))


def list_skills_for_prompt(registry: dict) -> str:
    """Texto para inyectar en el prompt: lista de skills disponibles."""
    if not registry:
        return ""
    lines = ["Skills disponibles — si la tarea coincide, USA el skill (ej. clima → SKILL:clima <ciudad>):"]
    for name, info in sorted(registry.items()):
        lines.append(f"- SKILL:{name} — {info['description']}")
    return "\n".join(lines) + "\n"


def create_skill_file(workspace_dir: Path, skill_name: str, code: str) -> tuple[bool, str]:
    """
    Crea o sobrescribe workspace/skills/{skill_name}.py.
    El código debe definir run(task="", **kwargs) -> str.
    Returns (success, message).
    """
    name = "".join(c for c in skill_name if c.isalnum() or c in "-_")
    if not name:
        return (False, "Nombre de skill inválido")
    skills_dir = get_skills_dir(workspace_dir)
    skills_dir.mkdir(parents=True, exist_ok=True)
    path = skills_dir / f"{name}.py"
    if "def run(" not in code and "def run (" not in code:
        return (False, "El código del skill debe definir def run(task=\"\", **kwargs) -> str")
    try:
        path.write_text(code.strip(), encoding="utf-8")
        return (True, f"Skill '{name}' creado en {path}")
    except Exception as e:
        return (False, str(e))
