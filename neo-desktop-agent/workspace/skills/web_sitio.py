# Crea una web o landing profesional y atractiva. Luego sube con GITHUB:push y envía el enlace.
# Uso: SKILL:web_sitio Landing de mi restaurante

DESCRIPTION = "Crea una web o landing profesional. Uso: SKILL:web_sitio <tema o nombre del negocio>"


def run(task: str = "", **kwargs) -> str:
    import re
    from pathlib import Path
    tema = (task or "Mi sitio web").strip()[:80]
    slug = re.sub(r"[^\w\s-]", "", tema)[:30].strip().replace(" ", "_") or "web"
    base = Path(__file__).resolve().parent.parent
    out_dir = base / "output" / "webs" / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    titulo = tema
    html = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>""" + titulo + """</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Outfit', system-ui, sans-serif; background: #0d0d0d; color: #f5f5f5; min-height: 100vh; overflow-x: hidden; }
    .hero { min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: 2rem; background: linear-gradient(160deg, #0d0d0d 0%, #1a1a2e 40%, #16213e 100%); position: relative; }
    .hero::before { content: ''; position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: radial-gradient(ellipse 80% 50% at 50% -20%, rgba(79, 195, 247, 0.15), transparent); pointer-events: none; }
    h1 { font-size: clamp(2rem, 6vw, 3.5rem); font-weight: 700; margin-bottom: 1rem; letter-spacing: -0.02em; position: relative; }
    .sub { font-size: clamp(1rem, 2.5vw, 1.25rem); opacity: 0.85; max-width: 500px; margin-bottom: 2rem; line-height: 1.6; position: relative; }
    .cta { display: inline-block; padding: 1rem 2rem; background: linear-gradient(135deg, #4fc3f7, #0288d1); color: #fff; text-decoration: none; border-radius: 12px; font-weight: 600; font-size: 1.1rem; transition: transform 0.2s, box-shadow 0.2s; position: relative; }
    .cta:hover { transform: translateY(-2px); box-shadow: 0 12px 28px rgba(2, 136, 209, 0.4); }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1.5rem; padding: 4rem 2rem; max-width: 1000px; margin: 0 auto; }
    .card { background: rgba(255,255,255,0.05); border-radius: 16px; padding: 2rem; border: 1px solid rgba(255,255,255,0.08); transition: border-color 0.2s; }
    .card:hover { border-color: rgba(79, 195, 247, 0.3); }
    .card h3 { font-size: 1.25rem; margin-bottom: 0.5rem; }
    .card p { opacity: 0.8; font-size: 0.95rem; line-height: 1.5; }
    footer { text-align: center; padding: 2rem; opacity: 0.6; font-size: 0.9rem; }
  </style>
</head>
<body>
  <section class="hero">
    <h1>""" + titulo + """</h1>
    <p class="sub">Bienvenido. Diseño profesional y adaptable a móviles, creado por NEO.</p>
    <a href="#contacto" class="cta">Contactar</a>
  </section>
  <section class="grid">
    <div class="card"><h3>Calidad</h3><p>Contenido y diseño pensados para enganchar a tu audiencia.</p></div>
    <div class="card"><h3>Responsive</h3><p>Se ve perfecto en móvil, tablet y escritorio.</p></div>
    <div class="card"><h3>Rápido</h3><p>Carga ligera y optimizada.</p></div>
  </section>
  <footer id="contacto">""" + titulo + """ — Creado con NEO Desktop Agent</footer>
</body>
</html>"""
    (out_dir / "index.html").write_text(html, encoding="utf-8")
    return "Web creada: " + str(out_dir) + "\nTema: " + tema + "\nPara publicar: GITHUB:push y DONE con la URL de GitHub Pages. Diseno profesional y responsive."
