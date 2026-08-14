"""Pull upcoming CS2 series markets from Polymarket."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from esports_model.config import feature_flags
from esports_model.db.session import init_db, session_scope
from esports_model.markets.client import PolymarketClient
from esports_model.markets.parse import depth_from_book, parse_event
from esports_model.markets.store import upsert_event, upsert_outcome


class MarketClient(Protocol):
    def __enter__(self) -> MarketClient: ...

    def __exit__(self, *exc: object) -> None: ...

    def search_events(self) -> list[dict[str, Any]]: ...

    def book(self, token_id: str) -> dict[str, Any]: ...


ClientFactory = Callable[[], MarketClient]


def pull_markets(
    *,
    database_url: str,
    client_factory: ClientFactory | None = None,
) -> dict[str, Any]:
    init_db(database_url)
    factory = client_factory or PolymarketClient
    flags = feature_flags()
    cents = float(flags.get("depth_cents", 0.03))
    stored = 0
    quarantined = 0
    series = 0
    errors: list[str] = []

    with factory() as client, session_scope(database_url) as session:
        for raw in client.search_events():
            try:
                parsed = parse_event(raw)
                if parsed is None:
                    continue
                event = upsert_event(session, parsed)
                for market in parsed.markets:
                    if not market.is_series_winner:
                        continue
                    series += 1
                    for outcome in market.outcomes:
                        book = {}
                        try:
                            book = client.book(outcome.token_id)
                        except Exception as exc:  # noqa: BLE001
                            errors.append(f"book {outcome.token_id[:12]}: {exc}")
                        asks = book.get("asks") if isinstance(book.get("asks"), list) else []
                        ask = outcome.ask
                        bid = outcome.bid
                        spread = None
                        if ask is not None and bid is not None:
                            spread = max(ask - bid, 0.0)
                        if spread is None:
                            spread = market.spread
                        depth = depth_from_book(asks, ask, cents)
                        row = upsert_outcome(
                            session,
                            event=event,
                            parsed_event=parsed,
                            condition_id=market.condition_id,
                            question=market.question,
                            market_type="moneyline",
                            outcome=outcome,
                            fee_rate=market.fee_rate,
                            volume=market.volume,
                            volume_24h=market.volume_24h,
                            spread=spread,
                            depth_usd=depth,
                            bid=bid,
                            ask=ask,
                        )
                        stored += 1
                        if row.identity_status == "quarantine":
                            quarantined += 1
            except Exception as exc:  # noqa: BLE001
                errors.append(str(exc))

    return {
        "ok": not errors,
        "implemented": True,
        "database_url": database_url,
        "series_markets": series,
        "outcomes_upserted": stored,
        "quarantined": quarantined,
        "errors": errors[:20],
        "message": "Unmatched markets are quarantined and cannot become BET rows.",
    }


