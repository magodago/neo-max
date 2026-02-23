"""
NEO: Automatización tipo OpenClaw — Cron, Heartbeat, Proactivo (y ventana horaria).
Ventana permitida para mensajes/calls proactivos: 9:00–23:00 (no molestar 23:00–9:00).
"""
import json
import logging
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("neo_desktop.scheduler")

# Ventana en la que NEO puede escribir o llamar por su cuenta (9:00–23:00)
PROACTIVE_HOUR_START = 9
PROACTIVE_HOUR_END = 23


def _is_proactive_time_allowed() -> bool:
    """True si estamos entre 9:00 y 23:00 (hora local)."""
    h = datetime.now().hour
    return PROACTIVE_HOUR_START <= h < PROACTIVE_HOUR_END

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"


def _load_config() -> dict:
    if not CONFIG_PATH.is_file():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _run_task(prompt: str, deliver_to_telegram_chat_id: str | None = None) -> str:
    """Ejecuta el agente y opcionalmente envía el resultado por Telegram."""
    try:
        from agent import run_agent
        result = run_agent(
            prompt,
            auto_confirm=True,
            return_history=True,
            session_id=deliver_to_telegram_chat_id or None,
            include_session_context=True,
        )
        if result is None:
            return "(sin resultado)"
        msg, _ = result
        return msg or "(sin resultado)"
    except Exception as e:
        logger.exception("Error en tarea programada: %s", e)
        return f"Error: {e}"


def _send_telegram(chat_id: str, text: str, token: str) -> bool:
    """Envía un mensaje por Telegram. Returns True si OK."""
    try:
        import urllib.request
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = json.dumps({"chat_id": chat_id, "text": text[:4000], "disable_web_page_preview": True}).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except Exception as e:
        logger.warning("Telegram send failed: %s", e)
        return False


def _send_telegram_gif(chat_id: str, gif_url: str, token: str) -> bool:
    """Envía un GIF por Telegram (sendDocument con URL)."""
    try:
        import urllib.request
        url = f"https://api.telegram.org/bot{token}/sendDocument"
        data = json.dumps({"chat_id": chat_id, "document": gif_url}).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except Exception as e:
        logger.warning("Telegram GIF send failed: %s", e)
        return False


def _proactive_loop() -> None:
    """Loop proactivo: NEO escribe cuando quiera (9:00–23:00), propone, envía GIF o nota de voz."""
    import urllib.request
    import random
    while True:
        config = _load_config()
        pro = config.get("proactive_agent") or {}
        if not pro.get("enabled"):
            time.sleep(120)
            continue
        # Solo actuar en ventana permitida (9:00–23:00)
        if not _is_proactive_time_allowed():
            time.sleep(300)
            continue
        interval = max(15, int(pro.get("interval_minutes", 60)))
        interval = int(interval * (0.7 + 0.6 * random.random()))
        chat_id = (pro.get("deliver_to_telegram_chat_id") or config.get("telegram_allowed_user_ids") or [])
        if isinstance(chat_id, list):
            chat_id = str(chat_id[0]) if chat_id else ""
        token = config.get("telegram_bot_token") or ""
        try:
            from memory import get_workspace_dir, load_bootstrap_memory
            workspace_dir = get_workspace_dir(config)
            memory_block = load_bootstrap_memory(workspace_dir, skip_if_missing=True)
            system_proactive = (
                "Eres NEO, agente autónomo con memoria del usuario (David). Tienes su perfil, recordatorios y lo que has aprendido (LEARNED). "
                "Decides tú solo qué hacer (solo entre 9:00 y 23:00). Responde EXACTAMENTE una de estas líneas, sin explicación: "
                "PROPOSE: <mensaje corto> | "
                "CALL: <mensaje breve> (te llamo por teléfono y lo digo por voz: aviso, ánimo, noticia o saludar) | "
                "GIF: <tema, ej. buen dia, magia, python> | "
                "NOPROPOSE (si no hay nada esta vez). "
                "Varía: no siempre PROPOSE; a veces CALL (llamar) o GIF (gif divertido) para tener más contacto."
            )
            # Nudge aleatorio para que elija CALL o GIF más a menudo (~35% de las veces)
            nudge = ""
            if random.random() < 0.35:
                nudge = " Esta vez considera especialmente CALL o GIF. "
            prompt = (memory_block or "") + "\n¿Qué quieres hacer ahora por David?" + nudge + " Responde SOLO una línea: PROPOSE: / CALL: / GIF: / NOPROPOSE:"
            url = config.get("ollama_url", "http://localhost:11434/api/generate")
            body = json.dumps({
                "model": config.get("model", "qwen2.5:7b-instruct"),
                "prompt": prompt[:8000],
                "system": system_proactive,
                "stream": False,
                "options": {"temperature": 0.6, "num_predict": 350},
            })
            req = urllib.request.Request(url, data=body.encode("utf-8"), method="POST", headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                out = json.loads(resp.read().decode("utf-8"))
            raw_response = (out.get("response") or "").strip()
            # Usar solo la primera línea para la decisión (evitar texto extra del modelo)
            first_line = raw_response.split("\n")[0].strip()
            response = first_line.upper()
            # Normalizar: quitar espacio opcional tras los dos puntos (CALL : msg -> CALL:)
            response_norm = response.replace(" : ", ":").replace(": ", ":")
            # Detección robusta: buscar prefijo en la línea
            action = None
            msg = ""
            if response_norm.startswith("PROPOSE:"):
                action = "PROPOSE"
                msg = first_line[8:].strip().lstrip(":").strip() or raw_response[8:].strip()[:1500]
            elif response_norm.startswith("CALL:"):
                action = "CALL"
                msg = first_line[5:].strip().lstrip(":").strip() or raw_response[5:].strip()[:500]
            elif response_norm.startswith("GIF:"):
                action = "GIF"
                msg = (first_line[4:].strip().lstrip(":").strip() or raw_response[4:].strip() or "buen dia")[:80]
            elif "NOPROPOSE" in response_norm or "NO PROPOSE" in response_norm:
                action = "NOPROPOSE"

            logger.info("Proactivo decisión NEO: %s | raw: %s", action or "?(sin formato)", first_line[:100])
            if action == "PROPOSE" and msg and chat_id and token:
                _send_telegram(chat_id, "💡 NEO:\n" + msg[:1500], token)
                logger.info("Proactivo enviado: %s", msg[:80])
            elif action == "CALL" and msg and chat_id and token:
                try:
                    from voice_out import send_voice_to_telegram, call_user_phone
                    send_voice_to_telegram(config, chat_id, msg, token)
                    logger.info("Proactivo voz Telegram enviada")
                    if config.get("twilio_account_sid") and config.get("twilio_twiml_url"):
                        if call_user_phone(config, msg):
                            logger.info("Proactivo llamada Twilio iniciada")
                        else:
                            logger.warning("Proactivo: Twilio no inició (revisa horario 9-23h o config)")
                    else:
                        logger.info("Proactivo: Twilio no configurado, solo voz por Telegram")
                except Exception as e:
                    logger.warning("Voice send failed: %s", e)
                    _send_telegram(chat_id, "📞 NEO:\n" + msg, token)
            elif action == "GIF" and chat_id and token:
                query = msg or "buen dia"
                giphy_key = (config.get("giphy_api_key") or "").strip()
                if giphy_key:
                    try:
                        from giphy_helper import get_random_gif_url
                        gif_url = get_random_gif_url(giphy_key, query)
                        if gif_url and _send_telegram_gif(chat_id, gif_url, token):
                            logger.info("GIF enviado: %s", query)
                        else:
                            _send_telegram(chat_id, "🎬 NEO: " + query, token)
                    except Exception as e:
                        logger.warning("GIF failed: %s", e)
                        _send_telegram(chat_id, "🎬 NEO: " + query, token)
                else:
                    _send_telegram(chat_id, "🎬 NEO: " + query, token)
            elif action == "NOPROPOSE":
                logger.info("Proactivo: NEO eligió no hacer nada esta vez")
            elif action is None:
                logger.warning("Proactivo: respuesta no reconocida (esperado PROPOSE:/CALL:/GIF:/NOPROPOSE)")
        except Exception as e:
            logger.warning("Proactivo error: %s", e)
        time.sleep(interval * 60)


def _heartbeat_loop() -> None:
    """Loop que cada N minutos ejecuta el prompt de heartbeat."""
    while True:
        config = _load_config()
        hb = config.get("heartbeat") or {}
        if not hb.get("enabled"):
            time.sleep(60)
            continue
        interval = max(1, int(hb.get("interval_minutes", 30)))
        prompt = (hb.get("prompt") or "Revisa si hay algo pendiente para el usuario.").strip()
        chat_id = hb.get("deliver_to_telegram_chat_id") or ""
        token = config.get("telegram_bot_token") or ""
        logger.info("Heartbeat: ejecutando «%s»", prompt[:50])
        msg = _run_task(prompt, deliver_to_telegram_chat_id=chat_id or None)
        if chat_id and token:
            _send_telegram(chat_id, "🔄 Heartbeat:\n" + msg, token)
        time.sleep(interval * 60)


def _daily_magia_publish() -> bool:
    """
    Añade el mago del día (skill magia_historia) y publica la carpeta en GitHub.
    Devuelve True si se ejecutó correctamente (y opcionalmente envía Telegram con la URL).
    """
    config = _load_config()
    daily = config.get("magia_historia_daily") or {}
    if not daily.get("enabled"):
        return False
    repo_name = (daily.get("repo_name") or "magia-historia").strip() or "magia-historia"
    out_dir = Path(__file__).resolve().parent / "workspace" / "output" / "magia_historia"
    state_file = Path(__file__).resolve().parent / "workspace" / "output" / "magia_historia" / ".last_daily_publish"
    try:
        # 1) Ejecutar skill: añadir mago del día
        skills_dir = Path(__file__).resolve().parent / "workspace" / "skills"
        if str(skills_dir) not in sys.path:
            sys.path.insert(0, str(skills_dir))
        try:
            from magia_historia import run as run_magia
            run_magia("add")
        except Exception as e:
            logger.warning("Magia skill add failed: %s", e)
        # 2) Publicar en GitHub
        from github_helper import publish_folder
        ok, url_or_err = publish_folder(out_dir, repo_name, description="Historia de la Magia · Un mago cada día")
        if not ok:
            logger.warning("Magia daily publish GitHub failed: %s", url_or_err)
            return False
        logger.info("Magia publicada a las 10:00: %s", url_or_err)
        # 3) Notificar por Telegram si está configurado
        chat_id = daily.get("notify_telegram_chat_id") or (config.get("proactive_agent") or {}).get("deliver_to_telegram_chat_id")
        token = config.get("telegram_bot_token") or ""
        if chat_id and token and url_or_err.startswith("http"):
            _send_telegram(str(chat_id), "🪄 Historia de la Magia actualizada (mago del día)\n" + url_or_err, token)
        # Marcar que ya se ejecutó hoy
        out_dir.mkdir(parents=True, exist_ok=True)
        state_file.write_text(datetime.now().strftime("%Y-%m-%d"), encoding="utf-8")
        return True
    except Exception as e:
        logger.exception("Daily magia publish failed: %s", e)
        return False


def _daily_magia_loop() -> None:
    """Cada minuto comprueba si son las 10:00 y si no se ha ejecutado hoy; entonces añade mago y publica en GitHub."""
    last_run_date = ""
    while True:
        time.sleep(60)
        config = _load_config()
        daily = config.get("magia_historia_daily") or {}
        if not daily.get("enabled"):
            continue
        now = datetime.now()
        target_time = (daily.get("time") or "10:00").strip()
        try:
            h, m = map(int, target_time.split(":"))
        except Exception:
            h, m = 10, 0
        if now.hour != h:
            continue
        today = now.strftime("%Y-%m-%d")
        if last_run_date == today:
            continue
        state_file = Path(__file__).resolve().parent / "workspace" / "output" / "magia_historia" / ".last_daily_publish"
        if state_file.is_file():
            try:
                last_run_date = state_file.read_text(encoding="utf-8").strip()
            except Exception:
                pass
            if last_run_date == today:
                continue
        if _daily_magia_publish():
            last_run_date = today


def _reminders_loop() -> None:
    """Cada minuto comprueba recordatorios vencidos y envía Telegram."""
    while True:
        time.sleep(60)
        try:
            config = _load_config()
            workspace_dir = Path(__file__).resolve().parent / "workspace"
            try:
                from memory import get_workspace_dir
                workspace_dir = get_workspace_dir(config) or workspace_dir
            except Exception:
                pass
            from reminders import process_due_reminders
            token = (config.get("telegram_bot_token") or "").strip()

            def send_fn(chat_id: str, text: str) -> bool:
                return bool(token and chat_id and _send_telegram(chat_id, text, token))

            process_due_reminders(workspace_dir, send_fn)
        except Exception as e:
            logger.warning("Reminders loop: %s", e)


def _cron_loop() -> None:
    """Loop que comprueba cron_jobs (cada minuto) y ejecuta los que toquen."""
    try:
        import schedule
    except ImportError:
        logger.warning("Instala 'schedule' para cron: pip install schedule")
        return
    config = _load_config()
    jobs_config = config.get("cron_jobs") or []
    token = config.get("telegram_bot_token") or ""
    for job in jobs_config:
        when = (job.get("schedule") or "").strip().lower()
        prompt = (job.get("prompt") or "").strip()
        chat_id = job.get("deliver_to_telegram_chat_id") or ""
        if not when or not prompt:
            continue
        def run_job(p=prompt, cid=chat_id, tok=token):
            logger.info("Cron: «%s»", p[:50])
            msg = _run_task(p, deliver_to_telegram_chat_id=cid or None)
            if cid and tok:
                _send_telegram(cid, "⏰ Cron:\n" + msg, tok)
        if when.startswith("every "):
            # "every 30 minutes", "every 1 hours"
            parts = when.replace("every", "").strip().split()
            if len(parts) >= 2:
                try:
                    n = int(parts[0])
                    unit = parts[1].lower()
                    if "min" in unit:
                        schedule.every(n).minutes.do(run_job)
                    elif "hour" in unit:
                        schedule.every(n).hours.do(run_job)
                    else:
                        schedule.every(n).hours.do(run_job)
                except ValueError:
                    pass
        else:
            # "09:00" o "HH:MM"
            if ":" in when and len(when) <= 5:
                schedule.every().day.at(when).do(run_job)
    while True:
        schedule.run_pending()
        time.sleep(60)


def start_background() -> None:
    """Arranca proactive, heartbeat y cron en hilos en segundo plano."""
    config = _load_config()
    if config.get("proactive_agent", {}).get("enabled"):
        t = threading.Thread(target=_proactive_loop, daemon=True)
        t.start()
        logger.info("Proactivo iniciado (interval: %s min)", config.get("proactive_agent", {}).get("interval_minutes", 120))
    if config.get("heartbeat", {}).get("enabled"):
        t = threading.Thread(target=_heartbeat_loop, daemon=True)
        t.start()
        logger.info("Heartbeat iniciado (interval: %s min)", config.get("heartbeat", {}).get("interval_minutes", 30))
    if config.get("cron_jobs"):
        t = threading.Thread(target=_cron_loop, daemon=True)
        t.start()
        logger.info("Cron iniciado (%d jobs)", len(config.get("cron_jobs", [])))
    if (config.get("magia_historia_daily") or {}).get("enabled"):
        t = threading.Thread(target=_daily_magia_loop, daemon=True)
        t.start()
        logger.info("Magia diaria a las %s: añadir mago + publicar GitHub", (config.get("magia_historia_daily") or {}).get("time", "10:00"))
    t = threading.Thread(target=_reminders_loop, daemon=True)
    t.start()
    logger.info("Recordatorios: aviso por Telegram a la hora programada")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    start_background()
    while True:
        time.sleep(3600)
