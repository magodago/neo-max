"""
Genera imágenes con la misma API Gemini que el libro (neo-max-engine/stories_agent).
Usa gemini_api_key en config.json o GEMINI_API_KEY en entorno.
Modelo: gemini-2.5-flash-image (imagen 2.0).
"""
import json
import logging
import os
import re
import unicodedata
from pathlib import Path

logger = logging.getLogger("neo_desktop.gemini_image")

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"


def _load_config() -> dict:
    if not CONFIG_PATH.is_file():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _slug(s: str) -> str:
    s = s.strip()
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^\w\s\-_]", "", s)
    # Mantener guiones bajos (ej. mago_001) para coincidir con rutas esperadas por skills
    s = re.sub(r"[\s]+", "-", s)
    return s.strip("-")[:60] or "image"


def generate_image(prompt: str, slug: str, output_dir: Path, model: str = "") -> str | None:
    """
    Genera una imagen con Gemini (misma API que el libro).
    prompt: descripción en texto.
    slug: nombre base del archivo (sin extensión).
    output_dir: carpeta donde crear output_dir/images/<slug>.png
    model: ej. gemini-2.5-flash-image (por defecto el del libro).
    Retorna ruta relativa "images/xxx.png" o None si falla.
    """
    config = _load_config()
    api_key = (config.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY") or "").strip()
    if not api_key:
        logger.warning("gemini_api_key / GEMINI_API_KEY no configurado")
        return None
    try:
        from google import genai
    except ImportError:
        logger.warning("pip install google-genai para imágenes con Gemini")
        return None
    prompt = prompt.strip()[:4000]
    (output_dir / "images").mkdir(parents=True, exist_ok=True)
    path = output_dir / "images" / f"{_slug(slug)}.png"
    client = genai.Client(api_key=api_key)
    model_name = (model or "gemini-2.5-flash-image").strip()
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        # Varios formatos de respuesta según versión del SDK / modelo
        parts = getattr(response, "parts", None)
        if not parts and getattr(response, "candidates", None) and len(response.candidates) > 0:
            content = getattr(response.candidates[0], "content", None)
            if content is not None:
                parts = getattr(content, "parts", None)
        if not parts:
            logger.warning("Gemini no devolvió parts (revisa modelo %s y que el prompt pida imagen)", model_name)
            return None
        for part in parts:
            # as_image() (PIL Image) — SDK reciente
            as_image = getattr(part, "as_image", None)
            if as_image is not None:
                try:
                    img = as_image()
                    if img is not None:
                        img.save(str(path))
                        return f"images/{path.name}"
                except Exception as e2:
                    logger.warning("Gemini as_image failed: %s", e2)
            # inline_data.data (bytes)
            inline = getattr(part, "inline_data", None)
            if inline is not None:
                data = getattr(inline, "data", None)
                if data and len(data) > 0:
                    path.write_bytes(data if isinstance(data, bytes) else bytes(data))
                    return f"images/{path.name}"
            # part.data directo (algunos SDK)
            data = getattr(part, "data", None)
            if data and len(data) > 0:
                path.write_bytes(data if isinstance(data, bytes) else bytes(data))
                return f"images/{path.name}"
        logger.warning("Sin datos de imagen en respuesta Gemini (modelo %s)", model_name)
        return None
    except Exception as e:
        logger.warning("Gemini imagen falló: %s", e)
        return None
