# Entra en Mercadona, busca ingrediente por ingrediente, anade al carrito y devuelve la URL del carrito.
DESCRIPTION = "Ingredientes de un plato en Mercadona: anade al carrito y devuelve la URL del carrito. Uso: SKILL:compra_ingredientes <plato>"

def run(task: str = "", **kwargs) -> str:
    import re
    import urllib.request
    import urllib.parse
    plato = (task or "").strip()[:80]
    if not plato:
        return "Indica el plato. Ejemplo: SKILL:compra_ingredientes paella"

    fallback = {
        "paella": ["arroz", "pollo", "tomate", "azafran", "pimiento", "aceite", "sal"],
        "tortilla de patatas": ["huevos", "patatas", "cebolla", "aceite", "sal"],
        "tortilla española": ["huevos", "patatas", "cebolla", "aceite", "sal"],
        "ensalada cesar": ["lechuga", "pollo", "parmesano", "pan", "salsa cesar"],
        "espaguetis carbonara": ["espaguetis", "bacon", "huevos", "queso parmesano", "nata", "sal"],
        "lasaña": ["pasta lasaña", "carne picada", "tomate", "cebolla", "bechamel", "queso rallado"],
        "gazpacho": ["tomate", "pepino", "pimiento", "cebolla", "ajo", "aceite", "vinagre", "sal"],
        "croquetas": ["leche", "harina", "jamon", "huevo", "pan rallado", "aceite"],
    }
    plato_lower = plato.lower()
    ingredientes = fallback.get(plato_lower)
    if not ingredientes:
        for k, v in fallback.items():
            if k in plato_lower or plato_lower in k:
                ingredientes = v
                break
    if not ingredientes:
        try:
            url_buscar = "https://www.recetasgratis.net/buscar/" + urllib.parse.quote(plato)
            req = urllib.request.Request(url_buscar, headers={"User-Agent": "Mozilla/5.0 (compatible; NEO/1.0)"})
            with urllib.request.urlopen(req, timeout=8) as r:
                html = r.read().decode("utf-8", errors="replace")
            enlaces = re.findall(r'href="(/receta-[^"]+)"', html)
            if enlaces:
                url_receta = "https://www.recetasgratis.net" + enlaces[0]
                req2 = urllib.request.Request(url_receta, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req2, timeout=8) as r2:
                    html2 = r2.read().decode("utf-8", errors="replace")
                ing = re.findall(r'class="ingrediente[^"]*"[^>]*>([^<]+)<', html2)
                if ing:
                    ingredientes = [re.sub(r'\s+', ' ', i).strip()[:50] for i in ing[:15] if len(i.strip()) > 1]
        except Exception:
            pass
    if not ingredientes:
        ingredientes = ["tomate", "cebolla", "aceite", "sal"]

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return "Playwright no instalado. Ejecuta: pip install playwright && playwright install chromium"

    base_url = "https://tienda.mercadona.es"
    search_url = base_url + "/search-results?query="
    cart_url_final = None
    anadidos = []
    errores = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.set_default_timeout(10000)
        try:
            page.goto(base_url, wait_until="domcontentloaded", timeout=12000)
            for ing in ingredientes[:10]:
                q = urllib.parse.quote(ing)
                page.goto(search_url + q, wait_until="domcontentloaded", timeout=10000)
                page.wait_for_timeout(1500)
                try:
                    btn = page.get_by_role("button", name=re.compile(r"Añadir al carro", re.I))
                    btn.first.click(timeout=5000)
                    anadidos.append(ing)
                    page.wait_for_timeout(600)
                except Exception:
                    try:
                        link = page.locator("a", has_text=re.compile(r"Añadir al carro", re.I)).first
                        link.click(timeout=3000)
                        anadidos.append(ing)
                        page.wait_for_timeout(600)
                    except Exception:
                        errores.append(ing + ": no se encontro boton Añadir al carro")
            try:
                page.goto(base_url + "/cart", wait_until="domcontentloaded")
                cart_url_final = page.url
            except Exception:
                try:
                    page.goto(base_url + "/carrito", wait_until="domcontentloaded")
                    cart_url_final = page.url
                except Exception:
                    cart_url_final = base_url + "/cart"
        except Exception as e:
            errores.append("Navegacion: " + str(e)[:80])
        finally:
            browser.close()

    lineas = ["Ingredientes para " + plato + " (en Mercadona):"]
    for i in ingredientes:
        lineas.append("  - " + i)
    lineas.append("")
    if anadidos:
        lineas.append("Anadidos al carrito: " + ", ".join(anadidos))
    if errores:
        lineas.append("Avisos: " + "; ".join(errores[:5]))
    lineas.append("")
    if cart_url_final:
        lineas.append("URL de tu carrito (termina la compra aqui):")
        lineas.append(cart_url_final)
        lineas.append("")
        lineas.append("Abre el enlace, revisa los productos y finaliza el pedido con tu sesion.")
    else:
        lineas.append("URL del carrito (abre para ver o anadir mas):")
        lineas.append(base_url + "/cart")
        lineas.append("")
        lineas.append("Si no se anadio nada automaticamente, la web de Mercadona puede haber cambiado o requerir sesion. Abre el enlace y anade los ingredientes manualmente.")
    return "\n".join(lineas)
