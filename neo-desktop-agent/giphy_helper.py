"""Giphy API: busca un GIF y devuelve la URL para enviar por Telegram."""
import json
import random
import urllib.request


def get_random_gif_url(api_key: str, query: str, rating: str = "g"):
    """Devuelve la URL de un GIF aleatorio para la busqueda. rating: g, pg, pg-13, r."""
    if not (api_key or "").strip():
        return None
    query_enc = urllib.request.quote((query or "ok").strip())
    url = "https://api.giphy.com/v1/gifs/search?api_key={}&q={}&limit=10&rating={}".format(
        api_key, query_enc, rating
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "NEO-Desktop-Agent"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        items = data.get("data") or []
        if not items:
            url_rand = "https://api.giphy.com/v1/gifs/random?api_key={}&tag={}&rating={}".format(
                api_key, query_enc, rating
            )
            req = urllib.request.Request(url_rand, headers={"User-Agent": "NEO-Desktop-Agent"})
            with urllib.request.urlopen(req, timeout=10) as r2:
                data = json.loads(r2.read().decode("utf-8"))
            item = data.get("data") or {}
        else:
            item = random.choice(items)
        return (item.get("images") or {}).get("original", {}).get("url") or item.get("embed_url")
    except Exception:
        return None
