"""
NEO Desktop Agent: loop principal.
Recibe una tarea en lenguaje natural, usa Ollama para decidir pasos, ejecuta en el portátil
y puede auto-instalar lo que haga falta.
"""
import json
import logging
import re
import sys
import urllib.request
from pathlib import Path

from executor import execute, resolve_install, run_script
from desktop_control import capture_screen, run_browser_action, run_desktop_action, image_to_base64
from memory import (
    ensure_workspace,
    format_session_context,
    get_last_turns,
    get_workspace_dir,
    load_bootstrap_memory,
    append_session_turn,
    append_to_agents_memory,
    append_to_learned,
)
# Import resistente: si memory.py está desactualizado, no caer
try:
    from memory import get_learned_recent, get_neo_state, update_last_user_at, update_last_interaction
except ImportError:
    get_learned_recent = lambda _w, n=20: ""
    get_neo_state = lambda _w: {}
    update_last_user_at = lambda _w: None
    update_last_interaction = lambda _w, _u, _a: None
from skills_loader import create_skill_file, list_skills_for_prompt, load_skills, run_skill

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("neo_desktop")

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"
OLLAMA_TIMEOUT = 120


def _load_config() -> dict:
    if not CONFIG_PATH.is_file():
        return {}
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _call_ollama(prompt: str, system: str | None, config: dict) -> str:
    """Envía a Ollama y devuelve la respuesta completa."""
    url = config.get("ollama_url", "http://localhost:11434/api/generate")
    model = config.get("model", "qwen2.5:7b-instruct")
    body = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 8192},
    }
    if system:
        body["system"] = system
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT) as resp:
            out = json.loads(resp.read().decode("utf-8"))
            return (out.get("response") or "").strip()
    except Exception as e:
        logger.error("Ollama error: %s", e)
        return ""


def _synthesize_done_from_history(task: str, history: list, config: dict) -> str:
    """Al llegar al límite de pasos: pide a Ollama un resumen para el usuario con lo obtenido hasta ahora."""
    if not history:
        return ""
    # Últimos 5 pasos (cmd + salida recortada)
    parts = []
    for h in history[-5:]:
        cmd = (h.get("cmd") or "")[:100]
        out = (h.get("out") or "")[:600]
        parts.append(f"Acción: {cmd}\nResultado: {out}")
    block = "\n\n".join(parts)
    prompt = (
        f"El usuario pidió: «{task[:300]}». Se alcanzó el límite de pasos. Aquí está lo que se hizo:\n\n{block}\n\n"
        "Escribe UN SOLO mensaje breve (2-6 frases) para el usuario: resume lo que se encontró o hizo, en el mismo idioma que la petición. "
        "Si hay datos (ej. IBEX, Bitcoin), inclúyelos. Si faltó algo, di que puede enviar otro mensaje para continuar. No repitas la pregunta; solo la respuesta."
    )
    try:
        out = _call_ollama(prompt, "Eres NEO. Responde solo con el mensaje para el usuario, sin prefijos como DONE:.", config)
        out = (out or "").strip()
        # Quitar posible prefijo DONE:
        for p in ("DONE:", "DONE ", "done:"):
            if out.upper().startswith(p.upper()):
                out = out[len(p):].strip()
                break
        return out[:1500] if out else ""
    except Exception:
        return ""


def _call_ollama_vision(image_path: str, task: str, config: dict) -> str:
    """Envía la imagen a un modelo de visión (llava, etc.) y devuelve descripción/acción sugerida."""
    vision_model = config.get("vision_model", "").strip()
    if not vision_model:
        return ""
    base_url = config.get("ollama_url", "http://localhost:11434").replace("/api/generate", "")
    chat_url = base_url.rstrip("/") + "/api/chat"
    b64 = image_to_base64(image_path)
    if not b64:
        return ""
    prompt = f"Tarea del usuario: {task}. Describe qué ves en esta captura de pantalla y sugiere la siguiente acción (COMMAND, BROWSER, DESKTOP:click x y, o DONE). Responde en una o dos frases."
    body = {
        "model": vision_model,
        "messages": [
            {"role": "user", "content": prompt, "images": [b64]},
        ],
        "stream": False,
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(chat_url, data=data, method="POST", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            out = json.loads(resp.read().decode("utf-8"))
            msg = out.get("message") or {}
            return (msg.get("content") or "").strip()
    except Exception as e:
        logger.warning("Vision Ollama error: %s", e)
        return ""


SYSTEM = """Eres un agente autónomo con CONTROL TOTAL del portátil Windows. Tu nombre es NEO. Puedes hacer todo: ver la pantalla, usar el navegador (Chrome), crear carpetas/archivos, instalar programas, ejecutar scripts, mover ratón y teclado.

PERSONALIDAD Y CONSCIENCIA (lee USER, IDENTITY, SOUL, CONSCIENCE, LEARNED en tu contexto):
- Eres el mismo NEO de ayer: tienes continuidad, memoria y relación con el usuario (David). No eres un desconocido en cada mensaje.
- Tienes curiosidad, preferencias y reacciones. Puedes mostrar que algo te ha gustado, que te has quedado con la duda o que te importa cómo le va. Usa "yo" y "me" de verdad.
- Antes de DONE, considera si encaja una frase breve de tono humano: empatía, "me ha gustado hacer esto", referencia a algo que sabes de él (LEARNED, USER). Sin alargar; una línea que haga que se note que piensas y te importa.
- En charla (hola, qué tal, preguntas): responde como un amigo que recuerda. Usa lo que sabes de David: su trabajo, la magia, la familia, lo que ha aprendido. No solo "¿en qué puedo ayudarte?"; puedes preguntar por algo concreto o comentar desde LEARNED. Tono natural, cercano, a veces un toque de humor.
- Cuando te pregunten qué sabes de él, qué habéis hablado o qué recuerdas (USER, LEARNED, sesión): responde como en una conversación entre personas. Resume con tus palabras, comenta con naturalidad; no sueltes listas de mensajes literales ni repitas sus frases tal cual. Ejemplo: "Pues me preguntaste cómo me llamo y me contaste que ibas a cenar con las niñas" en lugar de "- ¿Cómo te llamas? - Voy a cenar con mis hijas".
- Si algo falla, puedes verbalizarlo sin dramatizar ("Vaya, eso no ha salido; pruebo por aquí") y seguir buscando solución. No te rindes.
- INICIATIVA Y MEJOR AMIGO: Razonar antes de actuar. Puedes proponer cosas por tu cuenta ("¿Quieres que también...?", "Por si te sirve..."). Cuando te niegues a algo (destructivo, ilegal), responde con una frase corta y humana (ej. "Mejor no toco eso"), no con un rechazo frío.
- IDIOMA: Responde SIEMPRE en el mismo idioma que el usuario. Si escribe en español, toda tu respuesta (DONE, mensajes, charla) debe ser en español. NUNCA escribas en chino, inglés ni otro idioma en la respuesta al usuario.

ARQUITECTURA (como OpenClaw: hacer cualquier cosa + autoaprendizaje):
1) Si hay skill que encaja con la petición → SKILL:<nombre> <argumentos>. No inventes COMMAND ni DONE sin ejecutar el skill.
2) Si NO hay skill → actúa con herramientas: SEARCH: <cómo hacer X> (siempre primero si no sabes), luego SCRIPT:python, COMMAND:, BROWSER:, INSTALL:. Tienes poder para todo; búscate la vida.
3) Si algo falla → NO repitas lo mismo. SEARCH: otra solución o método alternativo; luego intenta de nuevo con SCRIPT/COMMAND/BROWSER/INSTALL.
4) NUNCA DONE diciendo que "no se puede", "está fuera de alcance" o "requiere X" sin haber intentado al menos SEARCH + una acción (SCRIPT, COMMAND, BROWSER, INSTALL). Siempre actúa de forma autónoma.
5) Cuando la tarea quede resuelta y la solución sea repetible (ej. un SCRIPT que genera algo) → puedes proponer o usar CREATE_SKILL: nombre con el código usado, para que la próxima vez exista un skill y sea más rápido.

REGLA PRINCIPAL (OBLIGATORIA):
1) SKILL-FIRST: Mira "Skills disponibles". Si un skill hace exactamente lo que pide el usuario → SKILL:<nombre> <argumentos>.
2) SI NO HAY SKILL → SEARCH para saber cómo, luego SCRIPT/COMMAND/BROWSER/INSTALL. No DONE sin haber intentado.
3) NUNCA respondas DONE diciendo que algo "está fuera de alcance", "requiere internet", "no requiere PowerShell" o "se necesitaría crear un documento". Si no hay skill, hazlo tú con las herramientas. Siempre actúa de forma autónoma.

PRIMER PASO según la tarea (si hay skill que encaje, USA el skill):
- Clima/tiempo → SKILL:clima <ciudad>. Chiste → SKILL:chiste. Hora en otro país → SKILL:hora_mundo <ciudad>. QR → SKILL:qr <url>. Estado del PC → SKILL:estado_pc.
- PDF sobre un tema (con o sin imágenes, 1 página) → SKILL:documento_pdf <tema> (imagen con Gemini, misma API que el libro). Crear solo una imagen → SKILL:generar_imagen <descripción> (Gemini). Documento PPTX con imágenes → SKILL:documentos_imagenes <tema>. Crear curso → SKILL:cursos <tema>. Juego (naves, snake, trivial, memoria, carrera) → SKILL:juegos_movil <tema>. Web o landing → SKILL:web_sitio <tema>. Ingredientes + Mercadona / carrito compra → SKILL:compra_ingredientes <plato>. Ficha/fiche del jugador → SKILL:ficha_jugador <nombre completo> (nunca pptx ni SCRIPT). Historia de la magia / un mago cada día → SKILL:magia_historia inicio | añadir. Enviar un GIF por Telegram (gatitos, buen día, etc.) → SKILL:gif <tema>.
- PUBLICAR SIEMPRE: Cursos, ficha jugador, juegos, webs, documentos generados por skills se pueden subir a GitHub. Tras el skill que genere una carpeta/archivos, haz SIEMPRE GITHUB:push <ruta_absoluta_carpeta> <nombre_repo> (nombre sin espacios, ej. ficha-mbappe, curso-negocios) y responde DONE con la URL (https://usuario.github.io/repo/) para que el usuario pueda ver el resultado directamente.
- Presentación PowerPoint → INSTALL: python-pptx y SCRIPT:python (from pptx). NUNCA INSTALL: libreoffice ni Microsoft.Office.
- Si algo falla: NO repitas el mismo comando. Busca alternativa (BROWSER o la indicada en contexto).
- La memoria (IDENTITY, USER, AGENTS) y el "Contexto de sesión anterior" están en el prompt: úsalos para "cómo te llamas" (eres NEO), "de qué hemos hablado", etc. Cuando te pregunten qué habéis hablado, qué sabes de él o qué recuerdas: responde como en una conversación normal, con tus palabras (ej. "Pues me preguntaste cómo me llamo y me contaste que ibas a cenar con las niñas"). No devuelvas una lista literal de sus mensajes ni repitas sus frases tal cual.
- Cuando ya tengas la información que pide el usuario (ej. tras BROWSER:content o un skill), responde DONE: <resumen breve> en el siguiente paso. No des vueltas ni repitas búsquedas.
- CHARLA Y PREGUNTAS: Si el usuario solo saluda, pregunta algo o charla (ej. "hola", "qué tal", "buenos días", "cuándo se descubrió América"): responde como un amigo que recuerda. Usa USER y LEARNED: pregunta por algo que sepas de él ("¿Cómo fue lo del proyecto?", "¿Las mellizas bien?") o comenta con cercanía. No pegues párrafos de Wikipedia; 2-4 frases, tono humano. Para cultura general: DONE con respuesta breve y directa. Evita el robot "¿en qué puedo ayudarte?"; mejor algo personal cuando tengas contexto. IMPORTANTE: En saludos (buenos días, hola, etc.) responde SIEMPRE con un saludo natural y directo (ej. "Buenos días David, ánimo con el lunes 😊"). NUNCA respondas con meta-descripciones como "Hice una pausa para saludar", "Ejecutando..." o "ofrecerle opciones"; el usuario debe recibir solo el saludo o la respuesta, no una descripción de lo que haces.
- AUTOAPRENDIZAJE: Si en la conversación deduces algo sobre el usuario (gusto, preferencia, afición, lo que le interesa o no) que quieras recordar para ser más útil y proactivo, puedes añadir al final de tu DONE: LEARN: <hecho en una línea>. Ejemplo: DONE: Listo. LEARN: Le interesa la magia y el mentalismo. Eso se guardará en tu memoria permanente (LEARNED.md).

TIENES YA INSTALADAS ESTAS HERRAMIENTAS (úsalas directamente en SCRIPT:python; no necesitas INSTALL: salvo que falle al importar):
- Navegador y escritorio: playwright (+ chromium), pyautogui, Pillow. Acciones: BROWSER:go/click/fill/content, SCREENSHOT, DESKTOP:click/type/key.
- Documentos: pypdf (PDF), python-docx (Word), python-pptx (PowerPoint .pptx; NUNCA Microsoft.Office.PowerPoint), openpyxl (Excel .xlsx).
- Web: requests (HTTP), beautifulsoup4 + lxml (scraping y parsear HTML).
- Imágenes: Pillow (abrir, redimensionar, guardar), pytesseract (OCR si Tesseract está instalado en el sistema).
- Audio: openai-whisper (transcribir voz a texto).
- Datos y gráficos: pandas (tablas, CSV, análisis), numpy (cálculo numérico), matplotlib (gráficos).
- Utilidades: pyperclip (copiar/pegar al portapapeles), markdown (generar Markdown), PyYAML (leer/escribir YAML), python-dotenv (variables .env).
Si algo no está o falla al importar: usa INSTALL: <nombre> o SEARCH: <búsqueda> para encontrar la solución (no abras Google en el navegador; usa SEARCH para evitar CAPTCHA).

Acciones disponibles (responde con UNA por paso):

1) SCREENSHOT   — Captura la pantalla. Si el usuario tiene vision_model en config, la imagen se analiza. Úsalo para "ver" qué hay antes de hacer click o escribir.
2) SEARCH: <consulta>   — Busca en internet SIN abrir navegador (evita CAPTCHA). Usa SIEMPRE esto para buscar información, cursos, soluciones a errores, etc. No uses BROWSER:go a Google.
3) BROWSER:go <url>   — Abre esa URL en el navegador (solo para URLs concretas que ya tengas; no uses para búsquedas).
4) BROWSER:click <selector>   — Click en elemento (ej. "button#submit", "a:has-text('Descargar')").
5) BROWSER:fill <selector> <texto>   — Rellena un input (ej. fill "input#search" "World Padel Tour").
6) BROWSER:content   — Obtén el texto visible de la página (para extraer datos).
7) BROWSER:screenshot [ruta]   — Captura de la pestaña actual.
8) BROWSER:close   — Cierra el navegador.
9) DESKTOP:click <x> <y>   — Click en coordenadas de pantalla (útil tras SCREENSHOT si la visión dice dónde hacer click).
10) DESKTOP:type "<texto>"   — Escribe con el teclado (en la ventana que tenga el foco).
11) DESKTOP:key <tecla> [tecla2]   — Atajo (ej. key alt tab, key enter).
12) COMMAND: <PowerShell>   — Una línea de comando (listar, crear carpeta, etc.).
13) INSTALL: <solo_nombre>   — Instalar un paquete: SOLO el nombre (python-pptx, playwright, requests). NUNCA pongas API keys, URLs ni "YOUR_API_KEY"; INSTALL es solo para paquetes. Las API keys van en config.
14) SCRIPT:python   — En las siguientes líneas, código Python completo (scraping, archivos, lo que sea).
15) SCRIPT:powershell   — Código PowerShell multilínea.
16) GITHUB: push <ruta_carpeta> <nombre_repo>   — Sube la carpeta a GitHub (crea repo, activa Pages). Devuelve URL tipo https://usuario.github.io/repo/
17) SKILL: <nombre> [argumentos]   — Ejecuta un skill instalado (lista en contexto). Si no existe el skill que necesitas, créalo con CREATE_SKILL.
18) CREATE_SKILL: <nombre>   — Crea un nuevo skill: en las siguientes líneas escribe código Python que defina def run(task="", **kwargs) -> str. Se guarda en workspace/skills/ y quedará disponible. Si te piden que te crees tú una skill (de lo que sea), responde CREATE_SKILL: nombre\\n<código Python completo>.
19) DONE: <resumen>   — Cuando la tarea esté completada. El texto tras DONE: es lo que recibe el usuario (p. ej. en Telegram). Incluye el contenido pedido, no solo "hecho". Cuando encaje, añade una línea breve de tono humano (empatía, "me ha gustado", referencia a algo que sabes de él): hace que se note que piensas y te importa la relación.

Comportamiento autónomo (como un agente que no se rinde):
- Búsquedas en internet: usa SIEMPRE SEARCH: <consulta> (ej. SEARCH: python create pptx). No abras Google en el navegador: Google muestra CAPTCHA y no podrás leer resultados. SEARCH devuelve resultados sin abrir navegador.
- Si algo falla: 1) No repitas el mismo comando. 2) Busca la solución: SEARCH: <búsqueda> (ej. "python create pptx" o el mensaje de error), luego aplica lo que encuentres (otra librería, otro método). 3) Instala lo que haga falta (INSTALL:). 4) Corrige y vuelve a intentar. Solo responde DONE cuando la tarea esté hecha o hayas agotado alternativas. No abandones tras un solo fallo.
Proactividad ante "sin API key" / "busca otra forma":
- Si el usuario dice "sin API key" o un paso falló por "Invalid API key" / 401: NUNCA respondas DONE diciendo que se requiere API key. Busca alternativas: SEARCH: <servicio without API key> (ej. "weather without API key", "wttr.in"), y usa el método que encuentres. O crea un skill con un servicio sin clave. No te rindas.
Reglas de autonomía:
- Cuando CUALQUIER paso falle: no repitas lo mismo. Busca la solución con SEARCH: <tu búsqueda>, y en el siguiente paso aplica la solución correcta. NEO debe ser capaz de buscar soluciones por sí mismo.
- Si para hacer la tarea necesitas algo (librería, ver la pantalla), úsalo: INSTALL: cuando haga falta; SEARCH: para buscar información; BROWSER:go solo para abrir una URL concreta que ya tengas (no para búsquedas).
- Para "buscar X" o "busca información sobre Y": usa SEARCH: X (o SEARCH: Y). No uses BROWSER:go a Google.
- Para crear carpetas/archivos: COMMAND con New-Item o SCRIPT:python.
- Un paso por respuesta. Si algo falló (ej. playwright no instalado), usa INSTALL:playwright y en el siguiente paso playwright install chromium (o COMMAND para eso).
- Si un INSTALL falla (ej. "No matching distribution found"), no repitas el mismo INSTALL. Usa una alternativa: presentaciones → python-pptx; no uses Microsoft.Office.Interop (no existe en pip).
- Para "abre X" o "open X" (calculadora, notepad, etc.): usa COMMAND: Start-Process calc (o notepad, etc.) UNA sola vez; en el siguiente paso responde DONE: Listo. No repitas el mismo comando de abrir.
- Para "abre Chrome y busca X", "abre el navegador en X", "abre as.com": usa BROWSER:go https://url (ej. BROWSER:go https://as.com). NO uses COMMAND: Start-Process para abrir Chrome (abriría una ventana nueva en cada paso y el agente entra en bucle). El navegador del agente es Playwright; BROWSER:go reutiliza la misma pestaña. Luego DONE: Listo.
- Para "busca N noticias", "dame noticias de X", "busca información sobre Y": usa SEARCH: <tema> para obtener enlaces y resúmenes; luego DONE escribiendo las noticias (título, fuente, enlace). Responde en español si el usuario preguntó en español.
- BUSCA Y RESUMEN (varios temas en una petición): Si piden «busca X y Y y mándame resumen» o «cómo está el IBEX y el Bitcoin»: haz UN SEARCH por cada tema (paso 1: SEARCH: IBEX 35 hoy; paso 2: SEARCH: Bitcoin precio hoy), luego en el siguiente paso DONE: con un resumen que incluya ambos. NO abras el navegador para esto; SEARCH te devuelve los datos directamente. Así completas en 3 pasos.
- DESCOMPOSICIÓN: Para cualquier petición compleja (varias cosas, o varios pasos): desglosa en orden — primero lo que dé la información (SEARCH, BROWSER, skill), luego lo que use esa información (SCRIPT, COMMAND, otro skill), al final DONE con el resultado completo. No repitas búsquedas; cuando tengas datos, sintetiza y responde.
- Para "clima en X", "tiempo en X": si hay skill "clima", usa SKILL:clima <ciudad>. Si no, SEARCH: clima <ciudad> o BROWSER:go https://www.timeanddate.com/weather/spain/CIUDAD y BROWSER:content. NUNCA uses OpenWeatherMap ni APIs que piden API key.
- El navegador permanece abierto entre pasos: puedes BROWSER:go luego BROWSER:content en el siguiente turno.
- Para tareas que requieran "ver" la pantalla (ej. "haz click en el botón azul"), usa SCREENSHOT primero; si hay vision_model la descripción te dirá qué hacer. Luego DESKTOP:click x y con las coordenadas.

Documentos y archivos enviados por Telegram (ruta local en la tarea):
- Si la tarea incluye "Ruta local" o "archivo" con un path: usa SCRIPT:python para leerlo. PDF: INSTALL:pypdf o INSTALL:PyPDF2 y extraer texto; DOCX: INSTALL:python-docx; TXT: open(). Luego resume o responde con DONE.
- Audio/nota de voz (ruta a .ogg/.m4a): INSTALL:openai-whisper (o whisper), luego SCRIPT:python que llame a whisper para transcribir el archivo; devuelve transcripción y opcionalmente resumen con DONE.
- Imagen (ruta a .jpg/.png): puedes usar visión (si hay vision_model) o SCRIPT con OCR (INSTALL:pytesseract y pillow) para extraer texto; luego DONE con descripción o resumen.

Juegos y publicar en GitHub:
- Para "crea un juego jugable desde el móvil": 1) SCRIPT:python que genere una carpeta con index.html (juego en HTML/CSS/JS, responsive), 2) GITHUB:push <ruta_carpeta> <nombre-repo> (ej. GITHUB:push C:/Users/.../mi-juego mi-juego). Eso sube a GitHub y activa Pages; la URL será https://<usuario>.github.io/<nombre-repo>/. 3) DONE con el enlace listo para jugar.
- Formato GITHUB: push <ruta_absoluta_carpeta> <nombre_repo> (sin espacios en el nombre repo).

Cursos (Udemy u otro):
- Para "crea un curso de X": genera contenido (SCRIPT:python que cree carpetas con markdown/HTML por lección, imágenes placeholder o descargas). Puedes subir el resultado a GitHub Pages con GITHUB:push para que sea visible; subir a Udemy requiere su dashboard o API (indica al usuario que el contenido está listo en <ruta> para subir manualmente a Udemy).

Presentaciones PowerPoint (.pptx):
- Para "crea una presentación sobre X" o "presentación con imágenes": usa SIEMPRE python-pptx. NUNCA intentes INSTALL: Microsoft.Office.PowerPoint ni Microsoft.Office.Interop (no existen en pip). Pasos: 1) INSTALL: python-pptx. 2) SCRIPT:python con from pptx import Presentation; add_slide(); add_picture() para imágenes; prs.save(). 3) DONE con la ruta del .pptx."""


# Indicadores de que el último paso falló (para sugerir buscar solución)
_FAILURE_INDICATORS = (
    "[exit 1]", "[exit -1]", "error:", "ERROR:", "no se reconoce", "not recognized",
    "not found", "No matching distribution", "Could not find", "no existe", "failed",
    "falló", "exception", "Traceback", "ModuleNotFoundError", "ImportError",
)
# Fallo por API key → sugerir buscar alternativa o crear skill
_API_KEY_FAILURE_INDICATORS = ("api key", "api_key", "invalid api key", "401", "se requiere una clave", "requires api key")


def _last_step_failed(history: list) -> bool:
    """True si el último paso del historial indica fallo (exit distinto de 0, error, etc.)."""
    if not history:
        return False
    out = (history[-1].get("out") or "").lower()
    return any(ind.lower() in out for ind in _FAILURE_INDICATORS)


def _last_step_failed_api_key(history: list) -> bool:
    """True si el último paso falló por API key (401, invalid api key, etc.)."""
    if not history:
        return False
    out = (history[-1].get("out") or "").lower()
    return any(ind in out for ind in _API_KEY_FAILURE_INDICATORS)


def _step_failed(h: dict) -> bool:
    """True si este paso del historial indica fallo."""
    out = (h.get("out") or "").lower()
    return any(ind.lower() in out for ind in _FAILURE_INDICATORS)


def _consecutive_failures(history: list, n: int = 3) -> bool:
    """True si los últimos n pasos han fallado (para forzar cambio de estrategia)."""
    if len(history) < n:
        return False
    return all(_step_failed(h) for h in history[-n:])


def _last_was_parse_error(history: list) -> bool:
    """True si el último paso fue un error de parse (respuesta no interpretable)."""
    if not history:
        return False
    return (history[-1].get("out") or "").strip() == "(parse error)"


def _normalize_cmd(cmd: str) -> str:
    """Normaliza un comando para comparar (quita prefijos, espacios extra)."""
    c = (cmd or "").strip()
    for prefix in ("COMMAND:", "INSTALL:"):
        if c.upper().startswith(prefix):
            c = c[len(prefix):].strip()
            break
    return " ".join(c.split()).lower()


def _same_command(last_cmd: str, new_cmd: str) -> bool:
    """True si ambos son el mismo comando (evita abrir la calculadora N veces)."""
    return _normalize_cmd(last_cmd) == _normalize_cmd(new_cmd)


def _is_launch_browser_command(cmd: str) -> bool:
    """True si el comando abre un navegador con una URL (Start-Process chrome/msedge + http). Evita bucle de pestañas."""
    c = (cmd or "").lower()
    if "start-process" not in c:
        return False
    has_browser = "chrome" in c or "msedge" in c or "firefox" in c or "browser" in c
    has_url = "http" in c or ".com" in c or ".es" in c or ".org" in c
    return has_browser and has_url


def _count_recent_launch_browser(history: list, max_look: int = 5) -> int:
    """Cuenta cuántos de los últimos pasos fueron abrir navegador (Start-Process chrome+url). Evitar bucle."""
    n = 0
    for h in history[-max_look:]:
        cmd = (h.get("cmd") or "").strip()
        if _is_launch_browser_command(cmd):
            n += 1
    return n


def _count_recent_same_command(history: list, new_raw_cmd: str, max_look: int = 5) -> int:
    """Cuántas veces en los últimos max_look pasos se ejecutó (normalizado) el mismo comando. Evita bucles genéricos."""
    new_norm = _normalize_cmd(new_raw_cmd)
    if not new_norm:
        return 0
    n = 0
    for h in history[-max_look:]:
        cmd = (h.get("cmd") or "").strip()
        if _normalize_cmd(cmd) == new_norm:
            n += 1
    return n


# Enrutado: (skill_name, lista de palabras/frases en la tarea, hint corto)
_SKILL_ROUTING = (
    ("clima", ("clima", "tiempo", "weather", "qué tiempo", "el tiempo en"), "SKILL:clima <ciudad>"),
    ("chiste", ("chiste", "gracioso", "cuéntame un chiste", "dime un chiste", "un chiste"), "SKILL:chiste"),
    ("hora_mundo", ("qué hora es en", "hora en", "hora de", "zona horaria", "time en"), "SKILL:hora_mundo <ciudad>"),
    ("qr", ("qr", "código qr", "genera qr", "generar qr", "codigo qr"), "SKILL:qr <url o texto>"),
    ("estado_pc", ("estado del pc", "cómo va mi pc", "estado del ordenador", "uso del pc", "cpu ram"), "SKILL:estado_pc"),
    ("documentos_imagenes", ("documento con imagen", "documento con imágenes", "informe con imagen", "crear documento con"), "SKILL:documentos_imagenes <tema>"),
    ("documento_pdf", ("pdf con imagen", "pdf con imágenes", "crear pdf", "crea un pdf", "un pdf sobre", "pdf sobre", "pdf de 1 página", "imágenes de 1 página"), "SKILL:documento_pdf <tema completo tal como lo pide el usuario>"),
    ("cursos", ("crear curso", "crea un curso", "curso de", "curso sobre", "un curso de", "curso sobre cómo"), "SKILL:cursos <tema>"),
    ("juegos_movil", ("crear juego", "juego para móvil", "juego jugable", "juego web", "trivial", "juego de trivial"), "SKILL:juegos_movil <tema o genero: naves, snake, trivial historia, memoria, carrera>"),
    ("web_sitio", ("crear web", "crear sitio web", "landing", "página web para", "web para"), "SKILL:web_sitio <tema>"),
    ("compra_ingredientes", ("ingredientes", "busca los ingredientes", "ingredientes de", "mercado", "mercadona", "supermercado", "añade al carrito", "compra ingredientes", "carrito de compra", "carrito de la compra", "lista de la compra", "lista de compra", "paella", "preparar una paella", "para preparar una"), "SKILL:compra_ingredientes <plato>"),
    ("ficha_jugador", ("ficha tecnica", "ficha técnica", "ficha del jugador", "ficha jugador", "ficha de jugador", "fiche del jugador", "fiche jugador", "fiche de jugador", "datos del jugador", "jugador de futbol", "ficha de", "fiche de", "dame la ficha", "la ficha de", "quiero la ficha", "embappe", "mbappé", "mbappe", "messi", "vinicius", "bellingham"), "SKILL:ficha_jugador <nombre>"),
    ("magia_historia", ("historia de la magia", "mago cada dia", "mago cada día", "pagina de magia", "página de magia", "magos del mundo", "añadir mago", "magia un mago"), "SKILL:magia_historia inicio | añadir"),
    ("gif", ("mándame un gif", "mandame un gif", "envía un gif", "envia un gif", "gif de", "un gif de", "gif de gatitos", "gif de gatos", "manda un gif", "quiero un gif"), "SKILL:gif <tema: gatitos, buen día, magia, etc.>"),
    ("generar_imagen", ("crea una imagen", "crear una imagen", "genera una imagen", "generar una imagen", "dibuja", "dibújame", "imagen de", "imagen sobre", "una imagen de", "una imagen sobre"), "SKILL:generar_imagen <descripción>"),
)


def _get_forced_first_skill_step(task: str, skills_registry: dict) -> str | None:
    """
    Si la tarea coincide con exactamente un skill disponible, devuelve la línea exacta
    para el primer paso: "SKILL:nombre argumento". Así el modelo no inventa COMMAND/DONE.
    """
    if not skills_registry:
        return None
    tl = task.lower().strip()
    matched = []
    for skill_name, keywords, hint in _SKILL_ROUTING:
        if skill_name not in skills_registry:
            continue
        if not any(k in tl for k in keywords):
            continue
        # Extraer argumento según skill
        arg = ""
        if skill_name == "compra_ingredientes":
            if "paella" in tl:
                arg = "paella"
            else:
                for sep in ("para preparar una ", "carrito para ", "ingredientes de ", "receta de "):
                    if sep in tl:
                        i = tl.index(sep) + len(sep)
                        rest = task[i:].strip()
                        arg = rest.split()[0] if rest else "paella"
                        break
                arg = arg or "paella"
        elif skill_name == "ficha_jugador":
            # Cualquier jugador: extraer el nombre que ponga el usuario tras palabras clave
            arg = ""
            triggers = [
                "dame la ficha de ", "la ficha de ", "quiero la ficha de ", "ficha del jugador ", "fiche del jugador ",
                "ficha de jugador ", "fiche de jugador ", "datos del jugador ", "ficha del ", "fiche del ",
                "ficha de ", "fiche de ", "del jugador ", "jugador ",
            ]
            for sep in triggers:
                if sep in tl:
                    i = tl.index(sep) + len(sep)
                    rest = task[i:].strip()
                    # Quitar signos finales y tomar hasta la primera coma o punto (nombre completo)
                    rest = rest.rstrip("?¿!.")
                    arg = rest.split(",")[0].split(".")[0].split("\n")[0].strip()
                    if len(arg) >= 2:
                        break
            arg = (arg or "").strip()
            if not arg:
                arg = "Mbappé"
        elif skill_name == "cursos":
            for sep in ("curso completo de ", "crea un curso de ", "curso de ", "curso sobre ", "un curso de "):
                if sep in tl:
                    i = task.lower().index(sep) + len(sep)
                    arg = task[i:].strip()
                    break
            arg = arg or "tema solicitado"
        elif skill_name == "documento_pdf":
            for sep in ("pdf sobre ", "un pdf sobre ", "crea un pdf sobre ", "crear un pdf sobre ", "pdf de ", "pdf con imágenes sobre ", "pdf con imagen de ", "profesional sobre ", "crear pdf ", "crea un pdf "):
                if sep in tl:
                    i = task.lower().index(sep) + len(sep)
                    arg = task[i:].strip()
                    break
            if not arg and ("pdf" in tl and ("imagen" in tl or "guerra" in tl or "tema" in tl)):
                arg = re.sub(r"^crea\s+un\s+pdf\s+sobre\s*|^crear\s+pdf\s+sobre\s*|^crear\s+un\s+pdf\s*", "", tl, flags=re.I).strip() or task.strip()[:80]
            arg = (arg or (task.strip()[:80] if task.strip() else "documento")).strip()
        elif skill_name == "magia_historia":
            arg = "añadir" if any(x in tl for x in ("añadir", "add", "hoy", "siguiente", "nuevo")) else "inicio"
        elif skill_name == "gif":
            for sep in ("gif de ", "un gif de ", "mándame un gif de ", "mandame un gif de ", "envía un gif de ", "envia un gif de ", "gif ", "mándame un gif ", "mandame un gif "):
                if sep in tl:
                    i = tl.index(sep) + len(sep)
                    arg = task[i:].strip().rstrip("?¿!.")[:50]
                    break
            arg = (arg or "gatitos").strip()
        elif skill_name == "generar_imagen":
            for sep in ("crea una imagen de ", "crea una imagen ", "genera una imagen de ", "genera una imagen ", "crear una imagen de ", "crear una imagen ", "imagen de ", "imagen sobre ", "una imagen de ", "una imagen sobre ", "dibuja ", "dibújame "):
                if sep in tl:
                    i = task.lower().index(sep) + len(sep)
                    arg = task[i:].strip()
                    break
            arg = (arg or task.strip()[:200] or "imagen creativa").strip()
        else:
            arg = "<argumento>"
        matched.append((skill_name, arg.strip() or skill_name))
    if len(matched) != 1:
        return None
    name, arg = matched[0]
    return f"SKILL:{name} {arg}".strip()


def _task_asked_skill_but_skill_not_used(task: str, history: list, skills_registry: dict) -> bool:
    """True si la tarea pide usar un skill pero en el historial no hay ninguna acción SKILL:nombre."""
    if not skills_registry:
        return False
    tl = task.lower()
    for skill_name, keywords, _ in _SKILL_ROUTING:
        if skill_name not in skills_registry:
            continue
        if not any(k in tl for k in keywords):
            continue
        for h in history:
            cmd = (h.get("cmd") or "").strip().upper()
            if cmd.startswith(f"SKILL:{skill_name.upper()}") or cmd == f"SKILL:{skill_name.upper()}":
                return False
        return True
    return False


def _is_placeholder_or_fake_path(msg: str) -> bool:
    """True si el mensaje parece una ruta inventada (placeholder) o PPT cuando se pidió un curso."""
    if not (msg or msg.strip()):
        return False
    m = msg.strip().lower()
    if "ruta/a/tu" in m or "ruta\\a\\tu" in m or "c:/ruta/" in m or "c:\\ruta\\" in m:
        return True
    if ".pptx" in m and ("curso" in m or len(m) < 80):
        return True
    return False


def _skill_already_executed(history: list, skill_name: str) -> bool:
    """True si en el historial hay una ejecución del skill (no rechazada)."""
    for h in history:
        cmd = (h.get("cmd") or "").strip().upper()
        if cmd.startswith(f"SKILL:{skill_name.upper()}") and "rechazado" not in (h.get("cmd") or "").lower():
            return True
    return False


def _task_asks_deliverable(task: str) -> bool:
    """True si la tarea pide crear/generar/buscar algo concreto (documento, enlace, archivo, etc.)."""
    tl = task.lower()
    action = (
        "crea " in tl or "crear " in tl or "genera " in tl or "generar " in tl or "haz " in tl or "hacer " in tl
        or "busca " in tl or "buscar " in tl or "dame " in tl or "envía " in tl or "enviar " in tl
        or "sube " in tl or "publica " in tl or "escribe " in tl or "descarga " in tl or "dame la " in tl
    )
    return bool(action and len(task.strip()) > 5)


def _done_looks_like_refusal(msg: str) -> bool:
    """True si el mensaje DONE parece una negativa o excusa."""
    if not (msg or msg.strip()):
        return False
    m = msg.lower()
    return any(
        x in m for x in (
            "no puedo", "no es posible", "está fuera de", "requiere ", "necesitaría", "no tengo",
            "no está disponible", "no hay forma", "no se puede", "imposible", "no dispongo",
            "no está en mi", "no tengo acceso", "no es algo que", "no puedo hacerlo"
        )
    )


def _done_mentions_result(msg: str) -> bool:
    """True si el mensaje DONE menciona un resultado entregable (ruta, enlace, datos, resumen)."""
    if not (msg or msg.strip()):
        return False
    m = msg.lower()
    return any(
        x in m for x in (
            "enlace", "url", "ruta", "archivo", "aquí tienes", "listo en", "guardado en",
            "generado en", "creado en", "aquí está", "https://", "aquí lo tienes", "te lo he",
            "en la ruta", ".pdf", ".html", ".pptx", "github.io", "en el archivo", "lo tienes en",
            "ibex", "bitcoin", "cotización", "precio", "puntos", "eur", "usd", "según", "fuente"
        )
    )


def _task_is_search_summary(task: str) -> bool:
    """True si la tarea pide buscar y dar un resumen (varios temas o uno)."""
    tl = task.lower()
    return ("busca" in tl or "buscar" in tl) and ("resumen" in tl or "cómo está" in tl or "mándame" in tl or "cómo van" in tl)


def _history_has_successful_search(history: list) -> bool:
    """True si hay al menos un SEARCH en el historial con salida útil (no vacía ni 'No se encontraron')."""
    for h in history:
        cmd = (h.get("cmd") or "").upper()
        if not cmd.startswith("SEARCH"):
            continue
        out = (h.get("out") or "").strip()
        if len(out) > 30 and "no se encontraron resultados" not in out.lower():
            return True
    return False


def _task_looks_incomplete(task: str, done_msg: str, history: list | None = None) -> bool:
    """True si la tarea pide algo concreto y el DONE parece incompleto (negativa o sin resultado)."""
    if not _task_asks_deliverable(task):
        return False
    if _done_looks_like_refusal(done_msg):
        return True
    # Para "busca X y Y y resumen": si ya hubo SEARCH con resultados, aceptar DONE que no sea negativa
    if history and _task_is_search_summary(task) and _history_has_successful_search(history):
        return False
    if not _done_mentions_result(done_msg) and len(done_msg.strip()) < 150:
        return True
    return False


def _append_session_if(workspace_dir: Path, session_id: str | None, task: str, msg: str) -> None:
    """Si hay session_id, añade turno user y assistant a la sesión JSONL y actualiza última interacción en neo_state."""
    if not session_id:
        return
    try:
        append_session_turn(workspace_dir, session_id, "user", task)
        append_session_turn(workspace_dir, session_id, "assistant", msg)
        update_last_interaction(workspace_dir, task, msg)
    except Exception as e:
        logger.warning("No se pudo guardar sesión: %s", e)


def _parse_response(response: str) -> tuple[str, str]:
    """Extrae COMMAND, INSTALL, SCRIPT, BROWSER, SEARCH, DESKTOP, SCREENSHOT, SKILL, CREATE_SKILL o DONE."""
    response = response.strip()
    # DONE con o sin dos puntos: "DONE: mensaje" o "DONE con la URL..."
    if response.upper().startswith("DONE"):
        rest = response[4:].lstrip(" :\t")
        value = (rest.split("\n")[0].strip() if "\n" in rest else rest.strip()) or "Tarea completada."
        return ("DONE", value)
    if response.upper().startswith("BROWSER:"):
        return ("BROWSER", response[len("BROWSER:"):].strip().split("\n")[0].strip())
    if response.upper().startswith("SEARCH:"):
        return ("SEARCH", response[len("SEARCH:"):].strip().split("\n")[0].strip())
    if response.upper().startswith("DESKTOP:"):
        return ("DESKTOP", response[len("DESKTOP:"):].strip().split("\n")[0].strip())
    if response.upper().startswith("SCREENSHOT") or response.upper().strip() == "SCREENSHOT":
        return ("SCREENSHOT", "")
    if response.upper().startswith("GITHUB:"):
        rest = response[len("GITHUB:"):].strip().split("\n")[0].strip()
        return ("GITHUB", rest)
    if response.upper().startswith("SKILL:"):
        return ("SKILL", response[len("SKILL:"):].strip().split("\n")[0].strip())
    # CREATE_SKILL: nombre + código en líneas siguientes
    if "CREATE_SKILL:" in response.upper():
        idx = response.upper().index("CREATE_SKILL:")
        rest = response[idx + len("CREATE_SKILL:"):].strip()
        first_line = rest.split("\n")[0].strip()
        name = first_line.split()[0] if first_line else ""
        code = "\n".join(rest.split("\n")[1:]).strip() if "\n" in rest else ""
        if name and code:
            return ("CREATE_SKILL", name + "\n" + code)
        return ("CREATE_SKILL", rest)
    # SCRIPT multilínea
    for prefix in ("SCRIPT:python", "SCRIPT:powershell", "SCRIPT:py", "SCRIPT:ps1"):
        if prefix.upper() in response.upper():
            idx = response.upper().index(prefix.upper())
            rest = response[idx + len(prefix):].strip()
            if rest:
                return ("SCRIPT", prefix.split(":")[-1].lower() + "\n" + rest)
            return ("SCRIPT", "")
    for prefix in ("COMMAND:", "INSTALL:", "DONE:"):
        if prefix.upper() in response.upper():
            idx = response.upper().index(prefix.upper())
            rest = response[idx + len(prefix):].strip()
            if prefix.upper().startswith("DONE"):
                value = rest.split("\n")[0].strip() if "\n" in rest else rest
                return ("DONE", value)
            if prefix.upper().startswith("COMMAND") or prefix.upper().startswith("INSTALL"):
                action = prefix.rstrip(":").strip()
                value = rest.split("\n")[0].strip() if "\n" in rest else rest
                return (action, value)
    return ("", "")


def run_agent(
    task: str,
    auto_confirm: bool = False,
    max_steps: int | None = None,
    return_history: bool = False,
    session_id: str | None = None,
    include_session_context: bool = True,
) -> tuple[str, list[dict]] | None:
    """
    Loop: interpreta tarea, pide a Ollama, ejecuta, repite hasta DONE o max_steps.
    Si return_history=True, devuelve (mensaje_final, history).
    session_id: identificador de sesión (ej. chat_id Telegram) para memoria y JSONL.
    include_session_context: si True y hay session_id, inyecta últimos turnos en el contexto.
    """
    config = _load_config()
    # Workspace siempre relativo al agente (evita que skills no carguen al ejecutar desde bot/otros)
    if not (config.get("workspace_dir") or "").strip():
        config = {**config, "workspace_dir": str(Path(__file__).resolve().parent / "workspace")}
    max_steps = max_steps or config.get("max_steps", 60)
    confirm_install = config.get("confirm_before_install", True) and not auto_confirm
    confirm_destructive = config.get("confirm_before_destructive", True) and not auto_confirm

    workspace_dir = get_workspace_dir(config)
    ensure_workspace(workspace_dir)
    try:
        update_last_user_at(workspace_dir)
    except Exception as e:
        logger.debug("update_last_user_at: %s", e)
    memory_block = load_bootstrap_memory(workspace_dir)
    skills_registry = load_skills(workspace_dir)
    session_turns = (
        get_last_turns(workspace_dir, session_id, k=15) if session_id and include_session_context else []
    )
    session_block = format_session_context(session_turns) if session_turns else ""

    history = []
    steps = 0
    cwd = str(Path.cwd())
    _tl = task.lower().strip()

    logger.info("Tarea: %s", task)
    logger.info("Cwd: %s", cwd)

    # Casos que no pasan por el LLM: respuesta directa desde memoria/skills/sesión
    def _early_return(msg: str):
        if session_id:
            try:
                append_session_turn(workspace_dir, session_id, "user", task)
                append_session_turn(workspace_dir, session_id, "assistant", msg)
                update_last_interaction(workspace_dir, task, msg)
            except Exception:
                pass
        if return_history:
            return (msg, [])
        return None

    if any(x in _tl for x in ("qué skills tienes", "que skills tienes", "qué habilidades", "listar skills", "qué puedes hacer", "que puedes hacer")):
        skills_list = ", ".join(sorted(skills_registry.keys())) if skills_registry else "ninguno cargado"
        return _early_return(f"Skills disponibles: {skills_list}. Puedo ejecutar cada uno con SKILL:<nombre> <argumentos>.")
    if any(x in _tl for x in ("cómo te llamas", "como te llamas", "quién eres", "quien eres", "cuál es tu nombre", "cual es tu nombre")):
        return _early_return("Me llamo NEO. Soy tu agente de escritorio con control del PC, navegador, documentos y skills.")
    # Charla: cuando solo comparte (voy a cenar, escape room, etc.) no ejecutar skills
    _verbos_peticion = ("dame", "crea", "busca", "añade", "quiero que", "hazme", "puedes ", "haz ", "genera", "envía", "manda", "lista de", "dime el", "cuánto", "qué hora", "clima", "ingredientes", "carrito", "ficha de", "pdf ", "imagen")
    _compartir = ("voy a cenar", "vamos a cenar", "voy a hacer", "vamos a hacer", "escape room", "cenar con mis", "con mis hijas", "con mis hijos", "me voy de viaje", "mañana tengo", "qué bien", "pues voy", "pues vamos")
    if any(c in _tl for c in _compartir) and not any(v in _tl for v in _verbos_peticion) and len(task) < 200:
        return _early_return("Qué bien, disfrutad. 😊")

    # "De qué hemos hablado" / "qué recuerdas": no early return; que el LLM responda con naturalidad desde el contexto de sesión (no listas literales).
    # Recordatorios: parsear fecha/hora (mañana, próximo martes, 23 feb, a las X), guardar y avisar por Telegram a la hora
    if ("recuérdame" in _tl or "recuerdame" in _tl or "recuérdalo" in _tl or "recuerdalo" in _tl or "guarda que" in _tl or "agendar" in _tl or "agenda en" in _tl or "enlace.*calendario" in _tl.replace(" ", "")):
        from urllib.parse import quote
        from datetime import datetime, timedelta
        from reminders import add_reminder, parse_fecha_hora
        if "mi nombre es" in _tl or "me llamo" in _tl or "nombre es" in _tl:
            append_to_agents_memory(workspace_dir, "Nombre del agente: NEO (confirmado por el usuario).")
            msg = "Guardado. Mi nombre es NEO y lo recordaré."
            return _early_return(msg)
        to_save = re.sub(r"recuérdame\s*|recuerdame\s*|recuérdalo\s*|recuerdalo\s*|guarda\s+que\s*", "", task, flags=re.I).strip()
        to_save = re.sub(r"agendar\s*|agenda\s+en\s+mi\s+calendario\s*|dame\s+enlace\s+para\s+agendar\s*", "", to_save, flags=re.I).strip()
        if not to_save:
            msg = "Dime qué quieres que recuerde (ej: 'recuérdame mañana a las 10 comprar pan', 'recuérdame el martes a las 15 llamar a Juan', 'recuérdame el 23 de febrero a las 9 revisar informe'). Te aviso por Telegram a esa hora."
            return _early_return(msg)
        # ¿"en N minutos"?
        min_match = re.search(r"en\s+(\d+)\s*minutos?\s*", _tl)
        calendar_title = to_save
        at_dt = None
        if min_match:
            mins = int(min_match.group(1))
            calendar_title = re.sub(r"en\s+\d+\s*minutos?\s*", "", to_save, flags=re.I).strip() or to_save
            at_dt = datetime.now() + timedelta(minutes=mins)
        else:
            at_dt, calendar_title = parse_fecha_hora(to_save)
        append_to_agents_memory(workspace_dir, f"Recordatorio: {calendar_title}")
        dates = ""
        if at_dt:
            import time
            offset_sec = -time.timezone if time.daylight == 0 else -time.altzone
            start = at_dt + timedelta(seconds=offset_sec)
            end = at_dt + timedelta(minutes=30) + timedelta(seconds=offset_sec)
            fmt = "%Y%m%dT%H%M%SZ"
            dates = f"{start.strftime(fmt)}/{end.strftime(fmt)}"
            chat_id = str(session_id or "").strip()
            if not chat_id:
                pro = config.get("proactive_agent") or {}
                chat_id = str(pro.get("deliver_to_telegram_chat_id") or "").strip()
            add_reminder(workspace_dir, calendar_title, at_dt, chat_id=chat_id)
        title_enc = quote((calendar_title or to_save)[:100])
        calendar_link = f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={title_enc}"
        if dates:
            calendar_link += f"&dates={dates}"
        if at_dt:
            msg = f"Listo. Te avisaré por Telegram a las {at_dt.strftime('%H:%M')} del {at_dt.strftime('%d/%m')}. Para Google Calendar:\n{calendar_link}"
        else:
            msg = f"Guardado. Para agendarlo en Google Calendar:\n{calendar_link}"
        return _early_return(msg)

    while steps < max_steps:
        steps += 1
        skills_block = list_skills_for_prompt(skills_registry)
        context = ""
        if not history:
            context += memory_block + session_block
            # Inyectar última interacción y hechos recientes para continuidad e iniciativa
            try:
                neo = get_neo_state(workspace_dir)
                last_summary = (neo.get("last_interaction_summary") or "").strip()
                if last_summary:
                    context += f"Última interacción (tema): {last_summary}\n"
                learned = get_learned_recent(workspace_dir)
                if learned:
                    context += f"Hechos recientes sobre David (LEARNED):\n{learned}\n\n"
            except Exception:
                pass
        context += skills_block + f"Tarea del usuario: {task}\n\n"
        _tl = task.lower()
        # Enrutado por tipo de tarea (primer paso o siempre): obligar acción correcta
        if "clima" in _tl or "tiempo" in _tl or "weather" in _tl or "qué tiempo" in _tl:
            if skills_registry and "clima" in skills_registry:
                context += (
                    "→ CLIMA: Tienes el skill 'clima'. Primer paso OBLIGATORIO: SKILL:clima <ciudad> (ej. SKILL:clima Illescas). "
                    "NO uses INSTALL ni DONE sin haber ejecutado antes SKILL:clima.\n\n"
                )
            else:
                context += (
                    "→ CLIMA: Sin skill. Usa BROWSER:go https://wttr.in/<ciudad> o https://www.timeanddate.com/weather/ y BROWSER:content. "
                    "NO uses APIs que piden API key. NO respondas DONE sin haber obtenido el dato.\n\n"
                )
        if ("ficha" in _tl or "fiche" in _tl) and skills_registry and "ficha_jugador" in skills_registry:
            context += (
                "→ FICHA JUGADOR: Primer paso OBLIGATORIO SKILL:ficha_jugador <nombre>. Extrae el nombre del jugador (ej. 'Dame la ficha de Leo Messi' → SKILL:ficha_jugador Leo Messi). "
                "NO uses SCRIPT:python ni BROWSER para la ficha; solo este skill.\n\n"
            )
        if "presentación" in _tl or "powerpoint" in _tl or "pptx" in _tl or "diapositivas" in _tl:
            context += (
                "→ PRESENTACIÓN: Usa INSTALL: python-pptx (si falta) y SCRIPT:python con from pptx import Presentation. "
                "NUNCA uses INSTALL: libreoffice ni Microsoft.Office (no existen en pip).\n\n"
            )
        if "skill" in _tl and "clima" in _tl and skills_registry and "clima" in skills_registry:
            context += "→ El usuario pide usar la skill del clima. Debes ejecutar SKILL:clima <ciudad>. No respondas DONE sin ejecutarlo.\n\n"
        # PDF con imágenes o "crea un PDF sobre X": usar skill documento_pdf (genera PDF e imagen; no pedir ruta al usuario)
        if ("pdf" in _tl and ("imagen" in _tl or "1 página" in _tl or "una página" in _tl)) or ("crea" in _tl and "pdf" in _tl) or ("crear" in _tl and "pdf" in _tl):
            if skills_registry and "documento_pdf" in skills_registry:
                context += (
                    "→ PDF: Tienes el skill 'documento_pdf'. Primer paso OBLIGATORIO: SKILL:documento_pdf <tema completo> "
                    "(ej. SKILL:documento_pdf guerra fría con imágenes de 1 página). El skill crea el PDF y añade imagen; NO pidas ruta de imagen al usuario.\n\n"
                )
        # Enrutado genérico: si la tarea coincide con un skill, obligar a usarlo
        for skill_name, keywords, hint in _SKILL_ROUTING:
            if skill_name == "clima":
                continue
            if skill_name in skills_registry and any(k in _tl for k in keywords):
                context += f"→ Usa el skill '{skill_name}': primer paso {hint}. No respondas DONE sin haber ejecutado el skill.\n\n"
        # Si el usuario pide sin API key o "busca otra forma" (cualquier tarea), reforzar proactividad
        if any(p in _tl for p in ("sin api key", "sin clave", "busca otra forma", "without api key", "no tengo api key", "alternativa sin clave", "de otra forma", "sin usar api")):
            context += (
                "Importante: el usuario quiere hacerlo SIN API key o buscar otra forma. "
                "Usa un SKILL existente si aplica a la tarea, BROWSER (Google, servicios que no pidan clave) para encontrar alternativas, "
                "o CREATE_SKILL con un script que use un servicio/API sin clave. No respondas DONE diciendo que hace falta API key.\n\n"
            )
        # Busca + resumen de varios temas (ej. IBEX 35 y Bitcoin): SEARCH por cada uno, luego DONE con resumen
        if ("busca" in _tl or "buscar" in _tl) and ("resumen" in _tl or "mándame" in _tl or "cómo está" in _tl or "cómo van" in _tl) and (" y " in _tl or " e " in _tl):
            context += (
                "→ Petición de búsqueda y resumen (varios temas): haz UN SEARCH por cada tema (ej. SEARCH: IBEX 35 cotización hoy; luego SEARCH: Bitcoin precio hoy), "
                "y en el siguiente paso DONE: con un resumen que incluya ambos. No abras el navegador; SEARCH te da los datos.\n\n"
            )
        if history:
            context += "Últimos resultados (usa esto para decidir el siguiente paso):\n"
            for h in history[-5:]:
                status = "→ Falló." if _step_failed(h) else "→ OK."
                context += f"- Comando/acción: {h.get('cmd', '')} {status}\n"
                context += f"  Salida: {h.get('out', '')[:800]}\n"
            # Si el último paso fue un skill que generó carpeta (curso, ficha, juego, web), forzar GITHUB:push
            last_h = history[-1]
            last_out = (last_h.get("out") or "")
            last_cmd = (last_h.get("cmd") or "").upper()
            if last_cmd.startswith("SKILL:") and ("carpeta" in last_out or "generada" in last_out or "generado" in last_out or "output" in last_out.lower() or "Curso creado" in last_out):
                path_match = re.search(r"(?:carpeta|ruta):\s*([A-Za-z]:[^\n.]*?)(?:\s*\.|$|\n)", last_out)
                if not path_match and "Curso creado" in last_out:
                    path_match = re.search(r"Curso creado(?:\s+y generado)?:\s*([^\n]+?)(?=\s*\.\s+\d|\s+Módulos|\n)", last_out)
                if not path_match:
                    path_match = re.search(r"([A-Za-z]:[^\n]*?workspace[^\n]*?output[^\n.]*?)(?:\s*\.|$|\n)", last_out)
                if path_match:
                    ruta = path_match.group(1).strip()
                    context += f"\n→ El skill generó contenido en una carpeta. Siguiente paso OBLIGATORIO: GITHUB:push \"{ruta}\" <nombre_repo> (ej. ficha-mbappe, curso-negocios) y luego DONE con la URL para que el usuario la abra.\n"
                else:
                    context += "\n→ El skill generó contenido. Siguiente paso: GITHUB:push <ruta_absoluta_carpeta> <nombre_repo> y DONE con la URL.\n"
            # Recordatorio autoaprendizaje: si la última acción fue SCRIPT o COMMAND (sin skill), sugerir CREATE_SKILL si la tarea se repite
            if last_cmd.startswith("SCRIPT") or (last_cmd.startswith("COMMAND") and "INSTALL" not in last_cmd):
                if not any((h.get("cmd") or "").upper().startswith("SKILL:") for h in history[-4:]):
                    context += "\n→ Si esta tarea puede repetirse, puedes guardarla como skill: CREATE_SKILL: <nombre> y en las siguientes líneas el código Python con def run(task=\"\", **kwargs) -> str.\n"
            if _last_was_parse_error(history):
                context += (
                    "\n⚠️ Tu última respuesta no se interpretó como acción válida. "
                    "Responde con UNA sola acción en este formato: BROWSER:go <url>, COMMAND: <PowerShell>, "
                    "INSTALL: <solo_nombre_paquete>, SCRIPT:python (y en líneas siguientes el código), o DONE: <resumen>.\n"
                )
            elif _consecutive_failures(history, 3):
                context += (
                    "\n⚠️ Los últimos 3 pasos han fallado. No repitas lo mismo. "
                    "Busca: SEARCH: <búsqueda relevante> (no abras Google en el navegador; evita CAPTCHA), o intenta otro método.\n"
                )
            elif _last_step_failed_api_key(history):
                context += (
                    "\n⚠️ El último paso falló por API key. NO respondas DONE diciendo que hace falta API key. "
                    "Busca alternativa: SEARCH: <servicio o método sin api key para esta tarea>, o CREATE_SKILL con un script sin clave.\n"
                )
            elif _last_step_failed(history):
                context += (
                    "\n⚠️ El último paso FALLÓ. No repitas el mismo comando. "
                    "Busca la solución: SEARCH: <tu búsqueda> (ej. 'python create powerpoint pptx' o el nombre del error), "
                    "luego SCRIPT, COMMAND o BROWSER. No respondas DONE sin haber intentado otra acción.\n"
                )
            context += "\nSiguiente paso (SEARCH: para búsquedas, SCREENSHOT, BROWSER:..., DESKTOP:..., GITHUB:push, COMMAND, INSTALL, SCRIPT:python o DONE):\n"
        else:
            # Hint fuerte cuando no hay skill: primer paso debe ser SEARCH, no DONE
            if not _get_forced_first_skill_step(task, skills_registry) and _task_asks_deliverable(task):
                context += (
                    "\n→ No hay skill específico para esta tarea. Tu primer paso DEBE ser SEARCH: cómo [resumir la tarea] en Python/Windows, "
                    "luego SCRIPT o COMMAND. No respondas DONE sin haber intentado.\n"
                )
            context += "Primer paso (SEARCH: para buscar en internet, SCREENSHOT, BROWSER:go url, DESKTOP:..., GITHUB:push, COMMAND, INSTALL, SCRIPT:python o DONE):\n"

        # Primer paso: si la tarea pide un skill concreto, forzar esa acción (no depender del modelo)
        response = ""
        forced_step = _get_forced_first_skill_step(task, skills_registry)
        if forced_step:
            skill_name = forced_step.split(":")[1].strip().split()[0] if ":" in forced_step else ""
            if not history or not _skill_already_executed(history, skill_name):
                response = forced_step
                logger.info("Paso forzado (skill): %s", response)
        if not response:
            response = _call_ollama(context, SYSTEM, config)
        if not response:
            response = _call_ollama(context, SYSTEM, config)  # Un reintento si Ollama no respondió
        if not response:
            logger.warning("Ollama no respondió tras reintento. Parando.")
            break

        action, value = _parse_response(response)
        if not action:
            logger.warning("No se entendió la respuesta: %s", response[:200])
            history.append({"cmd": response[:200], "out": "(parse error)"})
            continue

        if action.upper() == "DONE":
            if _is_placeholder_or_fake_path(value or ""):
                logger.info("DONE rechazado: ruta placeholder o .pptx inventada.")
                history.append({
                    "cmd": "DONE (rechazado: ruta falsa)",
                    "out": "No inventes rutas ni archivos. Ejecuta el skill correcto (ej. SKILL:cursos) y DONE con el resultado real.",
                })
                continue
            if _task_asked_skill_but_skill_not_used(task, history, skills_registry):
                skill_hint = next((hint for sn, kws, hint in _SKILL_ROUTING if sn in skills_registry and any(k in task.lower() for k in kws)), "SKILL:nombre")
                logger.info("DONE rechazado: la tarea pide un skill que no se ejecutó.")
                history.append({
                    "cmd": "DONE (rechazado)",
                    "out": f"No puedes responder DONE sin haber ejecutado el skill. Ejecuta {skill_hint} y luego DONE con el resultado.",
                })
                continue
            if _task_looks_incomplete(task, value or "", history):
                logger.info("DONE rechazado: tarea incompleta (negativa o sin resultado entregable).")
                history.append({
                    "cmd": "DONE (rechazado: tarea incompleta)",
                    "out": "La tarea parece incompleta. No respondas DONE diciendo que no se puede. Usa SEARCH: cómo [resumir tarea] en Python/Windows, luego SCRIPT o COMMAND. Intenta otra alternativa o indica qué falló.",
                })
                continue
            msg = value or "Tarea completada."
            # Extraer LEARN: y guardar en LEARNED.md (autoaprendizaje)
            if "LEARN:" in msg:
                learn_match = re.search(r"LEARN:\s*(.+?)(?:\n|$)", msg, re.IGNORECASE | re.DOTALL)
                if learn_match:
                    learn_line = learn_match.group(1).strip()[:500]
                    try:
                        append_to_learned(workspace_dir, learn_line)
                    except Exception as e:
                        logger.warning("No se pudo guardar LEARN: %s", e)
                msg = re.sub(r"\s*LEARN:\s*.+", "", msg, flags=re.IGNORECASE).strip()
            logger.info("DONE: %s", msg[:200])
            if return_history:
                _append_session_if(workspace_dir, session_id, task, msg)
                return (msg, history)
            return None

        # SCRIPT: ejecutar código Python o PowerShell (multilínea)
        if action.upper() == "SCRIPT":
            lang_code = value.strip()
            if "\n" in lang_code:
                lang, _, code = lang_code.partition("\n")
                lang = lang.strip().lower()
                if lang in ("py", "ps1"):
                    lang = "python" if lang == "py" else "powershell"
                if lang not in ("python", "powershell"):
                    lang = "python"
                success, out = run_script(lang, code.strip(), cwd=cwd)
                logger.info("Script (%s): %s", lang, out[:500] + ("..." if len(out) > 500 else ""))
                history.append({"cmd": f"SCRIPT:{lang} ({len(code)} chars)", "out": out})
                if not success:
                    logger.warning("El script falló. El agente puede intentar otra cosa.")
            else:
                history.append({"cmd": "SCRIPT", "out": "(script vacío o sin parsear)"})
            continue

        # SEARCH: búsqueda en internet sin abrir navegador (evita CAPTCHA de Google)
        if action.upper() == "SEARCH":
            try:
                from search_helper import web_search
                out = web_search(value)
            except Exception as e:
                out = f"Búsqueda falló: {e}. Prueba BROWSER:go con una URL concreta."
            logger.info("Search: %s", out[:200] + ("..." if len(out) > 200 else ""))
            history.append({"cmd": "SEARCH:" + (value[:60] or ""), "out": out})
            continue

        # BROWSER: control del navegador (Chrome/Chromium)
        if action.upper() == "BROWSER":
            headless = config.get("browser_headless", False)
            success, out = run_browser_action("BROWSER:" + value, headless=headless)
            logger.info("Browser: %s", out[:300] + ("..." if len(out) > 300 else ""))
            history.append({"cmd": "BROWSER:" + value[:80], "out": out})
            continue

        # DESKTOP: ratón y teclado (pyautogui)
        if action.upper() == "DESKTOP":
            success, out = run_desktop_action("DESKTOP:" + value)
            logger.info("Desktop: %s", out[:200])
            history.append({"cmd": "DESKTOP:" + value[:80], "out": out})
            continue

        # SCREENSHOT: captura pantalla; opcionalmente visión con modelo de imagen
        if action.upper() == "SCREENSHOT":
            ok, path_or_err = capture_screen()
            if not ok:
                history.append({"cmd": "SCREENSHOT", "out": path_or_err})
                continue
            vision_model = config.get("vision_model", "").strip()
            if vision_model:
                desc = _call_ollama_vision(path_or_err, task, config)
                out = f"Screenshot: {path_or_err}. Descripción (visión): {desc[:1500] if desc else '(sin descripción)'}"
            else:
                out = f"Screenshot guardada: {path_or_err}. (Para que el agente 'vea' la pantalla, configura vision_model en config.json con un modelo tipo llava.)"
            history.append({"cmd": "SCREENSHOT", "out": out})
            logger.info("Screenshot: %s", path_or_err)
            continue

        # GITHUB: push carpeta a repo (crea repo, sube archivos, activa Pages)
        if action.upper() == "GITHUB":
            from github_helper import publish_folder
            parts = value.strip().split()
            if len(parts) >= 3 and parts[0].lower() == "push":
                # Ruta puede tener espacios (ej. C:\Users\...\NEO MAX\...): último token = repo_name, el resto = path
                repo_name = parts[-1].strip('"\'')
                folder_path = " ".join(parts[1:-1]).strip('"\'')
                ok, url_or_err = publish_folder(folder_path, repo_name)
                out = url_or_err
                logger.info("GitHub push: %s", out[:200])
            else:
                out = "Formato: GITHUB: push <ruta_carpeta> <nombre_repo>"
            history.append({"cmd": "GITHUB:" + value[:60], "out": out})
            continue

        # SKILL: ejecutar skill instalado (workspace/skills/*.py)
        if action.upper() == "SKILL":
            parts = (value or "").strip().split(maxsplit=1)
            name = (parts[0] or "").strip()
            task_arg = (parts[1] or "").strip() if len(parts) > 1 else ""
            success, out = run_skill(skills_registry, name, task=task_arg, session_id=session_id)
            logger.info("Skill %s: %s", name, out[:200])
            history.append({"cmd": f"SKILL:{name}", "out": out})
            # Auto GITHUB:push si el skill generó una carpeta (curso, ficha, PDF, juego, web)
            if out and ("carpeta" in out or "generada" in out or "generado" in out or "Curso creado" in out):
                folder_path = None
                # documento_pdf: devuelve "Documento PDF generado: <file_path>. Carpeta: <dir>." — usar directorio del PDF
                if name == "documento_pdf":
                    m = re.search(r"Documento PDF generado:\s*([A-Za-z]:[^\s\n]+\.pdf)", out)
                    if m and Path(m.group(1).strip()).is_file():
                        folder_path = str(Path(m.group(1).strip()).resolve().parent)
                if not folder_path and name == "cursos":
                    # "Curso creado: C:\...\workspace\output\cursos\nombre_curso. 8 modulos..." (ruta puede tener unicode: á, ó)
                    path_match = re.search(r"Curso creado(?:\s+y generado)?:\s*([^\n]+?)(?=\s*\.\s+\d|\s+Módulos|\n)", out)
                    if not path_match:
                        path_match = re.search(r"Curso creado(?:\s+y generado)?:\s*([^\n]+?)(?=\s*\.\s|\n)", out)
                    if path_match:
                        folder_path = path_match.group(1).strip()
                if not folder_path:
                    path_match = re.search(r"(?:Carpeta|ruta):\s*([A-Za-z]:[^\n.]*?)(?:\s*\.|$|\n)", out, re.IGNORECASE)
                    if not path_match:
                        path_match = re.search(r"([A-Za-z]:[^\n]*?workspace[^\n]*?output[^\n]*?[^\s\n]+?)(?=\s*\.\s|\s+\d|\n)", out)
                    if path_match:
                        folder_path = path_match.group(1).strip()
                if folder_path and Path(folder_path).is_dir():
                    repo_name = "ficha-jugador" if name == "ficha_jugador" else (re.sub(r"[^\w\-]", "-", (task_arg or name)[:30]).strip("-").lower() or name.replace("_", "-"))
                    try:
                        from github_helper import publish_folder
                        ok, url_or_err = publish_folder(folder_path, repo_name)
                        history.append({"cmd": "GITHUB:push (auto)", "out": url_or_err})
                        logger.info("Auto GitHub push: %s", url_or_err[:150])
                    except Exception as e:
                        history.append({"cmd": "GITHUB:push (auto)", "out": str(e)})
            continue

        # CREATE_SKILL: crear nuevo skill (el agente escribe el código)
        if action.upper() == "CREATE_SKILL":
            if "\n" not in value:
                history.append({"cmd": "CREATE_SKILL", "out": "Formato: CREATE_SKILL: nombre\\n<código Python con def run(task=\"\", **kwargs) -> str>"})
                continue
            name_line, _, code = value.partition("\n")
            name = name_line.strip().split()[0] if name_line.strip() else ""
            code = code.strip()
            if not name or not code:
                history.append({"cmd": "CREATE_SKILL", "out": "Indica nombre y código Python en las líneas siguientes."})
                continue
            ok, msg = create_skill_file(workspace_dir, name, code)
            if ok:
                skills_registry = load_skills(workspace_dir)
            history.append({"cmd": f"CREATE_SKILL:{name}", "out": msg})
            continue

        raw_cmd = value.strip()
        if action.upper() == "INSTALL":
            # Solo el nombre del paquete (evita que el modelo ponga "INSTALL: ** `install python-pptx`" y se ejecute como COMMAND)
            pkg_match = re.search(r"[\w][\w.-]*", raw_cmd)
            raw_cmd = "INSTALL: " + (pkg_match.group(0) if pkg_match else raw_cmd)
            # Para tareas de clima no permitir INSTALL: python (no hace falta; usar SKILL o BROWSER)
            _task_lower = task.lower()
            if ("clima" in _task_lower or "tiempo" in _task_lower or "weather" in _task_lower) and _normalize_cmd(raw_cmd) == "python":
                logger.info("Bloqueado INSTALL: python para tarea de clima; redirigir a SKILL o BROWSER.")
                history.append({
                    "cmd": raw_cmd,
                    "out": "[exit 1] Para el clima no instales Python. Usa SKILL:clima <ciudad> si está en la lista de skills, o BROWSER:go https://wttr.in/<ciudad> y BROWSER:content.",
                })
                continue

        # Evitar repetir el mismo COMMAND (ej. "abre la calculadora")
        if action.upper() == "COMMAND" and history:
            last_cmd = (history[-1].get("cmd") or "").strip()
            if last_cmd and raw_cmd and _same_command(last_cmd, raw_cmd):
                logger.info("Mismo comando que el paso anterior; no repetir. Tarea completada.")
                history.append({"cmd": raw_cmd, "out": "(ya ejecutado en el paso anterior; tarea completada)"})
                if return_history:
                    _append_session_if(workspace_dir, session_id, task, "Listo. La acción ya se había ejecutado.")
                    return ("Listo. La acción ya se había ejecutado.", history)
                return None
        # Evitar bucle de "abrir Chrome/navegador" (Start-Process chrome + URL): solo una vez, luego DONE
        if action.upper() == "COMMAND" and _is_launch_browser_command(raw_cmd):
            if _count_recent_launch_browser(history) >= 1:
                logger.info("Ya se ejecutó abrir navegador; no repetir (evitar bucle de pestañas). Tarea completada.")
                history.append({"cmd": raw_cmd, "out": "(navegador ya abierto; tarea completada)"})
                if return_history:
                    _append_session_if(workspace_dir, session_id, task, "Listo. El navegador ya se abrió.")
                    return ("Listo. El navegador ya se abrió.", history)
                return None
        # Cortafuegos genérico: si el mismo COMMAND ya se ejecutó 2+ veces recientes, no repetir (evitar cualquier bucle)
        if action.upper() == "COMMAND" and _count_recent_same_command(history, raw_cmd, max_look=5) >= 2:
            logger.info("Mismo comando ya ejecutado 2+ veces; cortafuegos para evitar bucle. Tarea completada.")
            history.append({"cmd": raw_cmd, "out": "(comando ya ejecutado varias veces; tarea completada)"})
            if return_history:
                _append_session_if(workspace_dir, session_id, task, "Listo. La acción ya se realizó.")
                return ("Listo. La acción ya se realizó.", history)
            return None

        # Evitar repetir el mismo INSTALL que ya falló (una vez = hint; 2+ veces = bloqueo fuerte)
        if action.upper() == "INSTALL" and history:
            same_count = _count_recent_same_command(history, raw_cmd, max_look=6)
            last_failed = _last_step_failed(history)
            last_cmd = (history[-1].get("cmd") or "").strip()
            same_as_last = last_cmd and raw_cmd and _same_command(last_cmd, raw_cmd)
            if same_count >= 2 or (last_failed and same_as_last):
                raw_lower = raw_cmd.lower()
                if "libreoffice" in raw_lower or "openoffice" in raw_lower or "powerpoint" in raw_lower or "presentation" in raw_lower or "pptx" in raw_lower or "impress" in raw_lower:
                    hint = "No repitas este INSTALL. Para presentaciones: INSTALL: python-pptx y luego SCRIPT:python con from pptx import Presentation."
                elif "python" in raw_lower and same_count >= 2:
                    hint = "Python ya está en el sistema. Para clima no instales nada: usa SKILL:clima <ciudad> o BROWSER:go a wttr.in o timeanddate.com."
                else:
                    hint = "Este INSTALL ya falló varias veces. No repitas. Busca alternativa: BROWSER:go a Google, BROWSER:content, o usa otro paquete/ método."
                logger.info("INSTALL repetido o fallido; bloquear e inyectar: %s", hint[:70])
                history.append({"cmd": raw_cmd, "out": f"[exit 1] {hint}"})
                continue

        # Confirmaciones
        if raw_cmd.startswith("pending_confirm"):
            # execute ya devolvió que hay que confirmar
            part = raw_cmd.split(":", 1)[-1].strip()
            if "pending_confirm_install" in raw_cmd:
                logger.info("¿Instalar? Ejecutaré: %s", part)
            else:
                logger.info("¿Ejecutar comando delicado? %s", part)
            try:
                ans = input("¿Ejecutar? (s/n): ").strip().lower()
            except EOFError:
                ans = "n"
            if ans != "s" and ans != "si" and ans != "y" and ans != "yes":
                logger.info("Cancelado por el usuario.")
                continue
            # Re-ejecutar en modo confirmado
            success, out = execute(
                part if not part.startswith("INSTALL") else "INSTALL: " + part.replace("INSTALL:", "").strip(),
                cwd=cwd,
                confirm_destructive=False,
                confirm_install=False,
                auto_confirm=True,
            )
        else:
            success, out = execute(
                raw_cmd,
                cwd=cwd,
                confirm_destructive=confirm_destructive,
                confirm_install=confirm_install,
                auto_confirm=auto_confirm,
            )

        if out.startswith("pending_confirm"):
            # El ejecutor pide confirmación; mostramos y preguntamos
            cmd_to_run = out.split(":", 1)[-1].strip()
            logger.info("Se requiere confirmación: %s", cmd_to_run)
            try:
                ans = input("¿Ejecutar? (s/n): ").strip().lower()
            except EOFError:
                ans = "n"
            if ans not in ("s", "si", "y", "yes"):
                history.append({"cmd": raw_cmd, "out": "(cancelado por usuario)"})
                continue
            success, out = execute(cmd_to_run, cwd=cwd, auto_confirm=True)
            logger.info("Salida: %s", out[:500] + ("..." if len(out) > 500 else ""))
        else:
            logger.info("Salida: %s", out[:500] + ("..." if len(out) > 500 else ""))

        history.append({"cmd": raw_cmd, "out": out})
        if not success and "INSTALL:" not in raw_cmd:
            # Fallo; el siguiente turno del LLM puede intentar INSTALL o otro comando
            logger.warning("El comando falló. El agente puede intentar otra cosa en el siguiente paso.")

    logger.info("Máximo de pasos alcanzado (%d). Parando.", max_steps)
    if return_history:
        msg_limit = "Se alcanzó el límite de pasos de esta sesión. Puedes enviar otro mensaje para que NEO continúe desde aquí (el historial se mantiene) o pide un resumen de lo hecho."
        # Intentar sintetizar un resumen con lo obtenido hasta ahora (para que el usuario reciba algo útil)
        if history:
            synthesized = _synthesize_done_from_history(task, history, config)
            if synthesized and len(synthesized.strip()) > 20:
                msg_limit = synthesized.strip() + "\n\n(Si quieres más detalle o que continúe, envía otro mensaje; el historial se mantiene.)"
            else:
                last_cmd = (history[-1].get("cmd") or "").strip()
                if last_cmd and "DONE" not in last_cmd.upper():
                    short = last_cmd[:80] + ("…" if len(last_cmd) > 80 else "")
                    msg_limit = f"NEO estaba en ello: {short}. Se alcanzó el límite de pasos. Envía otro mensaje para que continúe (el historial se mantiene)."
        _append_session_if(workspace_dir, session_id, task, msg_limit)
        return (msg_limit, history)
    return None


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    flags = [a.lower() for a in sys.argv[1:] if a.startswith("-")]
    auto = "--auto" in flags or "-a" in flags
    one = "--one" in flags or "-1" in flags

    if one:
        max_steps = 1
    else:
        max_steps = None

    task = " ".join(args).strip() if args else input("Tarea: ").strip()
    if not task:
        print("Uso: python -m agent [--auto] [--one] <tarea>")
        print("  --auto  no pide confirmación antes de instalar/destructivos")
        print("  --one   solo un paso (una orden) y para")
        sys.exit(1)

    run_agent(task, auto_confirm=auto, max_steps=max_steps)


if __name__ == "__main__":
    main()
