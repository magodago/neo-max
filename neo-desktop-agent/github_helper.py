"""
Publica una carpeta en GitHub: crea repo (si no existe), sube archivos y activa Pages.
Misma lógica que neo-max-engine/tools/github_publisher: token y usuario desde .env del engine
(GITHUB_TOKEN, GITHUB_USER=magodago) para que las URLs sean igual que en tools SaaS y libro.
Fallback: config.json (github_token, github_user).
"""
import base64
import json
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

logger = logging.getLogger("neo_desktop.github")

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"
# Rutas posibles al .env (engine = mismo que SaaS tools y libro)
_AGENT_ROOT = Path(__file__).resolve().parent
_env_loaded = False


def _env_candidates() -> list:
    """Orden: engine (relativo a agente), cwd/parent (NEO MAX), cwd, agente. Mismo .env que tools/libro."""
    cwd = Path.cwd()
    candidates = [
        _AGENT_ROOT.parent / "neo-max-engine" / ".env",
        cwd.parent / "neo-max-engine" / ".env",
        cwd / "neo-max-engine" / ".env",
        cwd / ".env",
        _AGENT_ROOT / ".env",
    ]
    return [p for p in candidates if p.is_file()]

API_BASE = "https://api.github.com"
BINARY_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".woff", ".woff2", ".mp3", ".wav", ".ogg", ".pdf", ".db", ".pyc"}
SKIP_DIRS = {"__pycache__", ".git", ".venv", "venv", "node_modules"}
REQUEST_TIMEOUT = 30


def _load_config() -> dict:
    if not CONFIG_PATH.is_file():
        return {}
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


# Claves que siempre se sobrescriben desde .env (para que .env gane sobre config/otro)
_GITHUB_ENV_KEYS = {"GITHUB_TOKEN", "GITHUB_USER"}


def _load_env_file(force: bool = False) -> None:
    """Carga .env del engine (igual que tools SaaS y libro). GITHUB_* siempre desde .env."""
    global _env_loaded
    if _env_loaded and not force:
        return
    _env_loaded = True
    for env_path in _env_candidates():
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, _, v = line.partition("=")
                    k, v = k.strip(), v.strip().strip("'\"")
                    if not k:
                        continue
                    # GITHUB_TOKEN y GITHUB_USER siempre desde .env; el resto solo si no estaban
                    if k in _GITHUB_ENV_KEYS:
                        os.environ[k] = v
                    elif k not in os.environ:
                        os.environ[k] = v
            logger.info(
                "GitHub: .env desde %s → GITHUB_USER=%s GITHUB_TOKEN=%s",
                env_path,
                os.environ.get("GITHUB_USER", "") or "(no)",
                "***" if os.environ.get("GITHUB_TOKEN") else "(no)",
            )
            break
        except Exception as e:
            logger.warning("GitHub: no se pudo cargar .env desde %s: %s", env_path, e)


def _request(method: str, url: str, token: str, data: dict | None = None) -> tuple[dict | None, int]:
    body = json.dumps(data, ensure_ascii=False).encode("utf-8") if data else None
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8")
            return (json.loads(raw) if raw else None, resp.status)
    except urllib.error.HTTPError as e:
        try:
            raw = e.read().decode("utf-8")
            return (json.loads(raw) if raw else None, e.code)
        except Exception:
            return (None, e.code)
    except Exception as e:
        logger.warning("Request falló: %s", e)
        return (None, 0)


def _get_owner(token: str) -> str | None:
    """Misma lógica que engine: preferir GITHUB_USER de .env para que la URL sea siempre magodago."""
    _load_env_file()
    body, status = _request("GET", f"{API_BASE}/user", token)
    api_login = body.get("login") if status == 200 and body and isinstance(body.get("login"), str) else None
    env_user = os.environ.get("GITHUB_USER", "").strip()
    if env_user:
        return env_user
    config = _load_config()
    config_user = (config.get("github_user") or "").strip()
    if config_user:
        return config_user
    return api_login


def _repo_exists(token: str, owner: str, repo: str) -> bool:
    _, status = _request("GET", f"{API_BASE}/repos/{owner}/{repo}", token)
    return status == 200


def _create_repo(token: str, repo_name: str, description: str = "") -> bool:
    body, status = _request(
        "POST",
        f"{API_BASE}/user/repos",
        token,
        {"name": repo_name, "description": description or "Created by NEO Desktop Agent", "private": False, "auto_init": True},
    )
    return status in (200, 201)


def _get_file_sha(token: str, owner: str, repo: str, path: str) -> str | None:
    path_enc = urllib.parse.quote(path, safe="/")
    body, status = _request("GET", f"{API_BASE}/repos/{owner}/{repo}/contents/{path_enc}", token)
    if status == 200 and body and isinstance(body.get("sha"), str):
        return body["sha"]
    return None


def _put_file(
    token: str, owner: str, repo: str, path: str, content: str | bytes, message: str, sha: str | None = None
) -> bool:
    enc = base64.b64encode(content if isinstance(content, bytes) else content.encode("utf-8")).decode("ascii")
    payload = {"message": message, "content": enc, "branch": "main"}
    if sha:
        payload["sha"] = sha
    path_enc = urllib.parse.quote(path, safe="/")
    _, status = _request("PUT", f"{API_BASE}/repos/{owner}/{repo}/contents/{path_enc}", token, payload)
    return status in (200, 201)


def _enable_pages(token: str, owner: str, repo: str) -> bool:
    body, status = _request(
        "POST",
        f"{API_BASE}/repos/{owner}/{repo}/pages",
        token,
        {"source": {"branch": "main", "path": "/"}},
    )
    return status == 201 or status == 204 or (status == 200 and body)


def publish_folder(folder_path: str | Path, repo_name: str, description: str = "") -> tuple[bool, str]:
    """
    Sube la carpeta a un repo de GitHub (crea repo si no existe), activa Pages.
    Usa el mismo token y usuario que el engine: .env (GITHUB_TOKEN, GITHUB_USER) → URLs magodago.
    """
    _load_env_file(force=True)  # Siempre recargar para tener .env fresco (por si cwd cambió)
    config = _load_config()
    token = (os.environ.get("GITHUB_TOKEN") or config.get("github_token") or "").strip()
    if not token:
        return (False, "GITHUB_TOKEN no configurado (.env del engine o config.json)")

    root = Path(folder_path).resolve()
    if not root.is_dir():
        return (False, f"No existe la carpeta: {root}")

    owner = _get_owner(token)
    if not owner:
        return (False, "No se pudo obtener usuario GitHub (pon GITHUB_USER=magodago en .env del engine o github_user en config)")

    # Nombre de repo: solo segmento final, ASCII (evita 'ascii codec' en APIs)
    repo_name = repo_name.strip().replace("\\", "/").split("/")[-1].replace(" ", "-").lower()[:100]
    try:
        import unicodedata
        n = unicodedata.normalize("NFKD", repo_name)
        repo_name = "".join(c for c in n if not unicodedata.combining(c)).encode("ascii", "ignore").decode("ascii")
    except Exception:
        pass
    repo_name = re.sub(r"[^\w\-]", "-", repo_name).strip("-")
    if not repo_name:
        return (False, "repo_name vacío")

    # Recoger archivos (omitir __pycache__, .git, etc.)
    files: list[tuple[str, str | bytes]] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        parts = rel.parts
        if any(p in SKIP_DIRS for p in parts):
            continue
        path_str = str(rel).replace("\\", "/")
        try:
            if path.suffix.lower() in BINARY_EXTENSIONS:
                content = path.read_bytes()
            else:
                content = path.read_text(encoding="utf-8")
        except Exception as e:
            return (False, f"No se pudo leer {path_str}: {e}")
        files.append((path_str, content))

    if not files:
        return (False, "La carpeta está vacía o no hay archivos legibles")

    exists = _repo_exists(token, owner, repo_name)
    if not exists:
        if not _create_repo(token, repo_name, description):
            return (False, f"No se pudo crear el repo {repo_name} (¿nombre en uso?)")
        exists = True  # repo creado (puede tener README por auto_init; hay que usar sha para actualizar)

    for path_str, content in files:
        sha = _get_file_sha(token, owner, repo_name, path_str) if exists else None
        msg = f"Update {path_str}" if sha else f"Add {path_str}"
        if not _put_file(token, owner, repo_name, path_str, content, msg, sha=sha):
            return (False, f"Fallo al subir {path_str}")

    _enable_pages(token, owner, repo_name)
    # URL siempre con usuario del .env/config (magodago), nunca con el login de la API
    url_user = (os.environ.get("GITHUB_USER") or config.get("github_user") or owner or "").strip()
    if not url_user:
        url_user = owner
    url = f"https://{url_user}.github.io/{repo_name}/"
    return (True, url)


# Cargar .env al importar para que GITHUB_TOKEN y GITHUB_USER estén disponibles desde el primer uso
_load_env_file()
