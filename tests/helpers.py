from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select

from esports_model.db.models import (
    Event,
    MapResult,
    Market,
    MarketEvent,
    Match,
    OrderBookSnapshot,
    Team,
)
from esports_model.db.session import init_db, session_scope


def seed_linear_matches(
    database_url: str,
    *,
    n: int = 12,
    start: datetime | None = None,
) -> None:
    init_db(database_url)
    origin = start or datetime(2024, 1, 1, 12, 0, 0)
    with session_scope(database_url) as session:
        teams = [
            Team(liquipedia_page="alpha", name="Alpha"),
            Team(liquipedia_page="bravo", name="Bravo"),
            Team(liquipedia_page="charlie", name="Charlie"),
        ]
        session.add_all(teams)
        session.flush()
        event = Event(
            liquipedia_page="Test Cup",
            name="Test Cup",
            tier="S-Tier",
            game_version="cs2",
        )
        session.add(event)
        session.flush()
        for index in range(n):
            team1 = teams[index % 3]
            team2 = teams[(index + 1) % 3]
            winner = team1 if index % 2 == 0 else team2
            match = Match(
                liquipedia_match_id=f"test:{index}",
                event_id=event.id,
                team1_id=team1.id,
                team2_id=team2.id,
                winner_id=winner.id,
                start_time=origin + timedelta(days=index),
                format="bo3",
                score1=2 if winner.id == team1.id else 0,
                score2=0 if winner.id == team1.id else 2,
                game_version="cs2",
                offline=True,
                status="completed",
            )
            session.add(match)
            session.flush()
            session.add(
                MapResult(
                    match_id=match.id,
                    map_name="Mirage",
                    map_number=1,
                    team1_score=13 if winner.id == team1.id else 7,
                    team2_score=7 if winner.id == team1.id else 13,
                    winner_id=winner.id,
                )
            )


def seed_upcoming_book(
    database_url: str,
    *,
    identity_status: str = "matched",
    identity_confidence: str = "high",
    ask: float = 0.40,
    bid: float = 0.38,
    spread: float = 0.02,
    volume: float = 20000.0,
    depth: float = 500.0,
    hours_ahead: float = 12.0,
    token_id: str = "tok-alpha",
    attach_match: bool = True,
    now: datetime | None = None,
) -> dict[str, int | None]:
    clock = now or datetime(2026, 8, 14, 12, 0, 0)
    with session_scope(database_url) as session:
        teams = list(session.scalars(select(Team).order_by(Team.id)))
        event = session.scalar(select(Event))
        if len(teams) < 2 or event is None:
            raise RuntimeError("seed_linear_matches must run first")
        alpha, bravo = teams[0], teams[1]
        match_id = None
        if attach_match:
            upcoming = Match(
                liquipedia_match_id=f"upcoming:{token_id}",
                event_id=event.id,
                team1_id=alpha.id,
                team2_id=bravo.id,
                winner_id=None,
                start_time=clock + timedelta(hours=hours_ahead),
                format="bo3",
                game_version="cs2",
                offline=True,
                status="upcoming",
            )
            session.add(upcoming)
            session.flush()
            match_id = upcoming.id
        market_event = MarketEvent(
            provider="polymarket",
            provider_event_id=f"evt-{token_id}",
            slug=f"cs2-{token_id}",
            title="Counter-Strike: Alpha vs Bravo (BO3)",
            start_time=clock + timedelta(hours=hours_ahead),
            volume=volume,
        )
        session.add(market_event)
        session.flush()
        market = Market(
            provider="polymarket",
            event_id=market_event.id,
            match_id=match_id,
            condition_id=f"cond-{token_id}",
            question="Alpha vs Bravo",
            market_type="moneyline",
            outcome_name="Alpha",
            token_id=token_id,
            team_id=alpha.id if identity_confidence == "high" else None,
            identity_confidence=identity_confidence,
            identity_status=identity_status,
        )
        session.add(market)
        session.flush()
        session.add(
            OrderBookSnapshot(
                market_id=market.id,
                bid=bid,
                ask=ask,
                spread=spread,
                depth_usd=depth,
                volume_24h=volume,
                volume_lifetime=volume,
                fee_rate=0.05,
            )
        )
        return {"match_id": match_id, "team_id": alpha.id, "market_id": market.id}
