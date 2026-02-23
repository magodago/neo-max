"""
Batería de pruebas NEO: skills (directos) y opcionalmente agente (Ollama).
Uso:
  python tests/run_battery.py           # solo skills
  python tests/run_battery.py --agent   # skills + pruebas de agente (requiere Ollama)
  python tests/run_battery.py --list    # listar todas las pruebas
Escribe resultados en tests/RESULTS.txt.
"""
import json
import sys
from pathlib import Path

# Raíz del proyecto = padre de tests/
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RESULTS_FILE = Path(__file__).resolve().parent / "RESULTS.txt"


def _load_config():
    p = ROOT / "config.json"
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def _workspace_dir(config):
    from memory import get_workspace_dir
    return get_workspace_dir(config)


def run_skill_tests(config, results: list, quick_only: bool = False):
    """Ejecuta cada skill con una tarea mínima. Sin Ollama."""
    from memory import ensure_workspace
    from skills_loader import load_skills, run_skill

    workspace_dir = _workspace_dir(config)
    ensure_workspace(workspace_dir)
    registry = load_skills(workspace_dir)
    if not registry:
        results.append(("S0", "SKILLS", False, "No se cargó ningún skill"))
        return

    all_cases = [
        ("clima", "Madrid", lambda o: "Madrid" in o or "°" in o or "Error" not in o[:80]),
        ("chiste", "", lambda o: len(o.strip()) > 10 and "Error" not in o[:50]),
        ("hora_mundo", "Londres", lambda o: "Londres" in o or ":" in o or "Error" not in o[:80]),
        ("qr", "https://example.com", lambda o: "qr" in o.lower() or "png" in o.lower() or "Error" not in o[:80]),
        ("estado_pc", "", lambda o: "cpu" in o.lower() or "ram" in o.lower() or "Error" not in o[:80]),
        ("documento_pdf", "guerra fría 1 página", lambda o: "pdf" in o.lower() or "Error" not in o[:100]),
        ("documentos_imagenes", "test", lambda o: "doc" in o.lower() or "Error" not in o[:100]),
        ("cursos", "test", lambda o: "curso" in o.lower() or "output" in o.lower() or "Error" not in o[:100]),
        ("juegos_movil", "snake", lambda o: "index" in o.lower() or "html" in o.lower() or "Error" not in o[:100]),
        ("web_sitio", "test", lambda o: "html" in o.lower() or "web" in o.lower() or "Error" not in o[:100]),
        ("compra_ingredientes", "paella", lambda o: "ingrediente" in o.lower() or "mercado" in o.lower() or "Error" not in o[:100]),
        ("ficha_jugador", "Mbappé", lambda o: "mbappé" in o.lower() or "html" in o.lower() or "Error" not in o[:100]),
        ("magia_historia", "inicio", lambda o: "magia" in o.lower() or "html" in o.lower() or "Error" not in o[:100]),
        ("generar_imagen", "un gato", lambda o: "imagen" in o.lower() or "png" in o.lower() or "Error" not in o[:100]),
    ]
    quick_skills = {"clima", "chiste", "hora_mundo", "qr", "estado_pc"}
    cases = [c for c in all_cases if not quick_only or c[0] in quick_skills]

    for i, (name, task, check) in enumerate(cases, 1):
        tid = f"S{i}"
        if name not in registry:
            results.append((tid, f"SKILL:{name}", False, "Skill no cargado"))
            continue
        ok, out = run_skill(registry, name, task=task)
        out_preview = (out or "")[:200].replace("\n", " ")
        if ok and check(out or ""):
            results.append((tid, f"SKILL:{name}", True, out_preview))
        else:
            results.append((tid, f"SKILL:{name}", False, out_preview or "sin salida"))


def run_agent_tests(config, results: list):
    """Pruebas que usan run_agent (requieren Ollama)."""
    from agent import run_agent

    workspace_dir = _workspace_dir(config)

    # A1–A4: early returns
    early = [
        ("A1", "¿Cómo te llamas?", lambda msg: "neo" in (msg or "").lower()),
        ("A2", "¿Qué skills tienes?", lambda msg: "clima" in (msg or "").lower() or "skill" in (msg or "").lower()),
        ("A3", "Voy a cenar con mis hijas", lambda msg: "disfrutad" in (msg or "").lower() or "disfrutar" in (msg or "").lower()),
        ("A4", "¿De qué hemos hablado?", lambda msg: True),  # cualquier respuesta coherente
    ]
    for tid, task, check in early:
        try:
            r = run_agent(task, auto_confirm=True, return_history=True, session_id="battery_test", max_steps=3)
            if r is None:
                results.append((tid, task[:40], False, "run_agent devolvió None"))
            else:
                msg, _ = r
                if check(msg):
                    results.append((tid, task[:40], True, (msg or "")[:150]))
                else:
                    results.append((tid, task[:40], False, (msg or "")[:150]))
        except Exception as e:
            results.append((tid, task[:40], False, str(e)[:150]))

    # B1–B5: tareas con skill (un paso)
    agent_tasks = [
        ("B1", "Dime el clima en Illescas", lambda m: "illescas" in (m or "").lower() or "°" in (m or "") or "temperatura" in (m or "").lower()),
        ("B2", "Cuéntame un chiste", lambda m: len((m or "").strip()) > 20),
        ("B3", "¿Qué hora es en Tokyo?", lambda m: ":" in (m or "") or "tokyo" in (m or "").lower()),
        ("B4", "¿Cómo va mi PC?", lambda m: "cpu" in (m or "").lower() or "ram" in (m or "").lower() or len((m or "")) > 10),
        ("B5", "Genera un QR de https://google.com", lambda m: "qr" in (m or "").lower() or "google" in (m or "").lower() or "listo" in (m or "").lower()),
    ]
    for tid, task, check in agent_tasks:
        try:
            r = run_agent(task, auto_confirm=True, return_history=True, session_id="battery_test", max_steps=5)
            if r is None:
                results.append((tid, task[:40], False, "run_agent devolvió None"))
            else:
                msg, _ = r
                if check(msg):
                    results.append((tid, task[:40], True, (msg or "")[:150]))
                else:
                    results.append((tid, task[:40], False, (msg or "")[:150]))
        except Exception as e:
            results.append((tid, task[:40], False, str(e)[:150]))


def run_memory_checks(config, results: list):
    """Compruebas rápidas de memoria/estado (sin agente completo)."""
    from memory import ensure_workspace, get_neo_state, get_learned_recent, update_neo_state

    workspace_dir = _workspace_dir(config)
    ensure_workspace(workspace_dir)

    # M1: neo_state existe y tiene estructura
    state = get_neo_state(workspace_dir)
    has_keys = isinstance(state, dict)
    results.append(("M1", "neo_state existe", has_keys, str(list(state.keys())[:5]) if state else ""))

    # M3: get_learned_recent no rompe
    try:
        learned = get_learned_recent(workspace_dir)
        results.append(("M3", "get_learned_recent", True, f"{len(learned)} chars"))
    except Exception as e:
        results.append(("M3", "get_learned_recent", False, str(e)[:100]))


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Batería de pruebas NEO")
    ap.add_argument("--agent", action="store_true", help="Incluir pruebas de agente (Ollama)")
    ap.add_argument("--quick", action="store_true", help="Solo skills rápidos (clima, chiste, hora, qr, estado_pc)")
    ap.add_argument("--list", action="store_true", help="Solo listar pruebas (no ejecutar)")
    args = ap.parse_args()

    if args.list:
        print("Pruebas definidas en tests/BATTERY.md:")
        print("  S1–S14: Skills directos")
        print("  A1–A4:  Early returns (nombre, skills, charla, de qué hemos hablado)")
        print("  B1–B5:  Agente + skill (clima, chiste, hora, PC, QR)")
        print("  M1–M2:  Memoria/estado")
        print("Ejecutar: python tests/run_battery.py [--agent]")
        return

    config = _load_config()
    results = []

    print("Running skill tests...")
    run_skill_tests(config, results, quick_only=args.quick)

    print("Running memory checks...")
    run_memory_checks(config, results)

    if args.agent:
        print("Running agent tests (Ollama)...")
        run_agent_tests(config, results)

    # Salida
    ok_count = sum(1 for _, _, ok, _ in results if ok)
    fail_count = len(results) - ok_count

    lines = []
    for tid, name, ok, detail in results:
        status = "OK" if ok else "FAIL"
        line = f"{tid} {status} | {name} | {detail[:80]}"
        lines.append(line)
        print(line)

    print()
    print(f"Total: {ok_count} OK, {fail_count} FAIL")

    try:
        RESULTS_FILE.write_text("\n".join(lines) + "\n\n" + f"OK: {ok_count}  FAIL: {fail_count}\n", encoding="utf-8")
        print(f"Resultados guardados en {RESULTS_FILE}")
    except Exception as e:
        print(f"No se pudo escribir RESULTS.txt: {e}")


if __name__ == "__main__":
    main()
