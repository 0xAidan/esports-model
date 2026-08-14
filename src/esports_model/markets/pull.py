"""Markets stub."""

from __future__ import annotations


def pull_markets(*, database_url: str) -> dict[str, object]:
    return {
        "ok": True,
        "implemented": False,
        "database_url": database_url,
        "message": "Polymarket pull lands after identity matching is built.",
    }
