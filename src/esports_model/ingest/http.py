"""Polite MediaWiki HTTP client."""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from typing import Any

import httpx

from esports_model.config import Settings

API_URL = "https://liquipedia.net/counterstrike/api.php"
PARSE_ACTIONS = frozenset({"parse", "ask", "askargs"})


class PoliteClient:
    def __init__(
        self,
        *,
        settings: Settings,
        transport: httpx.BaseTransport | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._headers = settings.liquipedia_headers()
        self._min_interval = max(settings.liquipedia_min_interval_sec, 2.0)
        self._parse_interval = 30.0
        self._sleeper = sleeper
        self._monotonic = monotonic
        self._last_any: float | None = None
        self._last_parse: float | None = None
        self._client = httpx.Client(
            headers=self._headers,
            timeout=30.0,
            transport=transport,
            follow_redirects=True,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> PoliteClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def get_json(self, params: Mapping[str, str]) -> dict[str, Any]:
        action = params.get("action", "")
        self._wait(action)
        query = {"format": "json", **params}
        response = self._client.get(API_URL, params=query)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("Liquipedia returned a non-object JSON body")
        return payload

    def _wait(self, action: str) -> None:
        now = self._monotonic()
        needed = 0.0
        if self._last_any is not None:
            needed = self._min_interval - (now - self._last_any)
        if action in PARSE_ACTIONS:
            parse_from = self._last_parse if self._last_parse is not None else self._last_any
            if parse_from is not None:
                needed = max(needed, self._parse_interval - (now - parse_from))
        if needed > 0:
            self._sleeper(needed)
        stamped = self._monotonic()
        self._last_any = stamped
        if action in PARSE_ACTIONS:
            self._last_parse = stamped
