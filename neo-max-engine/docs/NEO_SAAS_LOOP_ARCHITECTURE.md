# NEO SaaS Loop – Arquitectura y especificación

Objetivo: que NEO genere automáticamente micro-SaaS (páginas + herramientas), blog SEO, monetización, y un loop que valide demanda, publique, mida y decida qué mantener, mejorar o descartar.

---

## 1. Estructura final del portal generado

```
/
  index.html
  style.css
  script.js
  sitemap.xml
  robots.txt
  blog/
    index.html          (índice del blog)
    post-slug-1.html
    post-slug-2.html
    ...
  tools/
    cac/
    ltv/
    mrr/
    churn/
    runway/
    [nuevas herramientas generadas]
  affiliate/
    notion/
    hubspot/
    monday/
    stripe/
    quickbooks/
    paddle/
    chartmogul/
    (cada uno: index.html con redirect o landing de afiliado)
```

Los slugs en `/affiliate/` son páginas que contienen el enlace de afiliado (PartnerStack, Impact, etc.) y un CTA. NEO puede generarlos como landings mínimas o redirects.

---

## 2. Flujo del loop autónomo

1. **Ideas**  
   NEO obtiene una idea de micro-SaaS: desde lista curada (niche_finder) + en el futuro long-tail keywords / tendencias. Se prioriza por demanda y monetización.

2. **Validación de demanda**  
   SerpAPI (Google): búsqueda por título/keyword → `market_score`. Si `market_score < umbral` → descartar y registrar en log; si no, seguir.

3. **Generación**
   - **Herramienta:** Ollama genera HTML/CSS/JS con **SEO completo** (title, meta description, canonical, og, JSON-LD WebApplication). Inputs claros, validación, botón Calcular, resultado dinámico, fórmulas correctas.
   - **Página herramienta:** Se escribe en `portal_root/tools/<slug>/` (index.html, style.css, script.js). Se inyecta bloque monetización (affiliate + AdSense placeholder) y CTA.

4. **Blog**
   - **Inicial:** Mínimo 5 posts largos (1200+ palabras), H1/H2/H3, internal links a herramientas, Schema Article, meta, OG, CTA a herramientas. Palabras clave long-tail SaaS.
   - **Continuo:** Generación automática de 1 post nuevo por semana (Ollama), actualización de sitemap y de índice del blog.

5. **Monetización**
   - Bloques `affiliate-grid` con enlaces de PartnerStack, Impact, FirstPromoter, CJ Affiliate (URLs desde config).
   - AdSense: `<div id="adsense"></div>` placeholder.
   - Lead magnet: formulario “Download PDF” + email (placeholder para MailerLite/ConvertKit).
   - Newsletter: placeholder suscripción.

6. **Publicación**
   - Generar/actualizar `sitemap.xml` y `robots.txt`.
   - Subir todo a GitHub Pages (o, en el futuro, dominio propio vía script deploy).

7. **Métricas y scoring**
   - **Métricas:** Visitas, clicks (en herramientas, affiliate, CTA). Origen: importación desde GA4/CSV o, más adelante, API GA4. Si no hay datos, se usa solo score de calidad.
   - **Score por herramienta (0–100):**  
     `score = 0.5 * quality_score + 0.5 * engagement_score`  
     - `quality_score`: tool_evaluator actual (estructura, HTML/CSS/JS).  
     - `engagement_score`: normalizado de visitas/clicks (ej. percentil 0–100).

8. **Decisiones automáticas**
   - **≥ 70:** Mantener y promocionar (ej. enlazar desde hero o “destacados”).
   - **50–70:** Marcar “mejorar”; NEO puede regenerar copy/diseño o marcar para revisión manual.
   - **< 50:** Descartar: marcar estado `discarded`, registrar en log, opcionalmente dejar de enlazar desde la home.

9. **Registro e historial**
   - SQLite (o CSV) con: herramientas (id, slug, title, path, created_at, status, quality_score, engagement_score, score_final), entradas de blog, métricas por URL/fecha, decisiones (descartado, mejorado, etc.). Todo para dashboard y reportes.

10. **Dashboard**
    - Vista para ti: listado de micro-SaaS, score, estado (activo / mejorar / descartado), visitas, clicks, últimas decisiones. Puede ser HTML estático que consuma un JSON exportado desde la DB (generado por script).

11. **Autonomía**
    - Loop infinito (o por N ciclos): cada X horas/días ejecutar idea → validar → generar → publicar → (cuando haya datos) importar métricas → recalcular scores → aplicar reglas 70/50/<50 → generar nuevo post si toca → reporte resumen en log o dashboard.

---

## 3. SEO completo (on-page y técnico)

- **Por página (home, herramienta, post):**  
  title único, meta description, canonical, og:title, og:description, og:type, robots index/follow.
- **Structured data:**  
  WebApplication en herramientas, Article en posts, FAQPage si hay FAQs.
- **Sitemap y robots:**  
  `sitemap.xml` con todas las URLs; `robots.txt` permitiendo todo y enlazando sitemap.
- **Blog:**  
  Internal links a herramientas y a otros posts; keywords long-tail; CTAs a herramientas.

---

## 4. Diseño y rendimiento

- UX/UI SaaS profesional, responsive mobile-first.
- Hero, CTA, tarjetas con sombra, footer con enlaces y afiliados.
- CSS/JS minificados (o al menos sin comentarios grandes), lazy load en imágenes, objetivo carga < 2 s.

---

## 5. Analítica (placeholders)

- GA4, GTM, Pixel: placeholders en el HTML; tú añades IDs reales en config.
- Los datos para el scoring se obtienen por import (CSV/API) y se guardan en la DB del engine.

---

## 6. Datos y credenciales que tú debes añadir

| Dato | Dónde / para qué |
|------|-------------------|
| **GITHUB_TOKEN** | Publicar repo y GitHub Pages. |
| **SERPAPI_KEY** | Validación de demanda (búsquedas Google). |
| **Ollama** | Corriendo en local para generar herramientas y posts. |
| **Base URL del sitio** | Para canonical, sitemap, og:url (ej. `https://tudominio.com` o `https://usuario.github.io/saas-metrics-tools/`). |
| **Enlaces de afiliado** | PartnerStack, Impact, FirstPromoter, CJ: una URL por producto (Notion, HubSpot, Monday, Stripe, QuickBooks, Paddle, ChartMogul). Se guardan en config (JSON o .env) y el builder los inyecta en `affiliate-grid`. |
| **AdSense** | Cuando lo tengas: ID de cuenta o slot; se sustituye el placeholder `<div id="adsense">` por el script real (o se documenta en config). |
| **Lead magnet / Newsletter** | MailerLite, ConvertKit, etc.: URL del form o endpoint; el HTML ya tiene placeholder (formulario email + botón); tú añades la URL en config para el action del form. |
| **GA4 / GTM / Pixel IDs** | Para analítica real; placeholders en el código, tú pones IDs en config para que el builder los inyecte. |
| **Dominio propio (opcional)** | Si no usas GitHub Pages: dominio y, si aplica, credenciales de deploy (FTP, Vercel, Netlify, etc.) para el script de publicación. |

Archivo de config propuesto: `config/saas_loop_config.json` (o `.env` para secretos y `saas_loop_config.json` para URLs públicas y opciones).

---

## 7. Fases de implementación sugeridas

| Fase | Qué | Prioridad |
|------|-----|-----------|
| 1 | Config (base_url, affiliate URLs, placeholders) + modelo de datos (SQLite) para tools, blog, métricas, decisiones | Alta |
| 2 | Prompt SEO en generación de herramientas + generador sitemap/robots + estructura /affiliate | Alta |
| 3 | Blog generator (Ollama): 1 post completo con schema, internal links, CTA; luego 5 iniciales + 1 semanal | Alta |
| 4 | Portal builder v2: index, /tools, /blog, /affiliate, sitemap, robots, bloques monetización | Alta |
| 5 | Loop de scoring (quality + engagement), reglas 70/50/<50, log a DB y CSV | Alta |
| 6 | Dashboard estático (HTML + JSON export desde DB) para ver micro-SaaS y métricas | Media |
| 7 | Import de métricas desde CSV (export GA4) o preparación para API GA4 | Media |
| 8 | Generación semanal de post + actualización sitemap sin intervención | Media |

Con esto NEO puede crear micro-SaaS, publicarlos, generar blog y enlaces para tráfico, hacer SEO, revisar cuáles funcionan con métricas y dashboard, y escalar en bucle. Los datos que necesitas añadir están listados en la sección 6.

---

## 8. Módulos implementados

| Módulo | Uso |
|--------|-----|
| `config/saas_loop_config.json` | base_url, affiliate URLs, umbrales scoring, placeholders. |
| `revenue/metrics_store.py` | SQLite: tools, blog_posts, metrics_daily, decisions. export_for_dashboard(), export_dashboard_json(). |
| `revenue/seo_utils.py` | sitemap_xml(), robots_txt(), tool_head_seo(), article_head_seo(), inject_seo_into_tool_html(), collect_urls_for_sitemap(). |
| `revenue/affiliate_builder.py` | build_affiliate_section(portal_root, base_url): genera /affiliate/<slug>/index.html. |
| `revenue/blog_generator.py` | generate_blog_post(topic, keyword, base_url, tool_slugs) → (slug, title, html). write_blog_post(). |
| `revenue/portal_builder_v2.py` | build_portal_v2(output_dir, generate_blog_count, register_in_db): landing, tools con SEO, affiliate, blog opcional, sitemap, robots. |
| `loop_saas.py` | review_portal(portal_root): score 70/50/<50, update status, record_decision, CSV log. run_review_and_export(). CLI: `python -m loop_saas review` o `build`. |
| `output/dashboard/index.html` | Dashboard estático: carga dashboard_data.json y muestra tools + decisions. |
| `output/dashboard/dashboard_data.json` | Generado por export_dashboard_json() o run_review_and_export(). |

**Cómo ejecutar**

- Generar portal completo (tools + affiliate + sitemap + robots, sin blog):  
  `python -c "from revenue.portal_builder_v2 import build_portal_v2; build_portal_v2(generate_blog_count=0)"`
- Generar portal con 5 posts de blog (Ollama):  
  `build_portal_v2(generate_blog_count=5)`
- Publicar en GitHub:  
  `python -c "from tools.github_publisher import publish_portal; publish_portal('output/saas-metrics-portal')"`
- Revisar herramientas y exportar dashboard:  
  `python -m loop_saas review`
- Build + publicar + revisar:  
  `python -m loop_saas build`
- Ver dashboard: abrir `output/dashboard/index.html` en el navegador (con `dashboard_data.json` en la misma carpeta).

---

## 9. Checklist: datos que tú debes añadir

| Dato | Dónde | Obligatorio para |
|------|--------|-------------------|
| **GITHUB_TOKEN** | `.env` o variable de entorno | Publicar portal en GitHub Pages |
| **SERPAPI_KEY** | `.env` | Validar demanda (loop de ideas) |
| **Ollama** | Corriendo en local (puerto 11434) | Generar herramientas y posts de blog |
| **base_url** | `config/saas_loop_config.json` | Canonical, sitemap, enlaces (ej. tu dominio o GitHub Pages) |
| **affiliate** | `config/saas_loop_config.json` → `affiliate.<slug>.url` | Sustituir `"#"` por tus enlaces de PartnerStack, Impact, CJ, etc. |
| **AdSense** | Cuando lo tengas: script o slot ID | Sustituir placeholder `<div id="adsense">` en plantillas |
| **Lead magnet / Newsletter** | URL del form (MailerLite, ConvertKit) | `placeholders.lead_magnet_action` y `newsletter_action` en config |
| **Métricas (visitas/clicks)** | Importar a DB o GA4 | Para engagement_score y decisiones 70/50/<50; sin datos se usa solo quality_score |
