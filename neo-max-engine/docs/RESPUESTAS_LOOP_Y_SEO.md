# Respuestas: loop, SEO y qué hace NEO

## 1. ¿Ha creado el SaaS con las 5 herramientas?

**En las últimas pruebas: no.** El flujo es este:

- **Primero** NEO intenta **modo tema**: pide a Ollama un tema + 5 herramientas (ej. "SaaS metrics" + 5 calculators). Luego **valida el tema** con SerpAPI (búsqueda tipo "{tema} calculator"); si el **score ≥ 65** acepta y genera esas 5 tools.
- En tus logs el tema **"SaaS metrics" ha salido con score 55** (por debajo de 65), así que se **rechaza** y no se crean esas 5 herramientas.
- Entonces pasa al **fallback**: una sola herramienta. Primero prueba con **8 ideas** generadas por Ollama y validadas con SerpAPI; si **ninguna llega a 65**, usa la **lista fija** (LTV calculator, Conversion rate calculator, etc.) y añade **1 herramienta**.
- **Resumen:** Si el tema pasa → 5 tools + posts de blog. Si no → 1 tool (idea validada o de la lista). En tus pruebas ha pasado lo segundo.

Para que cree las 5 herramientas hace falta que algún tema pase (score ≥ 65). Puedes bajar el umbral en `config/saas_loop_config.json` poniendo `"min_market_score": 50` o `55` para que "SaaS metrics" (55) cuente como válido.

---

## 2. ¿Ha creado todo lo referente al SEO?

**Sí.** Cada vez que se añade una herramienta o se construye el portal:

- **Por herramienta:** título, meta description, canonical, Open Graph, JSON-LD (WebApplication).
- **Portal:** `sitemap.xml` (con todas las URLs y `lastmod`), `robots.txt`, índice con grid de tools.
- **Blog:** cada post con Article schema, meta, canonical.
- **Páginas legales:** `privacy.html`, `about.html` (para AdSense y confianza).
- **Listo para AdSense:** si una tool tiene poco texto, se inyecta un bloque "How to use" con enlace al blog y a privacidad.

Todo eso se genera en `revenue/portal_builder_v2.py` y `revenue/seo_utils.py` al añadir tools y al publicar.

---

## 3. "Repo ya existe; actualizando" ¿En 6 h machacará lo que acaba de crear?

**No.** NEO **nunca borra** lo que ya está en el portal.

- **"Repo ya existe; actualizando"** significa: el repositorio de GitHub ya existe, así que en lugar de crearlo de nuevo se **actualizan** los archivos (se sube el contenido actual de la carpeta del portal).
- Esa carpeta es **acumulativa:** tiene las tools anteriores (p. ej. conversion-rate-calculator, ltv-calculator) y se **añaden** las nuevas. Al publicar se sube **todo** el portal (index, todas las tools, blog, sitemap, etc.).
- Dentro de 6 h: si encuentra un **tema válido** → añadirá **5 tools nuevas** a las que ya hay. Si no → añadirá **1 tool nueva**. Las que ya están siguen ahí; no se machacan.

---

## 4. ¿Se puede saber qué ha hecho para buscar y elegir? ¿Logs resumen?

- **En consola** ya se ve parte: tema probado y score, "Ollama generated 8 candidates", "New best idea: X (score=65)" o "No idea passed; trying fallback tool: X".
- **Resumen por ciclo:** al final de cada ciclo se escribe una línea en **`output/cycle_summary.log`**: fecha UTC, modo (theme = 5 tools, single = 1 tool), tema o título elegido, slugs de tools añadidas, posts de blog, publicado sí/no, error si hubo. Así puedes abrir ese archivo y ver qué hizo NEO en cada ciclo.

- **Candidatos e ideas:** en la consola se registra "Ollama generated 8 candidates: título1 | título2 | ..." y "Theme X did not pass validation (score=55)" o "New best idea: X (score=65)". SerpAPI valida cada candidato; si ninguno llega al umbral, se usa la lista de respaldo y se loguea "trying fallback tool: X".

---

*Resumen: 1) En tus pruebas no ha creado 5 tools porque el tema no pasó (55 < 65); sí 1 tool por ciclo. 2) SEO sí se genera. 3) El repo se actualiza sumando contenido, no machacando. 4) Hay resumen de ciclo en un log y se puede detallar candidatos y validación.*
