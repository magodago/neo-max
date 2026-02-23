DESCRIPTION = "Genera un código QR (imagen PNG). Uso: SKILL:qr <url o texto>"

def run(task: str = "", **kwargs) -> str:
    from pathlib import Path
    try:
        import qrcode
    except ImportError:
        return "Error: pip install qrcode Pillow"
    content = (task or "").strip() or "https://example.com"
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(content)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    out_path = Path(__file__).resolve().parent / "qr_output.png"
    img.save(out_path)
    return "QR generado. Guardado en: " + str(out_path)
