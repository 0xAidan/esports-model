"""Name normalization for team matching."""

from __future__ import annotations

import re
import unicodedata

_STRIP_WORDS = frozenset(
    {
        "esports",
        "esport",
        "gaming",
        "team",
        "club",
        "clan",
        "the",
        "gg",
        "academy",
        "ex",
    }
)


def normalize_name(raw: str) -> str:
    text = unicodedata.normalize("NFKD", raw or "")
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    parts = [part for part in text.split() if part and part not in _STRIP_WORDS]
    return " ".join(parts)


def tokens(raw: str) -> set[str]:
    cleaned = normalize_name(raw)
    return set(cleaned.split()) if cleaned else set()
