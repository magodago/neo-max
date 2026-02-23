# Hora en zona del mundo. Uso: SKILL:hora_mundo Tokyo
DESCRIPTION = "Hora actual en ciudad/zona. Ejemplo: SKILL:hora_mundo Tokyo"

def run(task: str = "", **kwargs) -> str:
    from datetime import datetime
    from zoneinfo import ZoneInfo
    tz_map = {"madrid": "Europe/Madrid", "tokyo": "Asia/Tokyo", "new york": "America/New_York", "london": "Europe/London", "paris": "Europe/Paris", "mexico": "America/Mexico_City", "local": None}
    query = (task or "").strip().lower() or "local"
    tz_name = tz_map.get(query)
    if tz_name is None and query != "local":
        try:
            ZoneInfo(query.replace(" ", "_"))
            tz_name = query.replace(" ", "_")
        except Exception:
            tz_name = "UTC"
    dt = datetime.now(ZoneInfo(tz_name)) if tz_name else datetime.now()
    tz_label = tz_name or "local"
    return dt.strftime("%Y-%m-%d %H:%M:%S") + " (" + tz_label + ")"
