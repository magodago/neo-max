"""
Control total del portátil: pantalla, navegador (Playwright), teclado/ratón (pyautogui).
Permite al agente ver la pantalla, usar Chrome y actuar en cualquier ventana.
"""
import base64
import logging
import re
import tempfile
from pathlib import Path

logger = logging.getLogger("neo_desktop.control")

_playwright = None
_browser = None
_page = None
_browser_thread_id = None


def capture_screen(path: str | Path | None = None) -> tuple[bool, str]:
    """
    Captura la pantalla completa. Si path no se da, guarda en temp y devuelve la ruta.
    Returns (success, path_or_error). Si path es None, devuelve ruta del temp file.
    """
    try:
        import pyautogui
        if path is None:
            f = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            path = f.name
            f.close()
        path = Path(path)
        img = pyautogui.screenshot()
        img.save(str(path))
        return (True, str(path))
    except ImportError:
        return (False, "pyautogui no instalado. Ejecuta: pip install pyautogui")
    except Exception as e:
        return (False, str(e))


def close_browser_if_open() -> None:
    """Cierra el navegador si está abierto. Evita error 'Cannot switch to a different thread' cuando
    el agente se ejecuta en un hilo (ej. Telegram run_in_executor) y Playwright quedó en otro."""
    global _playwright, _browser, _page, _browser_thread_id
    try:
        if _browser:
            _browser.close()
        if _playwright:
            _playwright.stop()
    except Exception:
        pass
    _browser = _page = _playwright = _browser_thread_id = None


def _ensure_browser(headless: bool = False):
    """Abre el navegador una vez y reutiliza la misma página entre pasos. Si el hilo actual no es
    el que creó el navegador, lo cierra y no reutiliza (evita greenlet/thread errors)."""
    global _playwright, _browser, _page, _browser_thread_id
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return (None, "playwright no instalado. pip install playwright && playwright install chromium")
    import threading
    current_tid = threading.current_thread().ident
    if _page is not None and _browser_thread_id is not None and current_tid != _browser_thread_id:
        close_browser_if_open()
    if _page is not None:
        return (_page, None)
    try:
        _playwright = sync_playwright().start()
        _browser = _playwright.chromium.launch(headless=headless)
        _page = _browser.new_context().new_page()
        _browser_thread_id = current_tid
        return (_page, None)
    except Exception as e:
        return (None, str(e))


def run_browser_action(action_line: str, headless: bool = False) -> tuple[bool, str]:
    """
    Ejecuta una acción de navegador. Reutiliza la misma pestaña entre pasos.
    BROWSER:go <url>
    BROWSER:click <selector>
    BROWSER:fill <selector> <texto>
    BROWSER:content
    BROWSER:screenshot [ruta]
    BROWSER:close
    """
    action_line = action_line.strip()
    if not action_line.upper().startswith("BROWSER:"):
        return (False, "No es una acción BROWSER")
    rest = action_line[len("BROWSER:"):].strip()
    parts = rest.split(maxsplit=1)
    verb = (parts[0] or "").lower()
    arg = (parts[1] or "").strip() if len(parts) > 1 else ""

    if verb == "close":
        close_browser_if_open()
        return (True, "Navegador cerrado")

    page, err = _ensure_browser(headless)
    if err:
        return (False, err)
    try:
        if verb == "go" or verb == "navigate":
            url = arg
            if not url.startswith("http"):
                url = "https://" + url
            page.goto(url, timeout=30000)
            return (True, f"Página cargada: {url}")
        if verb == "click":
            page.click(arg, timeout=8000)
            return (True, f"Click en {arg}")
        if verb == "fill" or verb == "type":
            match = re.match(r'["\']([^"\']+)["\']\s*(.*)', arg, re.DOTALL)
            if match:
                selector, text = match.group(1), match.group(2).strip().strip('"\'')
            else:
                sp = arg.find(" ")
                selector = arg[:sp] if sp > 0 else arg
                text = arg[sp+1:].strip().strip('"\'') if sp > 0 else ""
            page.fill(selector, text, timeout=5000)
            return (True, f"Rellenado {selector}")
        if verb == "content":
            text = page.inner_text("body", timeout=5000)[:8000]
            return (True, text or "(vacío)")
        if verb == "screenshot":
            out_path = arg or str(Path(tempfile.gettempdir()) / "browser_screenshot.png")
            page.screenshot(path=out_path)
            return (True, f"Screenshot: {out_path}")
        return (False, f"Acción desconocida: {verb}. Usa go, click, fill, content, screenshot, close")
    except Exception as e:
        return (False, str(e))


def run_desktop_action(action_line: str) -> tuple[bool, str]:
    """
    Control de ratón y teclado. action_line:
    DESKTOP:click <x> <y>
    DESKTOP:type "<texto>"
    DESKTOP:key <key1> [key2]   (ej. alt tab, enter)
    DESKTOP:move <x> <y>
    """
    action_line = action_line.strip()
    if not action_line.upper().startswith("DESKTOP:"):
        return (False, "No es una acción DESKTOP")
    rest = action_line[len("DESKTOP:"):].strip()
    parts = rest.split(maxsplit=1)
    verb = (parts[0] or "").lower()
    arg = (parts[1] or "").strip() if len(parts) > 1 else ""

    try:
        import pyautogui
    except ImportError:
        return (False, "pyautogui no instalado. pip install pyautogui")

    try:
        if verb == "click":
            coords = arg.split()
            if len(coords) >= 2:
                x, y = int(coords[0]), int(coords[1])
                pyautogui.click(x, y)
                return (True, f"Click en ({x},{y})")
            pyautogui.click()
            return (True, "Click en posición actual")
        if verb == "move":
            coords = arg.split()
            if len(coords) >= 2:
                x, y = int(coords[0]), int(coords[1])
                pyautogui.moveTo(x, y)
                return (True, f"Movido a ({x},{y})")
            return (False, "DESKTOP:move x y")
        if verb == "type":
            text = arg.strip('"\'')
            pyautogui.write(text, interval=0.05)
            return (True, f"Escrito: {text[:50]}...")
        if verb == "key" or verb == "hotkey":
            keys = arg.lower().split()
            pyautogui.hotkey(*keys)
            return (True, f"Teclas: {arg}")
        return (False, f"Acción desconocida: {verb}. Usa click, move, type, key")
    except Exception as e:
        return (False, str(e))


def image_to_base64(path: str | Path) -> str:
    """Lee una imagen y la devuelve en base64 para enviar a Ollama."""
    path = Path(path)
    if not path.is_file():
        return ""
    data = path.read_bytes()
    return base64.standard_b64encode(data).decode("ascii")
