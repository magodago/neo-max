# Arrancar NEO MAX en el PC (siempre encendido)

## Qué hace el loop

- **No machaca nada:** cada ciclo AÑADE un nuevo SaaS (un tema + 5 herramientas coherentes). Las anteriores siguen en el portal.
- **Un SaaS = un tema + 5 herramientas del mismo tema** (p. ej. "SaaS metrics" → CAC, LTV, MRR, Churn, Runway). Coherencia total.
- **Blog:** por cada SaaS crea 2 páginas de contenido (posts) con enlaces a las 5 herramientas. La gente que lee el post puede ir a las herramientas.
- **Dashboard:** se va llenando solo. Cada herramienta se registra en la base de datos; cuando corre la revisión (cada 24 h) se exporta `dashboard_data.json` y el dashboard muestra todo sin que hagas nada.
- **SEO para posicionar:** NEO genera sitemap.xml, robots.txt, meta title/description y canonical en cada página, JSON-LD (WebApplication/Article), y los posts del blog con internal links a las herramientas. Así Google indexa y el tráfico puede llegar por búsquedas.

## Parámetros para arrancar

1. **Copia `.env.example` a `.env`** en la raíz de `neo-max-engine` y rellena (no subas `.env` a ningún repositorio; contiene secretos; usa `.env.example` como plantilla):
   - `GITHUB_TOKEN` – token de GitHub (repo + Pages). Obligatorio para publicar.
   - `SERPAPI_KEY` – para que NEO investigue demanda en Google. Obligatorio para elegir temas por demanda.
   - `BASE_URL` – URL pública del sitio (ej. `https://tuusuario.github.io/saas-metrics-tools`).

2. **Ollama** debe estar abierto en el PC (puerto 11434). Sin Ollama no se generan herramientas ni posts.

3. **AdSense y afiliados:** no son necesarios para arrancar. Cuando los tengas, los añades en `config/saas_loop_config.json` (affiliate URLs) y/o en las plantillas (AdSense). Mientras tanto NEO sigue creando SaaS y posicionando.

## Cómo arrancar

**Opción A – Doble clic**  
Ejecuta `INICIAR_LOOP.bat`. El loop correrá hasta que cierres la ventana (Ctrl+C).

**Opción B – Terminal**  
Desde la carpeta `neo-max-engine`:
```bash
python run_saas_loop.py
```

- Por defecto cada **6 horas** crea un SaaS (tema + 5 herramientas + 2 posts) y publica, y cada **24 horas** revisa scores y exporta el dashboard. Los intervalos y el umbral de validación de mercado se leen de `config/saas_loop_config.json` (`cycle_hours`, `review_hours`, `min_market_score`).

## Ver el dashboard

1. Después de al menos una revisión (o un ciclo que haya registrado herramientas), en `output/dashboard/` estará `dashboard_data.json`.
2. Abre `output/dashboard/index.html` en el navegador (o sirve esa carpeta). Verás herramientas, visitas, revenue estimado y decisiones. Se actualiza solo cuando corre la revisión.

## Resumen

| Tú pones ahora | NEO hace solo |
|----------------|---------------|
| GITHUB_TOKEN, SERPAPI_KEY, BASE_URL en .env | Crear SaaS (tema + 5 tools + 2 posts), publicar, no machacar lo anterior |
| Ollama abierto | Generar herramientas y blog con IA |
| (Luego) AdSense y afiliados en config | Seguir igual; cuando los añadas, el sitio ya estará listo para monetizar |

El dashboard es bonito y se va llenando con cada SaaS que NEO crea, sin que tengas que hacer nada más.
