# NEO MAX Engine

Motor autónomo que genera portales de micro-SaaS: descubre temas por demanda (Ollama + SerpAPI), crea herramientas y blog, publica en GitHub Pages y revisa con métricas (scoring 70/50). Objetivo: generar tráfico e ingresos con mínima intervención.

## Requisitos

- **Python 3.10+**
- **Ollama** en ejecución (http://localhost:11434) para generar herramientas y posts
- **GitHub**: token con permisos de repo para publicar en GitHub Pages
- **SerpAPI** (opcional pero recomendado): para validar demanda de temas antes de construir

## Configuración rápida

1. **Copia `.env.example` a `.env`** en esta carpeta y rellena los valores reales.
   - **Importante:** Nunca subas `.env` a Git. Contiene secretos (GITHUB_TOKEN, SERPAPI_KEY). Usa siempre `.env.example` como plantilla sin valores reales.
2. Variables en `.env`:
   - `GITHUB_TOKEN` – obligatorio para publicar el portal
   - `SERPAPI_KEY` – para que NEO elija temas por demanda real
   - `BASE_URL` – URL pública del sitio (ej. `https://tuusuario.github.io/saas-metrics-tools`)
3. Ajusta si quieres `config/saas_loop_config.json`: `base_url`, `portal_repo_name`, umbrales de scoring, affiliate, lead magnet (ver más abajo).

## Cómo ejecutar

| Comando | Uso |
|--------|-----|
| `python run_saas_loop.py` | Loop continuo: cada 6 h un ciclo (tema + 5 tools + blog + publicar), cada 24 h revisión y export del dashboard. |
| `INICIAR_LOOP.bat` | Igual que lo anterior (doble clic en Windows). |
| `python -m autonomous_loop` | Un solo ciclo (tema + 5 tools + blog + publicar + ping sitemap). |
| `python -m loop_saas build` | Construye el portal desde cero, publica y hace review. |
| `python -m loop_saas review` | Recalcula scores 70/50, exporta el dashboard e **incluye enlaces a todos los sitios** creados (portal principal + portales por tema). |

Los intervalos y el umbral de validación se leen de `config/saas_loop_config.json` (`cycle_hours`, `review_hours`, `min_market_score`). Por defecto el ciclo es cada **1 h** para generar más contenido (LLM local). Cada 24 h se revisan scores y se **escala** el portal por tema que tenga más visitas (se le añaden 2 posts de blog y se republica).

**Modo un portal por tema:** Si en config tienes `"portal_per_theme": true`, cuando un tema pase la validación SerpAPI (score ≥ 65) NEO creará un **sitio nuevo** (nuevo repo en GitHub, ej. `saas-metrics-calculators`) con ese tema, 5 tools y blog, en `output/portals/<tema>-calculators/`. Así tendrás varios sitios posicionando por vertical. Con `portal_per_theme: false` todo se añade al mismo portal (`portal_repo_name`).

## Importar métricas desde GA4

Para que el scoring use visitas y clicks reales:

1. Exporta desde Google Analytics 4 (o similar) un CSV con columnas: **url_path** (o page_path), **date**, **visits** (o sessions), **clicks** (opcional).
2. Desde la carpeta `neo-max-engine`:
   ```bash
   python -m tools.import_metrics data/ga4_export.csv
   ```
3. La revisión (`loop_saas review` o el ciclo cada 24 h) usará esos datos para priorizar herramientas.

Más detalle: `docs/INGRESOS_MEJORAS_APLICADAS.md`.

## Lead magnet / Newsletter (MailerLite, ConvertKit)

Para capturar emails desde el formulario de la landing:

1. Crea un formulario en MailerLite (o ConvertKit) y obtén la **URL de submit** (action del form).
2. En `config/saas_loop_config.json`, dentro de `placeholders`, pon:
   - `"lead_magnet_action": "https://app.mailerlite.com/..."` (tu URL de submit)
   - Opcional: `"newsletter_action": "..."` si usas otro form.
3. Vuelve a generar/publicar el portal para que el HTML use la nueva URL. Por defecto está `"#"` (no envía a ningún sitio).

## Documentación

- **docs/RUN_PC.md** – Arrancar el loop en un PC siempre encendido, qué hace cada cuánto.
- **docs/AUTONOMOUS.md** – Un ciclo, revisión, programación.
- **docs/INGRESOS_MEJORAS_APLICADAS.md** – Ping sitemap, GA4, AdSense readiness, repo name, lead magnet.
- **docs/NEO_SAAS_LOOP_ARCHITECTURE.md** – Componentes y flujos.

## Estructura del proyecto

- `run_saas_loop.py` – Entrada del loop continuo.
- `autonomous_loop.py` – Un ciclo: tema + 5 tools + blog + publicar.
- `revenue/` – Descubrimiento de ideas, portal_builder_v2, blog, métricas, scoring, AdSense readiness.
- `tools/` – Publicación GitHub, ping sitemap, import métricas, validación mercado.
- `config/saas_loop_config.json` – URL del portal, repo, scoring, blog, placeholders (lead magnet, newsletter).
- `output/saas-metrics-portal/` – Portal generado (herramientas, blog, index, sitemap).
- `output/dashboard/` – Dashboard web (index.html + dashboard_data.json) con **enlaces a todos los sitios** creados. Para **verlo desde fuera de casa**: en `config/saas_loop_config.json` pon `"dashboard_repo_name": "neo-max-dashboard"` (o el nombre del repo que quieras). Cada vez que se exporte el dashboard (cada 24 h o al hacer `loop_saas review`), se publicará en GitHub Pages y podrás abrirlo en `https://TU_USUARIO.github.io/neo-max-dashboard/` desde el móvil o cualquier sitio.

Flujo recomendado: **run_saas_loop** + **portal_builder_v2** (un solo portal en un repo). `portal_engine` (v1) y `loop_engine` son alternativos/legacy.
