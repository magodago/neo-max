"""
design_system - CSS base para todas las herramientas: UX consistente y profesional.
Se escribe en portal_root/tools/_base.css y cada herramienta lo enlaza.
"""

from pathlib import Path

# Design system: SaaS moderno, limpio, accesible. Mobile-first.
BASE_CSS = """/* NEO MAX Tool Design System - SaaS modern, clean */
:root {
  --bg: #f8fafc;
  --card: #ffffff;
  --text: #1e293b;
  --muted: #64748b;
  --accent: #2563eb;
  --accent-hover: #1d4ed8;
  --radius: 12px;
  --shadow: 0 1px 3px rgba(0,0,0,.08);
  --shadow-hover: 0 10px 40px -15px rgba(0,0,0,.12);
  --font: 'Inter', system-ui, -apple-system, sans-serif;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: var(--font);
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
  padding: 1rem 1.5rem;
  min-height: 100vh;
}
.tool-wrap { max-width: 560px; margin: 0 auto; }
.tool-main h1 { font-size: 1.75rem; font-weight: 700; margin-bottom: 0.35rem; }
.tool-desc { color: var(--muted); margin-bottom: 1.25rem; font-size: 0.9375rem; }
.tool-form {
  background: var(--card);
  padding: 1.5rem;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  margin-bottom: 1.25rem;
}
.tool-form label { display: block; font-weight: 500; margin-bottom: 0.35rem; font-size: 0.9375rem; }
.tool-form input, .tool-form select {
  margin-bottom: 1rem;
  padding: 0.6rem 0.75rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 1rem;
  width: 100%;
  font-family: inherit;
}
.tool-form input:focus {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.btn {
  display: inline-block;
  padding: 0.6rem 1.25rem;
  font-weight: 600;
  border-radius: 8px;
  cursor: pointer;
  border: none;
  background: var(--accent);
  color: #fff;
  font-family: inherit;
  font-size: 1rem;
  transition: background 0.2s, transform 0.1s;
}
.btn:hover { background: var(--accent-hover); transform: translateY(-1px); }
.result-area {
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  border-radius: 8px;
  padding: 1.25rem;
  margin-top: 1rem;
  font-weight: 600;
  font-size: 1.125rem;
  transition: opacity 0.25s;
}
.error-msg { color: #b91c1c; margin-top: 0.5rem; font-size: 0.9375rem; }
.related-tools { margin-top: 2rem; padding-top: 1.5rem; border-top: 1px solid #e2e8f0; }
.related-tools h3 { font-size: 1rem; margin-bottom: 0.75rem; color: var(--muted); }
.related-tools a { display: inline-block; margin-right: 0.75rem; margin-bottom: 0.5rem; color: var(--accent); font-weight: 500; }
@media (max-width: 640px) {
  body { padding: 0.75rem 1rem; }
  .tool-form { padding: 1rem; }
}
"""


def ensure_design_system_in_portal(portal_root: Path) -> Path:
    """Escribe portal_root/tools/_base.css con el design system. Retorna la ruta."""
    portal_root = Path(portal_root)
    tools_dir = portal_root / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    path = tools_dir / "_base.css"
    path.write_text(BASE_CSS, encoding="utf-8")
    return path
