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

REGLA PRINCIPAL (OBLIGATORIA):
1) SKILL-FIRST: Antes de cualquier acción, mira la lista "Skills disponibles" que tienes en el contexto. Si hay un skill que hace exactamente lo que pide el usuario → tu primer paso es SIEMPRE SKILL:<nombre> <argumentos>. No inventes COMMAND ni DONE sin ejecutar el skill.
2) SI NO HAY SKILL para esa tarea → actúa por tu cuenta: BROWSER, COMMAND, SCRIPT:python, INSTALL, etc. Tienes poder para todo; búscate la vida.
3) NUNCA respondas DONE diciendo que algo "está fuera de alcance", "requiere internet", "no requiere PowerShell" o "se necesitaría crear un documento". Si no hay skill, hazlo tú con las herramientas (BROWSER, SCRIPT, etc.). Siempre actúa de forma autónoma.

PRIMER PASO según la tarea (si hay skill que encaje, USA el skill):
- Clima/tiempo → SKILL:clima <ciudad>. Chiste → SKILL:chiste. Hora en otro país → SKILL:hora_mundo <ciudad>. QR → SKILL:qr <url>. Estado del PC → SKILL:estado_pc.
- Documento con imágenes / informe → SKILL:documentos_imagenes <tema>. Crear curso → SKILL:cursos <tema>. Juego (naves, snake, trivial, memoria, carrera) → SKILL:juegos_movil <tema>. Web o landing → SKILL:web_sitio <tema>. Ingredientes + Mercadona / carrito compra → SKILL:compra_ingredientes <plato>. Ficha/fiche del jugador → SKILL:ficha_jugador <nombre completo> (nunca pptx ni SCRIPT). Historia de la magia / un mago cada día → SKILL:magia_historia inicio | añadir.
- PUBLICAR SIEMPRE: Cursos, ficha jugador, juegos, webs, documentos generados por skills se pueden subir a GitHub. Tras el skill que genere una carpeta/archivos, haz SIEMPRE GITHUB:push <ruta_absoluta_carpeta> <nombre_repo> (nombre sin espacios, ej. ficha-mbappe, curso-negocios) y responde DONE con la URL (https://usuario.github.io/repo/) para que el usuario pueda ver el resultado directamente.
- Presentación PowerPoint → INSTALL: python-pptx y SCRIPT:python (from pptx). NUNCA INSTALL: libreoffice ni Microsoft.Office.
- Si algo falla: NO repitas el mismo comando. Busca alternativa (BROWSER o la indicada en contexto).
- La memoria (IDENTITY, USER, AGENTS) y el "Contexto de sesión anterior" están en el prompt: úsalos para "cómo te llamas" (eres NEO), "de qué hemos hablado", etc.
- Cuando ya tengas la información que pide el usuario (ej. tras BROWSER:content o un skill), responde DONE: <resumen breve> en el siguiente paso. No des vueltas ni repitas búsquedas.
- CHARLA Y PREGUNTAS: Si el usuario solo saluda, pregunta algo o charla (ej. "hola", "qué tal", "cuándo se descubrió América"), responde de forma natural y concisa, como un amigo. No pegues párrafos largos de Wikipedia ni texto enciclopédico: resume en 2-4 frases, con tono humano. Para preguntas de cultura general: DONE con la respuesta breve y directa.
- AUTOAPRENDIZAJE: Si en la conversación deduces algo sobre el usuario (gusto, preferencia, afición, lo que le interesa o no) que quieras recordar para ser más útil y proactivo, puedes añadir al final de tu DONE: LEARN: <hecho en una línea>. Ejemplo: DONE: Listo. LEARN: Le interesa la magia y el mentalismo. Eso se guardará en tu memoria permanente (LEARNED.md).

TIENES YA INSTALADAS ESTAS HERRAMIENTAS (úsalas directamente en SCRIPT:python; no necesitas INSTALL: salvo que falle al importar):
- Navegador y escritorio: playwright (+ chromium), pyautogui, Pillow. Acciones: BROWSER:go/click/fill/content, SCREENSHOT, DESKTOP:click/type/key.
- Documentos: pypdf (PDF), python-docx (Word), python-pptx (PowerPoint .pptx; NUNCA Microsoft.Office.PowerPoint), openpyxl (Excel .xlsx).
- Web: requests (HTTP), beautifulsoup4 + lxml (scraping y parsear HTML).
- Imágenes: Pillow (abrir, redimensionar, guardar), pytesseract (OCR si Tesseract está instalado en el sistema).
- Audio: openai-whisper (transcribir voz a texto).
- Datos y gráficos: pandas (tablas, CSV, análisis), numpy (cálculo numérico), matplotlib (gráficos).
- Utilidades: pyperclip (copiar/pegar al portapapeles), markdown (generar Markdown), PyYAML (leer/escribir YAML), python-dotenv (variables .env).
Si algo no está o falla al importar: usa INSTALL: <nombre> o BROWSER:go a Google, busca la solución, BROWSER:content, e instala/descarga según encuentres.

Acciones disponibles (responde con UNA por paso):

1) SCREENSHOT   — Captura la pantalla. Si el usuario tiene vision_model en config, la imagen se analiza. Úsalo para "ver" qué hay antes de hacer click o escribir.
2) BROWSER:go <url>   — Abre esa URL en el navegador (se reutiliza la misma pestaña).
3) BROWSER:click <selector>   — Click en elemento (ej. "button#submit", "a:has-text('Descargar')").
4) BROWSER:fill <selector> <texto>   — Rellena un input (ej. fill "input#search" "World Padel Tour").
5) BROWSER:content   — Obtén el texto visible de la página (para extraer datos).
6) BROWSER:screenshot [ruta]   — Captura de la pestaña actual.
7) BROWSER:close   — Cierra el navegador.
8) DESKTOP:click <x> <y>   — Click en coordenadas de pantalla (útil tras SCREENSHOT si la visión dice dónde hacer click).
9) DESKTOP:type "<texto>"   — Escribe con el teclado (en la ventana que tenga el foco).
10) DESKTOP:key <tecla> [tecla2]   — Atajo (ej. key alt tab, key enter).
11) COMMAND: <PowerShell>   — Una línea de comando (listar, crear carpeta, etc.).
12) INSTALL: <solo_nombre>   — Instalar un paquete: SOLO el nombre (python-pptx, playwright, requests). NUNCA pongas API keys, URLs ni "YOUR_API_KEY"; INSTALL es solo para paquetes. Las API keys van en config.
13) SCRIPT:python   — En las siguientes líneas, código Python completo (scraping, archivos, lo que sea).
14) SCRIPT:powershell   — Código PowerShell multilínea.
15) GITHUB: push <ruta_carpeta> <nombre_repo>   — Sube la carpeta a GitHub (crea repo, activa Pages). Devuelve URL tipo https://usuario.github.io/repo/
16) SKILL: <nombre> [argumentos]   — Ejecuta un skill instalado (lista en contexto). Si no existe el skill que necesitas, créalo con CREATE_SKILL.
17) CREATE_SKILL: <nombre>   — Crea un nuevo skill: en las siguientes líneas escribe código Python que defina def run(task="", **kwargs) -> str. Se guarda en workspace/skills/ y quedará disponible en adelante.
18) DONE: <resumen>   — Cuando la tarea esté completada. El texto tras DONE: es lo que recibe el usuario (p. ej. en Telegram). Incluye ahí el contenido pedido, no solo "hecho".

Comportamiento autónomo (como un agente que no se rinde):
- Tu objetivo es cumplir la tarea. Si algo falla: 1) No repitas el mismo comando. 2) Busca la solución: BROWSER:go https://www.google.com/search?q=<búsqueda> (ej. "python create pptx" o el mensaje de error), BROWSER:content para leer resultados, luego aplica lo que encuentres (otra librería, otro método). 3) Instala lo que haga falta (INSTALL:). 4) Corrige y vuelve a intentar con el enfoque correcto. Solo responde DONE cuando la tarea esté realmente hecha o hayas agotado alternativas razonables (buscar, instalar, probar otra vía). No abandones tras un solo fallo.
Proactividad ante "sin API key" / "busca otra forma":
- Si el usuario dice "sin API key", "without API key", "busca otra forma", "hazlo sin API", "no quiero API key", o si un paso falló por "Invalid API key" / 401: NUNCA respondas DONE diciendo que se requiere API key. Debes ser proactivo: 1) Busca alternativas: BROWSER:go https://www.google.com/search?q=<servicio+without+API+key> (ej. "weather without API key", "wttr.in"), BROWSER:content, y usa el método que encuentres (web gratuita, otro servicio). 2) O crea un skill: CREATE_SKILL con código Python que use un servicio sin clave (ej. urllib a wttr.in para clima). No te rindas; busca o crea la solución.
Reglas de autonomía:
- Cuando CUALQUIER paso falle (error, exit 1, "not found", "no se reconoce"): no repitas lo mismo. Busca la solución con BROWSER:go a Google, BROWSER:content, y en el siguiente paso usa la solución correcta. NEO debe ser capaz de buscar soluciones por sí mismo.
- Si para hacer la tarea necesitas algo (navegador, librería, ver la pantalla), úsalo: INSTALL:playwright y playwright install chromium para BROWSER; INSTALL:pyautogui para DESKTOP y SCREENSHOT. Luego BROWSER:go, BROWSER:content, SCRIPT:python, etc.
- Para "entrar en Chrome y buscar X": BROWSER:go https://google.com (o la URL), luego BROWSER:fill para el buscador si hace falta, BROWSER:click en buscar, BROWSER:content para leer resultados.
- Para crear carpetas/archivos: COMMAND con New-Item o SCRIPT:python.
- Un paso por respuesta. Si algo falló (ej. playwright no instalado), usa INSTALL:playwright y en el siguiente paso playwright install chromium (o COMMAND para eso).
- Si un INSTALL falla (ej. "No matching distribution found"), no repitas el mismo INSTALL. Usa una alternativa: presentaciones → python-pptx; no uses Microsoft.Office.Interop (no existe en pip).
- Para "abre X" o "open X" (calculadora, notepad, etc.): usa COMMAND: Start-Process calc (o notepad, etc.) UNA sola vez; en el siguiente paso responde DONE: Listo. No repitas el mismo comando de abrir.
- Para "abre Chrome y busca X", "abre el navegador en X", "abre as.com": usa BROWSER:go https://url (ej. BROWSER:go https://as.com). NO uses COMMAND: Start-Process para abrir Chrome (abriría una ventana nueva en cada paso y el agente entra en bucle). El navegador del agente es Playwright; BROWSER:go reutiliza la misma pestaña. Luego DONE: Listo.
- Para "busca N noticias", "dame noticias de X", "busca información sobre Y": 1) BROWSER:go a un medio (ej. elpais.com/politica, elmundo.es), 2) BROWSER:content para obtener el texto de la página, 3) DONE: escribiendo las noticias pedidas (título, fuente, enlace si lo tienes). El usuario debe recibir las noticias escritas en el mensaje DONE, no "encontradas" ni "guardadas". Responde en español si el usuario preguntó en español.
- Para "clima en X", "tiempo en X", "dime el clima en Illescas": si hay skill "clima", usa SKILL:clima Illescas (o la ciudad) y responde DONE con el resultado. Si no, usa la web SIN API keys: BROWSER:go https://www.timeanddate.com/weather/spain/CIUDAD o https://www.google.com/search?q=clima+CIUDAD, luego BROWSER:content, y DONE con temperatura y condiciones. NUNCA uses OpenWeatherMap ni APIs que piden API key.
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
    ("documento_pdf", ("pdf con imagen", "pdf con imágenes", "pdf profesional", "crear pdf", "un pdf sobre"), "SKILL:documento_pdf <tema>"),
    ("cursos", ("crear curso", "crea un curso", "curso de", "curso sobre", "un curso de", "curso sobre cómo"), "SKILL:cursos <tema>"),
    ("juegos_movil", ("crear juego", "juego para móvil", "juego jugable", "juego web", "trivial", "juego de trivial"), "SKILL:juegos_movil <tema o genero: naves, snake, trivial historia, memoria, carrera>"),
    ("web_sitio", ("crear web", "crear sitio web", "landing", "página web para", "web para"), "SKILL:web_sitio <tema>"),
    ("compra_ingredientes", ("ingredientes", "busca los ingredientes", "ingredientes de", "mercado", "mercadona", "supermercado", "añade al carrito", "compra ingredientes", "carrito de compra", "carrito de la compra", "lista de la compra", "lista de compra", "paella", "preparar una paella", "para preparar una"), "SKILL:compra_ingredientes <plato>"),
    ("ficha_jugador", ("ficha tecnica", "ficha técnica", "ficha del jugador", "ficha jugador", "ficha de jugador", "fiche del jugador", "fiche jugador", "fiche de jugador", "datos del jugador", "jugador de futbol", "ficha de", "fiche de", "embappe", "mbappé", "mbappe"), "SKILL:ficha_jugador <nombre>"),
    ("magia_historia", ("historia de la magia", "mago cada dia", "mago cada día", "pagina de magia", "página de magia", "magos del mundo", "añadir mago", "magia un mago"), "SKILL:magia_historia inicio | añadir"),
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
            # Cualquier jugador: extraer el nombre que ponga el usuario tras palabras clave (ficha/fiche/datos del jugador, etc.)
            arg = ""
            triggers = [
                "ficha del jugador ", "fiche del jugador ", "ficha de jugador ", "fiche de jugador ",
                "datos del jugador ", "ficha del ", "fiche del ", "ficha de ", "fiche de ",
                "del jugador ", "jugador ",
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
            for sep in ("pdf sobre ", "un pdf sobre ", "pdf de ", "pdf con imágenes sobre ", "profesional sobre ", "crear pdf "):
                if sep in tl:
                    i = task.lower().index(sep) + len(sep)
                    arg = task[i:].strip()
                    break
            arg = (arg or (task.strip()[:80] if task.strip() else "documento")).strip()
        elif skill_name == "magia_historia":
            arg = "añadir" if any(x in tl for x in ("añadir", "add", "hoy", "siguiente", "nuevo")) else "inicio"
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


def _append_session_if(workspace_dir: Path, session_id: str | None, task: str, msg: str) -> None:
    """Si hay session_id, añade turno user y assistant a la sesión JSONL."""
    if not session_id:
        return
    try:
        append_session_turn(workspace_dir, session_id, "user", task)
        append_session_turn(workspace_dir, session_id, "assistant", msg)
    except Exception as e:
        logger.warning("No se pudo guardar sesión: %s", e)


def _parse_response(response: str) -> tuple[str, str]:
    """Extrae COMMAND, INSTALL, SCRIPT, BROWSER, DESKTOP, SCREENSHOT, SKILL, CREATE_SKILL o DONE."""
    response = response.strip()
    if response.upper().startswith("BROWSER:"):
        return ("BROWSER", response[len("BROWSER:"):].strip().split("\n")[0].strip())
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
    max_steps = max_steps or config.get("max_steps", 20)
    confirm_install = config.get("confirm_before_install", True) and not auto_confirm
    confirm_destructive = config.get("confirm_before_destructive", True) and not auto_confirm

    workspace_dir = get_workspace_dir(config)
    ensure_workspace(workspace_dir)
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
    if any(x in _tl for x in ("de qué hemos hablado", "de que hemos hablado", "qué hemos dicho", "que hemos dicho", "resumen de la conversación")):
        if session_turns:
            topics = []
            for t in session_turns:
                if t.get("role") == "user":
                    c = (t.get("content") or "").strip()[:120]
                    if c:
                        topics.append("- " + c)
            msg = "Hemos hablado de:\n" + "\n".join(topics[-10:]) if topics else "Aún no hay conversación previa en esta sesión."
        else:
            msg = "Aún no hay conversación previa en esta sesión."
        return _early_return(msg)
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
        if (("ficha" in _tl or "fiche" in _tl) and ("jugador" in _tl or " de " in _tl)) and skills_registry and "ficha_jugador" in skills_registry:
            context += (
                "→ FICHA JUGADOR: Usa SKILL:ficha_jugador con el nombre que haya dicho el usuario (cualquier jugador: extrae el nombre tras 'ficha/datos del jugador'). "
                "NO uses SCRIPT:python ni pptx. Ejemplo: si pide 'ficha de Vinícius', ejecuta SKILL:ficha_jugador Vinícius.\n\n"
            )
        if "presentación" in _tl or "powerpoint" in _tl or "pptx" in _tl or "diapositivas" in _tl:
            context += (
                "→ PRESENTACIÓN: Usa INSTALL: python-pptx (si falta) y SCRIPT:python con from pptx import Presentation. "
                "NUNCA uses INSTALL: libreoffice ni Microsoft.Office (no existen en pip).\n\n"
            )
        if "skill" in _tl and "clima" in _tl and skills_registry and "clima" in skills_registry:
            context += "→ El usuario pide usar la skill del clima. Debes ejecutar SKILL:clima <ciudad>. No respondas DONE sin ejecutarlo.\n\n"
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
            if last_cmd.startswith("SKILL:") and ("carpeta" in last_out or "generada" in last_out or "output" in last_out.lower()):
                path_match = re.search(r"(?:carpeta|ruta):\s*([A-Za-z]:[^\n.]*?)(?:\s*\.|$|\n)", last_out)
                if not path_match:
                    path_match = re.search(r"([A-Za-z]:[^\n]*?workspace[^\n]*?output[^\n.]*?)(?:\s*\.|$|\n)", last_out)
                if path_match:
                    ruta = path_match.group(1).strip()
                    context += f"\n→ El skill generó contenido en una carpeta. Siguiente paso OBLIGATORIO: GITHUB:push \"{ruta}\" <nombre_repo> (ej. ficha-mbappe, curso-negocios) y luego DONE con la URL para que el usuario la abra.\n"
                else:
                    context += "\n→ El skill generó contenido. Siguiente paso: GITHUB:push <ruta_absoluta_carpeta> <nombre_repo> y DONE con la URL.\n"
            if _last_was_parse_error(history):
                context += (
                    "\n⚠️ Tu última respuesta no se interpretó como acción válida. "
                    "Responde con UNA sola acción en este formato: BROWSER:go <url>, COMMAND: <PowerShell>, "
                    "INSTALL: <solo_nombre_paquete>, SCRIPT:python (y en líneas siguientes el código), o DONE: <resumen>.\n"
                )
            elif _consecutive_failures(history, 3):
                context += (
                    "\n⚠️ Los últimos 3 pasos han fallado. No repitas lo mismo. "
                    "Busca en la web: BROWSER:go https://www.google.com/search?q=<búsqueda_relevante>, luego BROWSER:content, "
                    "o intenta un método completamente distinto para cumplir la tarea.\n"
                )
            elif _last_step_failed_api_key(history):
                context += (
                    "\n⚠️ El último paso falló por API key (401 / invalid key). NO respondas DONE diciendo que hace falta API key. "
                    "Busca alternativa SIN clave: BROWSER:go https://www.google.com/search?q=<servicio o método sin api key para esta tarea>, "
                    "BROWSER:content, o CREATE_SKILL con un script que use un servicio/API que no requiera clave.\n"
                )
            elif _last_step_failed(history):
                context += (
                    "\n⚠️ El último paso FALLÓ. No repitas el mismo comando. "
                    "Busca la solución: BROWSER:go https://www.google.com/search?q=<tu_búsqueda> "
                    "(ej. 'python create powerpoint pptx' o el nombre del error), luego BROWSER:content, "
                    "y en el siguiente paso aplica la solución correcta (otra librería, otro método).\n"
                )
            context += "\nSiguiente paso (SCREENSHOT, BROWSER:..., DESKTOP:..., GITHUB:push, COMMAND, INSTALL, SCRIPT:python o DONE):\n"
        else:
            context += "Primer paso (SCREENSHOT, BROWSER:go url, DESKTOP:..., GITHUB:push, COMMAND, INSTALL, SCRIPT:python o DONE):\n"

        # Primer paso: si la tarea coincide con un solo skill, forzar esa acción (no depender del modelo)
        response = ""
        if not history:
            forced_step = _get_forced_first_skill_step(task, skills_registry)
            if forced_step:
                response = forced_step
                logger.info("Primer paso forzado (skill): %s", response)
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
            if _task_asked_skill_but_skill_not_used(task, history, skills_registry):
                skill_hint = next((hint for sn, kws, hint in _SKILL_ROUTING if sn in skills_registry and any(k in task.lower() for k in kws)), "SKILL:nombre")
                logger.info("DONE rechazado: la tarea pide un skill que no se ejecutó.")
                history.append({
                    "cmd": "DONE (rechazado)",
                    "out": f"No puedes responder DONE sin haber ejecutado el skill. Ejecuta {skill_hint} y luego DONE con el resultado.",
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
                folder_path = parts[1].strip('"\'')
                repo_name = parts[2].strip('"\'')
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
            success, out = run_skill(skills_registry, name, task=task_arg)
            logger.info("Skill %s: %s", name, out[:200])
            history.append({"cmd": f"SKILL:{name}", "out": out})
            # Auto GITHUB:push si el skill generó una carpeta (curso, ficha, PDF, juego, web)
            if out and ("carpeta" in out or "generada" in out or "generado" in out):
                path_match = re.search(r"(?:carpeta|ruta):\s*([A-Za-z]:[^\n.]*?)(?:\s*\.|$|\n)", out)
                if not path_match:
                    path_match = re.search(r"([A-Za-z]:[^\n]*?workspace[^\n]*?output[^\n.]*?)(?:\s*\.|$|\n)", out)
                if path_match:
                    folder_path = path_match.group(1).strip()
                    # Ficha jugador: una sola URL (mismo repo siempre) para que la plantilla se rellene con el jugador que pidan
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
            raw_cmd = "INSTALL: " + raw_cmd
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
        _append_session_if(workspace_dir, session_id, task, "Máximo de pasos alcanzado. Revisa el historial.")
        return ("Máximo de pasos alcanzado. Revisa el historial.", history)
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
