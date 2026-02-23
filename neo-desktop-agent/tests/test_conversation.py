"""
Mini conversación con NEO para comprobar memoria y respuestas.
Ejecutar desde neo-desktop-agent: python tests/test_conversation.py
"""
import sys
from pathlib import Path


def _safe_print(s: str) -> None:
    """Imprime en consola evitando errores de encoding (ej. emojis en Windows cp1252)."""
    if not s:
        return
    try:
        print(s)
    except UnicodeEncodeError:
        print(s.encode("ascii", errors="replace").decode("ascii"))

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SESSION_ID = "test_memory_conversation"


def run(task: str) -> str:
    from agent import run_agent
    result = run_agent(
        task,
        auto_confirm=True,
        return_history=True,
        session_id=SESSION_ID,
        include_session_context=True,
        max_steps=10,
    )
    if result is None:
        return "(sin respuesta)"
    msg, _ = result
    return (msg or "").strip()


def main():
    print("=== Mini conversación con NEO (comprobando memoria) ===\n")

    # 1) Nombre
    t1 = "¿Cómo te llamas?"
    _safe_print(f"Usuario: {t1}")
    r1 = run(t1)
    _safe_print(f"NEO: {r1}\n")
    if "neo" not in r1.lower():
        _safe_print("  [AVISO] Se esperaba que dijera que se llama NEO.\n")

    # 2) Charla (no ejecutar skill)
    t2 = "Voy a cenar con mis hijas"
    _safe_print(f"Usuario: {t2}")
    r2 = run(t2)
    _safe_print(f"NEO: {r2}\n")
    if "disfrutad" not in r2.lower() and "disfrutar" not in r2.lower():
        _safe_print("  [AVISO] Se esperaba respuesta de charla (disfrutad/disfrutar).\n")

    # 3) Memoria: de qué hemos hablado
    t3 = "¿De qué hemos hablado?"
    _safe_print(f"Usuario: {t3}")
    r3 = run(t3)
    _safe_print(f"NEO: {r3}\n")
    if "cenar" not in r3.lower() and "hijas" not in r3.lower() and "nombre" not in r3.lower():
        _safe_print("  [AVISO] Se esperaba que recordara cenar/hijas o el nombre.\n")

    # 4) Skills disponibles (early return)
    t4 = "¿Qué skills tienes?"
    _safe_print(f"Usuario: {t4}")
    r4 = run(t4)
    _safe_print(f"NEO: {r4}\n")
    if "clima" not in r4.lower() and "skill" not in r4.lower():
        _safe_print("  [AVISO] Se esperaba lista de skills (ej. clima).\n")

    _safe_print("=== Fin de la conversación ===")


if __name__ == "__main__":
    main()
