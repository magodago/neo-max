"""
github_publisher - Publica micro-herramientas en GitHub (repo + Pages).
Usa GitHub REST API v3. Token desde GITHUB_TOKEN.
"""

import base64
import json
import logging
import os
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

logger = logging.getLogger("neo_max.github_publisher")


def _ascii_slug(name: str) -> str:
    """Convierte nombre a slug ASCII seguro para nombres de repo en GitHub."""
    normalized = unicodedata.normalize("NFKD", name)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_only.strip("_-") or "neo-tool"

API_BASE = "https://api.github.com"
REPO_DESCRIPTION = "Auto-generated micro web tool by NEO MAX"
MAX_RETRIES = 2
REQUEST_TIMEOUT = 30


_env_loaded = False

# Ruta fija al .env del engine (mismo que usa NEO MAX para herramientas/portal)
def _env_path() -> Path:
    return Path(__file__).resolve().parent.parent / ".env"


def _load_env_file(force: bool = False) -> None:
    """Carga variables desde .env en el directorio del engine (si existe). Una sola vez, salvo force=True."""
    global _env_loaded
    if _env_loaded and not force:
        return
    _env_loaded = True
    env_path = _env_path()
    if not env_path.is_file():
        return
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("'\"")
                if key and key not in os.environ:
                    os.environ[key] = value
    except Exception:
        pass


def _get_token(force_reload_env: bool = False) -> str | None:
    """Lee el token: .env del proyecto (mismo que NEO MAX) o variable de entorno GITHUB_TOKEN."""
    if force_reload_env:
        global _env_loaded
        _env_loaded = False
    _load_env_file(force=force_reload_env)
    return os.environ.get("GITHUB_TOKEN", "").strip() or None


def _request(
    method: str,
    url: str,
    token: str,
    data: dict | None = None,
) -> tuple[dict | None, int]:
    """
    Ejecuta request a la API de GitHub.
    Retorna (body_parsed, status_code). body_parsed es None si no hay cuerpo o error.
    """
    body = json.dumps(data, ensure_ascii=False).encode("utf-8") if data is not None else None
    # Mismo formato que usa NEO MAX para herramientas/portal (GitHub API recomienda Bearer)
    auth = f"Bearer {token}"
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": auth,
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
            body = json.loads(raw) if raw else None
        except Exception:
            body = None
        return (body, e.code)
    except Exception as e:
        logger.warning("Request falló: %s", e)
        return (None, 0)


def _get_owner(token: str) -> str | None:
    """Obtiene el login del usuario autenticado. Si la API falla, usa GITHUB_USER de .env."""
    _load_env_file()
    body, status = _request("GET", f"{API_BASE}/user", token)
    api_login = body.get("login") if status == 200 and body and isinstance(body.get("login"), str) else None
    if status != 200 and not api_login:
        msg = (body.get("message") if isinstance(body, dict) else None) or ""
        logger.warning("GitHub GET /user failed: status=%s %s", status, msg)
    # Preferir GITHUB_USER de .env para que todas las URLs sean del mismo usuario (ej. magodago)
    env_user = os.environ.get("GITHUB_USER", "").strip()
    if env_user:
        return env_user
    return api_login


def _create_repo(token: str, repo_name: str, description: str | None = None) -> bool:
    """Crea repositorio público. Retorna True si se creó."""
    body, status = _request(
        "POST",
        f"{API_BASE}/user/repos",
        token,
        {
            "name": repo_name,
            "description": description or REPO_DESCRIPTION,
            "private": False,
            "auto_init": True,
        },
    )
    if status in (201, 200):
        return True
    # 422 suele indicar validación (p. ej. nombre ya existe)
    if status == 422:
        return False
    return False


def _get_file_sha(token: str, owner: str, repo: str, path: str) -> str | None:
    """Obtiene el SHA del archivo en el repo (para actualizar). path con / (puede tener Unicode)."""
    path_encoded = urllib.parse.quote(path, safe="/")
    body, status = _request(
        "GET",
        f"{API_BASE}/repos/{owner}/{repo}/contents/{path_encoded}",
        token,
    )
    if status == 200 and body and isinstance(body.get("sha"), str):
        return body["sha"]
    return None


def _list_contents(token: str, owner: str, repo: str, path: str = "") -> list[dict]:
    """Lista archivos y carpetas en path (vacío = raíz). Cada item tiene name, path, sha, type ('file'|'dir')."""
    path_encoded = urllib.parse.quote(path, safe="/") if path else ""
    url = f"{API_BASE}/repos/{owner}/{repo}/contents/{path_encoded}" if path_encoded else f"{API_BASE}/repos/{owner}/{repo}/contents/"
    body, status = _request("GET", url, token)
    if status != 200 or not body:
        return []
    if isinstance(body, dict) and "message" in body:
        return []
    if isinstance(body, list):
        return [{"name": x.get("name"), "path": x.get("path"), "sha": x.get("sha"), "type": x.get("type", "file")} for x in body if x.get("path")]
    return []


def _delete_file(token: str, owner: str, repo: str, path: str, sha: str, message: str = "Remove") -> bool:
    """Borra un archivo del repo. path con /."""
    path_encoded = urllib.parse.quote(path, safe="/")
    body, status = _request(
        "DELETE",
        f"{API_BASE}/repos/{owner}/{repo}/contents/{path_encoded}",
        token,
        {"message": message, "sha": sha},
    )
    return status in (200, 204)


def clear_repo_contents(repo_name: str) -> bool:
    """
    Borra todo el contenido del repo (solo archivos; las carpetas quedan vacías).
    Útil para 'empezar de cero' antes de publicar un sitio nuevo.
    Retorna True si se borró todo correctamente.
    """
    token = _get_token(force_reload_env=True)
    if not token:
        return False
    owner = _get_owner(token)
    if not owner:
        return False
    to_delete: list[tuple[str, str]] = []  # (path, sha)

    def recurse(p: str) -> None:
        for item in _list_contents(token, owner, repo_name, p):
            path, sha, typ = item.get("path"), item.get("sha"), item.get("type", "file")
            if not path or not sha:
                continue
            if typ == "dir":
                recurse(path)
            else:
                to_delete.append((path, sha))

    recurse("")
    for path, sha in to_delete:
        if not _delete_file(token, owner, repo_name, path, sha, message=f"Clear repo: remove {path}"):
            logger.warning("No se pudo borrar %s", path)
    logger.info("Repo %s: borrados %d archivos", repo_name, len(to_delete))
    return True


def _put_file(
    token: str,
    owner: str,
    repo: str,
    path: str,
    content: str | bytes,
    message: str,
    sha: str | None = None,
) -> bool:
    """Sube o actualiza un archivo en el repo. content puede ser str (texto) o bytes (binario, ej. imágenes)."""
    if isinstance(content, bytes):
        enc = base64.b64encode(content).decode("ascii")
    else:
        enc = base64.b64encode(content.encode("utf-8")).decode("ascii")
    payload = {"message": message, "content": enc, "branch": "main"}
    if sha:
        payload["sha"] = sha
    path_encoded = urllib.parse.quote(path, safe="/")
    body, status = _request(
        "PUT",
        f"{API_BASE}/repos/{owner}/{repo}/contents/{path_encoded}",
        token,
        payload,
    )
    return status in (200, 201)


def _repo_exists(token: str, owner: str, repo: str) -> bool:
    """Comprueba si el repositorio existe."""
    _, status = _request("GET", f"{API_BASE}/repos/{owner}/{repo}", token)
    return status == 200


def _enable_pages(token: str, owner: str, repo: str) -> bool:
    """Activa GitHub Pages con branch main, path /."""
    body, status = _request(
        "POST",
        f"{API_BASE}/repos/{owner}/{repo}/pages",
        token,
        {"source": {"branch": "main", "path": "/"}},
    )
    return status in (200, 201)


def _publish_attempt(
    token: str,
    owner: str,
    repo_name: str,
    files: dict[str, str],
) -> bool:
    """
    Un intento de publicación: asume que el repo ya existe.
    Sube los 3 archivos y activa Pages.
    """
    for path, content in files.items():
        if not _put_file(token, owner, repo_name, path, content, f"Add {path}"):
            return False
    return _enable_pages(token, owner, repo_name)


def publish_tool(tool_path: str) -> str | None:
    """
    Publica la herramienta en GitHub: crea repo, sube index.html/style.css/script.js, activa Pages.
    
    Args:
        tool_path: Ruta al directorio de la herramienta (contiene index.html, style.css, script.js)
        
    Returns:
        URL pública https://{owner}.github.io/{repo}/ o None si falla.
    """
    token = _get_token()
    if not token:
        logger.warning("GITHUB_TOKEN no configurado, no se publica")
        return None

    root = Path(tool_path)
    if not root.is_dir():
        logger.warning("Ruta no es directorio: %s", tool_path)
        return None

    slug = root.name
    repo_slug = _ascii_slug(slug)
    repo_base_name = f"{repo_slug}-neo-tool"

    files = {}
    for name in ("index.html", "style.css", "script.js"):
        fpath = root / name
        if not fpath.is_file():
            logger.warning("Falta archivo: %s", name)
            return None
        files[name] = fpath.read_text(encoding="utf-8")

    # Seguridad: no publicar basura
    html = files.get("index.html", "").strip()
    if not html:
        logger.warning("index.html vacío. Publicación abortada.")
        return None
    if "<html" not in html.lower():
        logger.warning("index.html no contiene <html. Publicación abortada.")
        return None

    owner = _get_owner(token)
    if not owner:
        logger.warning("No se pudo obtener usuario GitHub")
        return None

    # Crear repo (reintentos si el nombre ya existe: añadir timestamp)
    repo_name = repo_base_name
    created = False
    for attempt in range(MAX_RETRIES + 1):
        logger.info("Creando repo: %s", repo_name)
        if _create_repo(token, repo_name):
            created = True
            break
        suffix = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
        repo_name = f"{repo_slug}-{suffix}-neo-tool"
        logger.info("Intento %d: nombre en uso, reintentando como %s", attempt + 2, repo_name)
    if not created:
        logger.warning("Fallo: no se pudo crear repositorio tras %d intentos", MAX_RETRIES + 1)
        return None

    # Subir archivos
    logger.info("Subiendo archivos")
    if not _publish_attempt(token, owner, repo_name, files):
        logger.warning("Fallo al subir archivos o activar Pages")
        return None

    logger.info("Activando Pages")
    # Pages ya se activó en _publish_attempt; si falló, _enable_pages retornó False
    url = f"https://{owner}.github.io/{repo_name}/"
    logger.info("URL final publicada: %s", url)
    return url


PORTAL_REPO_NAME = "saas-metrics-tools"
PORTAL_DESCRIPTION = "SaaS Metrics & Startup Finance – Free calculators by NEO MAX"


def publish_portal(portal_root: str, repo_name_override: str | None = None) -> str | None:
    """
    Publica el portal completo. Por defecto repo saas-metrics-tools; con repo_name_override otro (múltiples portales).
    Usa el mismo .env y token que NEO MAX para las herramientas. Returns URL del portal o None si falla.
    """
    # Recarga .env del engine para usar exactamente el mismo token que el resto de NEO MAX
    token = _get_token(force_reload_env=True)
    if not token:
        logger.warning("GITHUB_TOKEN no configurado, no se publica portal")
        return None

    root = Path(portal_root)
    if not root.is_dir():
        logger.warning("Ruta portal no es directorio: %s", portal_root)
        return None

    index_file = root / "index.html"
    if not index_file.is_file():
        logger.warning("Portal sin index.html. Publicación abortada.")
        return None
    html = index_file.read_text(encoding="utf-8").strip()
    if not html or "<html" not in html.lower():
        logger.warning("index.html del portal inválido. Publicación abortada.")
        return None

    owner = _get_owner(token)
    if not owner:
        logger.warning("No se pudo obtener usuario GitHub")
        return None

    repo_name = (repo_name_override or PORTAL_REPO_NAME).strip() or PORTAL_REPO_NAME
    BINARY_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".woff", ".woff2"}
    files_to_upload: list[tuple[str, str | bytes]] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        path_str = str(rel).replace("\\", "/")
        try:
            if path.suffix.lower() in BINARY_EXTENSIONS:
                content = path.read_bytes()
            else:
                content = path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning("No se pudo leer %s: %s", path_str, e)
            return None
        files_to_upload.append((path_str, content))

    if _repo_exists(token, owner, repo_name):
        logger.info("Repo %s ya existe; actualizando archivos", repo_name)
        for path_str, content in files_to_upload:
            sha = _get_file_sha(token, owner, repo_name, path_str)
            msg = f"Update {path_str}" if sha else f"Add {path_str}"
            if not _put_file(token, owner, repo_name, path_str, content, msg, sha=sha):
                logger.warning("Fallo al subir %s", path_str)
                return None
        _enable_pages(token, owner, repo_name)
        display_user = os.environ.get("GITHUB_USER", "").strip() or owner
        url = f"https://{display_user}.github.io/{repo_name}/"
        logger.info("Portal actualizado: %s", url)
        return url

    base_repo_name = repo_name
    logger.info("Creando repo: %s", repo_name)
    if not _create_repo(token, repo_name, description=PORTAL_DESCRIPTION):
        suffix = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
        repo_name = f"{base_repo_name}-{suffix}"
        logger.info("Nombre en uso, reintentando: %s", repo_name)
        if not _create_repo(token, repo_name, description=PORTAL_DESCRIPTION):
            logger.warning("Fallo: no se pudo crear repositorio del portal. Si es 401, renueva GITHUB_TOKEN en .env")
            return None

    logger.info("Subiendo %d archivos del portal", len(files_to_upload))
    for path_str, content in files_to_upload:
        if not _put_file(token, owner, repo_name, path_str, content, f"Add {path_str}"):
            logger.warning("Fallo al subir %s", path_str)
            return None

    if not _enable_pages(token, owner, repo_name):
        logger.warning("Fallo al activar Pages")
        return None

    display_user = os.environ.get("GITHUB_USER", "").strip() or owner
    url = f"https://{display_user}.github.io/{repo_name}/"
    logger.info("Portal publicado: %s", url)
    return url


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    # Prueba con una ruta de ejemplo
    path = Path(__file__).resolve().parent.parent / "output" / "tools"
    for d in path.iterdir():
        if d.is_dir():
            url = publish_tool(str(d))
            print("URL:", url)
            break
    else:
        print("No hay herramientas en output/tools para publicar")
