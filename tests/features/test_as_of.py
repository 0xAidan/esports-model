from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select

from esports_model.db.models import Event, Match, Team
from esports_model.db.session import init_db, session_scope
from esports_model.features.builder import build_feature_row, build_feature_table
from tests.helpers import seed_linear_matches


def test_features_ignore_later_matches(tmp_path) -> None:
    db = tmp_path / "feat.db"
    url = f"sqlite:///{db}"
    seed_linear_matches(url, n=3)
    with session_scope(url) as session:
        matches = list(session.scalars(select(Match).order_by(Match.start_time)))
        mid = matches[1]
        before = build_feature_row(session, mid)
        assert before is not None
        assert before.prior_matches_min == 0 or before.prior_matches_min == 1
        snapshot = dict(before.values)

        late_event = session.scalar(select(Event))
        extra = Match(
            liquipedia_match_id="future-leak",
            event_id=late_event.id if late_event else None,
            team1_id=mid.team1_id,
            team2_id=mid.team2_id,
            winner_id=mid.team1_id,
            start_time=mid.start_time + timedelta(days=30),
            format="bo3",
            score1=2,
            score2=0,
            game_version="cs2",
            status="completed",
        )
        session.add(extra)
        session.flush()
        after = build_feature_row(session, mid)
        assert after is not None
        assert after.values == snapshot
        assert after.prior_matches_min == before.prior_matches_min


def test_feature_table_is_chronological(tmp_path) -> None:
    db = tmp_path / "feat.db"
    url = f"sqlite:///{db}"
    seed_linear_matches(url, n=6)
    with session_scope(url) as session:
        rows = build_feature_table(session)
        priors = [row.prior_matches_min for row in rows]
    assert priors[0] == 0
    assert priors[-1] >= priors[0]


def test_match_does_not_use_its_own_result(tmp_path) -> None:
    db = tmp_path / "feat.db"
    url = f"sqlite:///{db}"
    init_db(url)
    start = datetime(2024, 6, 1, 12, 0, 0)
    with session_scope(url) as session:
        a = Team(liquipedia_page="a", name="A")
        b = Team(liquipedia_page="b", name="B")
        session.add_all([a, b])
        session.flush()
        first = Match(
            liquipedia_match_id="only",
            team1_id=a.id,
            team2_id=b.id,
            winner_id=a.id,
            start_time=start,
            format="bo1",
            score1=1,
            score2=0,
            status="completed",
        )
        session.add(first)
        session.flush()
        row = build_feature_row(session, first)
        assert row is not None
        assert row.prior_matches_min == 0
        assert row.values["elo_diff"] == 0.0
        assert row.values["form5_diff"] == 0.0
