"""
Recordatorios: guardar (texto, fecha/hora, chat_id) y avisar por Telegram a la hora.
Fichero: workspace/recordatorios.json
"""
import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger("neo_desktop.reminders")

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}
DIAS_SEMANA = {
    "lunes": 0, "martes": 1, "miercoles": 2, "miércoles": 2, "jueves": 3, "viernes": 4,
    "sabado": 5, "sábado": 5, "domingo": 6,
}


def _get_path(workspace_dir: Path) -> Path:
    return workspace_dir / "recordatorios.json"


def _load(workspace_dir: Path) -> list:
    p = _get_path(workspace_dir)
    if not p.is_file():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(workspace_dir: Path, data: list) -> None:
    _get_path(workspace_dir).parent.mkdir(parents=True, exist_ok=True)
    _get_path(workspace_dir).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def add_reminder(workspace_dir: Path, text: str, at: datetime, chat_id: str = "") -> None:
    at_iso = at.strftime("%Y-%m-%dT%H:%M:%S")
    data = _load(workspace_dir)
    data.append({"text": text[:500], "at": at_iso, "chat_id": str(chat_id or "")})
    _save(workspace_dir, data)
    logger.info("Recordatorio guardado: %s a las %s", text[:50], at_iso)


def parse_fecha_hora(texto: str) -> tuple[datetime | None, str]:
    """
    Parsea fecha/hora en español del texto del recordatorio.
    Retorna (datetime en hora local, título_limpio) o (None, título_original).
    Ej: "comprar pan mañana a las 10" -> (mañana 10:00, "comprar pan")
    """
    from datetime import date
    texto = (texto or "").strip()
    tl = texto.lower()
    now = datetime.now()
    today = now.date()
    target_date = today
    hour, minute = 9, 0

    # Hora: "a las 10", "a las 10:30", "a las 9 y media"
    time_match = re.search(r"a\s+las\s+(\d{1,2})(?::(\d{2}))?(?:\s*y\s+media)?", tl)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2)) if time_match.group(2) else 0
        if "y media" in tl[time_match.start():time_match.end() + 10]:
            minute = 30
        hour = min(23, max(0, hour))
        minute = min(59, max(0, minute))

    # Fecha
    if "mañana" in tl and "pasado" not in tl:
        target_date = today + timedelta(days=1)
    elif "pasado mañana" in tl or "pasado manana" in tl:
        target_date = today + timedelta(days=2)
    else:
        # "próximo martes", "el martes", "el próximo lunes"
        for day_name, wday in DIAS_SEMANA.items():
            if f"proximo {day_name}" in tl or f"próximo {day_name}" in tl or f"el {day_name}" in tl:
                days_ahead = (wday - now.weekday()) % 7
                if days_ahead == 0:
                    days_ahead = 7
                target_date = today + timedelta(days=days_ahead)
                break
        else:
            # "el día 23", "el 23", "23 de febrero", "el 23 de febrero"
            for mes_nom, mes_num in MESES.items():
                m = re.search(rf"(?:el\s+)?(\d{{1,2}})\s+de\s+{mes_nom}", tl)
                if m:
                    day = int(m.group(1))
                    try:
                        target_date = date(now.year, mes_num, day)
                        if target_date < today:
                            target_date = date(now.year + 1, mes_num, day)
                    except ValueError:
                        pass
                    break
            else:
                m = re.search(r"el\s+(?:día\s+)?(\d{1,2})(?:\s+de\s+(?:febrero|enero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre))?", tl)
                if m:
                    day = int(m.group(1))
                    try:
                        target_date = date(now.year, now.month, day)
                        if target_date < today:
                            target_date = date(now.year, now.month + 1, day) if now.month < 12 else date(now.year + 1, 1, day)
                    except ValueError:
                        target_date = today + timedelta(days=1)

    try:
        at = datetime(target_date.year, target_date.month, target_date.day, hour, minute, 0)
        if at <= now:
            at = at + timedelta(days=1)
    except Exception:
        return (None, texto)

    # Limpiar el título: quitar la parte de fecha/hora
    title = texto
    for pattern in [
        r"\s*en\s+\d+\s*minutos?\s*",
        r"\s*mañana\s*",
        r"\s*pasado\s+mañana\s*",
        r"\s*el\s+(?:próximo\s+)?(?:lunes|martes|miércoles|jueves|viernes|sábado|domingo)\s*",
        r"\s*el\s+(?:día\s+)?\d{1,2}(?:\s+de\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre))?\s*",
        r"\s*a\s+las\s+\d{1,2}(?::\d{2})?(?:\s*y\s+media)?\s*",
    ]:
        title = re.sub(pattern, " ", title, flags=re.I).strip()
    title = re.sub(r"\s+", " ", title).strip() or texto

    return (at, title)


def process_due_reminders(workspace_dir: Path, send_telegram_fn) -> int:
    """
    Comprueba recordatorios vencidos, envía Telegram y los elimina.
    send_telegram_fn(chat_id, text) -> bool
    Retorna cuántos se enviaron.
    """
    data = _load(workspace_dir)
    if not data:
        return 0
    now = datetime.now()
    remaining = []
    sent = 0
    for item in data:
        try:
            at = datetime.strptime(item["at"], "%Y-%m-%dT%H:%M:%S")
        except Exception:
            remaining.append(item)
            continue
        if at <= now:
            chat_id = (item.get("chat_id") or "").strip()
            text = (item.get("text") or "").strip()
            if chat_id and send_telegram_fn(chat_id, f"⏰ Recordatorio: {text}"):
                sent += 1
                logger.info("Recordatorio enviado por Telegram: %s", text[:50])
        else:
            remaining.append(item)
    if sent:
        _save(workspace_dir, remaining)
    return sent
