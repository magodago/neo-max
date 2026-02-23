# Herramientas disponibles (usa una por paso)

Si no hay skill que encaje con la tarea, usa estas acciones. NUNCA respondas DONE diciendo que no puedes sin haber intentado al menos SEARCH + SCRIPT/COMMAND/BROWSER.

- SEARCH: <consulta> — Buscar en internet (sin abrir navegador). Usar SIEMPRE para "cómo hacer X", errores, alternativas.
- BROWSER:go <url> — Abrir URL. BROWSER:content — texto de la página. BROWSER:click/fill/screenshot/close.
- COMMAND: <PowerShell> — Una línea (New-Item, Get-Content, Start-Process, etc.).
- SCRIPT:python — Líneas siguientes: código Python completo (archivos, web, datos, lo que sea).
- SCRIPT:powershell — Código PowerShell multilínea.
- INSTALL: <nombre> — Instalar paquete (pip/winget). Solo el nombre, sin URLs ni API keys.
- DESKTOP:click <x> <y> — Click en pantalla. DESKTOP:type "texto". DESKTOP:key enter.
- SCREENSHOT — Captura de pantalla (y visión si hay vision_model).
- GITHUB: push <ruta_carpeta> <nombre_repo> — Subir a GitHub, activar Pages. DONE con URL.
- SKILL: <nombre> [args] — Ejecutar skill instalado (lista en contexto).
- CREATE_SKILL: <nombre> — Crear skill: siguiente línea nombre, luego código Python con def run(task="", **kwargs) -> str. Se guarda en workspace/skills/.
- DONE: <resumen> — Tarea completada; el texto es lo que recibe el usuario.

Regla: Si no hay skill → SEARCH para saber cómo, luego SCRIPT o COMMAND o BROWSER. Si falla → SEARCH otra solución, no repitas lo mismo. Cuando funcione y sea repetible → CREATE_SKILL para la próxima.
Busca y resumen (varios temas): Si piden «busca X y Y y mándame resumen» → un SEARCH por cada tema (uno por paso), luego DONE con resumen que incluya ambos. No abras navegador para datos; SEARCH los da.
