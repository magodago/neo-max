# Estudio de nichos para el agente de historias y cómo gana dinero

## Por qué este modelo (minihistorias + 1 imagen) gana dinero

1. **AdSense premia tiempo en página y páginas vistas.** Una historia corta (1–2 min lectura) + imagen hace que la gente se quede y que cada “post” sea una página. Más páginas = más impresiones de anuncios y más clics.
2. **Contenido único y “safe”.** Texto generado por LLM + imagen generada (no stock) = contenido original para Google. Temas emotivos, curiosidades o entretenimiento suelen pasar el filtro de AdSense (sin contenido adulto/violento).
3. **Escalable sin tocar código.** El agente publica 1 historia cada X horas. En un año puedes tener 365 páginas en un solo sitio, o varios sitios (varios nichos) con un agente por cada uno.
4. **Coste bajo.** Con Gemini (Nano Banana) o DALL·E: 1 imagen por historia = pocos céntimos. Probar con 1–2 imágenes por historia es barato.

## Cómo gana dinero el agente autónomo (en la práctica)

- **No “cobra” directamente.** El agente no tiene cuenta de banco. Lo que hace es:
  1. Generar y publicar contenido en una web en GitHub Pages (gratis).
  2. Tú, como dueño del sitio, solicitas **AdSense** (o similar) para ese dominio/URL. Cuando Google aprueba, insertas el código de anuncios en las plantillas del sitio (por ejemplo en `stories_agent` se podría añadir un snippet en `build_site.py` para el index y para cada historia).
  3. Los ingresos van a **tu** cuenta de AdSense cuando la gente visita las páginas y hace clic en los anuncios (o ves impresiones).
- **Otras vías:** newsletter (“una historia al día en tu email”) para captar emails y luego vender algo o monetizar con sponsors; redes compartiendo cada historia para llevar tráfico al sitio.

Resumen: **el agente crea el activo (la web con historias); tú monetizas ese activo con AdSense/newsletter/redes.**

---

## Estudio de nichos: cuáles funcionan mejor

Según volumen de búsqueda, competencia y compatibilidad con AdSense:

| Nicho | Ejemplo de tema | Búsquedas / competencia | Notas |
|-------|------------------|--------------------------|--------|
| **Heartwarming / animales** | Historias cortas de animales, rescates, bondad | Alto volumen, competencia media | Muy “safe”, fácil de aprobar AdSense. |
| **Minihistorias de miedo** | Historias cortas de terror (2–3 min) | Buen volumen (“short horror stories”) | Cuidado: AdSense puede ser más estricto con terror; contenido suave suele pasar. |
| **Gatitos / cats** | Curiosidades, anécdotas, “cat stories” | Muy alto volumen | Muy compartible en redes, ideal para 1 imagen por historia. |
| **Datos curiosos / “fun facts”** | Una curiosidad por día + imagen | Alto volumen | Rápido de consumir, buen engagement. |
| **Historias de 1 minuto** | Ficción muy corta, cualquier género | Volumen medio | Permite probar varios tonos (drama, humor, suspense suave). |

**Conclusión:** no hay un solo “mejor” nicho; depende de si priorizas aprobación AdSense (heartwarming, gatitos, curiosidades) o más viralidad (miedo, drama). Una estrategia sólida es **varios sitios en distintos nichos**: un repo y una web para “historias de gatitos”, otro para “minihistorias de miedo”, otro para “heartwarming animals”. Cada uno con su propio `config.json` (o su propia carpeta/instancia del agente) y su `repo_name` / `base_url`.

---

## Varios temas y varias páginas

Sí, el diseño actual lo permite:

- **Un sitio = un nicho.** En `stories_agent/config.json` defines `niche`, `repo_name`, `base_url`. Un agente (un `run_loop.py` en marcha) = un sitio que crece con historias de ese nicho.
- **Varios sitios = varios agentes (o varios configs).** Puedes:
  - Copiar la carpeta `stories_agent` (o usar dos configs) y ejecutar dos procesos: uno con `config_cats.json` (repo `daily-cat-stories`) y otro con `config_horror.json` (repo `short-horror-stories`). Cada uno publica en su repo y su GitHub Pages.
  - O generalizar el agente para que lea una lista de configuraciones y en cada ciclo elija un nicho/repo (por turnos o aleatorio) y publique en el sitio que toque.

Así puedes tener, por ejemplo:

- **daily-heartwarming-stories** → historias emotivas de animales.
- **short-horror-stories** → minihistorias de miedo.
- **daily-cat-stories** → historias/curiosidades de gatos.

Cada sitio tiene su propia URL en GitHub Pages y su propio contenido; el agente solo necesita el `config.json` (y opcionalmente la API de imágenes) para cada uno.

---

## Por qué se eligió este sistema para el agente

- **Automatizable al 100%:** texto (Ollama) + imagen (Gemini u OpenAI) + construir HTML + publicar con el mismo `publish_portal` que usa NEO. Cero intervención una vez configurado.
- **Coste predecible:** solo pagas por imagen (y opcionalmente dominio si no usas github.io).
- **Escalable:** mismo código para muchos nichos; solo cambias nicho, repo y URL en config.

Si quieres, el siguiente paso puede ser: añadir en `stories_agent` la opción de **múltiples configs** (varios nichos/repos en un solo proceso) o dejar que tú ejecutes varios `run_loop` con distintos configs para varios sitios a la vez.
