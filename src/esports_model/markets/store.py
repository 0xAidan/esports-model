"""Persist parsed Polymarket rows and identity decisions."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from esports_model.db.models import (
    IdentityReview,
    Market,
    MarketEvent,
    Match,
    OrderBookSnapshot,
)
from esports_model.identity.resolver import match_team_name, pair_confidence
from esports_model.markets.parse import ParsedEvent, ParsedOutcome


def upsert_event(session: Session, parsed: ParsedEvent) -> MarketEvent:
    row = session.scalar(
        select(MarketEvent).where(MarketEvent.provider_event_id == parsed.provider_event_id)
    )
    if row is None:
        row = MarketEvent(
            provider="polymarket",
            provider_event_id=parsed.provider_event_id,
            slug=parsed.slug,
            title=parsed.title,
        )
        session.add(row)
    row.slug = parsed.slug
    row.title = parsed.title
    row.start_time = parsed.start_time
    row.volume = parsed.volume
    session.flush()
    return row


def resolve_match(
    session: Session,
    *,
    left_team_id: int | None,
    right_team_id: int | None,
    start_time: datetime | None,
) -> int | None:
    if left_team_id is None or right_team_id is None:
        return None
    rows = list(
        session.scalars(
            select(Match).where(
                Match.team1_id.in_((left_team_id, right_team_id)),
                Match.team2_id.in_((left_team_id, right_team_id)),
            )
        )
    )
    candidates = [
        row
        for row in rows
        if {row.team1_id, row.team2_id} == {left_team_id, right_team_id}
    ]
    if not candidates:
        return None
    if start_time is None:
        return candidates[0].id
    window = timedelta(hours=36)

    def _score(row: Match) -> float:
        if row.start_time is None:
            return 10**9
        return abs((row.start_time - start_time).total_seconds())

    best = min(candidates, key=_score)
    if best.start_time is not None and abs((best.start_time - start_time).total_seconds()) > window.total_seconds():
        return None
    return best.id


def upsert_outcome(
    session: Session,
    *,
    event: MarketEvent,
    parsed_event: ParsedEvent,
    condition_id: str,
    question: str,
    market_type: str,
    outcome: ParsedOutcome,
    fee_rate: float,
    volume: float | None,
    volume_24h: float | None,
    spread: float | None,
    depth_usd: float | None,
    bid: float | None,
    ask: float | None,
) -> Market:
    left = match_team_name(session, parsed_event.team_left or "")
    right = match_team_name(session, parsed_event.team_right or "")
    this = match_team_name(session, outcome.name)
    pair = pair_confidence(left, right)
    status = "matched"
    reason = f"{left.via}/{right.via}"
    match_id = None
    if pair != "high":
        status = "quarantine"
        reason = f"identity {pair}: {left.normalized} vs {right.normalized}"
        existing = session.scalar(
            select(IdentityReview).where(IdentityReview.market_event_id == event.id)
        )
        if existing is None:
            session.add(
                IdentityReview(
                    market_event_id=event.id,
                    left_name=parsed_event.team_left or "",
                    right_name=parsed_event.team_right or "",
                    reason=reason,
                )
            )
    else:
        match_id = resolve_match(
            session,
            left_team_id=left.team_id,
            right_team_id=right.team_id,
            start_time=parsed_event.start_time,
        )
        if match_id is None:
            status = "watch"
            reason = "teams matched, no Liquipedia match in the time window"
    row = session.scalar(select(Market).where(Market.token_id == outcome.token_id))
    if row is None:
        row = Market(
            provider="polymarket",
            event_id=event.id,
            condition_id=condition_id,
            question=question,
            market_type=market_type,
            outcome_name=outcome.name,
            token_id=outcome.token_id,
        )
        session.add(row)
    row.event_id = event.id
    row.match_id = match_id
    row.question = question
    row.market_type = market_type
    row.outcome_name = outcome.name
    row.team_id = this.team_id
    row.identity_confidence = pair
    row.identity_status = status
    row.identity_reason = reason
    session.flush()
    session.add(
        OrderBookSnapshot(
            market_id=row.id,
            bid=bid if bid is not None else outcome.bid,
            ask=ask if ask is not None else outcome.ask,
            spread=spread,
            depth_usd=depth_usd,
            volume_24h=volume_24h,
            volume_lifetime=volume,
            fee_rate=fee_rate,
        )
    )
    return row
