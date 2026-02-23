# Pruebas rápidas de skills (ejecutar desde neo-desktop-agent):
#   python run_skill_test.py
# Prueba magia_historia (inicio + añadir) y opcionalmente otro skill.

import sys
from pathlib import Path

# Asegurar que el agente puede cargar skills desde workspace/skills
agent_root = Path(__file__).resolve().parent
workspace_skills = agent_root / "workspace" / "skills"
if str(workspace_skills) not in sys.path:
    sys.path.insert(0, str(workspace_skills))

def test_magia_historia():
    from magia_historia import run
    r1 = run("inicio")
    assert "1 magos" in r1 or "magos" in r1, r1
    r2 = run("add")  # "add" evita problemas de encoding en consola
    assert "magos" in r2, r2
    out = agent_root / "workspace" / "output" / "magia_historia"
    assert (out / "index.html").is_file(), "Falta index.html"
    assert (out / "mago_001.html").is_file(), "Falta mago_001.html"
    print("[OK] magia_historia: inicio + add")
    return True

if __name__ == "__main__":
    print("Probando skills...")
    try:
        test_magia_historia()
        print("Pruebas pasadas.")
    except Exception as e:
        print("Error:", e)
        sys.exit(1)
