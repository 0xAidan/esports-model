"""Historical sync. Real Liquipedia ETL lands after the scaffold."""

from __future__ import annotations

from typing import Any


def run_sync(
    *,
    profile_name: str,
    spec: dict[str, Any],
    resume: bool,
    database_url: str,
) -> dict[str, Any]:
    return {
        "ok": True,
        "implemented": False,
        "profile": profile_name,
        "resume": resume,
        "database_url": database_url,
        "tiers": spec.get("tiers"),
        "message": "Liquipedia sync is not implemented in the scaffold. Run init-db for now.",
    }
