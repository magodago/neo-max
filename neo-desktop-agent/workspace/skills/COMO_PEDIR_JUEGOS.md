# Cómo pedir un juego desde Telegram (y que NEO te envíe el enlace)

NEO usa el skill **juegos_movil** cuando pides crear un juego. Él genera el HTML del juego, lo sube a GitHub (si le pides el enlace) y te responde con la URL para jugar en el móvil.

## Ejemplos de mensajes que puedes escribir

- **"Crea un juego de naves y envíame el enlace"**  
  → NEO ejecuta SKILL:juegos_movil naves, luego GITHUB:push de la carpeta del juego y te responde con https://tu-usuario.github.io/juego-naves/

- **"Hazme un trivial de historia y pásame el link para jugar"**  
  → SKILL:juegos_movil trivial historia → genera el trivial con preguntas de historia → GITHUB:push → te manda la URL.

- **"Quiero un juego de la serpiente para el móvil, créalo y envíamelo"**  
  → SKILL:juegos_movil snake → GITHUB:push → DONE con el enlace.

- **"Crea un juego de memoria y dame el enlace"**  
  → Juego de parejas de cartas → mismo flujo.

- **"Un trivial de deportes"**  
  → Trivial con preguntas de deportes. Si además dices "y envíamelo" o "y el enlace", hará el push y te dará la URL.

- **"Juego de carrera infinita"**  
  → Corredor infinito (runner). Si pides el enlace, lo publica y te lo manda.

## Géneros y temas disponibles

| Lo que pides (ejemplo) | Genero | Tema del trivial (si aplica) |
|------------------------|--------|-------------------------------|
| naves, espacial, shooter | Shooter | — |
| snake, serpiente | Snake | — |
| trivial, quiz, preguntas | Trivial | historia, deportes, geografia, ciencia, cultura (o "cultura general") |
| memoria, puzzle, parejas | Memoria | — |
| carrera, runner, corredor | Runner | — |

Si no especificas tema en un trivial, se usa **Cultura general**.

## Flujo resumido

1. Tú escribes en Telegram algo como: *"Crea un trivial de historia y envíame el enlace"*.
2. NEO detecta que es un juego (y que quieres enlace).
3. Ejecuta **SKILL:juegos_movil trivial historia** → se genera la carpeta con `index.html`.
4. Ejecuta **GITHUB:push** &lt;ruta_carpeta&gt; &lt;nombre-repo&gt; (por ejemplo `trivial-historia`).
5. Te responde con **DONE** y el enlace: `https://tu-usuario.github.io/trivial-historia/`.

Solo necesitas tener configurado `github_token` y `github_user` en `config.json` para que el push funcione.
