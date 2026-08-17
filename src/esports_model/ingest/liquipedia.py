"""Liquipedia MediaWiki query helpers."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from esports_model.ingest.http import PoliteClient

CATEGORY_BY_VERSION = {
    "cs2": "Category:CS2 Tournaments",
    "csgo": "Category:CS:GO Tournaments",
}
LIVE_CATEGORY = "Category:Live Tournaments"


def iter_category_titles(
    client: PoliteClient,
    category: str,
    *,
    cmcontinue: str | None = None,
    limit: int | None = None,
) -> Iterator[tuple[str, str | None]]:
    fetched = 0
    cursor = cmcontinue
    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category,
            "cmsort": "timestamp",
            "cmdir": "desc",
            "cmlimit": "50",
        }
        if cursor:
            params["cmcontinue"] = cursor
        payload = client.get_json(params)
        members = payload.get("query", {}).get("categorymembers", [])
        next_cursor = (payload.get("continue") or {}).get("cmcontinue")
        for row in members:
            title = row.get("title")
            if not title:
                continue
            yield title, next_cursor
            fetched += 1
            if limit is not None and fetched >= limit:
                return
        if not next_cursor:
            return
        cursor = next_cursor


def fetch_wikitext(client: PoliteClient, title: str) -> str:
    payload = client.get_json(
        {
            "action": "query",
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "titles": title,
        }
    )
    pages: dict[str, Any] = payload.get("query", {}).get("pages", {})
    for page in pages.values():
        if "missing" in page:
            return ""
        revisions = page.get("revisions") or []
        if not revisions:
            return ""
        slot = revisions[0].get("slots", {}).get("main", {})
        return str(slot.get("*") or "")
    return ""
