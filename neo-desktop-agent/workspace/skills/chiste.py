# Chiste aleatorio en español (API gratuita sin key). Uso: SKILL:chiste
DESCRIPTION = "Cuenta un chiste aleatorio en español. Uso: SKILL:chiste"

_CHISTES_ES = (
    "¿Por qué el libro de matemáticas está triste? Porque tiene demasiados problemas.",
    "¿Qué le dice un gusano a otro? ¡Nos vemos en la manzana!",
    "¿Cuál es el colmo de un electricista? Tener muy mala corriente.",
    "¿Qué hace una abeja en el gimnasio? ¡Zum-ba!",
    "¿Por qué los pájaros no usan Facebook? Porque ya tienen Twitter.",
    "¿Qué le dice una iguana a su hermana gemela? ¡Somos iguanitas!",
    "¿Cuál es el animal más antiguo? La cebra, porque está en blanco y negro.",
    "¿Qué hace una vaca en el cine? Ver una película de muuuu-sica.",
    "¿Por qué el mar no se seca? Porque tiene mareas.",
    "¿Qué le dice un semáforo a otro? No me mires, me estoy cambiando.",
)


def run(task: str = "", **kwargs) -> str:
    import urllib.request
    import json
    import random
    url = "https://v2.jokeapi.dev/joke/Any?lang=es&safe-mode"
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "NEO-Desktop-Agent/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode("utf-8"))
            if data.get("error"):
                return random.choice(_CHISTES_ES)
            if data.get("type") == "twopart":
                return data.get("setup", "") + "\n" + data.get("delivery", "")
            return data.get("joke", random.choice(_CHISTES_ES))
    except Exception:
        return random.choice(_CHISTES_ES)

