# Historia de la Magia: una página por día con un mago distinto del mundo (foto con Gemini, biografía).
# Los primeros magos vienen de magos.json; cuando se acaban, se descubren nuevos con Ollama y la foto se genera con la API Gemini del libro.
# Uso: SKILL:magia_historia inicio | añadir | hoy
DESCRIPTION = "Cada día un mago: página de historia de la magia con biografía, foto (Gemini) y datos. Uso: SKILL:magia_historia inicio | añadir | hoy"

import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

def _agent_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _load_config() -> dict:
    config_path = _agent_root() / "config.json"
    if not config_path.is_file():
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _slug(s: str, max_len: int = 40) -> str:
    s = re.sub(r"[^\w\s-]", "", s)[:max_len].strip().replace(" ", "_")
    return s or "mago"


def _load_magos() -> list:
    base = Path(__file__).resolve().parent
    path = base / "magos.json"
    if not path.is_file():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_descubiertos(out_dir: Path) -> list:
    path = out_dir / "magos_descubiertos.json"
    if not path.is_file():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_descubiertos(out_dir: Path, lista: list) -> None:
    path = out_dir / "magos_descubiertos.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=2)


def _normalize_mago(m: dict) -> dict:
    """Asegura que un mago (de magos.json o descubierto por Ollama) tenga todas las claves necesarias."""
    return {
        "nombre": (m.get("nombre") or "Mago").strip(),
        "pais": (m.get("pais") or "").strip(),
        "pais_codigo": (m.get("pais_codigo") or "")[:2].upper() or "XX",
        "nacimiento": str(m.get("nacimiento") or "").strip(),
        "fallecimiento": m.get("fallecimiento"),
        "ciudad_nacimiento": (m.get("ciudad_nacimiento") or "").strip(),
        "bio_corta": (m.get("bio_corta") or "").strip() or "Mago destacado.",
        "bio_larga": (m.get("bio_larga") or m.get("bio_corta") or "").strip() or "Sin biografía detallada.",
        "aportaciones": [x for x in (m.get("aportaciones") or []) if isinstance(x, str) and x.strip()][:6],
        "curiosidades": [x for x in (m.get("curiosidades") or []) if isinstance(x, str) and x.strip()][:5],
        "frase_celebre": (m.get("frase_celebre") or "").strip() or None,
        "legado": (m.get("legado") or "").strip() or None,
        "especialidad": (m.get("especialidad") or "").strip() or None,
        "foto": (m.get("foto") or "").strip() or "",
    }


def _fetch_nuevo_mago_ollama(used_names: list, config: dict) -> dict | None:
    """Pide a Ollama un mago famoso REAL que no esté en used_names. Devuelve dict normalizado o None."""
    url = (config.get("ollama_url") or "http://localhost:11434/api/generate").strip()
    model = config.get("model") or "qwen2.5:7b-instruct"
    lista_str = ", ".join(used_names[-50:]) if used_names else "(ninguno)"
    prompt = f"""Eres un experto en historia de la magia. Devuelve ÚNICAMENTE un JSON válido, sin markdown ni explicación.
Un mago o mentalista famoso REAL que NO sea ninguno de: {lista_str}.
El JSON debe tener exactamente estas claves con MUCHA información:
- "nombre": nombre artístico completo
- "pais": país o países (ej. "Estados Unidos", "España")
- "pais_codigo": 2 letras (US, ES, FR...)
- "nacimiento": año (número)
- "fallecimiento": año o null si sigue vivo
- "ciudad_nacimiento": ciudad
- "bio_corta": 1-2 frases resumen
- "bio_larga": 2 o 3 párrafos detallados (vida, carrera, obras, anécdotas). Sé generoso con los datos.
- "aportaciones": array de 4-5 strings (trucos, libros, influencia, premios)
- "curiosidades": array de 3-4 strings (datos sorprendentes, anécdotas)
- "frase_celebre": cita famosa del mago o sobre él (string; si no conoces una, inventa una coherente con su estilo)
- "legado": 2-3 frases sobre su influencia en la magia y la cultura
- "especialidad": una palabra o dos (Escapismo, Cartomagia, Mentalismo, Ilusionismo, etc.)
Usa datos reales. Cuanta más información, mejor."""
    body = json.dumps({"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.4, "num_predict": 2200}})
    try:
        req = urllib.request.Request(url, data=body.encode("utf-8"), method="POST", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=90) as resp:
            out = json.loads(resp.read().decode("utf-8"))
        raw = (out.get("response") or "").strip()
        # Quitar posible markdown
        if raw.startswith("```"):
            raw = re.sub(r"^```\w*\n?", "", raw)
            raw = re.sub(r"\n?```\s*$", "", raw)
        data = json.loads(raw)
        return _normalize_mago(data) if isinstance(data, dict) and data.get("nombre") else None
    except Exception:
        return None


def _fetch_wikipedia_photo(nombre: str) -> str | None:
    """Obtiene la URL de la imagen principal del artículo de Wikipedia del mago (fallback cuando Gemini no está)."""
    if not (nombre or nombre.strip()):
        return None
    try:
        search_url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query", "list": "search", "srsearch": nombre.strip(), "format": "json", "srlimit": 1
        })
        req = urllib.request.Request(search_url, headers={"User-Agent": "NEO-magia-historia/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        hits = (data.get("query") or {}).get("search") or []
        if not hits:
            return None
        page_id = hits[0].get("pageid")
        if not page_id:
            return None
        img_url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query", "pageids": page_id, "prop": "pageimages", "format": "json", "pithumbsize": 500
        })
        req2 = urllib.request.Request(img_url, headers={"User-Agent": "NEO-magia-historia/1.0"})
        with urllib.request.urlopen(req2, timeout=10) as r2:
            img_data = json.loads(r2.read().decode("utf-8"))
        pages = (img_data.get("query") or {}).get("pages") or {}
        thumb = (pages.get(str(page_id)) or {}).get("thumbnail") or {}
        src = thumb.get("source")
        return (src if isinstance(src, str) and src.startswith("http") else None)
    except Exception:
        return None


def _placeholder_photo_url(nombre: str) -> str:
    """URL de placeholder con el nombre del mago (en lugar de solo 'Magia')."""
    text = (nombre or "Mago").strip()[:25].replace(" ", "+")
    return f"https://placehold.co/400x500/1a1525/c9b8e8?text={urllib.parse.quote(text)}"


def _rasgos_mago(mago: dict) -> str:
    """Descripción corta de rasgos distintivos del mago para que la imagen sea reconocible (nombre, país, época, rasgos conocidos)."""
    nombre = mago.get("nombre", "")
    # Rasgos conocidos para magos muy famosos (retrato reconocible)
    rasgos_por_nombre = {
        "Harry Houdini": "man in early 20th century style, strong build, dark hair, intense gaze, escape artist",
        "Juan Tamariz": "Spanish man, round friendly face, often with glasses, cards in hand, Madrid magician",
        "David Copperfield": "American man, dark wavy hair, charismatic smile, 1980s-90s illusionist style",
        "Dai Vernon": "elderly man, white hair, gentle face, card magic, classic close-up magician",
        "Penn & Teller": "two men: one tall and heavy with long dark hair who talks, one short and silent with glasses; duo magicians",
        "Robert-Houdin": "French man, 19th century, formal suit, elegant posture, father of modern magic",
    }
    if nombre in rasgos_por_nombre:
        return rasgos_por_nombre[nombre]
    pais = mago.get("pais", "")
    nac = mago.get("nacimiento", "")
    esp = mago.get("especialidad", "")
    return f"famous magician from {pais}, era {nac}, {esp}, recognizable portrait"


def _ensure_mago_imagen_gemini(mago: dict, dia: int, out_dir: Path, config: dict, forzar_gemini: bool = False) -> None:
    """Genera la foto del mago con los rasgos del mago: 1) Gemini (caricatura reconocible) si hay API key, 2) placeholder con nombre.
    Si forzar_gemini=True, intenta Gemini aunque exista archivo local."""
    img_rel = f"images/mago_{dia:03d}.png"
    local = out_dir / img_rel
    nombre = mago.get("nombre", "mago")
    if local.is_file() and not forzar_gemini:
        mago["foto"] = img_rel
        return
    root = _agent_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    rasgos = _rasgos_mago(mago)
    if config.get("gemini_api_key") or __import__("os").environ.get("GEMINI_API_KEY"):
        try:
            from gemini_image import generate_image
            pais = mago.get("pais", "")
            nac = mago.get("nacimiento", "")
            # Prompt principal: nombre + rasgos distintivos para que la imagen sea del mago, no genérica
            prompt = (
                f"Friendly cartoon or editorial illustration of {nombre}, {rasgos}. "
                f"From {pais}, era {nac}. Head and shoulders, face clearly visible and recognizable, "
                "stage or curtain background, no text. The image must look like this specific magician, not a generic magician."
            )
            rel = generate_image(prompt, f"mago_{dia:03d}", out_dir, model=config.get("gemini_image_model", ""), max_retries=4)
            if not rel:
                # Fallback: mismo nombre y rasgos, prompt más corto en inglés
                prompt_short = f"Editorial portrait of {nombre}, {rasgos}. Head and shoulders, soft colors, no text."
                rel = generate_image(prompt_short, f"mago_{dia:03d}", out_dir, model=config.get("gemini_image_model", ""), max_retries=3)
            if rel:
                mago["foto"] = rel
                return
        except Exception:
            pass
    # Sin Gemini o falló: placeholder con el nombre del mago (nunca imagen genérica de otro mago)
    mago["foto"] = _placeholder_photo_url(nombre)


def _load_state(out_dir: Path) -> int:
    state_path = out_dir / "estado.json"
    if state_path.is_file():
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                d = json.load(f)
                return int(d.get("dias_publicados", 0))
        except (json.JSONDecodeError, TypeError):
            pass
    return 0


def _save_state(out_dir: Path, dias: int) -> None:
    state_path = out_dir / "estado.json"
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump({"dias_publicados": dias}, f, ensure_ascii=False, indent=2)


_CSS_MAGO = """
    * { box-sizing: border-box; margin: 0; padding: 0; }
    html { background: #0a0612; -webkit-text-size-adjust: 100%; }
    body {
      font-family: 'Source Serif 4', Georgia, serif;
      background: #0a0612;
      background-image: radial-gradient(ellipse 120% 80% at 50% -20%, rgba(120,80,180,0.15), transparent),
        radial-gradient(ellipse 60% 40% at 80% 50%, rgba(180,100,255,0.08), transparent),
        radial-gradient(ellipse 60% 40% at 20% 80%, rgba(140,80,200,0.06), transparent);
      color: #e8e4ef;
      min-height: 100vh;
      line-height: 1.7;
      font-size: 1rem;
      overflow-x: hidden;
    }
    .magic-light { position: fixed; inset: 0; pointer-events: none; z-index: 0; overflow: hidden; }
    .magic-light::before {
      content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
      background: linear-gradient(105deg, transparent 35%, rgba(200,180,255,0.06) 48%, rgba(255,250,280,0.12) 50%, rgba(200,180,255,0.06) 52%, transparent 65%);
      animation: magicBeam 6s ease-in-out infinite;
    }
    @keyframes magicBeam { 0% { transform: translateX(-25%) translateY(-25%); } 100% { transform: translateX(25%) translateY(25%); } }
    .wrap { max-width: 900px; margin: 0 auto; padding: 1rem 1rem 2rem; position: relative; z-index: 1; }
    @media (min-width: 600px) { .wrap { padding: 2rem 1.5rem; } }
    .back { display: inline-block; margin-bottom: 1rem; margin-right: 0.5rem; padding: 0.5rem 1rem; background: linear-gradient(135deg, #3d2a5c, #2a1a45); border-radius: 8px; color: #c9b8e8; text-decoration: none; border: 1px solid rgba(201,184,232,0.3); font-size: 0.95rem; transition: box-shadow 0.3s, transform 0.2s; }
    .back:hover { background: #4a3570; box-shadow: 0 0 20px rgba(201,184,232,0.3); }
    h1 { font-family: 'Cinzel', serif; font-size: clamp(1.5rem, 5vw, 2.5rem); margin-bottom: 0.25rem; color: #e8e4ef; text-shadow: 0 0 30px rgba(201,184,232,0.2); }
    .meta { font-size: 0.95rem; color: #c9b8e8; margin-bottom: 1rem; }
    .meta span { margin-right: 0.5rem; }
    .tag-especialidad { display: inline-block; font-size: 0.8rem; background: rgba(80,50,120,0.5); color: #c9b8e8; padding: 0.2rem 0.5rem; border-radius: 12px; margin-left: 0.5rem; border: 1px solid rgba(201,184,232,0.2); }
    .foto-wrap { position: relative; margin: 1rem 0; border-radius: 16px; overflow: hidden; box-shadow: 0 15px 40px rgba(0,0,0,0.5), 0 0 40px rgba(180,120,255,0.15); border: 2px solid rgba(201,184,232,0.25); }
    .foto-wrap::before { content: ''; position: absolute; inset: 0; border-radius: 14px; padding: 2px; background: linear-gradient(135deg, rgba(255,255,255,0.15), transparent 40%, transparent 60%, rgba(255,255,255,0.08)); -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0); mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0); -webkit-mask-composite: xor; mask-composite: exclude; pointer-events: none; }
    .foto { width: 100%; max-width: 100%; height: auto; max-height: 70vh; object-fit: contain; object-position: center top; display: block; vertical-align: top; }
    .bio { margin: 1.25rem 0; padding: 1.25rem; background: rgba(61,42,92,0.4); border-radius: 12px; border-left: 4px solid #9b8ab8; color: #e8e4ef; box-shadow: 0 4px 20px rgba(0,0,0,0.2); }
    .bio p { margin-bottom: 0.75rem; color: #e8e4ef; }
    .bio p:last-child { margin-bottom: 0; }
    .quote { margin: 1.5rem 0; padding: 1.25rem 1.5rem; background: linear-gradient(135deg, rgba(80,50,120,0.4), rgba(50,30,80,0.4)); border-radius: 12px; border-left: 4px solid #c9b8e8; font-style: italic; color: #e0d8f0; box-shadow: 0 4px 20px rgba(0,0,0,0.2); }
    .quote p { margin: 0; font-size: 1.05rem; }
    .legado { margin: 1rem 0; padding: 1rem 1.25rem; background: rgba(40,25,70,0.5); border-radius: 12px; border: 1px solid rgba(201,184,232,0.2); color: #d8d0f0; font-size: 0.98rem; }
    .legado strong { color: #c9b8e8; }
    h2 { font-family: 'Cinzel', serif; font-size: 1.15rem; margin: 1.75rem 0 0.5rem; color: #b8a5d8; }
    ul { padding-left: 1.25rem; margin: 0.5rem 0 1rem; color: #e8e4ef; }
    li { margin: 0.4rem 0; }
    .curiosidades { font-style: italic; color: #e0d8f0; }
    .datos-clave { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 0.75rem; margin: 1rem 0; }
    .datos-clave span { display: block; padding: 0.5rem 0.75rem; background: rgba(61,42,92,0.35); border-radius: 8px; font-size: 0.9rem; color: #e0d8f0; border: 1px solid rgba(201,184,232,0.15); }
    footer { margin-top: 2.5rem; padding-top: 1rem; border-top: 1px solid rgba(255,255,255,0.1); font-size: 0.9rem; color: #a098b8; }
"""


def _html_mago(mago: dict, dia: int, base_url: str, total_dias: int) -> str:
    nombre = mago.get("nombre", "Mago")
    pais = mago.get("pais", "")
    nac = mago.get("nacimiento", "")
    fal = mago.get("fallecimiento") or "presente"
    ciudad = mago.get("ciudad_nacimiento", "")
    bio_larga = mago.get("bio_larga", mago.get("bio_corta", ""))
    aportaciones = mago.get("aportaciones", [])
    curiosidades = mago.get("curiosidades", [])
    frase_celebre = (mago.get("frase_celebre") or "").strip()
    legado = (mago.get("legado") or "").strip()
    foto = mago.get("foto", "").strip() or _placeholder_photo_url(nombre)
    placeholder_esc = _placeholder_photo_url(nombre).replace("'", "&#39;")

    meta = f"{pais}"
    if ciudad:
        meta += f" · {ciudad}"
    meta += f" · {nac}"
    if str(fal).lower() != "presente":
        meta += f" – {fal}"

    lis_aport = "".join(f"<li>{a}</li>" for a in aportaciones)
    lis_cur = "".join(f"<li>{c}</li>" for c in curiosidades)
    bio_paras = "".join(f"<p>{p.strip()}</p>" for p in bio_larga.split("\n") if p.strip()) or f"<p>{bio_larga}</p>"

    quote_block = ""
    if frase_celebre:
        quote_block = f'<div class="quote"><p>«{frase_celebre}»</p></div>'

    legado_block = ""
    if legado:
        legado_block = f'<div class="legado"><strong>Legado:</strong> {legado}</div>'

    especialidad = (mago.get("especialidad") or "").strip()
    tag_especialidad = f'<span class="tag-especialidad">{especialidad}</span>' if especialidad else ""
    datos_clave = []
    for a in (aportaciones or [])[:3]:
        datos_clave.append(a)
    for c in (curiosidades or [])[:2]:
        datos_clave.append(c)
    datos_block = ""
    if datos_clave:
        datos_block = '<div class="datos-clave">' + "".join(f"<span>{d}</span>" for d in datos_clave[:6]) + "</div>"

    nav = ""
    if dia > 1:
        nav += f'<a class="back" href="mago_{dia-1:03d}.html">← Anterior</a> '
    nav += f'<a class="back" href="index.html">← Índice</a>'
    if dia < total_dias:
        nav += f' <a class="back" href="mago_{dia+1:03d}.html">Siguiente →</a>'

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>{nombre} · Historia de la Magia</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@500;600&family=Source+Serif+4:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
  <style>
    body {{ font-family: 'Source Serif 4', Georgia, serif; }}
    h1 {{ font-family: 'Cinzel', serif; }}
    {_CSS_MAGO}
  </style>
</head>
<body>
  <div class="magic-light" aria-hidden="true"></div>
  <div class="wrap">
    <nav>{nav}</nav>
    <h1>{nombre}</h1>
    <p class="meta"><span>{meta}</span>{tag_especialidad}</p>
    <div class="foto-wrap">
      <img class="foto" src="{foto}" alt="{nombre}" loading="lazy" onerror="this.src='{placeholder_esc}'">
    </div>
    {quote_block}
    <div class="bio">
      {bio_paras}
    </div>
    {legado_block}
    {datos_block}
    <h2>Aportaciones a la magia</h2>
    <ul>{lis_aport}</ul>
    <h2>Curiosidades</h2>
    <ul class="curiosidades">{lis_cur}</ul>
    <footer>Día {dia} · Historia de la Magia · Creado con NEO</footer>
  </div>
</body>
</html>"""


def _html_index(magos_mostrados: list, out_dir: Path) -> str:
    titulo = "Historia de la Magia"
    items = []
    for i, m in enumerate(magos_mostrados, 1):
        nombre = m.get("nombre", "Mago")
        pais = m.get("pais", "")
        especialidad = (m.get("especialidad") or "").strip()
        bio_corta = m.get("bio_corta", "")[:140] + "…" if len(m.get("bio_corta", "")) > 140 else (m.get("bio_corta", ""))
        slug = f"mago_{i:03d}.html"
        foto = m.get("foto") or ""
        fallback = _placeholder_photo_url(nombre).replace("'", "&#39;")
        img_tag = f'<img class="card-img" src="{foto}" alt="{nombre}" loading="lazy" onerror="this.src=\'{fallback}\'">' if foto else f'<img class="card-img" src="{fallback}" alt="{nombre}" loading="lazy">'
        tag_especialidad = f'<span class="card-tag">{especialidad}</span>' if especialidad else ""
        items.append(f"""
    <article class="card">
      <a href="{slug}">
        <div class="card-img-wrap">{img_tag}</div>
        {tag_especialidad}
        <h3>{nombre}</h3>
        <p class="pais">{pais}</p>
        <p class="resumen">{bio_corta}</p>
      </a>
    </article>""")

    cards = "\n".join(items)
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>{titulo} · Un mago cada día</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@500;700&family=Source+Serif+4:wght@400;600&display=swap" rel="stylesheet">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html {{ background: #0a0612; -webkit-text-size-adjust: 100%; }}
    body {{
      font-family: 'Source Serif 4', Georgia, serif;
      background: #0a0612;
      background-image: radial-gradient(ellipse 100% 60% at 50% -10%, rgba(100,60,160,0.2), transparent 50%),
        radial-gradient(ellipse 80% 50% at 90% 20%, rgba(140,80,200,0.1), transparent 45%),
        radial-gradient(ellipse 80% 50% at 10% 80%, rgba(120,60,180,0.1), transparent 45%);
      color: #e8e4ef;
      min-height: 100vh;
      padding: 1rem 1rem 2rem;
      overflow-x: hidden;
    }}
    @media (min-width: 600px) {{ body {{ padding: 2rem 1.5rem; }} }}
    .wrap {{ max-width: 1000px; margin: 0 auto; position: relative; }}
    .magic-bg {{ position: fixed; inset: 0; pointer-events: none; overflow: hidden; z-index: 0; }}
    .magic-bg span {{ position: absolute; width: 4px; height: 4px; background: rgba(255,255,255,0.4); border-radius: 50%; animation: sparkle 4s ease-in-out infinite; }}
    .magic-bg span:nth-child(1) {{ left: 10%; top: 20%; animation-delay: 0s; }}
    .magic-bg span:nth-child(2) {{ left: 25%; top: 60%; animation-delay: 0.8s; }}
    .magic-bg span:nth-child(3) {{ left: 60%; top: 15%; animation-delay: 1.6s; }}
    .magic-bg span:nth-child(4) {{ left: 80%; top: 50%; animation-delay: 2.4s; }}
    .magic-bg span:nth-child(5) {{ left: 40%; top: 80%; animation-delay: 0.4s; }}
    .magic-bg span:nth-child(6) {{ left: 70%; top: 35%; animation-delay: 1.2s; }}
    @keyframes sparkle {{ 0%, 100% {{ opacity: 0.3; transform: scale(0.8); }} 50% {{ opacity: 0.9; transform: scale(1.2); }} }}
    .magic-light {{ position: fixed; inset: 0; pointer-events: none; z-index: 0; overflow: hidden; }}
    .magic-light::before {{
      content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
      background: linear-gradient(105deg, transparent 35%, rgba(200,180,255,0.07) 48%, rgba(255,250,280,0.14) 50%, rgba(200,180,255,0.07) 52%, transparent 65%);
      animation: magicBeam 6s ease-in-out infinite;
    }}
    @keyframes magicBeam {{ 0% {{ transform: translateX(-25%) translateY(-25%); }} 100% {{ transform: translateX(25%) translateY(25%); }} }}
    .wrap > * {{ position: relative; z-index: 1; }}
    h1 {{
      font-family: 'Cinzel', serif;
      font-size: clamp(1.75rem, 5vw, 3rem);
      text-align: center;
      margin-bottom: 0.5rem;
      color: #e8e4ef;
      text-shadow: 0 0 40px rgba(201,184,232,0.25);
    }}
    .sub {{
      text-align: center;
      color: #c9b8e8;
      margin-bottom: 1.5rem;
      font-size: 1rem;
    }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1.25rem; }}
    @media (min-width: 600px) {{ .grid {{ gap: 1.5rem; }} }}
    .card {{
      background: linear-gradient(160deg, rgba(61,42,92,0.5), rgba(40,25,70,0.5));
      border-radius: 20px;
      padding: 1.25rem;
      border: 1px solid rgba(201,184,232,0.25);
      transition: transform 0.25s, box-shadow 0.25s, border-color 0.25s;
      box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }}
    .card:hover {{
      transform: translateY(-4px);
      box-shadow: 0 12px 40px rgba(0,0,0,0.4), 0 0 30px rgba(180,120,255,0.2);
      border-color: rgba(201,184,232,0.45);
    }}
    .card a {{ text-decoration: none; color: inherit; display: block; }}
    .card-img-wrap {{
      position: relative;
      border-radius: 14px;
      overflow: hidden;
      margin-bottom: 0.75rem;
      box-shadow: 0 6px 20px rgba(0,0,0,0.4);
    }}
    .card-img-wrap::after {{
      content: '';
      position: absolute;
      inset: 0;
      border-radius: 14px;
      box-shadow: inset 0 0 30px rgba(180,120,255,0.08);
      pointer-events: none;
    }}
    .card-img {{
      width: 100%;
      height: 200px;
      object-fit: cover;
      object-position: center 25%;
      display: block;
      vertical-align: top;
    }}
    .card-tag {{
      display: inline-block;
      font-size: 0.75rem;
      color: #c9b8e8;
      background: rgba(80,50,120,0.5);
      padding: 0.25rem 0.6rem;
      border-radius: 20px;
      margin-bottom: 0.5rem;
      border: 1px solid rgba(201,184,232,0.2);
    }}
    .card h3 {{ font-family: 'Cinzel', serif; font-size: 1.15rem; margin-bottom: 0.3rem; color: #e8e4ef; }}
    .card .pais {{ font-size: 0.85rem; color: #b8a5d8; margin-bottom: 0.4rem; }}
    .card .resumen {{ font-size: 0.9rem; line-height: 1.5; color: #e0d8f0; }}
    footer {{ text-align: center; margin-top: 2rem; font-size: 0.85rem; color: #a098b8; }}
  </style>
</head>
<body>
  <div class="magic-bg"><span></span><span></span><span></span><span></span><span></span><span></span></div>
  <div class="magic-light" aria-hidden="true"></div>
  <div class="wrap">
    <h1>✨ {titulo} ✨</h1>
    <p class="sub">Un mago cada día · Biografías, fotos y datos de magos de todo el mundo</p>
    <div class="grid">
{cards}
    </div>
    <footer>{len(magos_mostrados)} magos · Creado con NEO</footer>
  </div>
</body>
</html>"""


def run(task: str = "", **kwargs) -> str:
    task_raw = (task or "inicio").strip().lower()
    task = task_raw
    if not any(x in task for x in ("inicio", "añadir", "add", "hoy", "siguiente", "nuevo", "regenerar")):
        task = "inicio"

    base = Path(__file__).resolve().parent.parent
    out_dir = base / "output" / "magia_historia"
    out_dir.mkdir(parents=True, exist_ok=True)
    config = _load_config()

    base_magos = _load_magos()
    if not base_magos:
        return "Error: No se encontró magos.json en la carpeta del skill."
    descubiertos = _load_descubiertos(out_dir)
    magos_combined = base_magos + descubiertos

    dias = _load_state(out_dir)

    if "añadir" in task or "add" in task or "hoy" in task or "siguiente" in task or "nuevo" in task:
        need = dias + 1
        while len(magos_combined) < need:
            used_names = [m.get("nombre", "") for m in magos_combined]
            nuevo = _fetch_nuevo_mago_ollama(used_names, config)
            if nuevo and nuevo.get("nombre"):
                descubiertos.append(nuevo)
                magos_combined = base_magos + descubiertos
                _save_descubiertos(out_dir, descubiertos)
            else:
                break
        if len(magos_combined) < need:
            return (
                f"No se pudo descubrir un mago nuevo (Ollama no respondió). "
                f"Hay {len(magos_combined)} magos. Carpeta: {out_dir}. Comprueba que Ollama esté en marcha."
            )
        dias = need
        _save_state(out_dir, dias)
    else:
        if dias == 0:
            dias = 1
            _save_state(out_dir, dias)

    magos_mostrados = magos_combined[:dias]
    forzar_gemini = any(x in task_raw for x in ("regenerar", "caricaturas", "actualizar imagen", "gemini"))

    # Asegurar imagen: Gemini (caricatura) si hay API key, si no Wikipedia o placeholder
    for dia, mago in enumerate(magos_mostrados, 1):
        _ensure_mago_imagen_gemini(mago, dia, out_dir, config, forzar_gemini=forzar_gemini)

    # Regenerar índice y todas las páginas
    index_html = _html_index(magos_mostrados, out_dir)
    (out_dir / "index.html").write_text(index_html, encoding="utf-8")

    for dia, mago in enumerate(magos_mostrados, 1):
        html = _html_mago(mago, dia, "", len(magos_mostrados))
        (out_dir / f"mago_{dia:03d}.html").write_text(html, encoding="utf-8")

    return (
        f"Historia de la Magia actualizada: {len(magos_mostrados)} magos. Carpeta: {out_dir}. "
        f"Para publicar: GITHUB:push y DONE con la URL de GitHub Pages."
    )
