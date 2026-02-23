"""
microtool_generator - Genera herramientas web funcionales con Ollama.
Sin fallback: si la IA falla se lanza OllamaGenerationError.
"""

import json
import logging
import re
import time
import urllib.request
from pathlib import Path

logger = logging.getLogger("neo_max.microtool_generator")

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:7b-instruct"
TIMEOUT_SECONDS = 300
MAX_RETRIES = 2

# Delimitadores en la respuesta (sin espacios)
MARKER_INDEX = "===INDEX==="
MARKER_STYLE = "===STYLE==="
MARKER_SCRIPT = "===SCRIPT==="


class OllamaGenerationError(Exception):
    """Se lanza cuando Ollama no devuelve código válido (timeout, parse, etc.)."""
    pass


def _build_prompt(problem: str, saas: bool = False) -> str:
    """Prompt optimizado: solo código, sin explicaciones ni markdown. Si saas=True, orientado a métricas SaaS."""
    base = f"""Herramienta web que resuelve: {problem}

REGLAS:
- SOLO código. SIN explicaciones. SIN markdown. SIN ```html ni ```.
- HTML + CSS + JS puro. Sin frameworks. Sin CDN.
- Respuesta BREVE. Máximo 300 líneas en total.
- Usa EXACTAMENTE estos marcadores para separar los tres bloques:

{MARKER_INDEX}
(contenido HTML completo aquí)

{MARKER_STYLE}
(contenido CSS completo aquí)

{MARKER_SCRIPT}
(contenido JavaScript completo aquí)
"""
    if saas:
        base = f"""Calculadora SaaS / métricas de startup: {problem}
- INTERFAZ EN ESPAÑOL: etiquetas de campos, botón "Calcular", mensajes y resultado en español.
- Fórmula correcta para la métrica: p. ej. CAC = coste total adquisición / número de clientes nuevos; LTV = valor medio * frecuencia * vida del cliente; Churn = (clientes perdidos / total) * 100.
- Una sola página con inputs, cálculo y resultado. Diseño limpio y profesional. Responsive mobile-first.
- En el HTML: <head> con <title> y <meta name="description"> en español.
- Inputs con labels en español, validación si falta campo, botón "Calcular", área de resultado destacada. No recargar página.
- SOLO código. SIN explicaciones. SIN markdown. SIN ```.

{MARKER_INDEX}
(HTML completo en español: head con title y meta description, body con formulario y resultado)

{MARKER_STYLE}
(CSS mínimo, tarjetas con sombra ligera, botones con hover)

{MARKER_SCRIPT}
(JavaScript: leer valores por id/querySelector, validar, calcular con la fórmula correcta, mostrar resultado formateado en español)
"""
    return base


def _clean_block(content: str) -> str:
    """Quita ``` y texto extra del bloque."""
    content = content.strip()
    content = re.sub(r"^```\w*\n?", "", content)
    content = re.sub(r"\n?```\s*$", "", content)
    return content.strip()


def _parse_blocks(text: str) -> dict | None:
    """
    Extrae los tres bloques por marcadores ===INDEX===, ===STYLE===, ===SCRIPT===.
    Retorna dict index.html, style.css, script.js o None.
    """
    text = text.strip()
    blocks = {}
    patterns = [
        (rf"{re.escape(MARKER_INDEX)}\s*\n(.*?)(?=\s*{re.escape(MARKER_STYLE)}|$)", "index.html"),
        (rf"{re.escape(MARKER_STYLE)}\s*\n(.*?)(?=\s*{re.escape(MARKER_SCRIPT)}|$)", "style.css"),
        (rf"{re.escape(MARKER_SCRIPT)}\s*\n(.*)$", "script.js"),
    ]
    for pattern, key in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if not match:
            return None
        blocks[key] = _clean_block(match.group(1))
    if len(blocks) == 3 and all(blocks.values()):
        return blocks
    return None


def _parse_blocks_lenient(text: str) -> dict | None:
    """
    Intenta extraer los tres bloques aunque los marcadores tengan variaciones (espacios, mayúsculas).
    Busca cada marcador en orden; el contenido de cada bloque es lo que hay hasta el siguiente marcador.
    """
    text = text.strip()
    markers = [MARKER_INDEX, MARKER_STYLE, MARKER_SCRIPT]
    keys = ["index.html", "style.css", "script.js"]
    content_starts = []
    marker_starts = []
    for marker in markers:
        pattern = re.compile(re.escape(marker) + r"\s*\n", re.IGNORECASE)
        match = pattern.search(text)
        if not match:
            return None
        content_starts.append(match.end())
        marker_starts.append(match.start())
    if len(content_starts) != 3:
        return None
    parts = [
        text[content_starts[0] : marker_starts[1]].strip(),
        text[content_starts[1] : marker_starts[2]].strip(),
        text[content_starts[2] :].strip(),
    ]
    out = {}
    for key, content in zip(keys, parts):
        cleaned = _clean_block(content)
        if not cleaned or len(cleaned) < 15:
            return None
        out[key] = cleaned
    return out


def _call_ollama(prompt: str, max_tokens: int | None = None) -> tuple[str | None, float, int]:
    """
    POST a Ollama. Retorna (texto o None, segundos, longitud respuesta).
    max_tokens: límite de tokens de salida (ej. 1200 para portal).
    """
    payload = {"model": MODEL, "prompt": prompt, "stream": False}
    if max_tokens is not None:
        payload["options"] = {"num_predict": max_tokens}
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    start = time.perf_counter()
    response_len = 0
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            response_text = (data.get("response") or "").strip()
            response_len = len(response_text)
            elapsed = time.perf_counter() - start
            logger.info(
                "Ollama: tiempo_generacion=%.1fs | longitud_prompt=%d | longitud_respuesta=%d",
                elapsed, len(prompt), response_len,
            )
            return (response_text, elapsed, response_len)
    except Exception as e:
        elapsed = time.perf_counter() - start
        logger.warning(
            "Ollama request falló: %s | tiempo=%.1fs | longitud_prompt=%d",
            e, elapsed, len(prompt),
        )
        return (None, elapsed, 0)


def generate_tool_code(problem: str, saas: bool = False, max_tokens: int | None = None) -> dict:
    """
    Genera código con Ollama. Retorna dict index.html, style.css, script.js.
    saas=True: prompt orientado a métricas SaaS. max_tokens: límite (ej. 1200).
    Lanza OllamaGenerationError si falla o el formato es inválido.
    """
    logger.info("Inicio generación: %s (saas=%s)", problem, saas)
    prompt = _build_prompt(problem, saas=saas)
    prompt_len = len(prompt)
    logger.info("longitud_prompt=%d", prompt_len)
    total_elapsed = 0.0

    num_attempts = MAX_RETRIES + 2
    for attempt in range(1, num_attempts + 1):
        logger.info("Intento %d de %d", attempt, num_attempts)
        raw, elapsed, response_len = _call_ollama(prompt, max_tokens=max_tokens)
        total_elapsed += elapsed

        if raw is None:
            logger.warning("Intento %d: sin respuesta (%.1fs)", attempt, elapsed)
            continue

        blocks = _parse_blocks(raw)
        if not blocks:
            blocks = _parse_blocks_lenient(raw)
        if blocks:
            logger.info(
                "Éxito: tiempo_generacion=%.1fs | longitud_prompt=%d | longitud_respuesta=%d",
                elapsed, prompt_len, response_len,
            )
            return blocks

        logger.warning("Intento %d: formato inválido (longitud_respuesta=%d)", attempt, response_len)

    logger.error(
        "Ollama falló tras %d intentos: tiempo_total=%.1fs | modelo=%s | longitud_prompt=%d",
        num_attempts, total_elapsed, MODEL, prompt_len,
    )
    raise OllamaGenerationError(
        f"Ollama no devolvió código válido (tiempo_total={total_elapsed:.1f}s, intentos={num_attempts})"
    )


def _slugify(text: str) -> str:
    """Nombre de directorio válido."""
    slug = text.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "_", slug)
    return slug.strip("_-")[:50]


def generate_tool_structure(problem: str, output_dir: str = "output/tools") -> tuple[str, bool]:
    """
    Genera la herramienta y la guarda en disco.
    Retorna (ruta, ai_generation_success=True).
    Lanza OllamaGenerationError si la IA falla (no hay fallback).
    """
    slug = _slugify(problem)
    tool_path = Path(output_dir) / slug
    tool_path.mkdir(parents=True, exist_ok=True)

    code = generate_tool_code(problem)

    (tool_path / "index.html").write_text(code["index.html"], encoding="utf-8")
    (tool_path / "style.css").write_text(code["style.css"], encoding="utf-8")
    (tool_path / "script.js").write_text(code["script.js"], encoding="utf-8")

    return (str(tool_path), True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    problem = "Convertir temperatura Celsius a Fahrenheit"
    try:
        path, ai_ok = generate_tool_structure(problem)
        print("Herramienta generada en:", path, "| IA éxito:", ai_ok)
    except OllamaGenerationError as e:
        print("Error:", e)
