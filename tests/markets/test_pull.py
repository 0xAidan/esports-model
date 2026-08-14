from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import func, select

from esports_model.db.models import IdentityReview, Market, Team
from esports_model.db.session import init_db, session_scope
from esports_model.markets.pull import pull_markets

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "polymarket" / "search.json"


class FakePolymarket:
    def __init__(self) -> None:
        self.payload = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def __enter__(self) -> FakePolymarket:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def search_events(self) -> list[dict]:
        return list(self.payload["events"])

    def book(self, _token_id: str) -> dict:
        return {
            "asks": [{"price": "0.66", "size": "200"}, {"price": "0.90", "size": "10"}],
            "bids": [{"price": "0.64", "size": "200"}],
        }


def test_pull_quarantines_unmatched_and_matches_aliases(tmp_path) -> None:
    url = f"sqlite:///{tmp_path / 'mkt.db'}"
    init_db(url)
    with session_scope(url) as session:
        session.add(Team(liquipedia_page="furia", name="FURIA"))
        session.add(Team(liquipedia_page="9z", name="9z"))
    summary = pull_markets(database_url=url, client_factory=FakePolymarket)
    assert summary["implemented"] is True
    assert summary["series_markets"] == 2
    with session_scope(url) as session:
        rows = list(session.scalars(select(Market)))
        statuses = [row.identity_status for row in rows]
        reviews = session.scalar(select(func.count()).select_from(IdentityReview))
        watched = [row for row in rows if row.identity_status == "watch"]
        quarantined = [row for row in rows if row.identity_status == "quarantine"]
        watched_confidence = [row.identity_confidence for row in watched]
        quarantined_match_ids = [row.match_id for row in quarantined]
    assert "quarantine" in statuses
    assert reviews == 1
    assert watched
    assert all(confidence == "high" for confidence in watched_confidence)
    assert quarantined
    assert all(match_id is None for match_id in quarantined_match_ids)
