"""
Arregla capítulos que tienen ### TITLE ... ### BODY en crudo dentro del body.
Ejecutar desde stories_agent: python fix_chapters_html.py
"""
import re
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent / "output" / "site"
STORY_DIR = OUTPUT_DIR / "story"


def _sanitize_body(content: str) -> tuple[str | None, str]:
    """Si content tiene ### TITLE ... ### BODY, devuelve (nuevo_titulo, body_limpio). Si no, (None, content)."""
    if "### TITLE" not in content or "### BODY" not in content:
        return None, content
    m = re.search(r"#+\s*TITLE\s*(.*?)\s*#+\s*BODY\s*(.*)", content, re.DOTALL | re.IGNORECASE)
    if not m:
        return None, content
    title_part = m.group(1).strip()
    body_part = m.group(2).strip()
    new_title = title_part.split("\n")[0].strip()[:200] if title_part else None
    new_body = body_part if len(body_part) > 50 else content
    return new_title, new_body


def main():
    if not STORY_DIR.is_dir():
        print("No existe", STORY_DIR)
        return
    fixed = 0
    for path in sorted(STORY_DIR.glob("*.html")):
        text = path.read_text(encoding="utf-8")
        # Buscar <div class="body">...</div>
        match = re.search(r'<div class="body">(.*?)</div>', text, re.DOTALL)
        if not match:
            continue
        body_content = match.group(1)
        new_title, new_body = _sanitize_body(body_content)
        if new_title is None:
            continue
        # Reemplazar body
        new_div = f'<div class="body">{new_body}</div>'
        text_new = text[: match.start()] + new_div + text[match.end() :]
        # Reemplazar título en <h1> si existe (escapar para HTML)
        if new_title:
            safe_title = new_title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
            text_new = re.sub(
                r"<h1[^>]*>.*?</h1>",
                f'<h1 style="font-size:clamp(1.4rem, 4vw, 1.9rem);margin:0 0 0.5rem;">{safe_title}</h1>',
                text_new,
                count=1,
            )
        path.write_text(text_new, encoding="utf-8")
        fixed += 1
        print("Fixed:", path.name)
    print("Total fixed:", fixed)


if __name__ == "__main__":
    main()
