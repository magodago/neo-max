"""
Script temporal para depurar conexión con Ollama.
POST a localhost:11434/api/generate, sin streaming, timeout 180s.
"""

import json
import time
import urllib.request
import urllib.error

URL = "http://localhost:11434/api/generate"
TIMEOUT = 180
PAYLOAD = {
    "model": "qwen2.5:7b-instruct",
    "prompt": "Genera un HTML simple con un título y un botón",
    "stream": False,
}


def main():
    print("Conectando a Ollama...")
    print("URL:", URL)
    print("Timeout:", TIMEOUT, "s")
    print("Payload:", json.dumps(PAYLOAD, indent=2))
    print("-" * 50)

    body = json.dumps(PAYLOAD).encode("utf-8")
    req = urllib.request.Request(
        URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    start = time.perf_counter()
    status_code = None
    response_text = ""
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            status_code = resp.status
            raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            response_text = (data.get("response") or "").strip()
    except urllib.error.HTTPError as e:
        status_code = e.code
        try:
            raw = e.read().decode("utf-8")
            data = json.loads(raw)
            response_text = data.get("error", raw)[:500]
        except Exception:
            response_text = str(e)
        print("ERROR HTTP:", e.code, e.reason)
    except urllib.error.URLError as e:
        print("ERROR URL:", e.reason)
        if "timed out" in str(e.reason).lower():
            print("Timeout alcanzado ({}s). ¿Ollama está corriendo?".format(TIMEOUT))
    except Exception as e:
        print("ERROR:", type(e).__name__, e)

    elapsed = time.perf_counter() - start

    print()
    print("--- Resultado ---")
    print("status_code:", status_code)
    print("tiempo_total_s:", round(elapsed, 2))
    print("longitud_respuesta:", len(response_text))
    print("primeros_200_caracteres:", repr(response_text[:200]) if response_text else "(vacío)")

    if status_code == 200 and response_text:
        print()
        print("OK: Ollama respondió correctamente.")
    else:
        print()
        print("FALLO: Revisa que Ollama esté en marcha (ollama serve) y el modelo cargado (ollama run qwen2.5:7b-instruct).")


if __name__ == "__main__":
    main()
