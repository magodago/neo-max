# Dashboard y dónde ejecutar los comandos

## 1. Dónde ejecutar `python -m loop_saas review`

Debes ejecutarlo **desde la carpeta raíz del motor**, es decir desde **`neo-max-engine`** (donde está el archivo `loop_saas.py`).

En PowerShell, por ejemplo:

```powershell
cd "c:\Users\dorti\Desktop\NEO MAX\neo-max-engine"
python -m loop_saas review
```

Desde ahí Python encuentra los módulos `revenue`, `tools`, `loop_saas`, etc. Si ejecutas desde `NEO MAX` (la carpeta padre) o desde otra ruta, fallará el import.

**Resumen:** la “raíz” para estos comandos es siempre **`neo-max-engine`**.

---

## 2. ¿La web del dashboard la crea NEO o ya existe?

**La crea (y actualiza) NEO.** No hace falta que crees el repo a mano.

- La **primera vez** que ejecutas `python -m loop_saas review` con `dashboard_repo_name` configurado en `config/saas_loop_config.json` (por ejemplo `"neo-max-dashboard"`):
  1. NEO genera los datos y el HTML en `output/dashboard/` (index.html + dashboard_data.json).
  2. NEO sube ese contenido a GitHub en un repositorio con ese nombre.
  3. Si el repositorio **no existe**, NEO lo **crea** por ti con la API de GitHub.
  4. Después activa GitHub Pages en ese repo para que la web sea pública.

- En **ejecuciones siguientes**, NEO solo **actualiza** los archivos del mismo repo. La URL queda fija, por ejemplo:
  `https://TU_USUARIO.github.io/neo-max-dashboard/`

**Qué debes tener:**  
- `GITHUB_TOKEN` en `.env` (con permisos para crear repos y escribir en ellos).  
- En `config/saas_loop_config.json` el campo `"dashboard_repo_name": "neo-max-dashboard"` (o el nombre que quieras).

No tienes que crear el repo en GitHub manualmente; NEO lo hace la primera vez que publica el dashboard.
