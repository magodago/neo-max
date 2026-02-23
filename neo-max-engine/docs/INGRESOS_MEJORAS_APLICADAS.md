# Mejoras aplicadas para que NEO MAX genere ingresos

Todo lo siguiente está implementado. Objetivo: maximizar probabilidad de tráfico, aprobación AdSense y datos reales para el scoring.

---

## 1. Ping del sitemap a Google y Bing

- **Dónde:** `tools/sitemap_ping.py`
- **Cuándo:** Tras cada publicación del portal (en `autonomous_loop`).
- **Qué hace:** Notifica a Google y Bing la URL del sitemap para que indexen antes.
- **Uso:** Automático. No hace falta configurar nada.

---

## 2. Más posts por tema (5 en vez de 2)

- **Dónde:** `revenue/portal_builder_v2.py` → `add_blog_posts_for_theme` con 5 temas; `autonomous_loop` usa `_blog_posts_per_saas()` (default 5).
- **Temas:** What is X, Best X tools, How to calculate X, X benchmarks, Common mistakes with X.
- **Config (opcional):** En `config/saas_loop_config.json` puedes poner `"posts_per_saas": 5` dentro de `"blog"`. Si no está, se usan 5 por defecto.

---

## 3. Lead magnet / newsletter configurables

- **Dónde:** `config/saas_loop_config.json` → `placeholders.lead_magnet_action` y `placeholders.newsletter_action`.
- **Qué hace:** El formulario de la landing usa `action="{lead_magnet_action}"`. Cuando tengas la URL de MailerLite/ConvertKit, ponla ahí (ej. `"https://app.mailerlite.com/.../submit"`).
- **Por defecto:** `"#"` (no envía a ningún sitio hasta que lo configures).

---

## 4. Import de métricas desde GA4 (CSV)

- **Dónde:** `tools/import_metrics.py`
- **Uso:** Exporta desde GA4 (o similar) un CSV con columnas: `url_path` (o `page_path`), `date`, `visits` (o `sessions`), `clicks` (opcional). Luego:
  ```bash
  python -m tools.import_metrics data/ga4_export.csv
  ```
- **Qué hace:** Rellena `metrics_daily` y actualiza `tools.visits` y `tools.clicks`. El scoring de revisión (70/50/descartar) usará esos datos reales.

---

## 5. Repo name desde config (varios portales)

- **Dónde:** `config/saas_loop_config.json` → `portal_repo_name`; `tools/github_publisher.py` → `publish_portal(portal_root, repo_name_override=None)`.
- **Qué hace:** Si quieres un segundo portal (ej. otro nicho), copia el proyecto o usa otra carpeta de salida y otro `saas_loop_config.json` con otro `portal_repo_name` y otro `base_url`. Al ejecutar el loop se publicará en ese repo.
- **Por defecto:** `saas-metrics-tools`.

---

## 6. Páginas listas para AdSense

- **Dónde:** `revenue/adsense_readiness.py`
- **Qué hace:**  
  - Si una herramienta tiene poco texto en el body, se inyecta un bloque "How to use this calculator" con enlace al blog y a la política de privacidad.  
  - Así cada página tiene más contenido y enlaces legales, lo que ayuda a la aprobación de AdSense.
- **Uso:** Automático al generar cada herramienta (`ensure_tool_page_ready` en `portal_builder_v2._write_tool`).

---

## Resumen

| Mejora              | Automático | Config / acción tuya                          |
|---------------------|-----------|-----------------------------------------------|
| Ping sitemap        | Sí        | Nada                                          |
| 5 posts por tema    | Sí        | Opcional: `posts_per_saas` en config           |
| Lead magnet         | Sí        | Poner URL en `placeholders.lead_magnet_action` |
| Import GA4          | No        | Exportar CSV y ejecutar `import_metrics`      |
| Varios portales     | Sí        | Otro config con otro `portal_repo_name`       |
| Listo para AdSense  | Sí        | Nada                                          |

Con esto NEO tiene control total para orientar el sistema a generar ingresos: más contenido, indexación más rápida, formularios configurables, métricas reales y páginas preparadas para AdSense.
