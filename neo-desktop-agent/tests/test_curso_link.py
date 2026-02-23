"""
Prueba: crear curso completo y profesional y obtener el link (GitHub Pages).
Tema: cómo montar un negocio en España si eres extranjero.
- Ejecuta el agente con la tarea de crear el curso (skill cursos) y subir a GitHub.
- Extrae la URL del resultado (github.io) y la imprime; opcionalmente envía por Telegram.

Uso (desde neo-desktop-agent):
  python tests/test_curso_link.py

Requisitos: Ollama, config con telegram_bot_token y chat_id (opcional para enviar link).
Timeout: 10 min (el curso tiene muchos archivos y el push puede tardar).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RUN_TIMEOUT_SEC = 600

TAREA_CURSO = (
    "Crea un curso completo y profesional sobre cómo montar un negocio en España si eres extranjero. "
    "Curso listo para monetizar (Udemy/Teachable). Usa el skill de cursos, sube la carpeta a GitHub con GITHUB:push "
    "y responde DONE con la URL de GitHub Pages para que pueda ver el curso."
)


def _load_config():
    p = ROOT / "config.json"
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def _extract_url_from_result(msg: str, history: list) -> str | None:
    """Extrae la URL de GitHub Pages. Prioriza la que viene del GITHUB:push (magodago)."""
    found = []
    for h in history or []:
        out = h.get("out") or ""
        if "github.io" in out and "http" in out:
            m = re.search(r"https://[a-zA-Z0-9_.-]+\.github\.io/[^\s\]\)\"'<>]+", out)
            if m:
                u = m.group(0).strip().rstrip("/.,;:")
                if not u.endswith("/"):
                    u = u + "/"
                found.append(u)
    # Preferir URL de magodago (la que devuelve nuestro push)
    for u in found:
        if "magodago" in u:
            return u
    combined = (msg or "") + "\n" + "\n".join(h.get("out") or "" for h in (history or []))
    m = re.search(r"https://[a-zA-Z0-9_.-]+\.github\.io/[^\s\]\)\"'<>]+", combined)
    if m:
        u = m.group(0).strip().rstrip("/.,;:")
        return u + "/" if not u.endswith("/") else u
    return found[0] if found else None


def main():
    config = _load_config()
    token = (config.get("telegram_bot_token") or "").strip()
    chat_id = config.get("proactive_agent") or {}
    if isinstance(chat_id, dict):
        chat_id = (chat_id.get("deliver_to_telegram_chat_id") or config.get("telegram_allowed_user_ids") or [])
    if isinstance(chat_id, list):
        chat_id = str(chat_id[0]) if chat_id else ""
    else:
        chat_id = str(chat_id or "")

    print("Tarea:", TAREA_CURSO[:80], "...")
    print("Ejecutando agente (curso + GitHub push, puede tardar varios minutos)...")

    try:
        from agent import run_agent
        result = run_agent(
            TAREA_CURSO,
            auto_confirm=True,
            return_history=True,
            session_id="test_curso",
            include_session_context=True,
            max_steps=25,
        )
    except Exception as e:
        print("Error ejecutando agente:", e)
        sys.exit(2)

    if result is None:
        print("El agente no devolvió resultado.")
        sys.exit(3)

    msg, history = result
    url = _extract_url_from_result(msg, history)

    if url:
        print("\n--- LINK DEL CURSO ---")
        print(url)
        print("---")
        if chat_id and token:
            try:
                import urllib.request
                api = f"https://api.telegram.org/bot{token}/sendMessage"
                body = json.dumps({"chat_id": chat_id, "text": "Curso listo:\n" + url, "disable_web_page_preview": False})
                req = urllib.request.Request(api, data=body.encode("utf-8"), method="POST", headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    if resp.status == 200:
                        print("Link enviado a Telegram.")
            except Exception as e:
                print("No se pudo enviar a Telegram:", e)
    else:
        print("No se encontró URL en el resultado. Mensaje:", (msg or "")[:400])
        sys.exit(4)


if __name__ == "__main__":
    main()
