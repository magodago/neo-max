# NEO MAX – Modo 100% autónomo

Objetivo: que NEO genere micro-SaaS, tráfico y beneficios **solo**. Tú solo revisas el dashboard de vez en cuando.

---

## No machaca lo anterior

Cada ciclo **añade** un nuevo SaaS (tema + 5 herramientas). Las herramientas y SaaS anteriores se mantienen. El dashboard va sumando cada herramienta sin que hagas nada.

---

## Un SaaS = un tema + 5 herramientas coherentes

NEO elige un **tema** (p. ej. "SaaS metrics", "Freelancer pricing") y genera **5 herramientas** de ese mismo tema. Así todo es coherente y las 5 comparten keywords y público.

---

## Qué hace NEO en modo autónomo

1. **Investiga el mercado**  
   No usa una lista fija. Genera candidatos con **Ollama** (ideas de herramientas que la gente busca) y valida cada una con **SerpAPI** (búsqueda real en Google). Elige la idea con **mayor demanda** (market_score).

2. **Construye la herramienta**  
   Genera HTML/CSS/JS con Ollama, aplica **design system** (misma UX en todas las herramientas), SEO completo, bloque de monetización y enlace “More tools”.

3. **Publica**  
   Añade la herramienta al portal, actualiza sitemap y landing, y publica en GitHub Pages (o en tu dominio si lo configuras).

4. **Revisa y decide**  
   Con métricas (visitas/clicks), puntúa cada herramienta. ≥70 mantiene, 50–70 mejora, &lt;50 descarta. Todo queda registrado en la base de datos y en el dashboard.

5. **Páginas de blog que llevan a los SaaS**
   Por cada SaaS (tema) genera **2 posts** de contenido sobre ese tema, con **enlaces internos** a las 5 herramientas. Quien lee el post puede ir a las calculadoras. Todo automático (Ollama). Incluye **Privacy** y **About** para AdSense.

6. **Monetización**  
   Placeholders para AdSense y afiliados. Cuando conectes tu cuenta de AdSense, el dashboard puede mostrar un **revenue estimado** (visitas × RPM) hasta que tengas datos reales.

---

## Cómo ejecutar el ciclo autónomo

**Un ciclo (investigar → construir → publicar):**
```bash
python -m autonomous_loop
```

**Revisar herramientas y exportar dashboard:**
```bash
python -m loop_saas review
```

**Para que corra 24/7 sin intervención:**

- **Cron (Linux/Mac):** cada 6 o 12 horas  
  `0 */6 * * * cd /ruta/neo-max-engine && python -m autonomous_loop`
- **Programador de tareas (Windows):** tarea que ejecute `python -m autonomous_loop` cada X horas.
- **GitHub Actions:** workflow programado que haga checkout, configure `GITHUB_TOKEN`, ejecute `autonomous_loop` y haga push (o use la API para publicar).

Requisitos: **Ollama** en marcha, **GITHUB_TOKEN** y **SERPAPI_KEY** en `.env`.

---

## Experiencia de usuario (UX)

- **Design system** (`tools/_base.css`): mismas variables CSS, tipografía (Inter), tarjetas, botones y estados en todas las herramientas.
- Cada herramienta enlaza `_base.css` + su propio `style.css`.
- Enlace “More tools” / “All calculators” en cada página de herramienta para tráfico interno.

---

## Qué hace NEO para posicionar (SEO)

- **En cada página:** title optimizado, meta description, canonical, Open Graph, JSON-LD (WebApplication en herramientas, Article en posts).
- **Sitemap y robots:** se generan y actualizan al añadir herramientas o blog.
- **Blog:** posts con enlaces internos a las herramientas (internal links) y palabras clave long-tail para que Google asocie búsquedas con tus páginas.
- **Indexación:** cuando el sitio esté en producción, envía el sitemap en Google Search Console (manual o por API) para que Google rastree todo.

---

## AdSense y beneficios

- Páginas **Privacy** y **About** para cumplir políticas.
- Placeholder `<div id="adsense">` en las plantillas; cuando tengas cuenta, sustituye por tu script en la config o en el builder.
- El **dashboard** muestra un revenue estimado (visitas × RPM de ejemplo) hasta que conectes AdSense; luego puedes sustituir por datos reales si exportas desde AdSense o GA4.

---

## Resumen

| Tú haces | NEO hace |
|----------|----------|
| Revisar el dashboard de vez en cuando | Investigar mercado, elegir idea con más demanda |
| Poner GITHUB_TOKEN, SERPAPI_KEY, Ollama | Construir herramienta, aplicar design system, SEO |
| Conectar AdSense cuando quieras | Publicar, revisar scores, descartar o mejorar |
| Opcional: programar cron/scheduler | Generar blog, actualizar sitemap, registrar decisiones |

Con esto NEO puede ser **autómata y orientado a beneficios**: genera herramientas útiles, con buena UX y SEO, listas para monetizar con AdSense cuando las conectes.
