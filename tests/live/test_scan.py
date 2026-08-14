from __future__ import annotations

from datetime import datetime

from esports_model.cli import main
from esports_model.db.models import Match
from esports_model.db.session import session_scope
from esports_model.features.spec import FeatureRow
from esports_model.live.grade import grade_settled, pending_path
from esports_model.live.scan import run_scan
from tests.helpers import seed_linear_matches, seed_upcoming_book

NOW = datetime(2026, 8, 14, 12, 0, 0)


def _hot(_row: FeatureRow) -> float:
    return 0.90


def _cold(_row: FeatureRow) -> float:
    return 0.45


def test_scan_emits_bet_watch_pass_and_never_bets_quarantine(tmp_path) -> None:
    url = f"sqlite:///{tmp_path / 'scan.db'}"
    out = tmp_path / "output"
    seed_linear_matches(url, n=12)
    seed_upcoming_book(url, token_id="tok-bet", now=NOW)
    seed_upcoming_book(url, token_id="tok-thin", volume=80.0, now=NOW)
    seed_upcoming_book(
        url,
        token_id="tok-q",
        identity_status="quarantine",
        identity_confidence="low",
        attach_match=False,
        now=NOW,
    )
    snapshot = run_scan(
        database_url=url,
        now=NOW,
        predict_fn=_hot,
        snapshot_path=tmp_path / "snapshot.json",
        output_dir=out,
    )
    by_token = {row["token_id"]: row for row in snapshot["rows"]}
    assert by_token["tok-bet"]["action"] == "BET"
    assert by_token["tok-bet"]["stake_usd"] > 0
    assert by_token["tok-thin"]["action"] == "WATCH"
    assert by_token["tok-q"]["action"] == "quarantine"
    assert snapshot["diagnostic"] == "edges_available"
    assert snapshot["counts"]["quarantine"] == 1


def test_liquid_no_edge_is_pass(tmp_path) -> None:
    url = f"sqlite:///{tmp_path / 'pass.db'}"
    seed_linear_matches(url, n=12)
    seed_upcoming_book(url, token_id="tok-pass", now=NOW)
    snapshot = run_scan(
        database_url=url,
        now=NOW,
        predict_fn=_cold,
        snapshot_path=tmp_path / "snapshot.json",
        output_dir=tmp_path / "output",
    )
    assert snapshot["rows"][0]["action"] == "PASS"
    assert snapshot["diagnostic"] == "market_available_no_edges"


def test_empty_scan_is_honest(tmp_path) -> None:
    url = f"sqlite:///{tmp_path / 'empty.db'}"
    snapshot = run_scan(
        database_url=url,
        snapshot_path=tmp_path / "snapshot.json",
        output_dir=tmp_path / "output",
    )
    assert snapshot["implemented"] is True
    assert snapshot["diagnostic"] == "no_market_posted_yet"
    assert snapshot["rows"] == []


def test_grade_hook_scores_settled_rows(tmp_path) -> None:
    url = f"sqlite:///{tmp_path / 'grade.db'}"
    out = tmp_path / "output"
    seed_linear_matches(url, n=12)
    seeded = seed_upcoming_book(url, token_id="tok-grade", now=NOW)
    run_scan(
        database_url=url,
        now=NOW,
        predict_fn=_hot,
        snapshot_path=tmp_path / "snapshot.json",
        output_dir=out,
    )
    with session_scope(url) as session:
        match = session.get(Match, seeded["match_id"])
        assert match is not None
        match.winner_id = seeded["team_id"]
        match.score1 = 2
        match.score2 = 0
        match.status = "completed"
    report = grade_settled(database_url=url, output_dir=out)
    assert report["n_graded"] == 1
    assert report["rows"][0]["won"] == 1
    assert pending_path(out).read_text(encoding="utf-8") == ""


def test_cli_scan_json(tmp_path, capsys, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    url = f"sqlite:///{tmp_path / 'cli.db'}"
    assert main(["scan", "--json", "--database-url", url]) == 0
    text = capsys.readouterr().out
    assert "no_market_posted_yet" in text
