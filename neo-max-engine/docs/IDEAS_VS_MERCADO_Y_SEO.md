# NEO MAX: Ideas, validación de mercado, SEO y blogs

## 1. ¿De dónde salen las ideas?

**No se buscan en internet.** Las ideas vienen de una **lista fija** en código:

- **Archivo:** `revenue/niche_finder.py`
- **Variable:** `PROBLEMAS_COMERCIALES`: lista de diccionarios con `problema`, `categoria`, `nivel_monetizacion`, `complejidad`.
- **Categorías:** Finanzas personales, Negocios online, Marketing digital, Freelancers, E-commerce, Inversión, Productividad, SaaS.

Cada ciclo del **loop_engine** llama a `generate_commercial_micro_problem()` y obtiene **un problema al azar** de esa lista. No hay scraping ni búsqueda externa para “encontrar” ideas nuevas.

---

## 2. Validación de mercado (aquí sí se usa internet)

**Sí se usa internet** para validar si tiene sentido construir la herramienta:

- **Archivo:** `tools/market_validator.py`
- **API:** SerpAPI (búsqueda en Google).
- **Flujo:** Se hace una búsqueda con el **título del problema** (ej. “Calculadora rentabilidad Airbnb España”), y se lee:
  - `total_results` (estimación de resultados)
  - `ads` (si hay anuncios)
  - `organic_results` (cuántos resultados orgánicos devuelve)

Con eso se calcula un **market_score** (0–100). Si `market_score >= 65` → `should_build = True` y el engine genera la herramienta. Si no, se salta ese ciclo.

Resumen: **ideas = lista fija en código; validación = búsqueda real en Google vía SerpAPI.**

---

## 3. SEO en las micro-herramientas (loop_engine)

Las herramientas sueltas (`*-neo-tool`) se generan con **Ollama** según el prompt de `revenue/microtool_generator.py`:

- El prompt pide: **solo código** (HTML, CSS, JS), sin frameworks, respuesta breve.
- **No** pide: `<title>`, `<meta name="description">`, canonical, Open Graph, JSON-LD, etc.

Por tanto, el SEO de cada micro-herramienta es **lo que la IA incluya por su cuenta** (suele ser poco o nada). El **tool_evaluator** puntúa existencia de archivos, estructura básica de HTML y algo de CSS/JS; **no** puntúa SEO (meta, schema, etc.).

Cada herramienta se publica en un **repo separado** con GitHub Pages; no hay sitemap ni robots global para ese “ecosistema” de herramientas.

---

## 4. SEO y blogs en el portal (saas-metrics-portal)

El **portal_engine** usa `revenue/portal_builder.py` para generar el portal:

- **Landing:** `_build_landing()` genera un HTML **fijo** con:
  - `<title>` y `<meta name="description">` básicos
  - Lista de herramientas, bloque de monetización, footer
- **No** genera: `sitemap.xml`, `robots.txt`, canonical, `og:title`/`og:description`, JSON-LD, FAQs con schema, ni artículos de blog.

Todo el SEO “avanzado” del portal actual (sitemap, robots, canonical, Open Graph, JSON-LD WebApplication/FAQPage, 5 artículos de blog con schema Article, enlaces internos, CTAs) se añadió **a mano** en la conversación con el asistente: son archivos estáticos en `output/saas-metrics-portal/` (index, style.css, script.js, sitemap.xml, robots.txt, `blog/*.html`, `tools/cac/`, etc.). El **portal_builder** no los genera ni los mantiene.

Si ejecutas de nuevo `python -m portal_engine`, el builder puede **sobrescribir** la landing y las herramientas con la versión mínima (sin ese SEO ni blog), a menos que el builder se modifique para incluir SEO y/o no sobrescribir esos archivos.

---

## 5. Resumen

| Qué | Dónde | Cómo |
|-----|--------|------|
| **Ideas** | Lista fija en `niche_finder.py` | No se buscan en internet; se elige un problema al azar. |
| **Validación mercado** | SerpAPI en `market_validator.py` | Búsqueda en Google con el título → market_score → decidir si construir. |
| **Generación** | Ollama en `microtool_generator.py` | Prompt sin instrucciones de SEO. |
| **Puntuación** | `tool_evaluator.py` | Archivos + HTML/CSS/JS; sin criterios SEO. |
| **SEO portal** | No en el engine | El SEO completo del portal actual está hecho a mano en los archivos del repo. |
| **Blogs** | No en el engine | Los 5 artículos en `blog/` son HTML estáticos creados a mano. |

Para que NEO MAX “haga” SEO y blogs de forma automática habría que:

- Incluir en el prompt de generación (micro-herramientas y/o portal) instrucciones de SEO (title, meta description, canonical, etc.) y, si se quiere, schema básico.
- En el portal_builder: generar y escribir `sitemap.xml`, `robots.txt`, y opcionalmente plantillas o generación de entradas de blog (p. ej. con IA) y enlazado interno.
