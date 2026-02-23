# Crea juegos web por genero: naves, snake, memoria, runner. Con detalle visual y logica completa.
DESCRIPTION = "Crea un juego web por genero (naves, snake, memoria, carrera). Uso: SKILL:juegos_movil <genero o tema>"

def run(task: str = "", **kwargs) -> str:
    import re
    from pathlib import Path
    tema = (task or "naves").strip()[:60]
    tema_lower = tema.lower()
    if any(x in tema_lower for x in ["trivial", "trivia", "quiz", "preguntas"]):
        genero = "trivial"
        for k in ["historia", "deportes", "geografia", "ciencia", "cultura"]:
            if k in tema_lower:
                titulo = "Trivial: " + k.capitalize()
                break
        else:
            titulo = "Trivial: Cultura general"
    elif any(x in tema_lower for x in ["snake", "serpiente", "culebra"]):
        genero, titulo = "snake", "Serpiente clasica"
    elif any(x in tema_lower for x in ["memoria", "puzzle", "parejas", "cartas"]):
        genero, titulo = "memoria", "Juego de memoria"
    elif any(x in tema_lower for x in ["carrera", "runner", "correr", "corredor", "infinito"]):
        genero, titulo = "runner", "Corredor infinito"
    else:
        genero, titulo = "shooter", tema if tema else "Naves espaciales"

    skills_dir = Path(__file__).resolve().parent
    import sys
    if str(skills_dir) not in sys.path:
        sys.path.insert(0, str(skills_dir))
    import _juegos_templates as t

    if genero == "shooter":
        html = t.get_shooter_html(titulo)
    elif genero == "snake":
        html = t.get_snake_html(titulo)
    elif genero == "memoria":
        html = t.get_memoria_html(titulo)
    elif genero == "trivial":
        trivial_tema = "cultura"
        for k in ["historia", "deportes", "geografia", "ciencia", "cultura"]:
            if k in tema_lower:
                trivial_tema = k
                break
        html = t.get_trivial_html(trivial_tema)
    else:
        html = t.get_runner_html(titulo)

    slug = re.sub(r"[^\w\s-]", "", tema)[:20].replace(" ", "_") or genero
    base = Path(__file__).resolve().parent.parent
    out_dir = base / "output" / "juegos" / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(html, encoding="utf-8")

    return "Juego creado (%s): %s. Controles tactiles y teclado. Publica con GITHUB:push y DONE con la URL de GitHub Pages." % (genero, out_dir)
