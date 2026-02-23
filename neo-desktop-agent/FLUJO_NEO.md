# Flujo NEO: cerebro, memoria, proactividad y autonomía

## Cómo está conectado todo

1. **Arranque**  
   Al ejecutar `python telegram_bot.py` (o `python -m telegram_bot`), el bot inicia y llama a `scheduler.start_background()`. Ahí se lanzan en segundo plano:
   - **Loop proactivo** (si `proactive_agent.enabled` es true)
   - Heartbeat (si está configurado)
   - Cron jobs (si hay `cron_jobs`)
   - Magia diaria (si `magia_historia_daily.enabled`)
   - **Recordatorios** (siempre): aviso por Telegram a la hora programada

2. **Cerebro**  
   El “cerebro” es **Ollama** (modelo en `config.json`, p. ej. `qwen2.5:7b-instruct`):
   - Cuando **tú escribes** en Telegram → `agent.run_agent()` usa ese modelo para decidir pasos (COMMAND, BROWSER, SKILL, DONE, etc.).
   - Cuando **NEO actúa solo** (proactivo) → el mismo modelo recibe el prompt “¿Qué quieres hacer ahora?” y responde PROPOSE / CALL / GIF / NOPROPOSE.

3. **Memoria**  
   - **Bootstrap** (`workspace/USER.md`, `IDENTITY.md`, `SOUL.md`, `AGENTS.md`, `TOOLS.md`, `LEARNED.md`): se carga en cada ejecución del agente y también en el **loop proactivo**. NEO tiene tu perfil (David), identidad (NEO), tono, recordatorios de AGENTS y lo aprendido en LEARNED.
   - **Sesión** (p. ej. `workspace/sessions/954890221.jsonl`): últimos turnos de la conversación por Telegram; el agente los usa cuando tú escribes (no en el loop proactivo).
   - **Recordatorios** (`workspace/recordatorios.json`): fechas/hora y chat_id; el scheduler los revisa y envía el aviso por Telegram a la hora.

4. **Proactividad (decisiones propias)**  
   - En ventana **9:00–23:00**, cada `interval_minutes` (con un poco de aleatoriedad) el loop proactivo:
     - Carga la misma memoria bootstrap (USER, LEARNED, etc.).
     - Pregunta a Ollama: “¿Qué quieres hacer ahora por David?” (a veces con un nudge: “considera CALL o GIF”).
     - Parsea la respuesta (PROPOSE: / CALL: / GIF: / NOPROPOSE) y actúa:
       - **PROPOSE** → mensaje de texto por Telegram.
       - **CALL** → nota de voz por Telegram + llamada Twilio al móvil (si está configurado).
       - **GIF** → GIF por Telegram (Giphy).
       - **NOPROPOSE** → no envía nada.
   - NEO **no** recibe tu mensaje en ese momento; decide solo en función de memoria y del prompt. Es automático y con decisiones propias.

5. **Por qué a veces solo texto (y no llamada/GIF)**  
   - El modelo puede responder muchas veces **PROPOSE** o **NOPROPOSE**; antes el parsing era estricto y cualquier variación (“Call: …” o texto extra) no se reconocía.
   - **Cambios hechos**: (1) parsing más robusto (solo primera línea, se acepta espacio tras `:`); (2) nudge aleatorio para que ~35 % de las veces se pida “considera CALL o GIF”; (3) prompt que pide “varía, no siempre PROPOSE”; (4) **interval_minutes**: con 120 hay pocos ciclos al día; con **60** hay más oportunidades (recomendado en CONFIG_OPCIONAL.md).
   - Revisa los logs: verás líneas como `Proactivo decisión NEO: CALL | raw: ...`. Si sale `?(sin formato)` o `respuesta no reconocida`, el modelo no está devolviendo exactamente PROPOSE:/CALL:/GIF:/NOPROPOSE.

## Resumen

| Parte        | Dónde está | Conectado a |
|-------------|------------|-------------|
| Cerebro     | Ollama     | Agente (tareas) y loop proactivo (PROPOSE/CALL/GIF) |
| Memoria     | workspace/*.md + sessions/*.jsonl + recordatorios.json | Bootstrap en agente y proactivo; sesión solo en agente |
| Proactividad| scheduler._proactive_loop | Misma memoria bootstrap, mismo modelo, ventana 9–23 h |
| Llamada/GIF | voice_out.call_user_phone, giphy_helper | Proactivo cuando NEO responde CALL: o GIF: |

Si no recibes llamadas ni GIFs: comprueba que el bot lleva tiempo corriendo, que es horario 9–23, que en logs aparece “Proactivo iniciado” y “Proactivo decisión NEO: …”. Bajar `interval_minutes` a 60 y reiniciar el bot da más ciclos para que NEO elija CALL o GIF.
