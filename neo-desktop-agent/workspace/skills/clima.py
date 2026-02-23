# Clima sin API key — usa wttr.in (servicio gratuito, sin registro).
# Uso: SKILL:clima Illescas  o  SKILL:clima Madrid

DESCRIPTION = "Clima en una ciudad (sin API key). Ejemplo: SKILL:clima Illescas"


def run(task: str = "", **kwargs) -> str:
    import urllib.request
    city = (task or "").strip() or "Madrid"
    city_enc = urllib.request.quote(city)
    url = f"https://wttr.in/{city_enc}?format=%l:+%t+%C+%h+%w&T"
    req = urllib.request.Request(url, headers={"User-Agent": "curl/7.64"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            text = r.read().decode("utf-8", errors="replace").strip()
            return text or f"Sin datos para {city}"
    except Exception as e:
        return f"Error obteniendo clima para {city}: {e}"
