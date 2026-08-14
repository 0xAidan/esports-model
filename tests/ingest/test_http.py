from __future__ import annotations

import httpx

from esports_model.config import Settings
from esports_model.ingest.http import PoliteClient


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def test_query_waits_two_seconds_between_calls() -> None:
    clock = Clock()
    settings = Settings(
        liquipedia_contact_email="dev@example.org",
        liquipedia_user_agent="esports-model-test/0.1 (dev@example.org)",
        liquipedia_min_interval_sec=2.0,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    client = PoliteClient(
        settings=settings,
        transport=transport,
        sleeper=clock.sleep,
        monotonic=clock.monotonic,
    )
    client.get_json({"action": "query", "list": "categorymembers"})
    client.get_json({"action": "query", "list": "categorymembers"})
    assert clock.sleeps
    assert clock.sleeps[0] >= 2.0
    client.close()


def test_parse_waits_thirty_seconds() -> None:
    clock = Clock()
    settings = Settings(
        liquipedia_contact_email="dev@example.org",
        liquipedia_user_agent="esports-model-test/0.1 (dev@example.org)",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    client = PoliteClient(
        settings=settings,
        transport=httpx.MockTransport(handler),
        sleeper=clock.sleep,
        monotonic=clock.monotonic,
    )
    client.get_json({"action": "query"})
    client.get_json({"action": "parse", "page": "X"})
    assert any(sleep >= 30.0 for sleep in clock.sleeps)
    client.close()
