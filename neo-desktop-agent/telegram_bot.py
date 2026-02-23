"""
Bot de Telegram para NEO Desktop Agent.
Acepta texto, documentos (PDF, DOCX…), fotos y notas de voz: los guarda y el agente puede
analizarlos, transcribir, resumir, etc. Respuesta con el resultado.
"""
import asyncio
import json
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("neo_desktop.telegram")

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"
DOWNLOADS_DIR = Path(__file__).resolve().parent / "downloads"
MAX_MESSAGE_LENGTH = 4000

# Extensiones por tipo de Telegram
VOICE_EXT = ".ogg"
AUDIO_EXT = ".m4a"
PHOTO_EXT = ".jpg"
DOC_EXT = ".bin"


def _load_config() -> dict:
    if not CONFIG_PATH.is_file():
        return {}
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _run_agent_sync(task: str, session_id: str | None = None):
    """Ejecuta el agente (para llamarlo desde async). session_id: ej. chat_id para memoria y sesión JSONL."""
    from agent import run_agent
    try:
        result = run_agent(
            task,
            auto_confirm=True,
            return_history=True,
            session_id=session_id,
            include_session_context=True,
        )
        if result is None:
            return ("(sin resultado)", [])
        return result
    finally:
        # Cerrar navegador en el mismo hilo que lo usó (evita "Cannot switch to a different thread")
        try:
            from desktop_control import close_browser_if_open
            close_browser_if_open()
        except Exception:
            pass


def _extract_content_from_history(history: list) -> str:
    """Extrae el contenido más sustancioso del historial (BROWSER:content, texto de páginas, etc.)."""
    best = ""
    for h in history:
        out = (h.get("out") or "").strip()
        cmd = (h.get("cmd") or "").lower()
        # Texto largo que parezca contenido (noticias, artículos), no salida de comandos
        if len(out) > 150 and ("browser:content" in cmd or "content" in out[:100]):
            # Preferir el más largo que parezca texto de artículo
            if len(out) > len(best) and not out.startswith("[exit") and "\n" in out:
                best = out
        if "script" in cmd and len(out) > 200 and not out.startswith("[exit"):
            if len(out) > len(best):
                best = out
    return best[:3500].strip() if best else ""


def send_document_to_telegram(chat_id: str, file_path: str | Path, token: str, caption: str = "") -> bool:
    """
    Envía un archivo local (ej. PDF) por Telegram al chat_id.
    Útil para que el agente o un test envíe documentos generados.
    """
    import urllib.request
    path = Path(file_path)
    if not path.is_file():
        logger.warning("send_document: archivo no existe %s", path)
        return False
    try:
        with open(path, "rb") as f:
            file_bytes = f.read()
        boundary = "----NEODocBoundary"
        filename = path.name
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{chat_id}\r\n'
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="document"; filename="{filename}"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n"
        ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendDocument",
            data=body,
            method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            ok = resp.status == 200
        if ok and caption:
            # Opcional: enviar caption en un mensaje aparte si se necesita
            pass
        return ok
    except Exception as e:
        logger.warning("send_document failed: %s", e)
        return False


def _format_reply(done_message: str, history: list) -> str:
    """Formatea el resultado para Telegram: solo lo que el usuario pidió (el DONE), sin listar pasos ni contenido largo."""
    done_message = (done_message or "").strip()
    if not done_message:
        done_message = "Listo."
    text = "✅ " + done_message
    if len(text) > MAX_MESSAGE_LENGTH:
        text = text[:MAX_MESSAGE_LENGTH - 50] + "\n… (recortado)"
    return text


async def _download_file(bot, file_id: str, dest_path: Path) -> bool:
    """Descarga el archivo de Telegram a dest_path."""
    try:
        f = await bot.get_file(file_id)
        await f.download_to_drive(dest_path)
        return dest_path.is_file()
    except Exception as e:
        logger.warning("Descarga fallida: %s", e)
        return False


def _build_task_for_file(local_path: str, file_kind: str, caption: str) -> str:
    """Construye la tarea que se pasa al agente cuando el usuario envía un archivo."""
    path_abs = str(Path(local_path).resolve())
    default = (
        "Transcribe el audio y dame un resumen." if file_kind in ("voice", "audio") else
        "Extrae el texto del documento y dame un resumen." if file_kind == "document" else
        "Describe la imagen y si tiene texto extraelo (OCR) y resúmelo."
    )
    task = (caption or default).strip()
    return (
        f"El usuario ha enviado un archivo por Telegram. Ruta local en el portátil: {path_abs}. "
        f"Tipo: {file_kind}. "
        f"Tarea que pide el usuario: {task}"
    )


async def handle_message(update, context) -> None:
    """Procesa texto o archivo (documento, voz, foto): ejecuta el agente y responde."""
    config = _load_config()
    allowed = config.get("telegram_allowed_user_ids") or []
    user_id = update.effective_user.id if update.effective_user else 0

    if allowed and user_id not in allowed:
        await update.message.reply_text("No autorizado. Tu user_id no está en la lista.")
        return

    task = (update.message.text or "").strip()
    chat_id = update.effective_chat.id
    bot = context.bot

    # Documento adjunto
    doc = update.message.document
    if doc:
        DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
        ext = Path(doc.file_name or "").suffix or DOC_EXT
        dest = DOWNLOADS_DIR / f"doc_{chat_id}_{doc.file_unique_id}{ext}"
        await update.message.reply_text("📎 Descargando documento…")
        if await _download_file(bot, doc.file_id, dest):
            task = _build_task_for_file(str(dest), "document", update.message.caption or "")
        else:
            await update.message.reply_text("❌ No se pudo descargar el archivo.")
            return

    # Nota de voz
    voice = update.message.voice
    if voice and not task:
        DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
        dest = DOWNLOADS_DIR / f"voice_{chat_id}_{voice.file_unique_id}{VOICE_EXT}"
        await update.message.reply_text("🎤 Descargando nota de voz…")
        if await _download_file(bot, voice.file_id, dest):
            task = _build_task_for_file(str(dest), "voice", update.message.caption or "")
        else:
            await update.message.reply_text("❌ No se pudo descargar el audio.")
            return

    # Audio (archivo de audio)
    audio = getattr(update.message, "audio", None)
    if audio and not task:
        DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
        dest = DOWNLOADS_DIR / f"audio_{chat_id}_{audio.file_unique_id}{AUDIO_EXT}"
        await update.message.reply_text("🔊 Descargando audio…")
        if await _download_file(bot, audio.file_id, dest):
            task = _build_task_for_file(str(dest), "audio", update.message.caption or "")
        else:
            await update.message.reply_text("❌ No se pudo descargar el audio.")
            return

    # Foto
    photo = update.message.photo
    if photo and not task:
        DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
        # Mayor resolución (último de la lista)
        largest = photo[-1]
        dest = DOWNLOADS_DIR / f"photo_{chat_id}_{largest.file_unique_id}{PHOTO_EXT}"
        await update.message.reply_text("🖼 Descargando imagen…")
        if await _download_file(bot, largest.file_id, dest):
            task = _build_task_for_file(str(dest), "photo", update.message.caption or "")
        else:
            await update.message.reply_text("❌ No se pudo descargar la imagen.")
            return

    if not task:
        await update.message.reply_text(
            "Escribe la tarea o envía un documento, nota de voz o foto y opcionalmente escribe qué quieres (resumen, transcripción, etc.)."
        )
        return

    await bot.send_message(chat_id=chat_id, text=f"🔄 Ejecutando: «{task[:100]}»…")

    loop = asyncio.get_event_loop()
    try:
        done_msg, history = await loop.run_in_executor(
            None,
            lambda: _run_agent_sync(task, session_id=str(chat_id)),
        )
        reply = _format_reply(done_msg, history)
        await update.message.reply_text(reply)
    except Exception as e:
        logger.exception("Error en agente: %s", e)
        await update.message.reply_text(f"❌ Error: {str(e)[:500]}")


async def cmd_start(update, context) -> None:
    await update.message.reply_text(
        "Soy el bot de NEO Desktop Agent. Puedes:\n"
        "• Escribir una tarea (ej: lista el Escritorio, abre Chrome y busca X).\n"
        "• Enviar un documento (PDF, DOCX…) y pedir resumen o extracción.\n"
        "• Enviar una nota de voz o audio y pedir transcripción o resumen.\n"
        "• Enviar una foto y pedir descripción o OCR.\n"
        "Ejemplo: envía un PDF y escribe «resume este documento»."
    )


def main() -> None:
    try:
        from telegram import Update
        from telegram.ext import Application, CommandHandler, MessageHandler, filters
    except ImportError:
        print("Instala: pip install python-telegram-bot")
        return

    config = _load_config()
    token = config.get("telegram_bot_token") or ""
    if not token:
        print("Añade telegram_bot_token en config.json (crea un bot con @BotFather en Telegram).")
        return

    app = Application.builder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_message))
    app.add_handler(MessageHandler(filters.AUDIO, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_message))
    app.add_handler(CommandHandler("start", cmd_start))

    # Arrancar proactivo, heartbeat, cron, recordatorios (si están en config)
    try:
        from scheduler import start_background
        start_background()
    except Exception as e:
        logger.warning("Scheduler no iniciado (no habrá proactividad/cron hasta reiniciar): %s", e)
    logger.info("Bot de Telegram iniciado. Envíale un mensaje con la tarea.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
