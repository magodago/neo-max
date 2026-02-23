"""
Genera capítulos de un serial con Ollama. Mantiene contexto (personajes, resúmenes, último capítulo)
y calidad de escritura profesional. Un capítulo nuevo cada día.
"""
import json
import logging
import re
import urllib.request
from pathlib import Path

from serial_state import (
    append_chapter,
    get_context_for_next_chapter,
    load_state,
    save_state,
    start_new_serial,
)

logger = logging.getLogger("stories_agent")

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:7b-instruct"
TIMEOUT = 600  # 10 min: capítulos largos (2800 tokens) pueden tardar en CPU/GPU lenta
MAX_CONTEXT_CHARS = 8000
NUM_PREDICT_CHAPTER = 2800


def _load_config() -> dict:
    config_path = Path(__file__).resolve().parent / "config.json"
    if not config_path.is_file():
        return {}
    return json.loads(config_path.read_text(encoding="utf-8"))


def _call_ollama(prompt: str, num_predict: int = 800, timeout: int | None = None) -> str | None:
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": num_predict},
    }
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t = timeout if timeout is not None else TIMEOUT
    try:
        with urllib.request.urlopen(req, timeout=t) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return (data.get("response") or "").strip()
    except Exception as e:
        logger.warning("Ollama request failed: %s", e)
        return None


def _parse_blocks(raw: str, block_names: list[str]) -> dict:
    """Parsea bloques con ===NAME=== o ### NAME ### (el modelo a veces devuelve ###)."""
    markers_triple = [f"==={n.upper().replace(' ', '_')}===" for n in block_names]
    markers_hash = [f"###{n.upper().replace(' ', '_')}###" for n in block_names]
    markers_hash_spaced = [f"### {n.upper().replace(' ', '_')} ###" for n in block_names]
    all_markers = markers_triple + markers_hash + markers_hash_spaced
    out = {}
    for i, name in enumerate(block_names):
        start = -1
        marker_len = 0
        for m in (markers_triple[i], markers_hash[i], markers_hash_spaced[i]):
            pos = raw.find(m)
            if pos != -1:
                start = pos
                marker_len = len(m)
                break
        if start == -1:
            alt = f"=={block_names[i].upper().replace(' ', '_')}=="
            pos = raw.find(alt)
            if pos != -1:
                start = pos
                marker_len = len(alt)
        if start == -1:
            continue
        start += marker_len
        end = len(raw)
        for m in all_markers:
            pos = raw.find(m, start)
            if pos != -1 and pos < end:
                end = pos
        text = raw[start:end].strip()
        out[name] = text
    return out


def _sanitize_title_body_from_raw(raw_title: str, body: str) -> tuple[str, str]:
    """Si el body contiene '### TITLE ... ### BODY', extrae título y cuerpo reales."""
    if not body or "### TITLE" not in body or "### BODY" not in body:
        return raw_title, body
    m = re.search(r"#+\s*TITLE\s*(.*?)\s*#+\s*BODY\s*(.*)", body, re.DOTALL | re.IGNORECASE)
    if m:
        title_part = m.group(1).strip()
        body_part = m.group(2).strip()
        if title_part and len(title_part) < 200:
            raw_title = title_part.split("\n")[0].strip()
        if body_part and len(body_part) > 100:
            body = body_part
    return raw_title, body


def _extract_body_fallback(raw: str) -> str:
    """Si no hay ===BODY===, intentar sacar el bloque de texto más largo que contenga <p>."""
    import re
    # Buscar entre TITLE y IMAGE_PROMPT o SUMMARY
    for start_m in ["===TITLE===", "===BODY==="]:
        idx = raw.find(start_m)
        if idx == -1:
            continue
        idx = raw.find("\n", idx) + 1
        if idx <= 0:
            continue
        for end_m in ["===IMAGE_PROMPT===", "===SUMMARY===", "==="]:
            end_idx = raw.find(end_m, idx)
            if end_idx > idx:
                block = raw[idx:end_idx].strip()
                if len(block) > 200 and ("<p>" in block or "\n\n" in block):
                    return block
    # Último recurso: trozo más largo que tenga <p>
    chunks = re.split(r"\n\s*===?\w+===?\s*\n", raw)
    for c in chunks:
        c = c.strip()
        if len(c) > 300 and "<p>" in c:
            return c
    return ""


def generate_first_chapter() -> dict | None:
    """Genera el primer capítulo y el título del serial. Crea estado nuevo. Todo en español, género adulto, capítulo largo."""
    config = _load_config()
    niche = config.get("niche", "misterio e intriga para adultos, estilo bestseller")
    genre = config.get("genre", "mystery")
    theme = config.get("serial_theme", "thriller")
    max_words = config.get("story_max_words", 1200)

    prompt = f"""Eres un novelista profesional. Crea el PRIMER capítulo de una serie que se publica un capítulo al día. Público adulto: {niche}.

Género: {genre}. Tema de la serie: misterio y/o terror. El título de la serie DEBE reflejar misterio o terror (nada de gatos, nada tierno, nada infantil).
Escribe TODO en español. Prosa cuidada, atmósfera inquietante, personajes claros. Este primer capítulo debe enganchar desde el inicio y terminar con un gancho que deje al lector con ganas de más. Extensión de capítulo de libro: entre 800 y {max_words} palabras, varias escenas, tensión o miedo. Usa <p> para cada párrafo. No más HTML.

Salida ÚNICAMENTE estos bloques, en este orden:

===SERIAL_TITLE===
(Un título atractivo para toda la serie, en español, que transmita misterio o terror. NO usar títulos de historias tiernas ni de animales.)

===CHARACTERS===
(2-4 nombres de personajes principales, separados por comas, en español)

===TITLE===
(Título del capítulo 1 con nombre descriptivo, en español. Formato: "Capítulo 1: Nombre del episodio", ej. "Capítulo 1: La Llamada Anónima". No solo "Capítulo 1".)

===BODY===
(El capítulo completo: muchos párrafos con <p>...</p>, entre 800 y {max_words} palabras. Varias escenas si hace falta.)

===IMAGE_PROMPT===
(Una frase corta en español describiendo una escena para ilustrar este capítulo. Sin texto en la imagen. Para generación de imagen.)

===SUMMARY===
(1-2 frases en español resumiendo este capítulo para continuidad.)
"""

    raw = _call_ollama(
        prompt,
        num_predict=NUM_PREDICT_CHAPTER,
        timeout=config.get("ollama_timeout"),
    )
    if not raw:
        return None

    blocks = _parse_blocks(raw, ["SERIAL_TITLE", "CHARACTERS", "TITLE", "BODY", "IMAGE_PROMPT", "SUMMARY"])
    serial_title = (blocks.get("SERIAL_TITLE") or "Serie diaria").split("\n")[0].strip()[:150]
    characters_str = (blocks.get("CHARACTERS") or "").split("\n")[0].strip()
    characters = [c.strip() for c in characters_str.split(",") if c.strip()][:5]
    raw_title = (blocks.get("TITLE") or "Capítulo 1").split("\n")[0].strip()[:200]
    body = (blocks.get("BODY") or "").strip()
    if not body:
        body = _extract_body_fallback(raw).strip()
    raw_title, body = _sanitize_title_body_from_raw(raw_title, body)
    title = raw_title
    image_prompt = (blocks.get("IMAGE_PROMPT") or "").split("\n")[0].strip()[:300] or f"Escena de la historia: {title}"
    summary = (blocks.get("SUMMARY") or "").split("\n")[0].strip()[:400]

    if not body:
        logger.warning("No BODY in first chapter response (and fallback found nothing)")
        return None
    if "<p>" not in body and body:
        body = "<p>" + body.replace("\n\n", "</p><p>") + "</p>"

    state = start_new_serial(genre=genre, theme=theme, niche=niche)
    state["serial_title"] = serial_title
    state["characters"] = characters
    append_chapter(state, title, body, summary)
    save_state(state)

    return {
        "title": title,
        "body": body,
        "prompt_for_image": image_prompt,
        "serial_title": serial_title,
        "theme": theme,
        "chapter_num": 1,
        "summary": summary,
        "is_serial": True,
    }


def generate_next_chapter(append_to_state: bool = True) -> dict | None:
    """
    Genera el siguiente capítulo con contexto completo.
    Si append_to_state=True (por defecto), lo añade a state.chapters y guarda.
    Si append_to_state=False, solo retorna el dict (para guardar como 'capítulo por delante').
    """
    state = load_state()
    if not state or not state.get("chapters"):
        return generate_first_chapter()

    config = _load_config()
    max_chapters = config.get("max_chapters_per_serial", 14)
    if len(state.get("chapters", [])) >= max_chapters:
        # Empezar nuevo serial
        return generate_first_chapter()

    max_words = config.get("story_max_words", 1200)
    context = get_context_for_next_chapter(state, max_chars=MAX_CONTEXT_CHARS)

    next_num = len(state["chapters"]) + 1
    prompt = f"""Eres un novelista profesional. Escribe el SIGUIENTE capítulo de una serie en curso. Tienes el contexto completo: resúmenes de todos los capítulos anteriores y el texto completo del último. Úsalo para mantener la continuidad, los mismos personajes y el hilo argumental.

Reglas de calidad: cada capítulo debe enganchar, tener tensión o misterio, y terminar con un gancho que deje al lector con ganas de más. Prosa cuidada. TODO en español. Público adulto.

{context}

Escribe SOLO el Capítulo {next_num}. Extensión de capítulo de libro: entre 800 y {max_words} palabras. Varios párrafos con <p>...</p>. Continúa desde el final del capítulo anterior. Salida ÚNICAMENTE estos bloques:

===TITLE===
(Título del capítulo {next_num} con nombre descriptivo, en español. Formato: "Capítulo N: Nombre del episodio", ej. "Capítulo 3: La noche del coche negro". No solo "Capítulo N".)

===BODY===
(El capítulo completo con <p>...</p>. Varias escenas si hace falta.)

===IMAGE_PROMPT===
(Una frase corta en español para una escena a ilustrar. Sin texto en la imagen.)

===SUMMARY===
(1-2 frases en español resumiendo este capítulo para continuidad.)
"""

    raw = _call_ollama(
        prompt,
        num_predict=NUM_PREDICT_CHAPTER,
        timeout=config.get("ollama_timeout"),
    )
    if not raw:
        return None

    blocks = _parse_blocks(raw, ["TITLE", "BODY", "IMAGE_PROMPT", "SUMMARY"])
    body = (blocks.get("BODY") or "").strip()
    if not body:
        body = _extract_body_fallback(raw).strip()
    raw_title = (blocks.get("TITLE") or f"Capítulo {next_num}").split("\n")[0].strip()[:200]
    raw_title, body = _sanitize_title_body_from_raw(raw_title, body)
    # Si el modelo devolvió solo "Capítulo N", usar primeras palabras del body para el menú
    if raw_title.strip().lower() in (f"capítulo {next_num}", f"capitulo {next_num}") and body:
        first_words = body.replace("<p>", " ").replace("</p>", " ").strip()[:200].strip()
        title = f"Capítulo {next_num}: {(first_words[:50] + '…') if len(first_words) > 50 else first_words}"
    else:
        title = raw_title
    image_prompt = (blocks.get("IMAGE_PROMPT") or "").split("\n")[0].strip()[:300] or f"Escena: {title}"
    summary = (blocks.get("SUMMARY") or "").split("\n")[0].strip()[:400]

    if not body:
        logger.warning("No BODY in next chapter response (and fallback found nothing)")
        return None
    if "<p>" not in body and body:
        body = "<p>" + body.replace("\n\n", "</p><p>") + "</p>"

    if append_to_state:
        append_chapter(state, title, body, summary)
        save_state(state)

    return {
        "title": title,
        "body": body,
        "prompt_for_image": image_prompt,
        "serial_title": state.get("serial_title", "Serie diaria"),
        "theme": state.get("theme", "heartwarming"),
        "chapter_num": next_num,
        "summary": summary,
        "is_serial": True,
    }


def generate_one_story(niche: str | None = None, max_words: int = 250) -> dict | None:
    """
    Genera un capítulo (serial mode) o una historia suelta (legacy).
    Retorna dict con title, body, prompt_for_image; si serial también serial_title, theme, chapter_num, is_serial.
    """
    config = _load_config()
    if config.get("serial_mode", True):
        state = load_state()
        if not state or not state.get("chapters"):
            return generate_first_chapter()
        return generate_next_chapter()

    # Legacy: una historia suelta (español, adulto)
    niche = niche or config.get("niche", "misterio o intriga para adultos")
    max_words = max_words or config.get("story_max_words", 800)
    prompt = (
        f"Escribe UNA historia (máx {max_words} palabras). Tema: {niche}. Público adulto. TODO en español. "
        "Salida ÚNICAMENTE tres bloques:\n"
        "===TITLE===\n(una línea, título en español)\n"
        "===BODY===\n(varios párrafos con <p> para cada uno)\n"
        "===IMAGE_PROMPT===\n(Una frase en español para una escena a ilustrar. Sin texto en la imagen.)"
    )
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": 500},
    }
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw = (data.get("response") or "").strip()
    except Exception as e:
        logger.warning("Ollama story failed: %s", e)
        return None
    blocks = _parse_blocks(raw, ["TITLE", "BODY", "IMAGE_PROMPT"])
    title = (blocks.get("TITLE") or "").split("\n")[0].strip()[:200]
    body = (blocks.get("BODY") or "").strip()
    image_prompt = (blocks.get("IMAGE_PROMPT") or "").split("\n")[0].strip()[:300] or f"Scene: {title}"
    if not title or not body:
        return None
    if "<p>" not in body and body:
        body = "<p>" + body.replace("\n\n", "</p><p>") + "</p>"
    return {"title": title, "body": body, "prompt_for_image": image_prompt, "is_serial": False}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    s = generate_one_story()
    if s:
        print("Title:", s["title"])
        print("Serial:", s.get("serial_title"), "Ch", s.get("chapter_num"))
        print("Body:", s["body"][:200], "...")
