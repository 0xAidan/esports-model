from __future__ import annotations

from datetime import datetime, timedelta

from esports_model.db.models import Event, MapResult, Match, Team
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
