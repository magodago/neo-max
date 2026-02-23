# PDF profesional con contenido real (Gemini texto + imagen) y diseño cuidado.
# Uso: SKILL:documento_pdf <tema>
DESCRIPTION = "Crea un PDF profesional sobre un tema con contenido generado por IA e imagen. Uso: SKILL:documento_pdf <tema>"


def _agent_root():
    from pathlib import Path
    return Path(__file__).resolve().parent.parent.parent


def _generar_texto_gemini(tema: str, config: dict) -> str | None:
    """Genera 8-12 párrafos profesionales sobre el tema con Gemini (solo texto)."""
    api_key = (config.get("gemini_api_key") or "").strip()
    if not api_key:
        return None
    try:
        from google import genai
    except ImportError:
        return None
    prompt = (
        f"Escribe un documento profesional completo para una empresa sobre: {tema}.\n\n"
        "Requisitos:\n"
        "- Entre 8 y 12 párrafos de 3 a 5 líneas cada uno (documento con cuerpo, no resumen).\n"
        "- Tono formal y claro, en español.\n"
        "- Estructura: 1-2 párrafos de introducción/contexto, 5-8 de desarrollo (definición, beneficios, aplicaciones prácticas, casos de uso, retos), 1-2 de conclusiones o recomendaciones.\n"
        "- Contenido concreto y útil, datos o ejemplos cuando encajen.\n"
        "- Sin títulos ni bullet points; solo párrafos separados por línea en blanco.\n"
        "- Sin frases genéricas tipo 'este documento trata de'."
    )
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt[:8000],
        )
        text = getattr(response, "text", None)
        if not text and getattr(response, "candidates", None):
            c = response.candidates[0]
            if getattr(c, "content", None) and getattr(c.content, "parts", None):
                text = "".join(getattr(p, "text", "") or "" for p in c.content.parts)
        text = (text or "").strip()
        if not text or len(text) < 100:
            return None
        return text.strip()
    except Exception:
        return None


def _esc(s: str) -> str:
    """Escapa para Reportlab Paragraph (HTML-like)."""
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _generar_imagen_gemini(tema: str, slug: str, out_dir, config: dict):
    """Genera imagen con Gemini. Retorna ruta absoluta del PNG o None."""
    import sys
    root = _agent_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    try:
        from gemini_image import generate_image
    except ImportError:
        return None
    if not (config.get("gemini_api_key") or "").strip():
        return None
    prompt = (
        f"Imagen ilustrativa y profesional para un documento de empresa sobre: {tema}. "
        "Estilo corporativo o infográfico, sin texto dentro de la imagen, colores sobrios."
    )
    rel = generate_image(prompt, slug + "_img", out_dir, model=config.get("gemini_image_model", ""))
    if rel and (out_dir / rel).is_file():
        return str((out_dir / rel).resolve())
    return None


def run(task: str = "", **kwargs) -> str:
    import json
    import re
    import tempfile
    import urllib.request
    from datetime import datetime
    from pathlib import Path
    temp_img_path = None
    task = (task or "").strip()
    tema = task[:200].strip() or "Documento"
    slug = re.sub(r"[^\w\s-]", "", tema)[:40].strip().replace(" ", "_") or "doc"
    slug = re.sub(r"_+", "_", slug).strip("_")
    base = Path(__file__).resolve().parent.parent
    out_dir = base / "output" / "documentos_pdf"
    out_dir.mkdir(parents=True, exist_ok=True)
    config = {}
    try:
        if (_agent_root() / "config.json").is_file():
            config = json.loads((_agent_root() / "config.json").read_text(encoding="utf-8"))
    except Exception:
        pass
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as PlatypusImage
    except ImportError:
        return "Error: pip install reportlab. Luego vuelve a ejecutar el skill."

    pdf_path = out_dir / (slug + ".pdf")
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name="DocTitle",
        parent=styles["Heading1"],
        fontSize=20,
        spaceAfter=6,
        textColor="darkslategray",
    )
    subtitle_style = ParagraphStyle(
        name="DocSubtitle",
        parent=styles["Normal"],
        fontSize=9,
        spaceAfter=14,
        textColor="gray",
    )
    body_style = ParagraphStyle(
        name="DocBody",
        parent=styles["Normal"],
        fontSize=11,
        leading=14,
        spaceAfter=10,
    )
    caption_style = ParagraphStyle(
        name="Caption",
        parent=styles["Normal"],
        fontSize=9,
        textColor="gray",
        spaceAfter=12,
        alignment=1,
    )
    story = []

    # Título
    story.append(Paragraph(_esc(tema[:80]), title_style))
    story.append(Paragraph(
        f"Documento profesional · {datetime.now().strftime('%d/%m/%Y')}",
        subtitle_style,
    ))
    story.append(Spacer(1, 0.3 * cm))

    # Contenido real con Gemini
    texto_ia = _generar_texto_gemini(tema, config)
    parrafos = []
    if texto_ia:
        parrafos = [p.strip() for p in texto_ia.split("\n\n") if p.strip()]
    # Antes de la imagen: primeros 4 párrafos (o todos si hay pocos)
    num_antes_imagen = min(4, max(2, len(parrafos) // 2))
    for p in parrafos[:num_antes_imagen]:
        story.append(Paragraph(_esc(p), body_style))
    if not parrafos:
        story.append(Paragraph(
            _esc(f"Este documento aborda el tema de {tema}. A continuación se presenta una visión de conjunto y sus aspectos más relevantes en el ámbito empresarial."),
            body_style,
        ))
    story.append(Spacer(1, 0.4 * cm))

    # Imagen
    img_path = _generar_imagen_gemini(tema, slug, out_dir, config)
    if not img_path:
        try:
            url = "https://picsum.photos/800/450"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; NEO/1.0)"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = resp.read()
            if data[:2] == b"\xff\xd8" or data[:8] == b"\x89PNG\r\n\x1a\n":
                f = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                f.write(data)
                f.close()
                img_path = f.name
                temp_img_path = img_path
        except Exception:
            img_path = None

    if img_path and Path(img_path).is_file():
        try:
            img = PlatypusImage(img_path, width=14 * cm, height=8 * cm)
            story.append(img)
            cap = _esc(tema[:60])
            story.append(Paragraph(f"Figura 1: Ilustración — {cap}", caption_style))
            story.append(Spacer(1, 0.4 * cm))
        except Exception:
            pass

    # Resto de párrafos (todo el contenido generado)
    for p in parrafos[num_antes_imagen:]:
        story.append(Paragraph(_esc(p), body_style))

    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph(
        "— Documento generado por NEO · Agente de escritorio",
        caption_style,
    ))

    doc.build(story)
    if temp_img_path and Path(temp_img_path).is_file():
        try:
            Path(temp_img_path).unlink(missing_ok=True)
        except Exception:
            pass
    return f"Documento PDF generado: {pdf_path}. Carpeta: {out_dir}. Siguiente paso: GITHUB:push \"{out_dir}\" pdf-{slug[:20]} y DONE con la URL para que el usuario pueda abrirlo."
