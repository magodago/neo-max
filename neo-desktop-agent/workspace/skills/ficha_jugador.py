# Ficha técnica de jugador (scraping Transfermarkt + HTML)
# Una sola URL/plantilla: siempre escribe en el mismo archivo (index.html) y rellena con el jugador pedido.
# Si pides otro jugador, se borra el contenido anterior y se rellena con el nuevo. Solo existe una URL.
DESCRIPTION = "Ficha tecnica de jugador de futbol (foto, datos, estadisticas). Uso: SKILL:ficha_jugador <nombre jugador>"
import re
import unicodedata
from pathlib import Path
from urllib.parse import quote

# Nombre fijo del archivo para una sola URL reutilizable (plantilla que se rellena)
FICHA_FILENAME = "index.html"

def _quitar_acentos(s: str) -> str:
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))

def _variantes_nombre(name: str):
    """Genera variantes para tolerar typos/acentos: nombre tal cual, sin acentos, apellido solo."""
    name = name.strip()
    yield name
    yield _quitar_acentos(name)
    parts = name.split()
    if len(parts) >= 2:
        yield parts[-1]
        yield _quitar_acentos(parts[-1])
    if name.lower() in ("embappe", "mbappe", "mbappé", "mbape"):
        yield "Kylian Mbappé"
        yield "Mbappe"

def run(task: str = "", **kwargs) -> str:
    task = (task or "").strip()
    if not task:
        return "Indica el nombre del jugador. Ejemplo: SKILL:ficha_jugador Mbappe"
    name_input = task.split(",")[0].strip()
    player_url = None
    html = ""
    import urllib.request
    for query in _variantes_nombre(name_input):
        if not query or len(query) < 2:
            continue
        try:
            query_encoded = quote(query.encode("utf-8").decode("utf-8"), safe="")
            url_search = f"https://www.transfermarkt.com/schnellsuche/ergebnis/schnellsuche?query={query_encoded}"
            req = urllib.request.Request(url_search, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
            with urllib.request.urlopen(req, timeout=15) as r:
                html = r.read().decode("utf-8", errors="replace")
        except Exception:
            continue
        m = re.search(r'href="(/[^"]+/profil/spieler/\d+)"', html)
        if m:
            player_url = "https://www.transfermarkt.com" + m.group(1).split('"')[0]
            break
    if not player_url:
        return f"No encontré al jugador '{name_input}' en Transfermarkt. Prueba con otro nombre o apellido (la búsqueda tolera acentos y pequeños errores)."
    try:
        req2 = urllib.request.Request(player_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        with urllib.request.urlopen(req2, timeout=15) as r2:
            page = r2.read().decode("utf-8", errors="replace")
    except Exception as e:
        return f"Error al cargar perfil: {e}"
    # Nombre para título: extraer de la página o usar input (slug en URL suele ser "nombre-apellido")
    name = name_input
    title_m = re.search(r"<title>([^<]+)</title>", page)
    if title_m:
        name = title_m.group(1).split("|")[0].strip()
    edad = re.search(r'"age":\s*(\d+)', page)
    edad = edad.group(1) if edad else ""
    altura = re.search(r'"height":\s*"([^"]+)"', page)
    altura = altura.group(1) if altura else ""
    posicion = re.search(r'"position":\s*"([^"]+)"', page)
    posicion = posicion.group(1) if posicion else ""
    club = re.search(r'"club":\s*"([^"]+)"', page)
    club = club.group(1) if club else ""
    valor = re.search(r'"marketValue":\s*"([^"]+)"', page)
    valor = valor.group(1) if valor else ""
    foto = re.search(r'<img[^>]+data-src="([^"]+)"[^>]*class="[^"]*bilderrahmen', page)
    foto_url = foto.group(1) if foto else ""
    # Una sola plantilla: siempre el mismo archivo (index.html). Se sobrescribe con cada jugador nuevo.
    out_dir = Path(__file__).resolve().parent.parent / "output" / "ficha_jugador"
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / FICHA_FILENAME
    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Ficha - {name}</title>
  <style>
    body {{ font-family: system-ui; max-width: 400px; margin: auto; padding: 1rem; }}
    h1 {{ font-size: 1.2rem; }}
    img {{ max-width: 100%; border-radius: 8px; }}
    .row {{ margin: 0.5rem 0; }}
    .label {{ font-weight: bold; color: #555; }}
  </style>
</head>
<body>
  <h1>{name}</h1>
  {f'<img src="{foto_url}" alt="{name}" />' if foto_url else ""}
  <div class="row"><span class="label">Edad:</span> {edad or "-"}</div>
  <div class="row"><span class="label">Altura:</span> {altura or "-"}</div>
  <div class="row"><span class="label">Posición:</span> {posicion or "-"}</div>
  <div class="row"><span class="label">Club:</span> {club or "-"}</div>
  <div class="row"><span class="label">Valor mercado:</span> {valor or "-"}</div>
  <p><a href="{player_url}">Ver en Transfermarkt</a></p>
</body>
</html>"""
    html_path.write_text(html_content, encoding="utf-8")
    return f"Ficha actualizada con {name} en la plantilla única: {html_path}. Carpeta generada: {html_path.parent}. Repo fijo para una sola URL: ficha-jugador. Si ya hiciste GITHUB:push antes, la misma URL mostrará ahora a este jugador. Si piden otro jugador, ejecuta de nuevo este skill y vuelve a hacer push a ficha-jugador."
