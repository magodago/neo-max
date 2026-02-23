# Genera una imagen con la API de Google (Gemini), igual que el libro de magia.
# Uso: SKILL:generar_imagen <descripción de la imagen que quieres>
DESCRIPTION = "Genera una imagen con IA (Google Gemini, misma API que el libro). Uso: SKILL:generar_imagen <descripción>"

def run(task: str = "", **kwargs) -> str:
    import json
    import re
    import sys
    from pathlib import Path

    desc = (task or "").strip()[:500] or "imagen creativa"
    base = Path(__file__).resolve().parent.parent
    agent_root = base.parent
    if str(agent_root) not in sys.path:
        sys.path.insert(0, str(agent_root))

    config = {}
    try:
        cfg_path = agent_root / "config.json"
        if cfg_path.is_file():
            config = json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        pass

    if not (config.get("gemini_api_key") or "").strip():
        return "No está configurada gemini_api_key en config.json. Añádela (la misma que usas para el libro de magia) para generar imágenes con Google Gemini."

    try:
        from gemini_image import generate_image
    except ImportError:
        return "Error: pip install google-genai. El módulo gemini_image está en la raíz del agente."

    out_dir = base / "output" / "imagenes_generadas"
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^\w\s-]", "", desc.lower())[:40].strip().replace(" ", "_") or "imagen"
    slug = re.sub(r"_+", "_", slug).strip("_")[:50]

    prompt = f"{desc}. Sin texto escrito en la imagen."
    rel = generate_image(prompt, slug, out_dir, model=config.get("gemini_image_model", ""))
    if not rel:
        return "No se pudo generar la imagen (revisa gemini_api_key y que el modelo soporte generación de imágenes)."
    path = out_dir / rel
    if not path.is_file():
        return "La imagen se generó pero no se encontró el archivo."
    return f"Imagen generada con Gemini (misma API que el libro): {path}. Carpeta: {out_dir}. Puedes enviar el archivo al usuario o hacer GITHUB:push de la carpeta y DONE con la URL."
