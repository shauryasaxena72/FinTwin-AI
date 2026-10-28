"""Multilingual copilot: translate responses."""

from __future__ import annotations

TRANSLATIONS = {
    "en": {},
    "hi": {"cash": "नकद", "plan": "योजना", "risk": "जोखिम"},
}

def translate(text: str, lang: str = "en") -> str:
    """Simple keyword translation stub."""
    if lang == "en":
        return text
    for k, v in TRANSLATIONS.get(lang, {}).items():
        text = text.replace(k, v)
    return text
