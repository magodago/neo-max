# Config opcional (config.json)

Puedes añadir estas claves a `config.json` para activar más funciones.

## GitHub (cursos, fichas, juegos, magia, etc.) — igual que tools SaaS y libro
- El agente usa **el mismo .env que neo-max-engine**: `neo-max-engine/.env` (o `neo-desktop-agent/.env`).
- Ahí pon **GITHUB_TOKEN** (token de la cuenta magodago) y **GITHUB_USER=magodago**. Así las URLs serán `https://magodago.github.io/<repo>/` como en las tools y el libro.
- Fallback: **config.json** con `github_token` y `github_user` si no hay .env.

## Proactivo y ventana horaria
- **proactive_agent** (ya existe): `enabled`, `interval_minutes`, `deliver_to_telegram_chat_id`
- NEO solo escribe/envía entre **9:00 y 23:00** (nunca de 23:00 a 9:00).
- **interval_minutes**: con 120 solo hay ~7–12 ciclos al día; con **60** hay más oportunidades de que NEO elija CALL o GIF. Recomendado 60 si quieres más llamadas/GIFs.

## Voz (Eleven Labs) y llamada
- **elevenlabs_api_key**, **elevenlabs_voice_id**: ya en config
- Cuando NEO responda `CALL: <mensaje>` en el loop proactivo, generará audio con tu voz y te lo enviará por Telegram. Misma ventana 9:00–23:00.

## Llamada real al móvil (Twilio)
- **user_phone_number**: Tu número (+34658237988 ya está)
- **twilio_account_sid**, **twilio_auth_token**, **twilio_phone_number**, **twilio_twiml_url**
- Guía paso a paso: **TWILIO_SETUP.md**. Twilio tiene trial gratis; con una Twilio Function que devuelva `<Say>mensaje</Say>`, NEO te llamará al móvil (9:00–23:00).

## Giphy (GIF por Telegram)
- **giphy_api_key**: ya en config. NEO puede responder `GIF: <tema>` y te enviará un GIF por Telegram.

## Historia de la Magia (publicación diaria a las 10:00)
- **magia_historia_daily**: `enabled` (true), `time` ("10:00"), `repo_name` ("magia-historia"), `notify_telegram_chat_id` (opcional).
- Cada día a las 10:00 se añade un mago (primero los de magos.json; después se descubren nuevos con Ollama), se genera la foto con Gemini y se publica en GitHub.
- **gemini_api_key**: misma API que el libro (neo-max-engine). Para que cada mago tenga una imagen generada por Gemini. Si no está, se usa placeholder.
- **gemini_image_model**: opcional; por defecto "gemini-2.5-flash-image".
