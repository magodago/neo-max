"""
market_validator - Validación de mercado real con SerpAPI.
Detecta demanda (resultados, anuncios) para decidir si construir la herramienta.
"""

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import TypedDict

logger = logging.getLogger("neo_max.market_validator")

SERPAPI_BASE = "https://serpapi.com/search"
REQUEST_TIMEOUT = 15
_env_loaded = False


def _load_env() -> None:
    global _env_loaded
    if _env_loaded:
        return
    _env_loaded = True
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.is_file():
        return
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key, value = key.strip(), value.strip().strip("'\"")
                if key and key not in os.environ:
                    os.environ[key] = value
    except Exception:
        pass


class ProblemData(TypedDict):
    titulo: str
    categoria: str
    nivel_monetizacion: int


class ValidationResult(TypedDict):
    market_score: int
    should_build: bool
    total_results: int
    has_ads: bool
    organic_count: int
    error: str


class MarketValidator:
    """Valida demanda de mercado vía SerpAPI (Google)."""

    def __init__(self) -> None:
        _load_env()
        self._api_key = os.environ.get("SERPAPI_KEY", "").strip()

    def validate_with_serpapi(self, problem_data: ProblemData) -> ValidationResult:
        """
        Consulta SerpAPI con el título y calcula market_score.
        should_build = True si market_score >= 60.
        """
        default_fail: ValidationResult = {
            "market_score": 0,
            "should_build": False,
            "total_results": 0,
            "has_ads": False,
            "organic_count": 0,
            "error": "",
        }

        if not self._api_key:
            logger.warning("SERPAPI_KEY no configurado; validación de mercado omitida")
            default_fail["error"] = "SERPAPI_KEY no configurado"
            return default_fail

        titulo = problem_data.get("titulo", "").strip()
        if not titulo:
            default_fail["error"] = "titulo vacío"
            return default_fail

        nivel = int(problem_data.get("nivel_monetizacion", 0))

        params = {
            "q": titulo,
            "api_key": self._api_key,
            "engine": "google",
            "hl": "es",
            "gl": "es",
        }
        url = SERPAPI_BASE + "?" + urllib.parse.urlencode(params)

        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            msg = f"SerpAPI HTTP {e.code}"
            try:
                body = e.read().decode("utf-8")
                err = json.loads(body)
                msg = err.get("error", msg)
            except Exception:
                pass
            logger.warning("Validación mercado fallida: %s", msg)
            default_fail["error"] = msg
            return default_fail
        except urllib.error.URLError as e:
            logger.warning("Validación mercado fallida: %s", e.reason)
            default_fail["error"] = str(e.reason)
            return default_fail
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Validación mercado fallida: %s", e)
            default_fail["error"] = str(e)
            return default_fail

        # Extraer datos
        search_info = data.get("search_information") or {}
        total_results = int(search_info.get("total_results") or 0)
        ads_results = data.get("ads") or data.get("ads_results") or []
        if not isinstance(ads_results, list):
            ads_results = []
        organic_results = data.get("organic_results") or []
        if not isinstance(organic_results, list):
            organic_results = []
        organic_count = len(organic_results)

        # Calcular market_score (favorece competencia media-baja)
        score = 0
        if total_results > 200_000:
            score += 20
        elif 10_000 <= total_results <= 200_000:
            score += 25
        elif 500 <= total_results < 10_000:
            score += 30
        else:
            score += 15  # total_results < 500
        if ads_results:
            score += 30
        if organic_count >= 8:
            score += 15
        if nivel >= 4:
            score += 20

        should_build = score >= 65

        return {
            "market_score": score,
            "should_build": should_build,
            "total_results": total_results,
            "has_ads": bool(ads_results),
            "organic_count": organic_count,
            "error": "",
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    v = MarketValidator()
    r = v.validate_with_serpapi({
        "titulo": "Calculadora rentabilidad Airbnb España",
        "categoria": "Finanzas personales",
        "nivel_monetizacion": 4,
    })
    print("Score:", r["market_score"], "| should_build:", r["should_build"])
    print("Total resultados:", r["total_results"], "| Ads:", r["has_ads"], "| Organic:", r["organic_count"])
