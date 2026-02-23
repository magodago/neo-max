"""
Genera una imagen a partir de un prompt.
Soporta: OpenAI DALL·E 3 (OPENAI_API_KEY) y Gemini Nano Banana (GEMINI_API_KEY).
Guarda en output_dir/images/slug.jpg y retorna la ruta relativa.
Los nombres de archivo se normalizan a ASCII para evitar fallos al subir a GitHub.
"""
import json
import logging
import os
import re
import unicodedata
import urllib.request
from pathlib import Path

logger = logging.getLogger("stories_agent")

# Cargar .env del proyecto padre
_env = Path(__file__).resolve().parent.parent / ".env"
if _env.is_file():
    for line in _env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip("'\"")
            if k and k not in os.environ:
                os.environ[k] = v


def _slug(s: str) -> str:
    s = s.lower().strip()
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return s.strip("-")[:60] or "story"


def _generate_gemini_image(prompt: str, slug: str, output_dir: Path, model: str) -> str | None:
    """Genera imagen con Gemini (Nano Banana). Requiere GEMINI_API_KEY y pip install google-genai."""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        logger.warning("GEMINI_API_KEY not set; skipping Gemini image")
        return None
    try:
        from google import genai
    except ImportError:
        logger.warning("google-genai not installed; pip install google-genai for Gemini images")
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
        # Respuesta puede ser response.parts o response.candidates[0].content.parts
        parts = getattr(response, "parts", None) or (
            getattr(response.candidates[0].content, "parts", []) if getattr(response, "candidates", None) else []
        )
        if not parts:
            logger.warning("Gemini returned no parts")
            return None
        for part in parts:
            inline = getattr(part, "inline_data", None)
            if inline is None:
                continue
            # Guardar: part.as_image().save() si existe, si no bytes de inline_data.data
            as_image = getattr(part, "as_image", None)
            if as_image is not None:
                try:
                    img = as_image()
                    img.save(str(path))
                    rel = f"images/{path.name}"
                    logger.info("Image saved (Gemini): %s", path)
                    return rel
                except Exception as e2:
                    logger.warning("Gemini as_image failed: %s", e2)
            data = getattr(inline, "data", None)
            if data:
                path.write_bytes(data)
                rel = f"images/{path.name}"
                logger.info("Image saved (Gemini): %s", path)
                return rel
        logger.warning("No image data in Gemini response")
        return None
    except Exception as e:
        logger.warning("Gemini image generation failed: %s", e)
        return None


def generate_and_save_image(
    prompt: str,
    slug: str,
    output_dir: Path,
    size: str = "1024x1024",
    model: str = "dall-e-3",
    image_provider: str = "openai",
) -> str | None:
    """
    Genera una imagen y la guarda en output_dir/images/<slug>.(jpg|png).
    image_provider: "openai" (OPENAI_API_KEY) o "gemini" (GEMINI_API_KEY, Nano Banana).
    Retorna la ruta relativa "images/..." o None si falla.
    """
    if (image_provider or "openai").lower() == "gemini":
        return _generate_gemini_image(prompt, slug, output_dir, model)

    # OpenAI
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        logger.warning("OPENAI_API_KEY not set; skipping image generation")
        return None
    prompt = prompt.strip()[:4000]
    (output_dir / "images").mkdir(parents=True, exist_ok=True)
    path = output_dir / "images" / f"{_slug(slug)}.jpg"
    url = "https://api.openai.com/v1/images/generations"
    payload = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": size,
        "response_format": "url",
        "quality": "standard",
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        img_url = (data.get("data") or [{}])[0].get("url")
        if not img_url:
            logger.warning("No URL in OpenAI response")
            return None
        with urllib.request.urlopen(img_url, timeout=30) as img_resp:
            path.write_bytes(img_resp.read())
        logger.info("Image saved: %s", path)
        return f"images/{path.name}"
    except Exception as e:
        logger.warning("Image generation failed: %s", e)
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    out = Path(__file__).resolve().parent / "output" / "site"
    rel = generate_and_save_image(
        "A small orange cat sleeping on a sunny windowsill next to a green plant, cozy, soft light",
        "cat-sleeping",
        out,
    )
    print("Saved:", rel)
