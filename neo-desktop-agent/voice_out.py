"""
NEO: Salida por voz — Eleven Labs TTS y envío por Telegram (nota de voz).
Opcional: Twilio para llamada real al móvil (config: twilio_* y user_phone_number).
Ventana permitida para llamar: 9:00–23:00 (igual que mensajes proactivos).
"""
import json
import logging
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

logger = logging.getLogger("neo_desktop.voice_out")


def _tts_elevenlabs(text: str, api_key: str, voice_id: str) -> str | None:
    """Genera audio con Eleven Labs. Devuelve ruta del archivo MP3 o None."""
    if not api_key or not voice_id or not text.strip():
        return None
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    data = json.dumps({"text": text[:1000], "model_id": "eleven_multilingual_v2"}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "xi-api-key": api_key,
            "Accept": "audio/mpeg",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            audio = resp.read()
        if not audio:
            return None
        f = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        f.write(audio)
        f.close()
        return f.name
    except Exception as e:
        logger.warning("Eleven Labs TTS failed: %s", e)
        return None


def send_voice_to_telegram(config: dict, chat_id: str, text: str, bot_token: str) -> bool:
    """
    Convierte texto a voz (Eleven Labs si hay api_key) y envía como nota de voz por Telegram.
    Si Eleven Labs falla (402, sin créditos, etc.), devuelve False; el caller puede enviar el texto como mensaje.
    """
    api_key = (config.get("elevenlabs_api_key") or "").strip()
    voice_id = (config.get("elevenlabs_voice_id") or "").strip()
    path = _tts_elevenlabs(text, api_key, voice_id)
    if not path:
        return False
    try:
        with open(path, "rb") as f:
            audio_bytes = f.read()
        boundary = "----NEOFormBoundary"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{chat_id}\r\n'
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="document"; filename="neo.mp3"\r\n'
            f"Content-Type: audio/mpeg\r\n\r\n"
        ).encode("utf-8") + audio_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{bot_token}/sendDocument",
            data=body,
            method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            ok = resp.status == 200
        Path(path).unlink(missing_ok=True)
        return ok
    except Exception as e:
        logger.warning("Send voice to Telegram failed: %s", e)
        Path(path).unlink(missing_ok=True)
        return False


def _escape_twiml(text: str) -> str:
    """Escapa el texto para usarlo dentro de <Say> en TwiML."""
    import html
    return html.escape(text[:500].strip(), quote=True)


def call_user_phone(config: dict, message: str, force_inline: bool = False) -> bool:
    """
    Llama al móvil del usuario y reproduce el mensaje por voz (Twilio).
    Por defecto usa TwiML inline (<Say language="es-ES">mensaje</Say>) para que escuches el texto en español
    con la voz de Twilio, sin depender de URLs externas ni de ElevenLabs. Si force_inline=True, siempre
    se usa inline (recomendado cuando ElevenLabs ha fallado). Solo si está en ventana 9:00–23:00.
    """
    import base64
    import urllib.parse
    from scheduler import _is_proactive_time_allowed
    if not _is_proactive_time_allowed():
        return False
    phone = (config.get("user_phone_number") or "").strip()
    sid = (config.get("twilio_account_sid") or "").strip()
    auth = (config.get("twilio_auth_token") or "").strip()
    from_num = (config.get("twilio_phone_number") or "").strip()
    if not all([phone, sid, auth, from_num]):
        return False
    # Números en formato E.164 (Twilio lo exige)
    if phone and not phone.startswith("+"):
        phone = "+" + phone.lstrip("0")
    if from_num and not from_num.startswith("+"):
        from_num = "+" + from_num.lstrip("0")
    if not (message or message.strip()):
        logger.warning("call_user_phone: mensaje vacío, no se inicia llamada")
        return False
    try:
        twilio_api = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls.json"
        # Siempre preferir TwiML inline: el usuario oye el mensaje en español (Twilio TTS). La URL externa
        # (twilio_twiml_url) puede depender de ElevenLabs y devolver error en inglés si falla.
        use_inline = force_inline or config.get("twilio_use_twiml_inline", True)
        twiml_url = (config.get("twilio_twiml_url") or "").strip()
        if use_inline or not twiml_url:
            say_text = _escape_twiml(message)
            twiml = f'<Response><Say language="es-ES">{say_text}</Say></Response>'
            data = urllib.parse.urlencode({
                "To": phone,
                "From": from_num,
                "Twiml": twiml,
            }).encode("utf-8")
        else:
            sep = "&" if "?" in twiml_url else "?"
            call_url = twiml_url + sep + "msg=" + urllib.parse.quote(message[:500])
            data = urllib.parse.urlencode({
                "To": phone,
                "From": from_num,
                "Url": call_url,
            }).encode("utf-8")
        req = urllib.request.Request(
            twilio_api,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": "Basic " + base64.b64encode(f"{sid}:{auth}".encode()).decode(),
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            ok = resp.status == 201
        if ok:
            logger.info("Twilio call initiated to %s", phone)
        return ok
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace").strip()[:500]
        except Exception:
            pass
        logger.warning("Twilio call failed: %s — %s", e, body or "(no body)")
        return False
    except Exception as e:
        logger.warning("Twilio call failed: %s", e)
        return False
