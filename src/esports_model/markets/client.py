"""Polymarket Gamma + CLOB HTTP helpers."""

from __future__ import annotations

from typing import Any

import httpx

GAMMA_SEARCH = "https://gamma-api.polymarket.com/public-search"
CLOB_BOOK = "https://clob.polymarket.com/book"
SEARCH_QUERIES = ("Counter-Strike", "CS2 Esports World Cup", "cs2-")


class PolymarketClient:
    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        self._client = httpx.Client(timeout=30.0, transport=transport, follow_redirects=True)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> PolymarketClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def search_events(self) -> list[dict[str, Any]]:
        seen: dict[str, dict[str, Any]] = {}
        for query in SEARCH_QUERIES:
            response = self._client.get(GAMMA_SEARCH, params={"q": query})
            response.raise_for_status()
            payload = response.json()
            events = payload.get("events") if isinstance(payload, dict) else payload
            if not isinstance(events, list):
                continue
            for event in events:
                if not isinstance(event, dict):
                    continue
                key = str(event.get("id") or event.get("slug") or "")
                if key:
                    seen[key] = event
        return list(seen.values())

    def book(self, token_id: str) -> dict[str, Any]:
        response = self._client.get(CLOB_BOOK, params={"token_id": token_id})
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {}
