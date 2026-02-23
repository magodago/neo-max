# Probar el agente de historias ahora

## ¿Está todo listo?

| Requisito | Estado |
|-----------|--------|
| **Ollama** instalado y en marcha (http://localhost:11434) | Tienes que abrirlo y tener el modelo **qwen2.5:7b-instruct** (o similar). En Ollama: `ollama pull qwen2.5:7b-instruct` |
| **GITHUB_TOKEN** en `.env` | ✅ Ya lo tienes |
| **GEMINI_API_KEY** en `.env` | ✅ Ya está |
| **google-genai** (Python) | Ejecuta: `pip install google-genai` |

## Qué hace **ahora mismo** si lo ejecutas

1. **Genera una historia**  
   Llama a Ollama (modelo qwen2.5) con el tema del config (“heartwarming short stories about animals and kindness”). Obtiene: título, 2–4 párrafos y una frase para la imagen.

2. **Genera una imagen**  
   Envía esa frase a Gemini (Nano Banana) y guarda la imagen en `stories_agent/output/site/images/`.

3. **Monta la web**  
   Crea (o actualiza) la página de esa historia, el índice y el sitemap en `stories_agent/output/site/`.

4. **Publica en GitHub**  
   Sube todo ese sitio al repo **daily-heartwarming-stories**. Si el repo no existe, lo crea y activa GitHub Pages. La URL queda:  
   **https://magodago.github.io/daily-heartwarming-stories/**

5. **Si lo dejas corriendo (sin “once”)**  
   Espera 24 horas y repite: otra historia, otra imagen, actualiza el sitio y vuelve a publicar.

## Cómo ejecutarlo

Abre PowerShell, ve a la carpeta del motor y:

**Prueba de un solo ciclo (recomendado la primera vez):**
```powershell
cd "c:\Users\dorti\Desktop\NEO MAX\neo-max-engine"
pip install google-genai
python -m stories_agent.run_loop once
```

Si todo va bien, verás en consola algo como: “Story generated: …”, “Image saved…”, “Published: https://magodago.github.io/daily-heartwarming-stories/”. Luego puedes abrir esa URL en el navegador.

**Para que siga publicando una historia cada 24 h:**
```powershell
python -m stories_agent.run_loop
```
(Ctrl+C para parar.)

## Si Ollama no está o falla

- Si Ollama no está abierto o el modelo no está instalado, verás “Ollama story failed” y ese ciclo no publicará historia (pero no se rompe nada).
- Solución: abre Ollama, en la terminal ejecuta `ollama pull qwen2.5:7b-instruct` y vuelve a lanzar `python -m stories_agent.run_loop once`.

## Si la imagen falla (Gemini)

- Si falta `pip install google-genai` o la API de Gemini falla, la historia se publica **sin imagen** (solo texto). El resto funciona igual.
