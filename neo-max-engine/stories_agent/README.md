# Agente de historias diarias (autónomo)

Genera **una historia corta + una imagen** cada X horas y publica el sitio en GitHub Pages. Pensado para nichos tipo "heartwarming stories", "curiosidades", etc. Monetización: AdSense + opcional newsletter.

## Requisitos

- **Python 3.10+**
- **Ollama** en marcha (historias en texto, gratis)
- **Imágenes:** en `.env` una de: **GEMINI_API_KEY** (Gemini Nano Banana; recomendado) o **OPENAI_API_KEY** (DALL·E 3). En `config.json` pon `"image_provider": "gemini"` o `"openai"`.
- **GITHUB_TOKEN** en `.env` para publicar el sitio

## Configuración

1. En la raíz de **neo-max-engine** (no dentro de stories_agent), en `.env`:
   - `GITHUB_TOKEN=...` (igual que para NEO MAX)
   - Para **Gemini (Nano Banana):** `GEMINI_API_KEY=AIzaSy...` (crear clave en [Google AI Studio](https://aistudio.google.com/apikey)). En `config.json`: `"image_provider": "gemini"`, `"image_model": "gemini-2.0-flash-preview-image-generation"`.
   - Para OpenAI: `OPENAI_API_KEY=sk-...` y `"image_provider": "openai"`.
   - Si usas Gemini, instala: `pip install google-genai`

2. En **stories_agent/config.json** puedes cambiar:
   - `niche`: tema de las historias (ej. "heartwarming short stories about animals", "short horror stories", "fun cat stories")
   - `repo_name`: nombre del repo en GitHub (ej. "daily-heartwarming-stories")
   - `base_url`: URL del sitio (ej. `https://tu-usuario.github.io/daily-heartwarming-stories`)
   - `interval_hours`: cada cuántas horas genera una historia (ej. 24)
   - `image_provider`: `"gemini"` o `"openai"`. `image_model`, `image_size`: para OpenAI; para Gemini el modelo va en `image_model` (ej. gemini-2.0-flash-preview-image-generation)
   - **Formulario de contacto (sin mostrar tu email):** en [Formspree](https://formspree.io) crea un formulario gratis, pon tu email (donde quieres recibir los mensajes) y copia el ID del formulario. En `config.json` pon `"formspree_form_id": "tu-id"`. Los lectores verán un formulario (nombre, email opcional, mensaje) y al enviar te llega a tu correo. Si dejas `formspree_form_id` vacío, se muestra un enlace "Email me" con `author_email`.

## Cómo ejecutar

Desde la carpeta **neo-max-engine** (para que encuentre `tools` y `.env`):

```bash
python -m stories_agent.run_loop
```

O desde dentro de stories_agent:

```bash
cd neo-max-engine
python -m stories_agent.run_loop
```

El agente generará una historia (Ollama), una imagen (OpenAI), actualizará el sitio y lo publicará en GitHub Pages. Cada `interval_hours` repetirá el ciclo.

## Estructura del sitio publicado

- **Index:** lista de enlaces a cada historia
- **story/slug.html:** una página por historia (título, imagen, texto, fecha)
- **sitemap.xml** para SEO

## Coste aproximado

- Texto: gratis (Ollama local)
- Imagen: ~0,04–0,08 USD por imagen (DALL·E 3 standard). Con 1 historia/día ≈ 2–3 USD/mes
