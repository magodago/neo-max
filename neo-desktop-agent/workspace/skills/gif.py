# Envía un GIF por Telegram (Giphy). Uso: SKILL:gif <tema> (ej. gatitos, buen dia, magia).
# Requiere GIPHY_API_KEY y telegram_bot_token en config; session_id = chat_id cuando se usa desde Telegram.
DESCRIPTION = "Envía un GIF por Telegram (tema: gatitos, buen día, magia, etc.). Uso: SKILL:gif <tema>"

import json
import sys
import urllib.request
from pathlib import Path


def _agent_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _load_config() -> dict:
    p = _agent_root() / "config.json"
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _send_telegram_gif(chat_id: str, gif_url: str, token: str) -> bool:
    """Envía un GIF por Telegram (sendDocument)."""
    if not (chat_id and gif_url and token):
        return False
    try:
        url = f"https://api.telegram.org/bot{token}/sendDocument"
        data = json.dumps({"chat_id": chat_id, "document": gif_url}).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except Exception:
        return False


def run(task: str = "", **kwargs) -> str:
    task = (task or "ok").strip()[:100]
    session_id = kwargs.get("session_id") or kwargs.get("chat_id") or ""
    chat_id = str(session_id).strip()
    config = _load_config()
    giphy_key = (config.get("giphy_api_key") or __import__("os").environ.get("GIPHY_API_KEY") or "").strip()
    token = (config.get("telegram_bot_token") or __import__("os").environ.get("TELEGRAM_BOT_TOKEN") or "").strip()

    if not giphy_key:
        return "No está configurada GIPHY_API_KEY en config o entorno. Añádela para poder enviar GIFs."
    if not chat_id:
        return "Para recibir el GIF por Telegram, pide el gif desde el chat de Telegram con NEO."
    if not token:
        return "No está configurado telegram_bot_token. Necesario para enviar el GIF al chat."

    root = _agent_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    try:
        from giphy_helper import get_random_gif_url
    except ImportError:
        return "No se encontró giphy_helper. Revisa la instalación del agente."

    gif_url = get_random_gif_url(giphy_key, task or "cat", rating="g")
    if not gif_url:
        return f"No se pudo obtener un GIF para «{task}». Prueba otro tema (ej. gatitos, buen día)."

    if _send_telegram_gif(chat_id, gif_url, token):
        return f"GIF enviado al chat (tema: {task})."
    return "El GIF se obtuvo pero no se pudo enviar por Telegram. Comprueba telegram_bot_token y que el bot pueda escribir en el chat."
