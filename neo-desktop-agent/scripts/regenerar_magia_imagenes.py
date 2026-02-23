"""
Regenera las páginas de magia con imágenes (Wikipedia o placeholder con nombre)
y publica en GitHub. Ejecutar desde neo-desktop-agent: python scripts/regenerar_magia_imagenes.py
"""
import sys
from pathlib import Path

# Asegurar que el agente y los skills se encuentran
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "workspace" / "skills"))

def main():
    from magia_historia import run as run_magia
    from github_helper import publish_folder

    print("Regenerando páginas de magia con imágenes (Wikipedia/placeholder)...")
    result = run_magia("inicio")
    print(result)

    out_dir = root / "workspace" / "output" / "magia_historia"
    ok, url_or_err = publish_folder(out_dir, "magia-historia", description="Historia de la Magia · Un mago cada día")
    if ok:
        print("Publicado:", url_or_err)
    else:
        print("Error al publicar:", url_or_err)

if __name__ == "__main__":
    main()
