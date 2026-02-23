# Crea un curso completo profesional: muchos modulos, lecciones con contenido real, indice y listo para publicar.
DESCRIPTION = "Crea un curso completo (varios modulos y lecciones). Uso: SKILL:cursos <tema del curso>"

_CSS_CURSO = """
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Segoe UI', system-ui, sans-serif; background: linear-gradient(160deg, #1a1a2e 0%%, #16213e 100%%); color: #eee; min-height: 100vh; padding: 2rem; line-height: 1.6; }
    .wrap { max-width: 800px; margin: 0 auto; }
    h1 { font-size: 1.8rem; margin-bottom: 0.5rem; }
    .sub { opacity: 0.9; margin-bottom: 1.5rem; font-size: 0.95rem; }
    h2 { font-size: 1.2rem; margin: 1.25rem 0 0.5rem; color: #4fc3f7; }
    p, ul { margin: 0.75rem 0; }
    ul { padding-left: 1.5rem; }
    a { color: #4fc3f7; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .back { display: inline-block; margin-bottom: 1.5rem; padding: 0.5rem 1rem; background: rgba(79,195,247,0.2); border-radius: 8px; }
    .card { background: rgba(255,255,255,0.06); border-radius: 12px; padding: 1.5rem; border: 1px solid rgba(255,255,255,0.08); margin: 1rem 0; }
    .nav-lecciones { margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid rgba(255,255,255,0.1); display: flex; gap: 1rem; flex-wrap: wrap; align-items: center; }
    .nav-lecciones .nav-prev { margin-right: auto; }
    .nav-lecciones .nav-next { margin-left: auto; }
    .nav-lecciones a { padding: 0.5rem 1rem; background: rgba(79,195,247,0.2); border-radius: 8px; }
    .meta { margin-top: 2rem; padding: 1rem; background: rgba(0,0,0,0.2); border-radius: 8px; font-size: 0.9rem; }
    .index ul { list-style: none; padding-left: 0; }
    .index ul li { padding: 0.35rem 0; border-bottom: 1px solid rgba(255,255,255,0.08); }
"""


def _load_config():
    import json
    from pathlib import Path
    config_path = Path(__file__).resolve().parent.parent.parent / "config.json"
    if config_path.is_file():
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _generate_lesson_content(tema: str, nombre_mod: str, nombre_lec: str, config: dict) -> str:
    """Genera el markdown de la lección con Ollama; si falla, devuelve plantilla con el tema."""
    import json
    import urllib.request
    url = config.get("ollama_url", "http://localhost:11434/api/generate")
    model = config.get("model", "qwen2.5:7b-instruct")
    prompt = """Eres un profesor. Escribe el contenido de UNA lección de un curso sobre "%s".

Módulo: %s. Lección: %s.

Formato exacto en Markdown (responde solo esto, sin explicaciones previas):
## Objetivos
- (2 o 3 objetivos concretos para esta lección)

## Contenido
(2 a 4 párrafos desarrollando el tema de la lección, específicos del curso)

## Ejercicio
(Un ejercicio o práctica concreta para el alumno)

## Resumen
- (2 o 3 puntos clave)

Máximo 350 palabras. Todo en español. Solo el contenido, sin títulos extra ni "Aquí va...".""" % (tema, nombre_mod, nombre_lec)
    body = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.4, "num_predict": 1200},
    }
    try:
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=90) as resp:
            out = json.loads(resp.read().decode("utf-8"))
            text = (out.get("response") or "").strip()
            if text and len(text) > 100:
                return "# %s\n\n%s" % (nombre_lec, text)
    except Exception:
        pass
    return """# %s

## Objetivos
- Comprender los conceptos principales de esta lección sobre %s.
- Aplicar lo aprendido en un ejemplo práctico.

## Contenido
En esta lección veremos aspectos importantes de "%s" dentro del módulo "%s". Dedica 15-25 minutos a leer y practicar.

## Ejercicio
Realiza el ejercicio propuesto y comprueba el resultado.

## Resumen
- Punto clave 1.
- Punto clave 2.
""" % (nombre_lec, tema, nombre_lec, nombre_mod)


def _md_to_html(contenido_md: str) -> str:
    import html as html_module
    lines = contenido_md.strip().split("\n")
    body_html = ""
    for line in lines:
        if line.startswith("# "):
            body_html += "<h1>%s</h1>" % html_module.escape(line[2:])
        elif line.startswith("## "):
            body_html += "<h2>%s</h2>" % html_module.escape(line[3:])
        elif line.startswith("- "):
            if "<ul>" not in body_html or body_html.rstrip().endswith("</ul>"):
                body_html += "<ul>"
            body_html += "<li>%s</li>" % html_module.escape(line[2:])
        elif line.strip():
            if body_html.rstrip().endswith("</li>"):
                body_html += "</ul>"
            body_html += "<p>%s</p>" % html_module.escape(line)
    if "<ul>" in body_html and not body_html.rstrip().endswith("</ul>"):
        body_html += "</ul>"
    return body_html or contenido_md.replace("\n", "<br>")


def _write_leccion_html(path, tema_curso, nombre_mod, nombre_lec, contenido_md, num_mod, num_lec,
                        prev_url, next_url):
    body_html = _md_to_html(contenido_md)
    # Volver al índice: desde modulo_XX/leccion_YY.html -> ../../index.html (raíz del curso)
    back_link = "../../index.html"
    nav_html = '<div class="nav-lecciones">'
    nav_html += '<a class="back" href="%s">&larr; Volver al curso</a>' % back_link
    if prev_url:
        nav_html += '<a class="nav-prev" href="%s">&larr; Lección anterior</a>' % prev_url
    if next_url:
        nav_html += '<a class="nav-next" href="%s">Siguiente lección &rarr;</a>' % next_url
    nav_html += "</div>"
    html = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>%s - %s</title>
  <style>%s
  </style>
</head>
<body>
  <div class="wrap">
    <a class="back" href="%s">&larr; Volver a la página principal</a>
    <p class="sub">Módulo %d: %s</p>
    <div class="card">
      %s
      %s
    </div>
  </div>
</body>
</html>""" % (nombre_lec, tema_curso, _CSS_CURSO, back_link, num_mod, nombre_mod, body_html, nav_html)
    path.write_text(html, encoding="utf-8")


def _ascii_slug_for_course(text: str) -> str:
    """Slug solo ASCII para carpeta y repo (evita 'ascii codec' en GitHub/Windows)."""
    import re
    import unicodedata
    n = unicodedata.normalize("NFKD", text)
    ascii_only = "".join(c for c in n if not unicodedata.combining(c)).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^\w\s-]", "", ascii_only)[:50].strip().replace(" ", "_").lower()
    return slug or "curso"


def run(task: str = "", **kwargs) -> str:
    import re
    from pathlib import Path
    tema = (task or "Curso profesional").strip()[:120]
    # Slug solo ASCII (sin acentos) para carpeta y GitHub
    slug = _ascii_slug_for_course(tema)
    base = Path(__file__).resolve().parent.parent
    out_dir = base / "output" / "cursos" / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    config = _load_config()

    modulos = [
        ("Introduccion y contexto", ["Bienvenida al curso", "Que vas a aprender", "Requisitos previos", "Como sacar el maximo partido", "Recursos adicionales"]),
        ("Fundamentos esenciales", ["Conceptos clave", "Terminologia basica", "Primeros pasos practicos", "Ejercicio guiado 1", "Resumen del modulo"]),
        ("Profundizando", ["Temas intermedios", "Casos de uso reales", "Buenas practicas", "Ejercicio guiado 2", "Puntos clave"]),
        ("Tecnicas avanzadas", ["Nivel avanzado", "Optimizacion", "Integracion con otras herramientas", "Proyecto practico 1", "Revision"]),
        ("Proyectos reales", ["Diseño del proyecto", "Implementacion paso a paso", "Pruebas y validacion", "Despliegue", "Mantenimiento"]),
        ("Troubleshooting y rendimiento", ["Problemas frecuentes", "Diagnostico", "Soluciones", "Rendimiento y metricas", "Checklist final"]),
        ("Comunidad y continuidad", ["Recursos de la comunidad", "Actualizaciones", "Donde seguir aprendiendo", "Certificacion y siguiente nivel", "Cierre del modulo"]),
        ("Proyecto final", ["Enunciado del proyecto", "Criterios de evaluacion", "Entrega y revision", "Feedback", "Conclusiones"]),
    ]

    # Lista plana (mod_num, lec_num, mod_slug, lec_slug, mod_name, lec_name) para navegación
    items = []
    for num_mod, (nombre_mod, lecciones) in enumerate(modulos, 1):
        mod_slug = re.sub(r"[^\w\s-]", "", nombre_mod)[:30].replace(" ", "_").lower() or "mod"
        for num_lec, nombre_lec in enumerate(lecciones, 1):
            lec_slug = re.sub(r"[^\w\s-]", "", nombre_lec)[:25].replace(" ", "_").lower() or "lec"
            items.append((num_mod, num_lec, mod_slug, lec_slug, nombre_mod, nombre_lec))

    for idx, (num_mod, num_lec, mod_slug, lec_slug, nombre_mod, nombre_lec) in enumerate(items):
        mod_dir = out_dir / ("modulo_%02d_%s" % (num_mod, mod_slug))
        mod_dir.mkdir(parents=True, exist_ok=True)
        contenido_md = _generate_lesson_content(tema, nombre_mod, nombre_lec, config)
        path_md = mod_dir / ("leccion_%02d_%s.md" % (num_lec, lec_slug))
        path_md.write_text(contenido_md, encoding="utf-8")
        path_html = mod_dir / ("leccion_%02d_%s.html" % (num_lec, lec_slug))
        prev_url = None
        next_url = None
        if idx > 0:
            pm, pl, pms, pls, _, _ = items[idx - 1]
            prev_url = "leccion_%02d_%s.html" % (pl, pls) if pm == num_mod else "../modulo_%02d_%s/leccion_%02d_%s.html" % (pm, pms, pl, pls)
        if idx < len(items) - 1:
            nm, nl, nms, nls, _, _ = items[idx + 1]
            next_url = "leccion_%02d_%s.html" % (nl, nls) if nm == num_mod else "../modulo_%02d_%s/leccion_%02d_%s.html" % (nm, nms, nl, nls)
        _write_leccion_html(path_html, tema, nombre_mod, nombre_lec, contenido_md, num_mod, num_lec, prev_url, next_url)

    for num_mod, (nombre_mod, lecciones) in enumerate(modulos, 1):
        mod_slug = re.sub(r"[^\w\s-]", "", nombre_mod)[:30].replace(" ", "_").lower() or "mod"
        mod_dir = out_dir / ("modulo_%02d_%s" % (num_mod, mod_slug))
        (mod_dir / "README.md").write_text(
            "# Modulo %d: %s\n\nLecciones: %s\n" % (num_mod, nombre_mod, ", ".join(lecciones)),
            encoding="utf-8"
        )

    # Index con el mismo CSS que las lecciones
    index_html = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>%s</title>
  <style>%s
  </style>
</head>
<body>
  <div class="wrap index">
    <h1>%s</h1>
    <p class="sub">Curso completo creado por NEO. %d módulos, varias lecciones por módulo.</p>
""" % (tema, _CSS_CURSO, tema, len(modulos))

    for num_mod, (nombre_mod, lecciones) in enumerate(modulos, 1):
        mod_slug = re.sub(r"[^\w\s-]", "", nombre_mod)[:30].replace(" ", "_").lower() or "mod"
        mod_path = "modulo_%02d_%s" % (num_mod, mod_slug)
        index_html += "    <h2>Módulo %d: %s</h2>\n    <ul>\n" % (num_mod, nombre_mod)
        for num_lec, nombre_lec in enumerate(lecciones, 1):
            lec_slug = re.sub(r"[^\w\s-]", "", nombre_lec)[:25].replace(" ", "_").lower() or "lec"
            index_html += '      <li><a href="%s/leccion_%02d_%s.html">%s</a></li>\n' % (mod_path, num_lec, lec_slug, nombre_lec)
        index_html += "    </ul>\n"

    index_html += """    <div class="meta">
      <p>Para publicar en web: sube esta carpeta con GITHUB:push y activa GitHub Pages. La URL será https://<tu_usuario>.github.io/<nombre_repo>/</p>
    </div>
  </div>
</body>
</html>"""
    (out_dir / "index.html").write_text(index_html, encoding="utf-8")

    readme = """# %s

## Estructura

- **%d módulos**, cada uno con varias lecciones (Markdown + HTML).
- Contenido generado para cada lección. Index en index.html.

## Publicar

- **GitHub Pages:** GITHUB:push de esta carpeta; responde DONE con la URL (https://usuario.github.io/repo/) para que el usuario reciba el enlace.
- **Udemy / Teachable:** Importa la estructura y el contenido.

Ruta: %s
""" % (tema, len(modulos), out_dir)
    (out_dir / "README.md").write_text(readme, encoding="utf-8")

    return "Curso creado y generado: " + str(out_dir) + ". " + str(len(modulos)) + " módulos con varias lecciones. Siguiente paso OBLIGATORIO: GITHUB:push \"" + str(out_dir) + "\" <nombre_repo_sin_espacios> y DONE con la URL (https://magodago.github.io/<repo>/) para que el usuario reciba el enlace."
