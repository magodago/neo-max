"""
Prueba: crear documento profesional con imágenes y enviarlo por Telegram.
- Ejecuta el agente con la tarea de crear un PDF (skill documento_pdf).
- Extrae la ruta del PDF del resultado/historial.
- Envía ese PDF al chat_id configurado en config.json.

Uso (desde neo-desktop-agent):
  python tests/test_pdf_telegram.py

Requisitos: config.json con telegram_bot_token y deliver_to_telegram_chat_id
(o telegram_allowed_user_ids). Ollama en marcha. Tiempo: puede tardar 1-3 min
(Gemini para imagen + reportlab). Timeout interno: 10 minutos.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Timeout total para la prueba (generación PDF + posible Gemini puede ser lento)
RUN_TIMEOUT_SEC = 600


def _load_config() -> dict:
    p = ROOT / "config.json"
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def _extract_pdf_path_from_result(msg: str, history: list) -> str | None:
    """Extrae la ruta absoluta de un PDF del mensaje DONE o del historial del skill."""
    # Patrón: "Documento PDF generado: C:\...\algo.pdf" o "...\algo.pdf"
    for block in [msg or "", *[h.get("out") or "" for h in (history or [])]]:
        # Ruta Windows: C:\ o D:\ ... \archivo.pdf
        m = re.search(r"(?:Documento PDF generado:\s*)?([A-Za-z]:[^\s\[\]]+\.pdf)", block)
        if m:
            path = m.group(1).strip()
            if Path(path).is_file():
                return path
        # Ruta relativa o con "Carpeta:" que a veces incluye el nombre del pdf
        m = re.search(r"([A-Za-z]:[^\s]+(?:documentos_pdf|output)[^\s]*\.pdf)", block)
        if m:
            path = m.group(1).strip()
            if Path(path).is_file():
                return path
    # Buscar en workspace/output/documentos_pdf el PDF más reciente
    out_dir = ROOT / "workspace" / "output" / "documentos_pdf"
    if out_dir.is_dir():
        pdfs = sorted(out_dir.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
        if pdfs:
            return str(pdfs[0].resolve())
    return None


def main() -> None:
    config = _load_config()
    token = (config.get("telegram_bot_token") or "").strip()
    chat_id = config.get("proactive_agent") or {}
    if isinstance(chat_id, dict):
        chat_id = (chat_id.get("deliver_to_telegram_chat_id") or config.get("telegram_allowed_user_ids") or [])
    if isinstance(chat_id, list):
        chat_id = str(chat_id[0]) if chat_id else ""
    else:
        chat_id = str(chat_id or "")

    if not token or not chat_id:
        print("Configura telegram_bot_token y deliver_to_telegram_chat_id (o telegram_allowed_user_ids) en config.json")
        sys.exit(1)

    task = (
        "Crea un documento profesional con imágenes sobre inteligencia artificial en la empresa. "
        "Usa el skill de PDF con imágenes. El documento puede tener varias páginas si hace falta."
    )
    print("Tarea:", task[:80], "...")
    print("Ejecutando agente (puede tardar 1-3 min por Gemini + PDF)...")
    print("(Timeout", RUN_TIMEOUT_SEC, "s)")

    try:
        from agent import run_agent
        result = run_agent(
            task,
            auto_confirm=True,
            return_history=True,
            session_id="test_pdf",
            include_session_context=True,
            max_steps=20,
        )
    except Exception as e:
        print("Error ejecutando agente:", e)
        sys.exit(2)

    if result is None:
        print("El agente no devolvió resultado.")
        sys.exit(3)

    msg, history = result
    pdf_path = _extract_pdf_path_from_result(msg, history)

    if not pdf_path:
        print("No se encontró la ruta del PDF en el resultado. Mensaje:", (msg or "")[:300])
        print("Revisa el historial por si el skill devolvió la ruta en otro paso.")
        sys.exit(4)

    print("PDF encontrado:", pdf_path)
    print("Enviando a Telegram...")

    from telegram_bot import send_document_to_telegram
    ok = send_document_to_telegram(chat_id, pdf_path, token, caption="Documento profesional (prueba NEO)")

    if ok:
        print("Listo. Revisa Telegram: te debe haber llegado el PDF.")
    else:
        print("Falló el envío a Telegram. Revisa token y chat_id.")
        sys.exit(5)


if __name__ == "__main__":
    main()
