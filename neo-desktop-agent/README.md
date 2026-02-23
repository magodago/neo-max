# NEO Desktop Agent

Agente autónomo que **controla tu portátil** y hace lo que le pidas. Si le falta algo (Python, Node, una librería), **se auto-instala** lo necesario y sigue.

## Qué hace (control total)

- **Pantalla:** captura la pantalla (SCREENSHOT). Con un modelo de visión en Ollama (ej. llava), puede "ver" y decidir clics.
- **Navegador:** abre Chrome/Chromium (Playwright), navega a URLs, hace click, rellena formularios, extrae el texto de la página. La misma pestaña se reutiliza entre pasos.
- **Escritorio:** ratón y teclado (pyautogui): click en coordenadas, escribir texto, atajos (alt+tab, enter).
- **Terminal:** comandos PowerShell, scripts Python/PowerShell, instalar lo que falte (pip, winget).
- **Documentos y audio por Telegram:** envías un PDF, DOCX, nota de voz o foto; el agente los descarga, los analiza (extrae texto, transcribe audio con whisper) y devuelve resumen o lo que pidas.
- **GitHub:** puede subir una carpeta a un repo (crea repo, activa Pages). Ideal para "crea un juego y dame el enlace": genera el juego en HTML/JS y hace GITHUB:push para que quede en https://usuario.github.io/repo/.
- **Cursos:** puede generar contenido de curso (lecciones, estructura); para Udemy indica que el material está listo para subida manual o por su API.
- Todo en lenguaje natural: *"Resume este PDF"*, *"Transcribe este audio"*, *"Crea un juego de memoria y envíame el enlace"*, *"Abre Chrome y extrae los datos de esta web"*.

## Requisitos

- **Windows** (PowerShell).
- **Ollama** instalado y en marcha. Modelo: `qwen2.5:7b-instruct` o similar. Para "ver" la pantalla: modelo de visión (ej. `llava`) en config como `vision_model`.

## Instalación

Instala **todo lo necesario** para cualquier tipo de petición (documentos, web, datos, audio, imágenes, etc.):

```bash
cd neo-desktop-agent
pip install -r requirements.txt
playwright install chromium
```

Quedan instalados: navegador (playwright), pantalla/teclado (pyautogui), PDF (pypdf), Word (python-docx), Excel (openpyxl), presentaciones (python-pptx), web (requests, beautifulsoup4, lxml), OCR (pytesseract), transcripción de voz (openai-whisper), datos y gráficos (pandas, numpy, matplotlib), clipboard/markdown/YAML (pyperclip, markdown, PyYAML). El agente sabe que tiene todo eso disponible y lo usará sin perder pasos en instalaciones. Si algo falla o falta, usará INSTALL: o lo buscará en la web. Para OCR con pytesseract opcionalmente instala Tesseract en el sistema (winget install UB-Mannheim.TesseractOCR).

**Por consola (te pide confirmación antes de instalar o comandos delicados):**
```bash
python -m agent "lista los archivos de mi Escritorio"
```

**Por Telegram (recomendado):** envías la tarea desde el móvil o el PC y el agente responde en el chat.

1. Crea un bot en Telegram: abre [@BotFather](https://t.me/BotFather), envía `/newbot`, pon nombre y username.
2. Copia el **token** que te da.
3. En `config.json` pon: `"telegram_bot_token": "TU_TOKEN"`.
4. (Opcional) Restringe quién puede mandar tareas: obtén tu user_id (por ejemplo con [@userinfobot](https://t.me/userinfobot)) y en config: `"telegram_allowed_user_ids": [123456789]`.
5. Arranca el bot (con Ollama corriendo):
   ```bash
   python -m telegram_bot
   ```
6. Abre el chat con tu bot en Telegram y escribe la tarea: *"lista los archivos de mi Escritorio"*.

Las tareas por Telegram se ejecutan con **auto-confirmación** (no pide OK para instalar); solo tú puedes mandar si configuras `telegram_allowed_user_ids`.

**Modo automático por consola:**
```bash
python -m agent --auto "crea una carpeta Proyectos/Test y un archivo README.txt dentro"
```

**Una sola orden:**
```bash
python -m agent --one "¿Qué versión de Python tengo?"
```

## Seguridad

- Por defecto **pide confirmación** antes de: instalar software, borrar archivos, o comandos que contengan `rm`, `del`, `format`, etc.
- Con `--auto` no pide confirmación; úsalo solo en tareas que controles.
- Los comandos que ejecuta se muestran siempre en consola.

## Estructura

```
neo-desktop-agent/
  agent.py           # Loop: tarea, memoria, skills, acciones (BROWSER, COMMAND, SCRIPT, SKILL, etc.)
  memory.py           # Memoria persistente: workspace, USER/IDENTITY/SOUL/AGENTS/TOOLS.md, sesiones JSONL
  skills_loader.py    # Carga skills desde workspace/skills/; el agente puede crear nuevos con CREATE_SKILL
  scheduler.py        # Cron y Heartbeat (tareas recurrentes y revisión periódica)
  webhook_server.py   # Webhooks: POST /hooks/wake, POST /hooks/agent
  executor.py         # Comandos PowerShell, INSTALL, SCRIPT python/powershell
  desktop_control.py   # Pantalla (captura), navegador (Playwright), ratón/teclado (pyautogui)
  telegram_bot.py     # Bot Telegram (usa session_id=chat_id para memoria)
  workspace/          # USER.md, IDENTITY.md, SOUL.md, AGENTS.md, TOOLS.md, sessions/, skills/
  config.json         # ollama, telegram, vision_model, heartbeat, cron_jobs, webhook_token, etc.
  ARCHITECTURE.md     # Arquitectura y comportamiento ante fallos
  OPENCLAW_VS_NEO.md  # Comparativa con OpenClaw
```

## Memoria persistente y sesiones (como OpenClaw)

- **Workspace:** en `workspace/` (o la ruta en `workspace_dir` de config) se crean automáticamente **USER.md**, **IDENTITY.md**, **SOUL.md**, **AGENTS.md**, **TOOLS.md**. Edítalos para dar perfil, preferencias y reglas al agente; se inyectan al inicio de cada ejecución.
- **Sesiones:** por cada `session_id` (p. ej. chat_id de Telegram) se guarda un historial en `workspace/sessions/{id}.jsonl`. Los últimos turnos se pueden inyectar como contexto en la siguiente tarea.
- El bot de Telegram pasa el `chat_id` como sesión; así NEO recuerda el hilo de la conversación.

## Skills (el agente puede crear los que necesite)

- **Skills instalados:** archivos `.py` en `workspace/skills/` con una función `run(task="", **kwargs) -> str` (y opcionalmente `DESCRIPTION`). El agente ve la lista y puede ejecutarlos con **SKILL:nombre argumentos**.
- **Crear skills:** el agente puede crear un skill nuevo con **CREATE_SKILL: nombre** y en las siguientes líneas el código Python. Se guarda en `workspace/skills/` y queda disponible en adelante. Así NEO se extiende solo cuando necesita nuevas capacidades.
- Incluido un ejemplo: `workspace/skills/example_clock.py` (devuelve la hora).

## Automatización: Cron y Heartbeat

- **Heartbeat:** cada N minutos el agente ejecuta un prompt (ej. "Revisa si hay algo pendiente") sin que el usuario escriba. Opcionalmente envía el resultado por Telegram.
- **Cron:** tareas recurrentes a hora fija o cada X minutos/horas, con envío opcional a un chat de Telegram.
- Configuración en `config.json`:

```json
{
  "heartbeat": {
    "enabled": true,
    "interval_minutes": 30,
    "prompt": "Revisa si hay algo pendiente para el usuario.",
    "deliver_to_telegram_chat_id": "TU_CHAT_ID"
  },
  "cron_jobs": [
    {
      "schedule": "09:00",
      "prompt": "Resumen matinal: qué tareas tengo hoy.",
      "deliver_to_telegram_chat_id": "TU_CHAT_ID"
    },
    {
      "schedule": "every 60 minutes",
      "prompt": "Comprueba el correo y resume lo urgente."
    }
  ]
}
```

- Si arrancas el bot con `python -m telegram_bot`, el scheduler se inicia en segundo plano cuando hay `heartbeat` o `cron_jobs` configurados. Necesitas `pip install schedule`.

## Webhooks

- Servidor HTTP (FastAPI) para disparar tareas desde fuera: **POST /hooks/wake** (ejecuta el prompt del heartbeat una vez), **POST /hooks/agent** (body: `{"prompt": "tu tarea", "deliver_to_telegram_chat_id": "opcional"}`). Respuesta 202 con `task_id`; consulta **GET /hooks/agent/{task_id}** para el resultado.
- Auth: header **x-neo-token** o **Authorization: Bearer** con el valor de `webhook_token` en config.
- Arranque: `python -m webhook_server` (puerto por defecto 18790, o `webhook_port` en config). Añade `webhook_token` en config para proteger los endpoints.

## Config (vision, navegador, GitHub, memoria, webhooks)

- **workspace_dir:** ruta del workspace (por defecto `neo-desktop-agent/workspace`).
- **vision_model:** si lo rellenas (ej. `llava`), al usar SCREENSHOT la imagen se envía a ese modelo. `ollama pull llava`.
- **browser_headless:** `true`/`false` para ocultar o mostrar Chrome.
- **github_token** y **github_user:** para que el agente pueda subir carpetas a GitHub.
- **webhook_token:** token para autorizar POST a /hooks/wake y /hooks/agent.
- **webhook_port:** puerto del servidor webhook (default 18790).
