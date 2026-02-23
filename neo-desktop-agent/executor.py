"""
Ejecutor seguro de comandos en Windows (PowerShell).
Puede auto-instalar herramientas (INSTALL) y ejecutar scripts (SCRIPT:python/powershell).
"""
import logging
import re
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger("neo_desktop.executor")

# Mapeo: lo que el agente pide -> comando de instalación (Windows)
INSTALL_MAP = {
    "python": "winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements",
    "node": "winget install OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements",
    "nodejs": "winget install OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements",
    "git": "winget install Git.Git --accept-package-agreements --accept-source-agreements",
    "pip": "python -m ensurepip --upgrade",
    "choco": "Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))",
    "playwright": "pip install playwright",
    "chromium": "playwright install chromium",
    "pyautogui": "pip install pyautogui",
    "pypdf": "pip install pypdf",
    "pypdf2": "pip install PyPDF2",
    "python-docx": "pip install python-docx",
    "openai-whisper": "pip install openai-whisper",
    "whisper": "pip install openai-whisper",
    "pytesseract": "pip install pytesseract",
    "python-pptx": "pip install python-pptx",
    "pptx": "pip install python-pptx",
    "requests": "pip install requests",
    "beautifulsoup4": "pip install beautifulsoup4",
    "bs4": "pip install beautifulsoup4",
    "lxml": "pip install lxml",
    "openpyxl": "pip install openpyxl",
    "pandas": "pip install pandas",
    "numpy": "pip install numpy",
    "matplotlib": "pip install matplotlib",
    "pyperclip": "pip install pyperclip",
    "markdown": "pip install markdown",
    "pyyaml": "pip install PyYAML",
    "yaml": "pip install PyYAML",
    "python-dotenv": "pip install python-dotenv",
    "dotenv": "pip install python-dotenv",
}

# Paquetes que NO existen en pip (o son .NET/COM o apps de escritorio). Alternativa sugerida.
BAD_INSTALL_PACKAGES = {
    "microsoft.office.powerpoint",
    "microsoft.office.interop.powerpoint",
    "microsoft.office.interop",
    "presentationframework",
    "presentationframework.aero",
    "libreoffice",
    "libre.office",
    "openoffice",
    "open.office",
    "impress",  # LibreOffice Impress
}
# Mensaje cuando piden presentaciones por pip (no existe)
BAD_INSTALL_MESSAGE = (
    "Este paquete no existe en pip (Office/LibreOffice son programas de escritorio, no pip). "
    "Para crear presentaciones .pptx en Python: INSTALL: python-pptx y luego SCRIPT:python con from pptx import Presentation."
)

# Comandos o patrones que requieren confirmación (destructivos)
DESTRUCTIVE_PATTERNS = [
    r"\brm\s+-rf\b", r"\brmdir\s+/s", r"\bdel\s+/s\s+/q\b",
    r"\bRemove-Item\s+.*-Recurse", r"\bFormat-", r"\bformat\s+\w:",
    r"\bdiskpart\b", r"\breg\s+delete\b",
]


def _is_destructive(command: str) -> bool:
    """True si el comando parece destructivo (borrar, formatear, etc.)."""
    cmd_lower = command.strip().lower()
    for pat in DESTRUCTIVE_PATTERNS:
        if re.search(pat, command, re.IGNORECASE):
            return True
    if "remove-item" in cmd_lower and "-recurse" in cmd_lower:
        return True
    return False


def _needs_confirm_install(command: str) -> bool:
    """True si es una instalación (winget, choco, pip install global, npm install -g)."""
    c = command.strip().lower()
    if "winget install" in c or "choco install" in c:
        return True
    if "pip install" in c and "--user" not in c and "venv" not in c:
        return True
    if "npm install -g" in c or "npm i -g" in c:
        return True
    return False


def run_command(
    command: str,
    cwd: str | Path | None = None,
    timeout_seconds: int = 120,
) -> tuple[int, str, str]:
    """
    Ejecuta un comando en PowerShell.
    Returns (exit_code, stdout, stderr).
    """
    cwd = Path(cwd) if cwd else Path.cwd()
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            encoding="utf-8",
            errors="replace",
        )
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        return (proc.returncode, out, err)
    except subprocess.TimeoutExpired:
        return (-1, "", "Command timed out.")
    except Exception as e:
        return (-1, "", str(e))


def resolve_install(command: str) -> str | None:
    """
    Si command es INSTALL:algo, devuelve el comando real de instalación.
    Si no, devuelve None.
    """
    m = re.match(r"^\s*INSTALL\s*:\s*(\w[\w.-]*)\s*$", command.strip(), re.IGNORECASE)
    if not m:
        return None
    key = m.group(1).strip().lower()
    key = key.replace(" ", "")
    if key in INSTALL_MAP:
        return INSTALL_MAP[key]
    # Pip packages: INSTALL:requests -> pip install requests
    if key not in ("winget", "choco", "python", "node", "nodejs", "git", "pip", "chocolatey"):
        return f"pip install {m.group(1).strip()}"
    return None


def execute(
    command: str,
    cwd: str | Path | None = None,
    confirm_destructive: bool = True,
    confirm_install: bool = True,
    auto_confirm: bool = False,
) -> tuple[bool, str]:
    """
    Ejecuta un comando. Si es INSTALL:xxx, resuelve e instala.
    confirm_*: si True y no auto_confirm, devuelve (False, "pending_confirm") para que el caller pida OK.
    Returns (success, output_or_message).
    """
    raw = command.strip()
    if not raw:
        return (True, "(no command)")

    # Resolver INSTALL:xxx
    resolved = resolve_install(raw)
    if resolved is not None:
        # Interceptar paquetes que no existen en pip (evitar repetir el mismo error)
        if resolved.strip().lower().startswith("pip install "):
            pkg = resolved.strip()[len("pip install "):].split()[0].lower().replace("-", ".")
            if pkg in BAD_INSTALL_PACKAGES or any(bad in pkg for bad in ("microsoft.office", "presentationframework", "libreoffice", "openoffice", "libre.office", "open.office")):
                return (False, f"[exit 1] {BAD_INSTALL_MESSAGE}")
        raw = resolved
        if confirm_install and not auto_confirm:
            return (False, "pending_confirm_install:" + raw)

    if _is_destructive(raw) and confirm_destructive and not auto_confirm:
        return (False, "pending_confirm_destructive:" + raw)

    code, out, err = run_command(raw, cwd=cwd)
    full = (out + "\n" + err).strip() if err else out
    if code != 0:
        full = f"[exit {code}]\n{full}"
    success = code == 0
    return (success, full)


def run_script(
    language: str,
    code: str,
    cwd: str | Path | None = None,
    timeout_seconds: int = 300,
) -> tuple[bool, str]:
    """
    Escribe el código en un archivo temporal, lo ejecuta y devuelve la salida.
    language: "python" o "powershell".
    Returns (success, output).
    """
    code = code.strip()
    if not code:
        return (True, "(script vacío)")
    if code.startswith("```"):
        lines = code.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        code = "\n".join(lines)
    cwd = Path(cwd) if cwd else Path.cwd()
    try:
        if language.lower() == "python":
            suffix = ".py"
            cmd = ["python", "-u"]
        elif language.lower() in ("powershell", "ps1", "pwsh"):
            suffix = ".ps1"
            cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File"]
        else:
            return (False, f"Lenguaje no soportado: {language}. Usa python o powershell.")

        with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False, encoding="utf-8") as f:
            f.write(code)
            path = f.name
        try:
            cmd.append(path)
            proc = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                encoding="utf-8",
                errors="replace",
            )
            out = (proc.stdout or "").strip()
            err = (proc.stderr or "").strip()
            full = (out + "\n" + err).strip() if err else out
            if proc.returncode != 0:
                full = f"[exit {proc.returncode}]\n{full}"
            return (proc.returncode == 0, full)
        finally:
            Path(path).unlink(missing_ok=True)
    except subprocess.TimeoutExpired:
        return (False, "Script superó el tiempo límite.")
    except Exception as e:
        return (False, str(e))
