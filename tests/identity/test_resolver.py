from __future__ import annotations

from esports_model.db.models import Team
from esports_model.db.session import init_db, session_scope
from esports_model.identity.normalize import normalize_name
from esports_model.identity.resolver import match_team_name, pair_confidence


def test_normalize_strips_noise() -> None:
    assert normalize_name("FaZe Clan") == "faze"
    assert normalize_name("Natus Vincere") == "natus vincere"


def test_alias_is_high_confidence(tmp_path) -> None:
    url = f"sqlite:///{tmp_path / 'id.db'}"
    init_db(url)
    with session_scope(url) as session:
        session.add(Team(liquipedia_page="faze", name="FaZe"))
        session.flush()
        hit = match_team_name(session, "FaZe Clan")
        assert hit.confidence == "high"
        assert hit.team_id is not None


def test_unknown_name_is_not_high(tmp_path) -> None:
    url = f"sqlite:///{tmp_path / 'id.db'}"
    init_db(url)
    with session_scope(url) as session:
        session.add(Team(liquipedia_page="faze", name="FaZe"))
        session.flush()
        miss = match_team_name(session, "Totally Fake Squad XYZ")
        assert miss.confidence != "high"
        pair = pair_confidence(miss, miss)
        assert pair == "low"
