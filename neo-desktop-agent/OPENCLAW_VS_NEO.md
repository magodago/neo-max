# OpenClaw vs NEO Desktop Agent — Comparativa

Revisión basada en documentación oficial (docs.openclaw.ai, getopenclaw.ai), GitHub (openclaw/openclaw), ClawHub, foros y guías comunitarias (learnopenclaw.com, clawhub.biz). Actualizado febrero 2026.

---

## Resumen ejecutivo

**OpenClaw** es un gateway self-hosted que conecta muchas apps de mensajería a un agente de IA con herramientas reales, memoria persistente, tareas programadas y un ecosistema de skills. **NEO** es un agente de escritorio que recibe tareas (hoy sobre todo por Telegram), ejecuta acciones en el PC (navegador, terminal, documentos, GitHub) y no tiene memoria persistente ni multi-canal ni skills.

Lo que OpenClaw tiene y NEO **no** (o tiene de forma más limitada) se resume más abajo por bloques.

---

## 1. Canales y mensajería

| Aspecto | OpenClaw | NEO |
|--------|----------|-----|
| **Canales** | WhatsApp, Telegram, Discord, Slack, iMessage, Signal, WeChat, Google Chat, Microsoft Teams, WebChat, Mattermost (plugin) | Solo **Telegram** |
| **Multi-canal** | Un mismo gateway sirve todos los canales a la vez | Un bot = un canal (Telegram) |
| **Voz en tiempo real** | Wake word ("hey OpenClaw"), Talk Mode (hablas, responde por voz), notas de voz con transcripción automática, TTS (ElevenLabs, OpenAI, Edge TTS) | Notas de voz por Telegram → transcripción (Whisper) y respuesta en **texto**; sin wake word ni TTS ni modo conversación por voz |
| **Media** | Imágenes, audio, documentos en todos los canales | Documentos, voz, foto por Telegram (descarga y procesa en el agente) |

**Gap NEO:** Un solo canal (Telegram), sin WhatsApp/Discord/Slack, sin wake word, sin TTS ni Talk Mode.

---

## 2. Memoria y contexto

| Aspecto | OpenClaw | NEO |
|--------|----------|-----|
| **Memoria persistente** | Sí: archivos Markdown (USER.md, IDENTITY.md, SOUL.md, AGENTS.md, TOOLS.md) inyectados al inicio de sesión; opcionalmente grafos de conocimiento (Graphiti, Cognee) para relaciones entre hechos | **No**: cada tarea es un run independiente; solo historial de los últimos pasos de esa ejecución |
| **Historial entre sesiones** | Sesiones estables (JSONL), transcript por sesión | Solo lo que cabe en el prompt del run actual (últimos N pasos) |
| **Preferencias / perfil** | USER.md, IDENTITY.md, SOUL.md configurables | No hay perfil ni preferencias persistentes |
| **Conocimiento a largo plazo** | Memoria que "aprende" preferencias y proyectos (con plugins tipo Cognee/Graphiti) | No |

**Gap NEO:** Sin memoria persistente, sin sesiones estables, sin perfil de usuario ni conocimiento a largo plazo.

---

## 3. Automatización y tareas programadas

| Aspecto | OpenClaw | NEO |
|--------|----------|-----|
| **Cron / programado** | Sí: cron (expresiones 5 campos), `every` (intervalos), `at` (recordatorios puntuales); jobs en `~/.openclaw/cron/` | **No** |
| **Heartbeat** | Motor que lanza turnos de agente a intervalo (ej. 30 min) para revisar email, calendario, notificaciones sin que el usuario escriba | **No** |
| **Webhooks** | `POST /hooks/wake`, `POST /hooks/agent` para disparar desde fuera | **No** |
| **Triggers** | Gmail Pub/Sub y otros vía skills | No |

**Gap NEO:** Nada de tareas programadas, ni heartbeat ni webhooks; todo es bajo demanda (usuario escribe o envía algo por Telegram).

---

## 4. Herramientas y ejecución

| Aspecto | OpenClaw | NEO |
|--------|----------|-----|
| **Modelo de herramientas** | Agente con tool use (tipo pi-mono): read, write, edit, exec, apply_patch, etc. + skills + MCP | Acciones fijas: BROWSER, DESKTOP, COMMAND, INSTALL, SCRIPT, GITHUB, SCREENSHOT, DONE |
| **Ejecución real** | "Envía el email" → lo envía; "Añade al calendario" → lo añade (con skills/integraciones) | Ejecuta lo que el agente pide: PowerShell, Python, Playwright, GitHub; no tiene integraciones tipo email/calendario listas |
| **Shell / sistema** | exec, bash, process (background); workspace fijo, opcional sandbox por sesión | COMMAND (PowerShell), SCRIPT (Python/PowerShell), INSTALL (pip/winget) |
| **Navegador** | Navegador dedicado para automatización web, scraping, formularios | Playwright (go, click, fill, content); misma pestaña entre pasos |
| **Escritorio / pantalla** | Vía nodes (iOS/Android) y skills | SCREENSHOT (pyautogui), DESKTOP (click, type, key) en Windows |
| **Archivos** | read, write, edit, apply_patch en workspace | Creación/lectura vía COMMAND o SCRIPT:python |

**Gap NEO:** No hay tool-calling estándar (sí acciones propias); no hay integraciones listas para email/calendario/smart home; no MCP.

---

## 5. Extensibilidad: Skills, plugins, MCP

| Aspecto | OpenClaw | NEO |
|--------|----------|-----|
| **Skills** | Ecosistema propio: Skills instalables (`/skills install @author/skill-name`), ClawHub con miles de skills (productividad, dev, smart home, etc.) | **No**: capacidades fijas en código (BROWSER, COMMAND, SCRIPT, GITHUB, etc.) |
| **Plugins / MCP** | Plugins MCP (Model Context Protocol); compatibilidad con clientes MCP (ej. Claude Code) | **No** MCP ni sistema de plugins |
| **Built-in tools** | ~20 herramientas base (fs, runtime, web, nodes, messaging, automation, memory, sessions) | Acciones definidas en agent.py + executor + desktop_control + github_helper |
| **Añadir integraciones** | Instalar skill o conectar MCP | Requiere cambiar código Python (nuevas acciones o scripts) |

**Gap NEO:** Sin skills, sin ClawHub, sin MCP; extensión = desarrollo interno.

---

## 6. Modelos y privacidad

| Aspecto | OpenClaw | NEO |
|--------|----------|-----|
| **LLM** | Multi-provider: Anthropic (Claude), OpenAI, Ollama, OpenRouter, etc. | **Solo Ollama** (local o red) |
| **Self-hosted** | Gateway en tu máquina/servidor; datos en tu control | Sí: agente + Telegram bot en tu PC; Ollama local |
| **Offline** | Con modelos locales (Ollama), puede ir sin internet | Con Ollama local, puede trabajar offline |
| **API keys** | Bring your own keys (Anthropic, OpenAI, etc.) | No obligatorio (Ollama sin key); GitHub/Telegram en config |

**Gap NEO:** Un solo backend (Ollama); no hay multi-provider ni cambio de modelo por canal/sesión desde config.

---

## 7. Dispositivos y nodos

| Aspecto | OpenClaw | NEO |
|--------|----------|-----|
| **Mobile nodes** | iOS y Android: cámara, GPS, notificaciones, Canvas, pairing con el gateway | **No** |
| **Escritorio** | Principalmente vía skills y exec en el host del gateway | Windows nativo: pantalla, teclado, ratón, navegador (Playwright), PowerShell |

**Gap NEO:** Sin nodos móviles ni integración cámara/GPS/notificaciones en el ecosistema.

---

## 8. UI y operación

| Aspecto | OpenClaw | NEO |
|--------|----------|-----|
| **Dashboard / Control UI** | UI web en el gateway (chat, config, sesiones, nodos); puerto por defecto 18789 | **No**: consola o solo Telegram |
| **Onboarding** | `openclaw onboard --install-daemon` (asistente guiado) | Instalación manual (pip, config.json, token Telegram) |
| **Config** | `~/.openclaw/openclaw.json` (canales, agent, skills, cron, etc.) | `config.json` (Ollama, Telegram, vision_model, GitHub, max_steps) |

**Gap NEO:** Sin UI de control, sin wizard de onboarding.

---

## 9. Qué sí tiene NEO (y OpenClaw no o lo tiene distinto)

- **Control directo del escritorio Windows**: SCREENSHOT, DESKTOP (pyautogui), COMMAND (PowerShell), todo en la misma máquina donde corre el agente.
- **Stack simple**: Python + Ollama + Telegram; sin Node, sin daemon ni gateway aparte.
- **Auto-instalación y resiliencia**: INSTALL (pip/winget), detección de fallos, búsqueda de soluciones en web, anti-bucles (comandos repetidos, abrir navegador).
- **Documentos y voz en Telegram**: PDF, DOCX, Excel, imágenes, notas de voz con transcripción (Whisper) y respuesta en el mismo chat.
- **GitHub integrado**: GITHUB:push para subir carpetas, crear repo y Pages (ideal para "juego y enlace").
- **Un solo proceso**: no requiere gateway + nodos; suficiente con `python -m telegram_bot` y Ollama.

---

## 10. Roadmap sugerido para acercar NEO a OpenClaw (priorizado)

1. **Memoria persistente mínima**  
   Archivo(s) tipo USER.md / prefs (nombre, preferencias, últimas tareas) que se inyecten al inicio de cada run. Opcional: vector store sencillo (SQLite + embeddings) para "recordar" conversaciones o hechos.

2. **Más canales**  
   Al menos WhatsApp o Discord además de Telegram (adaptadores similares a telegram_bot.py).

3. **Voz salida (TTS)**  
   Respuesta en audio en Telegram (voice note) cuando el usuario envíe voz o pida "respóndeme por voz" (Edge TTS o ElevenLabs).

4. **Tareas programadas**  
   Cron simple (ej. script que cada X minutos encole una tarea o llame a `run_agent` con un prompt fijo) o webhook HTTP para triggers externos.

5. **Skills / plugins mínimos**  
   Carpeta `skills/` con módulos Python que registren acciones extra (ej. "EMAIL: enviar a X con asunto Y") sin tocar el core del agente.

6. **MCP (opcional)**  
   Servidor MCP que exponga herramientas de NEO para que Claude Code u otros clientes MCP las usen.

7. **Multi-modelo**  
   Config para elegir proveedor (Ollama, OpenAI, Anthropic) y modelo en config.json.

8. **UI web mínima**  
   Dashboard simple (historial de tareas, estado, log, config básica) en Flask/FastAPI junto al bot.

---

## Fuentes consultadas

- docs.openclaw.ai (Agent Runtime, Tools, Skills, Cron, Webhooks, TTS, Channels)
- getopenclaw.ai/features (memoria, self-hosted, automatización, voz)
- github.com/openclaw/openclaw
- learnopenclaw.com (Skills, Automation, Voice)
- docs.openclaw.ai/tools/clawhub (ClawHub)
- getopenclaw.ai/help/cron-heartbeat-automation
- Cognee/Graphiti memory integrations for OpenClaw
