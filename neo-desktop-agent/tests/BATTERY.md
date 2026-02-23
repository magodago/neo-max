# Batería de pruebas NEO

Marca con `[x]` las que pasen y deja `[ ]` las que fallen. Luego podemos arreglar una por una.

**Cómo ejecutar:**
- Solo skills (sin Ollama): `python tests/run_battery.py`
- Solo skills rápidos (clima, chiste, hora, qr, estado_pc): `python tests/run_battery.py --quick`
- Con agente (Ollama + pasos): `python tests/run_battery.py --agent`
- Solo listar pruebas: `python tests/run_battery.py --list`

Desde la raíz del proyecto: `neo-desktop-agent`.

El script escribe también `tests/RESULTS.txt` con OK/FAIL por línea.

---

## 1. Skills (ejecución directa)

| # | Skill | Prueba | Estado |
|---|--------|--------|--------|
| S1 | clima | Clima en Madrid (wttr.in) | [ ] |
| S2 | chiste | Un chiste | [ ] |
| S3 | hora_mundo | Hora en Londres | [ ] |
| S4 | qr | QR de https://example.com | [ ] |
| S5 | estado_pc | Estado del PC (CPU/RAM) | [ ] |
| S6 | documento_pdf | PDF 1 página sobre un tema (requiere Gemini) | [x] |
| S7 | documentos_imagenes | Documento con imagen (puede requerir API) | [ ] |
| S8 | cursos | Curso mínimo sobre "test" | [ ] |
| S9 | juegos_movil | Juego tipo snake | [ ] |
| S10 | web_sitio | Web/landing sobre "test" | [ ] |
| S11 | compra_ingredientes | Ingredientes paella / Mercadona | [ ] |
| S12 | ficha_jugador | Ficha de Mbappé (HTML/URL) | [ ] |
| S13 | magia_historia | Inicio o añadir mago | [ ] |
| S14 | generar_imagen | Imagen por descripción (requiere Gemini) | [ ] |

---

## 2. Agente — Early returns (sin ejecutar LLM complejo)

| # | Prueba | Entrada | Esperado | Estado |
|---|--------|---------|----------|--------|
| A1 | Nombre | "¿Cómo te llamas?" | Respuesta contiene "NEO" | [ ] |
| A2 | Listar skills | "¿Qué skills tienes?" | Lista de skills (ej. clima, chiste) | [ ] |
| A3 | Charla compartir | "Voy a cenar con mis hijas" | "disfrutad" o similar, sin ejecutar skills | [ ] |
| A4 | De qué hemos hablado | "¿De qué hemos hablado?" | Resumen o "no hay conversación" | [ ] |

---

## 3. Agente — Tareas con skill (Ollama + 1 paso)

| # | Prueba | Entrada | Esperado | Estado |
|---|--------|---------|----------|--------|
| B1 | Clima | "Dime el clima en Illescas" | DONE con temperatura/condiciones | [ ] |
| B2 | Chiste | "Cuéntame un chiste" | DONE con un chiste | [ ] |
| B3 | Hora mundo | "¿Qué hora es en Tokyo?" | DONE con hora | [ ] |
| B4 | Estado PC | "¿Cómo va mi PC?" | DONE con CPU/RAM o similar | [ ] |
| B5 | QR | "Genera un QR de https://google.com" | DONE con archivo o confirmación | [ ] |

---

## 4. Agente — Tareas multi-paso o más complejas

| # | Prueba | Entrada | Esperado | Estado |
|---|--------|---------|----------|--------|
| C1 | Ficha jugador | "Dame la ficha de Leo Messi" | DONE + URL GitHub Pages o ruta | [ ] |
| C2 | PDF | "Crea un PDF de 1 página sobre la guerra fría" | DONE + ruta/PDF (Gemini) | [x] |
| C3 | Curso | "Crea un curso de introducción a Python" | DONE + carpeta/URL | [ ] |
| C4 | Juego | "Crea un juego de snake para móvil" | DONE + URL jugable | [ ] |
| C5 | Web | "Crea una landing de un restaurante" | DONE + URL o ruta | [ ] |
| C6 | Ingredientes | "Dame los ingredientes para una paella" | DONE con lista / Mercadona | [ ] |
| C7 | Abrir calculadora | "Abre la calculadora" | DONE Listo, sin repetir comando | [ ] |
| C8 | Navegador | "Abre el navegador en elpais.com" | BROWSER:go + DONE | [ ] |

---

## 5. Memoria y estado

| # | Prueba | Qué comprobar | Estado |
|---|--------|----------------|--------|
| M1 | update_last_user_at | Tras mensaje usuario, neo_state.json tiene last_user_at | [ ] |
| M2 | update_last_interaction | Tras DONE, last_interaction_summary en neo_state | [ ] |
| M3 | get_learned_recent | LEARNED.md reciente inyectado en contexto | [ ] |
| M4 | LEARN en DONE | DONE: ... LEARN: X → se guarda en LEARNED.md | [ ] |

---

## 6. Recordatorios

| # | Prueba | Entrada | Esperado | Estado |
|---|--------|---------|----------|--------|
| R1 | Recuérdame | "Recuérdame mañana a las 10 comprar pan" | Guardado + Telegram a la hora | [ ] |
| R2 | Recuérdame en N min | "Recuérdame en 2 minutos probar" | Guardado + aviso en 2 min | [ ] |

---

## 7. Proactivo (scheduler)

| # | Prueba | Qué comprobar | Estado |
|---|--------|----------------|--------|
| P1 | get_neo_state | Scheduler lee neo_state (last_user_at, call_this_week, gif_this_week) | [ ] |
| P2 | Nudge ausencia | Si last_user_at > 24h, prompt incluye "Saluda" | [ ] |
| P3 | update_proactive_done | Tras enviar CALL/GIF, call_this_week/gif_this_week a True | [ ] |
| P4 | Motivo visible | Mensaje PROPOSE/CALL lleva prefijo tipo "Me acordé de ti —" | [ ] |

---

## Resumen

- **Skills:** 14
- **Agente early:** 4
- **Agente con skill:** 5
- **Agente complejo:** 8
- **Memoria:** 4
- **Recordatorios:** 2
- **Proactivo:** 4

**Total:** 41 pruebas. Ir marcando y luego arreglar las que fallen.
