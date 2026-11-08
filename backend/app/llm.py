"""Optional LLM layer. Used only to phrase replies and to parse free text the rules missed.
It never chooses products or prices. With no API key every function returns None and the
deterministic path is used."""
from __future__ import annotations

import json
import logging

import httpx

from .config import ANTHROPIC_API_KEY, LLM_MODEL

log = logging.getLogger("sync.llm")


def enabled() -> bool:
    return bool(ANTHROPIC_API_KEY)


def complete(system: str, user: str, max_tokens: int = 300) -> str | None:
    if not enabled():
        return None
    try:
        r = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": LLM_MODEL, "max_tokens": max_tokens, "system": system,
                  "messages": [{"role": "user", "content": user}]},
            timeout=12,
        )
        r.raise_for_status()
        return "".join(b.get("text", "") for b in r.json().get("content", [])).strip() or None
    except Exception as e:  # network or quota problems must never break the journey
        log.warning("LLM unavailable, using deterministic reply: %s", type(e).__name__)
        return None


def extract_slots(message: str, allowed: dict) -> dict:
    """Ask the LLM to map free text onto the advisor's known slot values. Output is validated by the caller."""
    out = complete(
        "You extract structured facts about a small business from one message. Reply with JSON only. "
        f"Allowed keys and values: {json.dumps(allowed)}. Omit anything not stated. Never guess.",
        message, max_tokens=200)
    if not out:
        return {}
    try:
        start, end = out.find("{"), out.rfind("}")
        return json.loads(out[start:end + 1]) if start >= 0 else {}
    except json.JSONDecodeError:
        return {}


def explain(profile: dict, option: dict, language: str) -> str | None:
    """Plain-language summary of a bundle that the engine already chose."""
    facts = {"business": profile.get("business_type"), "employees": profile.get("employees"),
             "sites": profile.get("sites"), "city": profile.get("city"),
             "products": [{"name": li["name"], "qty": li["quantity"], "reasons": r}
                          for li, r in zip(option["pricing"]["lines"], [i["reasons"] for i in option["items"]])],
             "monthly_from": option["pricing"]["monthly_min"], "monthly_max": option["pricing"]["monthly_max"],
             "setup": option["pricing"]["setup_total"]}
    lang = {"en": "English", "hi": "Hindi", "ta": "Tamil"}.get(language, "English")
    return complete(
        f"You explain a telecom bundle to a small-business owner in simple {lang}, in 3 short sentences. "
        "Use only the facts given. Do not add products, prices, discounts or promises.",
        json.dumps(facts, ensure_ascii=False), max_tokens=250)
