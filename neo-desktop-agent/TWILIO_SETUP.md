# Cómo configurar Twilio para que NEO te llame al móvil

## ¿Twilio es gratis?

- **Sí tiene prueba gratuita:** te dan crédito inicial (suficiente para bastantes llamadas) sin tarjeta.
- En **cuenta de pago**, las llamadas se cobran (aprox. ~0,01 USD/min hacia España). Puedes seguir usando solo el crédito del trial mientras dure.

## Pasos (resumen)

1. Crear cuenta en [twilio.com](https://www.twilio.com) (trial).
2. Anotar **Account SID** y **Auth Token** (en la consola).
3. Comprar o usar un **número de Twilio** (en trial te dan uno).
4. Crear una **Twilio Function** que devuelva TwiML con `<Say>` y el mensaje (parámetro `msg`).
5. Añadir en **config.json** las claves de Twilio y la URL de la Function.

---

## 1. Cuenta Twilio

- Entra en [twilio.com/try-twilio](https://www.twilio.com/try-twilio).
- Regístrate (no hace falta tarjeta para el trial).
- En la consola (Dashboard) verás:
  - **Account SID** (ej. `ACxxxxxxxx`)
  - **Auth Token** (clic en “Show” para verlo).

---

## 2. Número de teléfono

- En el menú: **Phone Numbers → Manage → Buy a number**.
- En trial suelen darte un número gratis (p. ej. USA). Para un número español puede hacer falta cuenta de pago.
- El número que compres/actives es el que pondrás en config como **twilio_phone_number** (el “desde” que llama).

---

## 3. Twilio Function (para que diga el mensaje)

Twilio, al conectar la llamada, pide una URL que devuelva **TwiML**. Usamos una Function que lee el parámetro `msg` y lo devuelve dentro de `<Say>` (voz en español).

**Importante:** En la consola actual primero creas un **Service** y dentro de él la **Function** (no hay un solo botón "Create Function" suelto).

1. Ir a **Functions**: [console/functions/overview](https://www.twilio.com/console/functions/overview) (o menú: **Explore Products** → **Develop** → **Functions**).
2. **Create Service** (botón en esa página; nombre ej. neo-voice). Next, Create. Entras al editor del Service; ahí usas el paso 3.
3. **Add +** → **Add Function**. Nombre: `neo_say` (será el path de la URL).
4. **Código** (sustituye el que venga):

```javascript
exports.handler = function(context, event, callback) {
  const msg = event.msg || event.Body || 'Hola, soy NEO.';
  const twiml = '<?xml version="1.0" encoding="UTF-8"?><Response><Say voice="Polly.Miguel" language="es-ES">' + msg + '</Say></Response>';
  callback(null, twiml);
};
```

5. **Save** y luego **Deploy All** (o Deploy). Espera a que termine.
6. Copia la **URL** de la Function (en la misma pantalla o en Environment; formato: `https://[service]-[numeros].twil.io/neo_say`). Esa URL es **twilio_twiml_url** (NEO añade `?msg=...` al llamar).

---

## 4. config.json (neo-desktop-agent)

Añade o completa en **config.json**:

```json
"user_phone_number": "+34658237988",
"twilio_account_sid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
"twilio_auth_token": "tu_auth_token",
"twilio_phone_number": "+1xxxxxxxxxx",
"twilio_twiml_url": "https://xxxx-1234.twil.io/neo_say"
```

- **user_phone_number:** tu móvil (formato internacional, con +).
- **twilio_phone_number:** el número de Twilio desde el que se hace la llamada.
- **twilio_twiml_url:** la URL de la Function del paso 3 (sin `?msg=...`; NEO la añade solo).

---

## Comportamiento

- Cuando NEO decide **CALL: &lt;mensaje&gt;** (en horario 9:00–23:00):
  1. Te envía el audio por Telegram (Eleven Labs).
  2. Si Twilio está configurado, además **te llama al +34658237988** y Twilio reproduce el mismo mensaje por voz (voz de Twilio en español, p. ej. Polly.Miguel).

Si no configuras Twilio, solo recibirás el audio en Telegram.

---

## ¿Puede NEO llamarme cuando quiera?

**Sí.** En el loop proactivo (entre 9:00 y 23:00) NEO decide cada cierto tiempo si hace PROPOSE, **CALL**, GIF o nada. Si elige **CALL: &lt;mensaje&gt;** te llama al móvil y reproduce ese mensaje por voz. Puede usarlo para avisarte de algo, darte ánimo, contarte una noticia o simplemente saludarte.

---

## Si yo hablo cuando me llama, ¿NEO puede responderme en la llamada?

**No**, con la configuración actual. La llamada es **solo salida**: Twilio reproduce el mensaje que NEO eligió (&lt;Say&gt;) y la llamada termina. No se escucha lo que tú dices ni se envía a NEO. Para que NEO pudiera **responderte en la misma llamada** haría falta:

- Usar **Twilio &lt;Gather input="speech"&gt;** para capturar tu voz y enviar el texto a un webhook, que pida respuesta a NEO (Ollama) y devuelva nuevo TwiML con &lt;Say&gt;, o  
- Usar **Twilio Media Streams** (WebSocket) para recibir el audio en tiempo real, transcribir (p. ej. Whisper), enviar a NEO, generar respuesta y devolverla por TTS en la misma sesión.

Eso sería una extensión futura (llamada bidireccional / conversación por teléfono).
