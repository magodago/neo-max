# Cómo funciona NEO Tools (loop autónomo de herramientas)

## Resumen en una frase

NEO Tools es un **loop que cada X horas** intenta descubrir un **tema + 5 herramientas** (o, si falla la validación de mercado, **una sola herramienta** de respaldo), las **genera con Ollama**, las **añade al portal** (sin borrar lo que ya hay), genera **entradas de blog** con enlaces a las tools, y **publica** en GitHub Pages. Opcionalmente puede crear **un portal distinto por tema** (varios repos).

---

## Flujo paso a paso

### 1. ¿Existe el portal?

- Si **no** existe `output/saas-metrics-portal/index.html`:
  - Se crea el **portal inicial** con 5 herramientas base (CAC, LTV, MRR, Churn, Runway).
  - Se publica y termina el ciclo.

### 2. Modo tema (por defecto): descubrir tema + 5 tools

- **Ollama** recibe un prompt y devuelve:
  - **Línea 1:** nombre del tema (ej. "SaaS metrics", "Freelancer pricing").
  - **Líneas 2–6:** 5 títulos de herramientas (ej. "CAC calculator", "Churn rate calculator").
- Si Ollama devuelve solo 4 tools, se pide **una 5.ª** con otro prompt ("You already have these 4 tools: …").
- **Validación de mercado (SerpAPI):**
  - Se valida el **tema** con una búsqueda tipo "{tema} calculator".
  - Si el **market_score** del tema es **< min_market_score** (p. ej. 65), el tema se **rechaza** (ej. "Theme SaaS metrics did not pass validation (score=55)").
- Si el tema **sí pasa**: se construye el bloque de 5 tools (ver más abajo).
- Si el tema **no pasa**: se le pide a Ollama **otro tema distinto** (hasta 3 intentos), con preferencia por "Freelancer pricing", "Small business", "Marketing ROI" para variar y no quedarse siempre en "SaaS metrics". Si **ningún tema pasa** después de los intentos, se pasa al **fallback de una sola herramienta** (paso 4).

### 3. Construcción cuando el tema pasa

- **Opción A – Un portal por tema** (`portal_per_theme: true` en config):
  - Se crea una **carpeta nueva** en `output/portals/<tema-slug>/` (ej. `saas-metrics-calculators`).
  - Se generan las **5 herramientas** ahí, más blog del tema, y se publica en un **repo distinto** (ej. `saas-metrics-calculators`).
- **Opción B – Portal único** (por defecto):
  - Las **5 herramientas** se **añaden** al portal principal (`output/saas-metrics-portal`).
  - Cada una solo se añade si **no existe ya** una tool con el **mismo slug canónico** (ej. "Customer acquisition cost calculator" y "CAC calculator" → mismo slug `cac-calculator`, no se duplica).
  - Si se añaden al menos 2 tools, se generan **N entradas de blog** (configurable) con enlaces a esas tools.
  - Se actualiza **index.html** (grid de tools), **sitemap.xml** y se **publica** el portal.

### 4. Fallback: una sola herramienta

- Cuando **el tema no pasa** validación (o hay timeout de SerpAPI, etc.):
  1. Se intenta **descubrir la mejor idea** con Ollama (8 candidatos) y validar cada uno con SerpAPI; se elige la de mayor **market_score** si supera el umbral.
  2. Si **ninguna idea pasa** (o hay error de red/timeout):
     - Se usa la lista **FALLBACK_TOOL_TITLES** (CAC, LTV, MRR to ARR, Churn, Runway, etc.).
     - Se **filtran** los títulos cuya **versión en slug ya existe** en `portal/tools/` (p. ej. si ya existe `cac-calculator`, no se intenta "CAC calculator" ni "Customer acquisition cost calculator").
     - Se elige **al azar** uno de los que quedan y se intenta **añadir** esa tool.
     - Si falla (p. ej. fallo de Ollama o de lógica), se prueba **otro** de la lista (hasta 3 intentos).
- Si al final **no se añade ninguna** tool (p. ej. todos los fallbacks ya existían o fallaron), el ciclo termina con "No idea passed market validation and fallback tool failed" o "All fallback tools already exist in portal; nothing new to add."

---

## Qué genera cada ciclo

- **Herramientas:** archivos en `portal/tools/<slug>/`: `index.html`, `style.css`, `script.js`. Cada tool es una calculadora o conversor generada por Ollama a partir del título/problema.
- **SEO:** cada página de tool recibe **meta title, description, canonical, Open Graph y JSON-LD** (seo_utils). El portal tiene **sitemap.xml** y **robots.txt**.
- **Blog:** entradas en `portal/blog/` con enlaces internos a las tools (solo si hay al menos 2 tools nuevas en ese ciclo).
- **Publicación:** subida del árbol del portal a GitHub (repo configurado en `portal_repo_name` o, en modo “un portal por tema”, un repo por tema).

---

## ¿Genera otros temas y otras tools?

- **Sí.** Cada ciclo puede:
  - Proponer un **tema nuevo** (Ollama) y, si pasa validación, **5 tools de ese tema** (en portal único o en portal por tema).
  - O, en fallback, **una tool** de la lista fija (CAC, LTV, MRR to ARR, Churn, etc.) que **aún no exista** en el portal.
- Los **temas** no están fijos: Ollama puede sugerir "SaaS metrics", "Freelancer pricing", "Startup finance", etc. Lo que **sí** está acotado es el tipo (SaaS, startup, freelancer, marketing) por el prompt.

---

## ¿Revisa el SEO?

- **Sí.** Para cada tool:
  - Se inyecta **title, description, canonical, og:*, JSON-LD** (revenue/seo_utils).
  - Se asegura que la página esté lista para AdSense (adsense_readiness).
- A nivel de portal: **sitemap.xml** con URLs de landing, tools y blog; **robots.txt** con Sitemap. Tras publicar se hace **ping** al sitemap (sitemap_ping).

---

## Por qué “lo que creó ya existía”

- Puede pasar por dos motivos:
  1. **Mismo concepto, otro nombre:**  
     "Customer acquisition cost calculator" y "CAC calculator" son el **mismo tipo** de tool. Antes, el slug se calculaba solo a partir del título:  
     - "CAC calculator" → `cac-calculator`  
     - "Customer acquisition cost calculator" → `customer-acquisition-cost-calculator`  
     Así se creaban **dos carpetas** para la misma herramienta.
  2. **Fallback sin filtrar bien:**  
     Si la validación de mercado falla (p. ej. timeout de SerpAPI), se usa la lista de respaldo. Si esa lista no comprobaba bien contra las tools **ya existentes** en el portal, podía elegir una que era equivalente a una ya creada.

**Qué se ha cambiado:**

- **Slug canónico:** Títulos que describen el **mismo concepto** (CAC, LTV, MRR to ARR, churn, conversion rate, etc.) se mapean al **mismo slug** (ej. "Customer acquisition cost calculator" y "CAC calculator for startups" → `cac-calculator`). Si `tools/cac-calculator/` ya existe, **no se vuelve a añadir** esa tool.
- **Fallback filtrado:** Los títulos de la lista de respaldo se filtran por ese **slug canónico**: si el slug ya existe en `portal/tools/`, no se intenta añadir esa tool.

Con esto, NEO **no debería** volver a crear una tool que ya existe por ser el mismo concepto con otro nombre.

---

## ¿Qué hacen sitemap, robots y ping?

- **sitemap.xml**  
  Es un archivo (en la raíz del sitio, p. ej. `https://magodago.github.io/saas-metrics-tools/sitemap.xml`) que **lista todas las URLs** del portal: página principal, cada herramienta (`/tools/cac-calculator/`, etc.) y cada entrada del blog. Los buscadores (Google, Bing) usan este archivo para **saber qué páginas existen y cuándo se actualizaron** (`lastmod`). Así indexan antes y más completo.

- **robots.txt**  
  Es un archivo (`/robots.txt`) que indica a los bots de búsqueda **qué pueden rastrear**. En NEO dice: "User-agent: *" (todos), "Allow: /" (todo permitido) y **dónde está el sitemap** ("Sitemap: https://.../sitemap.xml"). No bloquea nada; solo orienta y les dice dónde encontrar el sitemap.

- **ping**  
  Tras publicar, NEO llama a las URLs de "ping" de Google y Bing pasando la URL del sitemap (ej. `https://www.google.com/ping?sitemap=...`). Era para **avisar** a los buscadores de que el sitemap se actualizó. Google y Bing **ya no usan** ese endpoint (devuelven 404/410), así que el ping casi no tiene efecto. Lo que sí importa es: tener **sitemap con `lastmod`** y, si quieres, **enviar la URL del sitemap en Google Search Console** (y Bing Webmaster Tools) para que indexen bien.

**Resumen:** sitemap = lista de URLs para que Google/Bing las indexen; robots.txt = reglas + enlace al sitemap; ping = aviso antiguo (hoy lo importante es el sitemap y Search Console).

---

## Config relevante

- **config/saas_loop_config.json:**
  - `portal_repo_name`: repo del portal principal (ej. `saas-metrics-tools`).
  - `portal_per_theme`: si es `true`, un portal (y repo) por tema.
  - `base_url`, `github_user`: para URLs y publicación.
  - `scoring`, `min_market_score`: umbral de validación (ej. 65).
  - `blog.posts_per_saas`: cuántos posts de blog por bloque de tools.

- **.env:**
  - `GITHUB_TOKEN`: para publicar en GitHub.
  - `SERPAPI_KEY`: para validación de mercado (sin él, las validaciones fallan o dan error).
  - Opcional: `GEMINI_API_KEY` / `OPENAI_API_KEY` para otras partes del engine (las tools las genera Ollama).

---

## Resumen de un ciclo típico (como el tuyo)

1. Ollama propone tema "SaaS metrics" y 5 tools (una de ellas "Churn rate calculator").
2. Validación del tema con SerpAPI → **score=55** → tema **rechazado** (umbral 65).
3. Se intenta **mejor idea** con 8 candidatos de Ollama; validación con SerpAPI → **timeout** ("The read operation timed out").
4. **Fallback:** se elige al azar de la lista una tool que **no exista** por slug; se elige "Customer acquisition cost calculator".
5. Antes del fix: slug `customer-acquisition-cost-calculator` ≠ `cac-calculator` → se **añadía** como tool “nueva”.  
   Con el fix: "Customer acquisition cost calculator" → slug canónico `cac-calculator`; si ya existe `cac-calculator`, **no se añade** y en el siguiente ciclo se probará otro fallback que no exista.

Si quieres, en el siguiente paso podemos revisar juntos el `cycle_summary.log` o la config para afinar umbrales o lista de fallback.
