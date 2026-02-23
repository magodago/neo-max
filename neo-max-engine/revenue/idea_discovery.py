"""
idea_discovery - Descubre ideas de herramientas investigando el mercado.
Genera candidatos con Ollama (long-tail, demanda real) y elige el de mayor demanda con SerpAPI.
Objetivo: NEO elige qué construir según demanda real, no lista fija.
"""

import json
import logging
import re
import time
import urllib.request
from typing import TypedDict

from tools.market_validator import MarketValidator

logger = logging.getLogger("neo_max.idea_discovery")

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:7b-instruct"
TIMEOUT = 120
MAX_CANDIDATES = 10
MIN_MARKET_SCORE = 65
OLLAMA_MAX_RETRIES = 3
OLLAMA_RETRY_DELAYS = (2, 4, 8)  # segundos entre intentos


class DiscoveredIdea(TypedDict):
    problema: str
    categoria: str
    market_score: int
    total_results: int
    has_ads: bool
    organic_count: int


def _call_ollama(prompt: str, max_tokens: int = 800) -> str | None:
    payload = {"model": MODEL, "prompt": prompt, "stream": False, "options": {"num_predict": max_tokens}}
    last_err = None
    for attempt in range(OLLAMA_MAX_RETRIES):
        req = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return (data.get("response") or "").strip()
        except Exception as e:
            last_err = e
            logger.warning("Ollama idea discovery attempt %d/%d failed: %s", attempt + 1, OLLAMA_MAX_RETRIES, e)
            if attempt < OLLAMA_MAX_RETRIES - 1 and attempt < len(OLLAMA_RETRY_DELAYS):
                time.sleep(OLLAMA_RETRY_DELAYS[attempt])
    if last_err:
        logger.warning("Ollama idea discovery failed after %d attempts: %s", OLLAMA_MAX_RETRIES, last_err)
    return None


def _parse_candidates(raw: str) -> list[str]:
    """Extrae líneas no vacías; cada una es un título de herramienta."""
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    out = []
    for ln in lines:
        ln = re.sub(r"^\d+[\.\)]\s*", "", ln)
        ln = re.sub(r"^[\-\*]\s*", "", ln)
        if len(ln) > 15 and len(ln) < 120:
            out.append(ln)
    return out[:MAX_CANDIDATES]


DISCOVERY_PROMPT = """You are a market researcher for a website that publishes free online tools (calculators, converters) to get traffic and earn with ads.

Generate exactly 8 specific tool ideas that people search for on Google. Each line = one tool title in English.
Focus on: SaaS metrics, startup finance, freelancer income, small business, marketing ROI.
Format: concrete titles like "CAC calculator for startups", "freelancer hourly rate calculator", "MRR to ARR converter".
Output ONLY the 8 titles, one per line. No numbering, no explanation."""


def discover_best_idea(
    min_market_score: int = MIN_MARKET_SCORE,
    use_ollama: bool = True,
    fallback_list: list[dict] | None = None,
) -> DiscoveredIdea | None:
    """
    Investiga el mercado: genera candidatos (Ollama o lista fallback) y elige el de mayor market_score.
    Returns la mejor idea con market_score >= min_market_score, o None si ninguna pasa.
    """
    candidates = []
    if use_ollama:
        raw = _call_ollama(DISCOVERY_PROMPT)
        if raw:
            candidates = _parse_candidates(raw)
            logger.info("Ollama generated %d candidates: %s", len(candidates), " | ".join(candidates[:10]))
    if not candidates and fallback_list:
        for item in fallback_list[:MAX_CANDIDATES]:
            if isinstance(item, dict) and item.get("problema"):
                candidates.append(item["problema"])
            elif isinstance(item, dict) and item.get("titulo"):
                candidates.append(item["titulo"])
            elif isinstance(item, str):
                candidates.append(item)
    if not candidates:
        logger.warning("No candidates for idea discovery")
        return None

    validator = MarketValidator()
    best: DiscoveredIdea | None = None
    for titulo in candidates:
        v = validator.validate_with_serpapi({
            "titulo": titulo,
            "categoria": "SaaS",
            "nivel_monetizacion": 4,
        })
        if v.get("error"):
            continue
        score = v.get("market_score", 0)
        if score < min_market_score:
            continue
        if best is None or score > best["market_score"]:
            best = {
                "problema": titulo,
                "categoria": "SaaS",
                "market_score": score,
                "total_results": v.get("total_results", 0),
                "has_ads": v.get("has_ads", False),
                "organic_count": v.get("organic_count", 0),
            }
            logger.info("New best idea: %s (score=%d)", titulo, score)
    return best


class ThemeWithTools(TypedDict):
    theme: str
    tools: list[str]
    market_score: int


THEME_AND_TOOLS_PROMPT = """You are a market researcher. Choose ONE vertical/theme for a free tools website (to get traffic and ads). Then list exactly 5 concrete calculator or converter tools that fit that theme.

CRITICAL: You MUST output exactly 6 lines. No intro, no explanation.
Line 1: the theme name (2-4 words, e.g. "SaaS metrics" or "Freelancer pricing")
Lines 2-6: exactly 5 tool titles, one per line, in English (e.g. "CAC calculator", "hourly rate calculator for freelancers").

Theme must be: SaaS, startup finance, freelancer, small business, or marketing. Output ONLY these 6 lines."""

THEME_RETRY_PROMPT = """You already suggested "{rejected_theme}" which we cannot use. Pick a DIFFERENT theme and 5 tools.

CRITICAL: Output exactly 6 lines. Line 1 = theme name (2-4 words). Lines 2-6 = 5 tool titles in English.
Choose a different vertical: prefer "Freelancer pricing", "Small business metrics", or "Marketing ROI" (not SaaS metrics). Output ONLY these 6 lines."""

ONE_MORE_TOOL_PROMPT = """Theme: {theme}
You already have these 4 tools: {tools}
Output exactly ONE more calculator or converter tool title in English that fits this theme. One line only, no numbering."""


def discover_theme_and_5_tools(
    min_market_score: int = MIN_MARKET_SCORE,
    use_ollama: bool = True,
    max_theme_attempts: int = 3,
) -> ThemeWithTools | None:
    """
    Descubre un TEMA coherente y 5 herramientas para ese tema. No machaca nada anterior.
    Valida el tema con SerpAPI. Si un tema no pasa, pide a Ollama OTRO tema (hasta max_theme_attempts)
    para no quedarse siempre en "SaaS metrics" y dar paso a Freelancer, Marketing, etc.
    Returns theme + list of 5 tool titles, o None.
    """
    if not use_ollama:
        return None
    validator = MarketValidator()
    rejected_themes: list[str] = []

    for attempt in range(max_theme_attempts):
        if attempt == 0:
            raw = _call_ollama(THEME_AND_TOOLS_PROMPT, max_tokens=400)
        else:
            prompt = THEME_RETRY_PROMPT.format(rejected_theme=rejected_themes[-1])
            raw = _call_ollama(prompt, max_tokens=400)
        if not raw:
            continue
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        for i, ln in enumerate(lines):
            lines[i] = re.sub(r"^\d+[\.\)]\s*", "", ln).strip()
        if len(lines) < 5:
            logger.warning("Ollama did not return theme + tools (got %d lines)", len(lines))
            continue
        theme = lines[0][:80]
        tools = []
        for ln in (lines[1:6] if len(lines) >= 6 else lines[1:5]):
            if len(ln) > 10 and len(ln) < 120:
                tools.append(ln)
        if len(tools) == 4 and len(lines) == 5:
            extra = _call_ollama(
                ONE_MORE_TOOL_PROMPT.format(theme=theme, tools=", ".join(tools[:3])),
                max_tokens=80,
            )
            if extra:
                extra_line = (extra.splitlines() or [""])[0].strip()
                extra_line = re.sub(r"^\d+[\.\)]\s*", "", extra_line).strip()
                if len(extra_line) > 10 and len(extra_line) < 120:
                    tools.append(extra_line)
                    logger.info("Ollama provided 5th tool: %s", extra_line)
            if len(tools) < 5:
                tools.append(f"{theme} calculator")
                logger.info("Using default 5th tool: %s", tools[-1])
        if len(tools) < 5:
            logger.warning("Only %d valid tool titles", len(tools))
            continue
        tools = tools[:5]
        v = validator.validate_with_serpapi({
            "titulo": f"{theme} calculator",
            "categoria": "SaaS",
            "nivel_monetizacion": 4,
        })
        if v.get("error"):
            logger.warning("Theme %s validation error: %s", theme, v.get("error"))
            rejected_themes.append(theme)
            continue
        if v.get("market_score", 0) < min_market_score:
            logger.info("Theme %s did not pass validation (score=%s); trying another theme.", theme, v.get("market_score"))
            rejected_themes.append(theme)
            continue
        logger.info("Theme validated: %s (score=%d) with 5 tools", theme, v.get("market_score"))
        return {
            "theme": theme,
            "tools": tools,
            "market_score": v.get("market_score", 0),
        }
    logger.info("No theme passed validation after %d attempts (rejected: %s)", max_theme_attempts, rejected_themes)
    return None
