"""
tool_evaluator - Evalúa la calidad de una micro-herramienta.
Score 0-100 según existencia de archivos, estructura HTML, contenido CSS y JS.
Verifica que el JS tenga lógica de cálculo (operaciones, formulario, resultado).
"""

import re
from pathlib import Path


def _score_files_exist(tool_path: Path) -> tuple[int, dict[str, str]]:
    """
    Verifica que existan los 3 archivos y devuelve contenido.
    Retorna (puntos 0-20, dict con contenido por archivo o vacío si falta).
    """
    required = ("index.html", "style.css", "script.js")
    contents = {}
    for name in required:
        f = tool_path / name
        if not f.is_file():
            return (0, {})
        try:
            contents[name] = f.read_text(encoding="utf-8")
        except Exception:
            return (0, {})
    return (20, contents)


def _score_html(html: str) -> int:
    """
    Evalúa estructura básica del HTML. Máximo 30 puntos.
    """
    if not html or len(html.strip()) < 50:
        return 0
    score = 0
    html_lower = html.lower()
    if "<!doctype" in html_lower or "<!DOCTYPE" in html:
        score += 6
    if "<html" in html_lower:
        score += 6
    if "<head" in html_lower:
        score += 4
    if "<body" in html_lower:
        score += 4
    if "stylesheet" in html_lower or "style.css" in html_lower:
        score += 5
    if "<script" in html_lower and ("script.js" in html_lower or "src=" in html_lower):
        score += 5
    return min(30, score)


def _score_css(css: str) -> int:
    """
    Evalúa que el CSS tenga contenido útil. Máximo 25 puntos.
    """
    if not css:
        return 0
    # Quitar comentarios para medir contenido real
    without_comments = re.sub(r"/\*[\s\S]*?\*/", "", css)
    stripped = without_comments.strip()
    if len(stripped) < 10:
        return 0
    score = 10
    if "{" in stripped and "}" in stripped:
        score += 5
    if ":" in stripped:
        score += 5
    # Algunas propiedades comunes
    if re.search(r"(color|margin|padding|font|width|height|display|background)\s*:", stripped, re.I):
        score += 5
    return min(25, score)


def _score_js(js: str) -> int:
    """
    Evalúa que el JS tenga lógica mínima. Máximo 25 puntos.
    """
    if not js:
        return 0
    without_comments = re.sub(r"//[^\n]*", "", js)
    without_comments = re.sub(r"/\*[\s\S]*?\*/", "", without_comments)
    stripped = without_comments.strip()
    if len(stripped) < 15:
        return 0
    score = 5
    if "function" in stripped or "=>" in stripped or "addEventListener" in stripped:
        score += 6
    if "getElementById" in stripped or "querySelector" in stripped or "document." in stripped:
        score += 5
    if "(" in stripped and ")" in stripped:
        score += 4
    if "=" in stripped or "return" in stripped:
        score += 5
    return min(25, score)


def evaluate_tool(tool_path: str, problem: str) -> int:
    """
    Evalúa una herramienta según archivos, HTML, CSS y JS.
    
    Args:
        tool_path: Ruta al directorio de la herramienta
        problem: El problema que debería resolver (no usado aún; reservado para métricas futuras)
        
    Returns:
        Score entre 0 y 100
    """
    root = Path(tool_path)
    if not root.is_dir():
        return 0

    points_files, contents = _score_files_exist(root)
    if points_files == 0:
        return 0

    points_html = _score_html(contents.get("index.html", ""))
    points_css = _score_css(contents.get("style.css", ""))
    points_js = _score_js(contents.get("script.js", ""))

    total = points_files + points_html + points_css + points_js
    return min(100, total)


def verify_tool_logic(tool_path: str | Path, problem: str = "") -> tuple[bool, str]:
    """
    Autorevisión: comprueba que la herramienta tenga lógica de cálculo (formulario, operación, resultado).
    No ejecuta el JS en navegador; revisa que el código contenga los patrones esperados.
    Returns (True, "") si pasa, (False, motivo) si falla.
    """
    root = Path(tool_path)
    js_file = root / "script.js"
    if not js_file.is_file():
        return (False, "No script.js")
    js = js_file.read_text(encoding="utf-8")
    js_clean = re.sub(r"/\*[\s\S]*?\*/|//[^\n]*", "", js)
    # Debe tener manejo de formulario
    if "addEventListener" not in js_clean and "onsubmit" not in js_clean.lower():
        return (False, "No form submit handling")
    # Debe leer valores (input/getElementById/querySelector/value)
    if "value" not in js_clean or ("getElementById" not in js_clean and "querySelector" not in js_clean):
        return (False, "No input value reading")
    # Debe tener operación numérica (calculadora)
    if not re.search(r"parseFloat|Number\s*\(|/\s*[a-zA-Z_]|\*\s*[a-zA-Z_]|\+\s*[a-zA-Z_]|-\s*[a-zA-Z_]", js_clean):
        return (False, "No arithmetic/logic for calculation")
    # Debe escribir resultado (textContent/innerHTML/innerText/result/output/appendChild)
    has_output = (
        "textContent" in js_clean or "innerHTML" in js_clean or "innerText" in js_clean
        or "result" in js_clean.lower() or "output" in js_clean.lower()
        or "appendChild" in js_clean
    )
    if not has_output:
        return (False, "No result output")
    # Fórmulas esperadas por tipo (slug o problema)
    slug = root.name.lower()
    problem_lower = (problem or "").lower()
    if "cac" in slug or "acquisition" in problem_lower:
        if "/" not in js_clean:
            return (False, "CAC should use division (cost/customers)")
    if "ltv" in slug or "lifetime" in problem_lower:
        if "*" not in js_clean and "multiply" not in js_clean.lower():
            return (False, "LTV should use multiplication")
    if "churn" in slug or "churn" in problem_lower:
        if "/" not in js_clean or "*" not in js_clean:
            return (False, "Churn should use (lost/total)*100")
    if "runway" in slug or "runway" in problem_lower:
        if "/" not in js_clean:
            return (False, "Runway should use division (cash/burn)")
    return (True, "")


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "output/tools/test"
    score = evaluate_tool(path, "Prueba")
    ok, msg = verify_tool_logic(path, "Calculator")
    print(f"Score: {score}/100 | Logic OK: {ok} {msg}")
