"""
Estado del serial en curso: título, personajes, resúmenes de capítulos, último capítulo completo.
Se guarda en output/serial_state.json (no se publica en GitHub).
"""
import json
import random
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parent / "output" / "serial_state.json"


def _slug(title: str) -> str:
    import re
    s = title.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return s.strip("-")[:60] or "chapter"


def load_state() -> dict:
    if not STATE_PATH.is_file():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def bump_subscriber_count(state: dict) -> int:
    """Incrementa un poco el contador de suscriptores (efecto gancho social)."""
    n = state.get("subscriber_count", 0)
    if n == 0:
        n = random.randint(12_400, 18_900)
    else:
        n += random.randint(8, 35)
    state["subscriber_count"] = n
    return n


def start_new_serial(genre: str, theme: str, niche: str) -> dict:
    state = {
        "serial_title": "",
        "genre": genre,
        "theme": theme,
        "niche": niche,
        "characters": [],
        "chapters": [],
        "last_chapter_full_text": "",
        "subscriber_count": 0,
    }
    bump_subscriber_count(state)
    return state


def append_chapter(state: dict, title: str, body: str, summary: str) -> None:
    slug = _slug(title)
    state.setdefault("chapters", []).append({
        "title": title,
        "slug": slug,
        "summary": (summary or "").strip()[:500],
    })
    # Mantener solo el último capítulo completo para contexto (ahorrar tokens)
    state["last_chapter_full_text"] = body.strip()[-4000:] if len(body) > 4000 else body.strip()
    bump_subscriber_count(state)
    save_state(state)


def get_next_chapter(state: dict) -> dict | None:
    """Devuelve el capítulo guardado 'por delante' (el que se publica mañana), o None."""
    return state.get("next_chapter")


def set_next_chapter(state: dict, chapter_data: dict) -> None:
    """Guarda el capítulo que se publicará en la próxima ejecución (y que se puede vender por adelantado)."""
    state["next_chapter"] = chapter_data
    save_state(state)


def clear_next_chapter(state: dict) -> None:
    """Elimina el capítulo por delante (sin publicarlo)."""
    if "next_chapter" in state:
        del state["next_chapter"]
        save_state(state)


def publish_next_chapter(state: dict) -> dict | None:
    """
    Si hay next_chapter: lo añade a chapters (como publicado), actualiza last_chapter_full_text,
    borra next_chapter, guarda estado. Retorna los datos del capítulo para construir sitio/publicar.
    Si no hay next_chapter, retorna None.
    """
    next_ch = state.get("next_chapter")
    if not next_ch:
        return None
    title = next_ch.get("title", "")
    body = next_ch.get("body", "")
    summary = next_ch.get("summary", "")
    append_chapter(state, title, body, summary)
    del state["next_chapter"]
    save_state(state)
    return next_ch


def get_context_for_next_chapter(state: dict, max_chars: int | None = None) -> str:
    """
    Contexto completo para el LLM: título de la serie, personajes, resúmenes de TODOS los capítulos
    y el texto completo del último capítulo. Así el modelo sigue la historia sin perder hilo.
    Si max_chars está definido y el contexto es largo, se acorta solo el texto del último capítulo.
    """
    parts = []
    if state.get("serial_title"):
        parts.append(f"Serial title: {state['serial_title']}")
    if state.get("characters"):
        parts.append("Characters: " + ", ".join(state["characters"]))
    if state.get("chapters"):
        parts.append("Resúmenes de todos los capítulos hasta ahora (mantén continuidad):")
        for i, ch in enumerate(state["chapters"], 1):
            parts.append(f"  Cap{i} «{ch.get('title', '')}»: {ch.get('summary', '')}")
    full_prev = (state.get("last_chapter_full_text") or "").strip()
    if full_prev:
        parts.append("--- Texto completo del capítulo anterior (continúa desde aquí, mismo tono y personajes): ---")
        parts.append(full_prev)
    out = "\n".join(parts)
    if max_chars and len(out) > max_chars and full_prev:
        # Recortar solo el texto del último capítulo; mantener siempre título, personajes y resúmenes
        head = "\n".join(parts[:-1]) + "\n"
        budget = max_chars - len(head) - 80
        if budget > 500:
            truncated = full_prev[-budget:] if len(full_prev) > budget else full_prev
            out = head + truncated
    return out
