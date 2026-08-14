"""Parse Polymarket Gamma payloads into series-winner rows."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ParsedOutcome:
    name: str
    token_id: str
    bid: float | None
    ask: float | None


@dataclass(frozen=True)
class ParsedMarket:
    condition_id: str
    question: str
    market_type: str
    group_title: str
    fee_rate: float
    volume: float | None
    volume_24h: float | None
    liquidity: float | None
    spread: float | None
    outcomes: tuple[ParsedOutcome, ...]
    is_series_winner: bool


@dataclass(frozen=True)
class ParsedEvent:
    provider_event_id: str
    slug: str
    title: str
    start_time: datetime | None
    volume: float | None
    team_left: str | None
    team_right: str | None
    markets: tuple[ParsedMarket, ...]


def maybe_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
        except json.JSONDecodeError:
            return [value]
        return loaded if isinstance(loaded, list) else [loaded]
    return [value]


def _float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_teams_from_title(title: str) -> tuple[str | None, str | None]:
    cleaned = title.replace(" vs. ", " vs ")
    match = re.search(
        r"(?:Counter-Strike|CS2)\s*:\s*(.+?)\s+vs\s+(.+?)(?:\s*\(|\s+-|$)",
        cleaned,
        flags=re.I,
    )
    if match:
        return match.group(1).strip(), match.group(2).strip()
    match = re.search(r"(.+?)\s+vs\s+(.+)", cleaned, flags=re.I)
    if match:
        left = re.sub(r"^(Counter-Strike|CS2)\s*:\s*", "", match.group(1), flags=re.I)
        right = re.split(r"\s+\(|\s+-", match.group(2), maxsplit=1)[0]
        return left.strip(), right.strip()
    return None, None


def _parse_time(raw: Any) -> datetime | None:
    if not raw:
        return None
    text = str(raw).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        return parsed.replace(tzinfo=None)
    return parsed


def parse_market(raw: dict[str, Any]) -> ParsedMarket | None:
    outcomes = [str(item) for item in maybe_list(raw.get("outcomes"))]
    tokens = [str(item) for item in maybe_list(raw.get("clobTokenIds"))]
    prices = maybe_list(raw.get("outcomePrices"))
    if len(outcomes) < 2 or len(tokens) < 2:
        return None
    market_type = str(raw.get("sportsMarketType") or raw.get("groupItemTitle") or "unknown")
    group = str(raw.get("groupItemTitle") or "")
    is_series = market_type == "moneyline" or group.lower() == "match winner"
    fee = raw.get("feeSchedule") or {}
    fee_rate = _float(fee.get("rate")) if isinstance(fee, dict) else None
    parsed_outcomes: list[ParsedOutcome] = []
    bid = _float(raw.get("bestBid"))
    ask = _float(raw.get("bestAsk"))
    for index, name in enumerate(outcomes[:2]):
        token = tokens[index]
        price = _float(prices[index]) if index < len(prices) else None
        # Complementary ask for the other side when Gamma only posts one bestAsk.
        side_ask = ask if index == 0 else (1.0 - bid if bid is not None else price)
        side_bid = bid if index == 0 else (1.0 - ask if ask is not None else price)
        parsed_outcomes.append(
            ParsedOutcome(name=name, token_id=token, bid=side_bid, ask=side_ask)
        )
    return ParsedMarket(
        condition_id=str(raw.get("conditionId") or raw.get("id") or ""),
        question=str(raw.get("question") or ""),
        market_type=market_type,
        group_title=group,
        fee_rate=fee_rate or 0.05,
        volume=_float(raw.get("volume")),
        volume_24h=_float(raw.get("volume24hr")),
        liquidity=_float(raw.get("liquidityNum") or raw.get("liquidity")),
        spread=_float(raw.get("spread")),
        outcomes=tuple(parsed_outcomes),
        is_series_winner=is_series,
    )


def parse_event(raw: dict[str, Any]) -> ParsedEvent | None:
    title = str(raw.get("title") or "")
    slug = str(raw.get("slug") or "")
    if not _looks_like_cs2(title, slug):
        return None
    left, right = parse_teams_from_title(title)
    markets = []
    for item in raw.get("markets") or []:
        if not isinstance(item, dict):
            continue
        parsed = parse_market(item)
        if parsed is not None:
            markets.append(parsed)
    start = _parse_time(raw.get("gameStartTime") or raw.get("endDate") or raw.get("startDate"))
    return ParsedEvent(
        provider_event_id=str(raw.get("id") or slug),
        slug=slug,
        title=title,
        start_time=start,
        volume=_float(raw.get("volume")),
        team_left=left,
        team_right=right,
        markets=tuple(markets),
    )


def _looks_like_cs2(title: str, slug: str) -> bool:
    blob = f"{title} {slug}".lower()
    return "counter-strike" in blob or slug.lower().startswith("cs2-") or " cs2 " in f" {blob} "


def depth_from_book(asks: list[dict[str, Any]], ask: float | None, cents: float) -> float:
    if ask is None:
        return 0.0
    total = 0.0
    for level in asks:
        price = _float(level.get("price"))
        size = _float(level.get("size"))
        if price is None or size is None:
            continue
        if ask - 1e-9 <= price <= ask + cents + 1e-9:
            total += price * size
    return total
