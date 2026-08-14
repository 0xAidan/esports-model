from __future__ import annotations

from pathlib import Path

from esports_model.ingest.wikitext import parse_event_page, parse_match_date

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "liquipedia" / "ewc_snippet.wiki"


def test_parse_event_and_bo3_from_fixture() -> None:
    event = parse_event_page("Esports World Cup/2026", FIXTURE.read_text(encoding="utf-8"))
    assert event.name == "Esports World Cup 2026"
    assert event.tier == "S-Tier"
    assert event.game_version == "cs2"
    assert event.offline is True
    assert len(event.matches) == 2

    finished = event.matches[0]
    assert finished.team1_slug == "jjh"
    assert finished.team2_slug == "gl"
    assert finished.finished is True
    assert finished.score1 == 0
    assert finished.score2 == 2
    assert finished.format == "bo3"
    assert finished.hltv_id == "2396575"
    assert [item.map_name for item in finished.maps] == ["Dust II", "Ancient"]
    assert finished.maps[0].team1_score == 3
    assert finished.maps[0].team2_score == 13
    assert finished.winner_side == 2

    upcoming = event.matches[1]
    assert upcoming.finished is False
    assert upcoming.team1_slug == "big"
    assert upcoming.maps == ()


def test_parse_match_date_converts_cest_to_utc() -> None:
    parsed = parse_match_date("August 13, 2026 - 13:00 CEST")
    assert parsed is not None
    assert parsed.hour == 11
    assert parsed.day == 13
