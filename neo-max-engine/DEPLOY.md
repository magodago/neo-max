# Publicar el portal SaaS Metrics en GitHub

El portal está en **carpeta local** `output/saas-metrics-portal/`. No se sube a GitHub solo por editar archivos; hay que ejecutar el publicador.

## Requisitos

- **GITHUB_TOKEN**: token de GitHub con permisos para crear/actualizar repos y activar Pages.
  - Crear en: GitHub → Settings → Developer settings → Personal access tokens.
  - Permisos: `repo` (y `delete_repo` si quieres borrar repos desde scripts).
  - Puedes ponerlo en un archivo `.env` en la raíz de `neo-max-engine`:
    ```
    GITHUB_TOKEN=ghp_xxxx...
    ```
  - O exportar en la terminal: `set GITHUB_TOKEN=ghp_xxxx...` (Windows) / `export GITHUB_TOKEN=ghp_xxxx...` (Linux/Mac).

## Cómo publicar

Desde la raíz de **neo-max-engine** (donde está `portal_engine.py`):

```bash
python -m portal_engine
```

Eso **genera** el portal (si usas el flujo completo) y **publica** en GitHub.

Solo publicar (sin regenerar), con el portal ya generado en `output/saas-metrics-portal`:

```bash
python -c "from tools.github_publisher import publish_portal; publish_portal('output/saas-metrics-portal')"
```

## Comportamiento

- Si el repo **no existe**: se crea `saas-metrics-tools` bajo tu usuario, se suben todos los archivos del portal y se activa GitHub Pages.
- Si el repo **ya existe**: se actualizan los archivos existentes y se añaden los nuevos. No se borran archivos que ya no estén en la carpeta local.
- **URL final**: `https://<tu-usuario>.github.io/saas-metrics-tools/`

Ejemplo: si tu usuario es `magodago`, la web queda en  
`https://magodago.github.io/saas-metrics-tools/`

## Resumen

| Pregunta | Respuesta |
|----------|-----------|
| ¿Está ya subido? | No. Solo al ejecutar `publish_portal` (o `portal_engine`). |
| ¿Dónde está el código? | En `neo-max-engine/output/saas-metrics-portal/`. |
| ¿Cómo subir/actualizar? | `GITHUB_TOKEN` + `python -m portal_engine` o el `publish_portal(...)` de arriba. |
| ¿Qué URL tiene? | `https://<owner>.github.io/saas-metrics-tools/` |
