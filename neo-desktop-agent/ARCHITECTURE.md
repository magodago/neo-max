# Arquitectura NEO — Agente que puede hacer cualquier cosa

NEO está pensado como un **agente de escritorio con capacidad total**: si el usuario pide algo, NEO debe intentarlo con las herramientas disponibles y, si no existe un skill, usar búsqueda + scripts/comandos. Inspirado en la filosofía de [OpenClaw](https://docs.openclaw.ai): el modelo aporta la inteligencia; el runtime aporta el sistema (workspace, memoria, herramientas, skills).

---

## 1. Workspace (único directorio de trabajo)

- **Ubicación:** `workspace/` junto al agente (o `config.workspace_dir`).
- **Contenido:**
  - **Bootstrap:** `USER.md`, `IDENTITY.md`, `SOUL.md`, `CONSCIENCE.md`, `AGENTS.md`, `TOOLS.md`, `LEARNED.md` — se inyectan al inicio de cada sesión.
  - **Sesiones:** `sessions/<session_id>.jsonl` — historial de conversación por canal (ej. Telegram chat_id).
  - **Skills:** `skills/*.py` — habilidades cargadas dinámicamente; el agente puede crear nuevas con `CREATE_SKILL`.
  - **Salida:** `output/` — cursos, documentos, juegos, etc. generados por skills.
- El agente **siempre** opera en este workspace (y rutas absolutas que el usuario indique). No hay “varios workspaces”; uno por instalación.

---

## 2. Bootstrap (memoria inyectada)

Cada turno del agente recibe al inicio:

| Archivo       | Uso |
|---------------|-----|
| **USER.md**   | Perfil del usuario (nombre, preferencias, idioma). |
| **IDENTITY.md** | Quién es NEO (nombre, rol). |
| **SOUL.md**   | Tono, límites, qué no hacer. |
| **CONSCIENCE.md** | Consciencia emocional, qué le importa a NEO. |
| **AGENTS.md** | Instrucciones operativas y recordatorios (como “memoria de trabajo”). |
| **TOOLS.md**  | Resumen de herramientas y convenciones (qué acción usar para qué). |
| **LEARNED.md** | Hechos aprendidos sobre el usuario (gustos, contexto) — se actualiza con `LEARN:` en DONE. |

Si un archivo no existe, se crea con una plantilla por defecto. Archivos muy grandes se recortan en el prompt.

---

## 3. Flujo: “Cualquier petición → actuar, no rendirse”

Orden de decisión en cada paso:

1. **¿Hay un skill que encaja con la petición?**  
   → **SÍ:** `SKILL:<nombre> <argumentos>`.  
   → **NO:** seguir al 2.

2. **Actuar con herramientas base:**  
   - **Buscar:** `SEARCH: <consulta>` (sin abrir Google; evita CAPTCHA).  
   - **Ejecutar:** `SCRIPT:python`, `COMMAND:`, `BROWSER:go/click/fill/content`, `INSTALL:`, `DESKTOP:click/type/key`, `SCREENSHOT`, etc.  
   - NUNCA responder `DONE` diciendo “no puedo” o “está fuera de alcance” sin haber intentado al menos **SEARCH** + una acción (SCRIPT, COMMAND, BROWSER, INSTALL).

3. **Si algo falla:**  
   - No repetir el mismo comando.  
   - Usar **SEARCH:** para encontrar otra forma (otra librería, otro método, “without API key”, etc.).  
   - Probar alternativa (otro SCRIPT, COMMAND, BROWSER, INSTALL).

4. **Cuando la tarea quede resuelta:**  
   - `DONE: <resumen>` con lo que el usuario pidió.  
   - Si la solución fue con SCRIPT/COMMAND y es **repetible**, el agente puede ofrecer o usar **CREATE_SKILL: nombre** con el código usado, para que la próxima vez exista un skill y sea más rápido.

5. **Publicar resultados (cursos, juegos, webs, documentos):**  
   Tras generar carpetas/archivos, usar **GITHUB:push** y terminar con **DONE** incluyendo la URL (ej. `https://usuario.github.io/repo/`).

Regla de oro: **si no hay skill, NEO se “busca la vida” con SEARCH + SCRIPT/COMMAND/BROWSER/INSTALL.** No hay “eso no lo hago” sin haber intentado.

---

## 4. Herramientas base (siempre disponibles)

- **SEARCH:** búsqueda en internet (DuckDuckGo, sin abrir navegador).  
- **COMMAND:** una línea de PowerShell.  
- **SCRIPT:python / SCRIPT:powershell:** código multilínea.  
- **BROWSER:** go, click, fill, content, screenshot, close.  
- **DESKTOP:** click, type, key (coordenadas/teclado).  
- **SCREENSHOT:** captura de pantalla (y visión si hay `vision_model`).  
- **INSTALL:** instalar paquete (pip, winget, etc.) por nombre.  
- **GITHUB: push** &lt;ruta&gt; &lt;repo&gt; — publicar carpeta en GitHub Pages.  
- **SKILL:** ejecutar un skill por nombre.  
- **CREATE_SKILL:** crear nuevo skill (nombre + código Python con `def run(task="", **kwargs) -> str`).  
- **DONE:** fin del turno; el texto es lo que ve el usuario.

Detalle y ejemplos en **TOOLS.md** (plantilla en workspace y editable por el usuario).

---

## 5. Skills (extensión dinámica)

- **Carga:** todos los `.py` en `workspace/skills/` con `def run(task="", **kwargs) -> str` (y opcionalmente `DESCRIPTION`).  
- **Uso:** el agente elige `SKILL:<nombre> <argumentos>` cuando la intención encaja con la descripción del skill.  
- **Creación:** el agente puede crear un skill nuevo con **CREATE_SKILL: nombre** y en las siguientes líneas el código Python. Se guarda en `workspace/skills/<nombre>.py` y se recarga en la siguiente invocación.  
- **Autoaprendizaje:** si una tarea se resuelve con SCRIPT/COMMAND y es repetible, el agente puede crear un skill con ese código para futuras peticiones similares.

Skills típicos: cursos, documento_pdf, generar_imagen, juegos_movil, web_sitio, ficha_jugador, clima, compra_ingredientes, magia_historia, etc. La lista exacta está en el prompt como “Skills disponibles”.

---

## 6. Sesiones y estado

- **Sesión:** identificada por `session_id` (ej. chat_id de Telegram). Historial en `sessions/<id>.jsonl`.  
- **Estado NEO:** `neo_state.json` — última interacción, última vez que escribió el usuario, flags proactivos (llamada, GIF, etc.).  
- **LEARNED.md:** se actualiza cuando el agente responde con `LEARN: <hecho>` en un DONE.

---

## 7. Canales (Telegram, webhook, etc.)

- **Telegram:** bot que recibe mensajes, ejecuta el agente con `session_id=chat_id`, y envía la respuesta (y opcionalmente voz, llamada Twilio, etc.).  
- **Proactivo:** scheduler que puede enviar PROPOSE, CALL, GIF según memoria y estado.  
- **Webhook:** mismo agente, otra entrada (HTTP).

El **mismo agente** (mismo workspace, misma memoria, mismos skills) atiende todos los canales; solo cambia el `session_id` y el modo de envío de la respuesta.

---

## 8. Resumen: “Cualquier cosa” + autoaprendizaje

- **Cualquier petición:** skill si encaja → si no, SEARCH + SCRIPT/COMMAND/BROWSER/INSTALL. No DONE de “no puedo” sin haber intentado.  
- **Descomposición:** Peticiones con varias partes (ej. busca IBEX y Bitcoin y resumen) se resuelven con un SEARCH por tema y luego DONE con resumen combinado.
- **Límite de pasos:** Si se alcanza el máximo (60), el agente sintetiza un resumen con lo obtenido para que el usuario reciba algo útil.
- **Autoaprendizaje:** LEARN en DONE para hechos del usuario; CREATE_SKILL para guardar flujos repetibles.  
- **Arquitectura:** un workspace, bootstrap inyectado, herramientas base siempre disponibles, skills cargados desde `workspace/skills/`, sesiones y estado en disco.

Referencia de herramientas: **TOOLS.md** en el workspace.  
Referencia del flujo y la filosofía: este documento (ARCHITECTURE.md).
