"""
Script para listar y opcionalmente borrar repos antiguos *-neo-tool (herramientas sueltas).
No toca saas-metrics-tools ni otros repos.
Uso:
  python -m tools.cleanup_old_repos           # solo lista
  python -m tools.cleanup_old_repos --delete  # borra (pide confirmación)
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Cargar .env
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.is_file():
    for line in _env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip("'\"")
            if k and k not in os.environ:
                os.environ[k] = v

API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
SUFFIX = "-neo-tool"  # solo repos que terminan así (antiguos)


def _req(method: str, url: str, data: dict | None = None) -> tuple[dict | list | None, int]:
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {TOKEN}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return (json.loads(raw) if raw else None, resp.status)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8") if e.fp else ""
        try:
            err = json.loads(raw)
            msg = err.get("message", raw) or str(e)
        except Exception:
            msg = raw or str(e)
        perm = e.headers.get("X-Accepted-GitHub-Permissions", "")
        print(f"  [GitHub] {msg}")
        if perm:
            print(f"  [Permiso que pide GitHub] {perm}")
        return (None, e.code)
    except Exception as e:
        print("Error:", e)
        return (None, 0)


def list_repos():
    """Lista repos del usuario que terminan en -neo-tool."""
    if not TOKEN:
        print("GITHUB_TOKEN no configurado (usa .env o variable de entorno)")
        return []
    body, status = _req("GET", f"{API}/user/repos?per_page=100&sort=created")
    if status != 200 or not body:
        print("No se pudieron listar repos. Status:", status)
        return []
    return [r["full_name"] for r in body if r["name"].endswith(SUFFIX)]


def delete_repo(full_name: str) -> bool:
    """Borra un repo. full_name = owner/repo."""
    _, status = _req("DELETE", f"{API}/repos/{full_name}")
    if status == 403:
        print("  Si usas token Fine-grained: Repository permissions → Administration → Read and write")
        print("  Si usas token Classic: scope 'repo' (completo) debe estar activado.")
    return status == 204


def main():
    do_delete = "--delete" in sys.argv or "-y" in sys.argv
    repos = list_repos()
    if not repos:
        print("No hay repos que terminen en '-neo-tool'.")
        return
    print(f"Repos antiguos (*-neo-tool): {len(repos)}")
    for r in repos:
        print("  -", r)
    if not do_delete:
        print("\nPara borrarlos ejecuta: python -m tools.cleanup_old_repos --delete")
        return
    print("\n¿Borrar estos repos? (escribe 'si' para confirmar)")
    if input().strip().lower() != "si":
        print("Cancelado.")
        return
    for r in repos:
        if delete_repo(r):
            print("  Borrado:", r)
        else:
            print("  Fallo al borrar:", r)


if __name__ == "__main__":
    main()
