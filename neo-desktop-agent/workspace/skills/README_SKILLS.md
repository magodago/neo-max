# Skills de NEO (todos en español)

## Instalados

| Skill | Uso | Descripción |
|-------|-----|-------------|
| **clima** | SKILL:clima Illescas | Clima en una ciudad (sin API key). |
| **chiste** | SKILL:chiste | Chiste aleatorio en español. |
| **hora_mundo** | SKILL:hora_mundo Tokyo | Hora actual en ciudad o zona horaria. |
| **qr** | SKILL:qr https://... | Genera código QR (imagen PNG). |
| **estado_pc** | SKILL:estado_pc | Estado del PC: CPU, RAM, disco. |
| **documentos_imagenes** | SKILL:documentos_imagenes Informe guerra fría | Crea presentación PPTX profesional con imágenes. |
| **cursos** | SKILL:cursos Curso de Python | Crea estructura de curso (módulos, lecciones). Listo para Udemy/Teachable o GitHub Pages. |
| **juegos_movil** | SKILL:juegos_movil Naves espaciales | Crea juego web responsive para móvil. Subir con GITHUB:push y enviar enlace. |
| **web_sitio** | SKILL:web_sitio Landing mi restaurante | Crea web o landing profesional. Subir con GITHUB:push y enviar enlace. |
| **compra_ingredientes** | SKILL:compra_ingredientes paella | Entra en Mercadona, busca ingrediente por ingrediente, anade al carrito y devuelve la URL del carrito para terminar la compra. |

## Juego movil (varios generos + Trivial con tema)

**juegos_movil** genera un juego segun lo que pidas:
- **naves** (shooter)
- **snake / serpiente**
- **trivial** + tema: **trivial historia**, **trivial deportes**, **trivial geografia**, **trivial ciencia**, o **trivial** (cultura general). Plantilla con preguntas por tema.
- **memoria / puzzle** (parejas de cartas)
- **carrera / runner** (corredor infinito)

Ejemplos desde Telegram: "Crea un trivial de historia y enviame el enlace" / "Hazme un juego de naves y pasame el link". Ver **COMO_PEDIR_JUEGOS.md** en esta carpeta.

## Compra ingredientes (Mercadona)

**compra_ingredientes** obtiene los ingredientes del plato, abre Mercadona con Playwright, busca cada ingrediente, anade el primer resultado al carrito y te devuelve **una sola URL**: la del carrito con todo anadido, para que termines la compra tu.

## Ficha tecnica jugador

**ficha_jugador**: "Mandame la ficha tecnica de Mbappe" → SKILL:ficha_jugador Mbappe. Hace scraping en Transfermarkt, obtiene foto, edad, altura, posicion, club, valor, goles/asistencias y genera un **dashboard HTML** para ver en el movil. Ruta del archivo o publicar con GITHUB:push y enviar el enlace.

## Cursos: paginas bonitas

Cada **leccion** del curso se genera como **HTML** con el mismo estilo que la portada (fondo, tarjetas, tipografia). El index enlaza a leccion_XX_nombre.html (no solo .md). Cuando pidas un curso "de verdad", cada pagina sera tan cuidada como la intro.

## Flujo para publicar (juegos y webs)

1. Usuario: "Crea un juego de naves y dame el enlace para jugar en el móvil."
2. NEO ejecuta SKILL:juegos_movil naves.
3. El skill crea la carpeta en workspace/output/juegos/...
4. NEO ejecuta GITHUB:push <ruta> juego-naves.
5. NEO responde DONE con https://usuario.github.io/juego-naves/

Lo mismo para SKILL:web_sitio y SKILL:cursos (si se quiere publicar en web).

## Ideas futuras (sin email)

- **traducir**: texto a otro idioma.
- **resumen_url**: resumir contenido de una URL.
- **voz_respuesta**: transcribir voz, responder y TTS a nota de voz (Telegram).
