# Estrategia NEO: ingresos, tráfico y escalado

Ideas para que NEO sea **autónomo al máximo** y **genere más dinero**: más sitios, más contenido, más frecuencia y más vías de monetización.

---

## 1. ¿Una página/sitio nuevo por tema en vez de ampliar uno solo?

**Sí, suele ser mejor para posicionar.**

- **Un solo portal** con 50 tools: una URL (magodago.github.io/saas-metrics-tools), muchos slugs. Google ve “un solo sitio” y compite por muchas keywords a la vez; la autoridad se reparte.
- **Varios sitios (un repo/portal por tema):** por ejemplo “saas-metrics-tools”, “freelancer-calculators”, “startup-runway-tools”. Cada uno tiene su dominio/URL, su sitemap, su tema claro. Más entradas a Google, más long-tail, menos competencia entre tus propias páginas.

**Recomendación:** que NEO pueda crear **un portal (repo) por tema** cuando el tema pase validación: mismo flujo (tema + 5 tools + blog), pero en un repo nuevo (ej. `freelancer-calculators`) y otra `base_url`. Así tienes varios “mini-sitios” posicionando por vertical. El código ya soporta `portal_repo_name` y `base_url` por config; faltaría que el loop **genere un portal nuevo por tema** en lugar de siempre añadir al mismo.

---

## 2. ¿Webs aparte por tema que hablen del tema y lleven a las tools?

**Muy buena idea.** Es el patrón “content hub + product/tools”.

- **Sitio temático:** contenido que la gente busca (guías, “cómo calcular X”, “mejores herramientas para Y”). SEO y tráfico por intención informativa.
- **Desde ese contenido** enlazas a **tus tools** (calculadoras) en la misma web o en otra. El tráfico que llega por el artículo puede usar la tool; más uso = más páginas vistas y más opciones de monetizar (ads, lead magnet, affiliate).

Con **un portal por tema** (punto 1), ese portal ya es “la web de ese tema”: landing + 5 tools + blog sobre ese tema. El blog es justo ese “contenido que habla del tema y lleva a las tools”. No hace falta “otra web” separada: el mismo portal tiene:
- **Herramientas** (las 5 calculators).
- **Blog** (posts tipo “What is X”, “Best X tools”, “How to calculate X”) con enlaces a las tools.

Si quisieras **más** contenido por tema (más posts, más páginas tipo “guía”), se podría aumentar `posts_per_saas` o añadir páginas estáticas por tema (ej. “/guides/runway” con texto largo). La idea es la misma: más contenido útil → más tráfico → más clicks a las tools.

---

## 3. Blogs: ¿separados o por tema dentro de cada portal?

**Dentro de cada portal (por tema) suele ser suficiente y más simple.**

- Un blog por portal, con posts sobre **ese** tema y enlaces a **sus** 5 tools. Así el blog y las tools comparten tema y autoridad.
- Varios blogs “aparte” (repos distintos) complican mantenimiento y reparto de autoridad; solo tendría sentido si quisieras marcas/dominios muy distintos.

**Resumen:** un portal = un tema = landing + 5 tools + blog de ese tema. Es la “web aparte por tema” que comentas, con el blog ya incluido.

---

## 4. Objetivo: autónomo y generar dinero. ¿Más tráfico = más ganancia? ¿Hace falta crear mucho?

**Sí: más tráfico bien monetizado = más ganancia.** Para eso NEO necesita:

- **Crear mucho contenido útil** (tools + texto + blog) que Google quiera rankear → más impresiones y visitas.
- **No solo cantidad:** que cada página tenga sentido (tema claro, intención de búsqueda clara). Por eso “un portal por tema” ayuda: cada sitio tiene un tema y un nicho.
- **Monetizar bien:** AdSense en las tools y en el blog; affiliate donde encaje; lead magnet (email) para luego vender o remarketing. El código ya tiene placeholders para AdSense y affiliate; cuando los conectes, más tráfico = más ingresos.

**Conclusión:** crear **mucho** contenido (varios portales, varios temas, muchos posts) está alineado con el objetivo, siempre que cada pieza sea coherente (un tema, una intención). NEO ya va en esa dirección; el salto es “varios portales” en vez de uno solo.

---

## 5. ¿Por qué cada 6 h? Si el LLM es local, ¿no podemos ir más rápido?

**No hay obligación de 6 h.** Es un valor de config (`cycle_hours` en `saas_loop_config.json`).

- **LLM local (Ollama):** no pagas por uso; el límite es tiempo de CPU y que no sature el PC.
- **SerpAPI:** suele tener límite de consultas/día; más ciclos = más validaciones = más consumo. Ahí sí puede haber un tope.
- **GitHub:** ver punto 6.

**Recomendación:** si quieres más contenido en menos tiempo, puedes bajar a **2 h o 1 h** (o incluso menos) y vigilar:
- Uso de SerpAPI (cuántas validaciones por día).
- Que el PC aguante (Ollama + disco, etc.).

Si un día añades “un portal por tema”, cada ciclo podría ser más pesado (más herramientas + más blog por ciclo), y entonces 4–6 h puede seguir siendo razonable para no saturar.

---

## 6. Límites de GitHub (repos y Pages)

- **Por repo/sitio:** ~1 GB publicados, 1 GB en el repo (recomendado).
- **Banda:** soft limit ~100 GB/mes por sitio.
- **Builds:** soft limit ~10/hora (con push manual no suele ser problema; no es 10 “ciclos NEO”, sino builds de Pages).

**Conclusión:**  
- **Un solo portal** con muchas tools y blogs: bien mientras no te acerques a 1 GB.  
- **Varios portales (un repo por tema):** cada repo es un sitio de hasta 1 GB; 5–10 repos temáticos están muy dentro de lo normal. No hay límite estricto de “número de repos” para uso personal/pequeño; el límite es por repo (tamaño) y por ancho de banda.

---

## 7. Otras acciones además de micro-tools para generar dinero

Ideas que encajan con NEO y el mismo stack (generar contenido, publicar, posicionar):

- **Landing + lead magnet por tema:** “Descarga la guía de métricas SaaS” → formulario (MailerLite/ConvertKit) → email para vender curso, plantillas o consultoría. Ya tienes el placeholder del form en la landing.
- **Affiliate por herramienta:** en cada tool o en el blog, enlaces a software (Notion, HubSpot, Stripe, etc.) con tu link de afiliado. Ya hay sección affiliate en config; falta rellenar URLs reales.
- **Más formatos de contenido:** además de “calculadora”, NEO podría generar **checklists** (HTML/PDF), **comparativas** (tabla “Tool A vs B”) o **miniguías** (una página larga por tema) y publicarlas en el mismo portal o en uno temático. Más páginas = más long-tail.
- **Varios portales temáticos (multi-repo):** ya comentado: un portal por tema, cada uno con su repo y su URL, posicionando por vertical.
- **Automatizar GA4 + decisiones:** importar métricas (ya existe `import_metrics`) y que el scoring 70/50 influya en “repetir tema” o “no volver a crear tools de este tipo” (futuro).

---

## Resumen de prioridades

| Prioridad | Acción | Impacto |
|-----------|--------|--------|
| Alta | **Un portal (repo) por tema** cuando el tema pase validación | Más sitios, más keywords, mejor posicionamiento por vertical |
| Alta | **Bajar `cycle_hours`** a 2–3 h si SerpAPI y PC lo permiten | Más contenido en el mismo tiempo |
| Media | **Aumentar posts por tema** o añadir páginas “guía” por tema | Más contenido útil, más tráfico al blog y a las tools |
| Media | **Conectar affiliate y lead magnet** (URLs reales en config) | Monetizar el tráfico que ya tengas |
| Baja | **Otros formatos** (checklists, comparativas) en el mismo flujo | Más variedad de contenido y más páginas |

**Implementado:** En `config/saas_loop_config.json` puedes usar:
- **`portal_per_theme`: true** – Cuando un tema pasa validación (score ≥ min_market_score), NEO crea un **portal nuevo** en `output/portals/<tema>-calculators/`, lo publica en un **repo nuevo** (ej. `saas-metrics-calculators`) y hace ping del sitemap. Así tienes un sitio por vertical.
- **`portal_per_theme`: false** – Comportamiento clásico: todas las tools se añaden al mismo portal (`portal_repo_name`).
- **`github_user`** – Usuario de GitHub para las URLs de los portales nuevos (ej. `magodago` → `https://magodago.github.io/saas-metrics-calculators`).
- **`cycle_hours`: 1** – Ciclo cada 1 hora para generar más contenido (LLM local).
- **Escalado automático:** Tras cada revisión (cada 24 h), NEO mira qué portales (por tema) tienen **buenos datos** (visitas ≥ 5, desde GA4 import o métricas). Al que más visitas tenga le **añade 2 posts de blog** y lo vuelve a publicar. Así escala contenido donde ya está funcionando.
