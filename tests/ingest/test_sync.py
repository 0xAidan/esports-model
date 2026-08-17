from __future__ import annotations

from pathlib import Path

from sqlalchemy import func, select

from esports_model.config import profile
from esports_model.db.models import Match
from esports_model.db.session import session_scope
from esports_model.ingest.coverage import coverage_report
from esports_model.ingest.sync import run_sync

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "liquipedia" / "ewc_snippet.wiki"


class FakeClient:
    def __init__(self, wikitext: str) -> None:
        self.wikitext = wikitext
        self.calls: list[dict[str, str]] = []

    def __enter__(self) -> FakeClient:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def get_json(self, params: dict[str, str]) -> dict[str, object]:
        self.calls.append(dict(params))
        if params.get("list") == "categorymembers":
            return {"query": {"categorymembers": [{"title": "Esports World Cup/2026"}]}}
        if params.get("prop") == "revisions":
            return {
                "query": {
                    "pages": {
                        "1": {
                            "revisions": [{"slots": {"main": {"*": self.wikitext}}}],
                        }
                    }
                }
            }
        raise AssertionError(f"unexpected params: {params}")


def test_sync_upserts_fixture_matches(tmp_path) -> None:
    db = tmp_path / "esports.db"
    url = f"sqlite:///{db}"
    client = FakeClient(FIXTURE.read_text(encoding="utf-8"))
    spec = profile("quick")
    spec["max_matches_per_run"] = 50
    summary = run_sync(
        profile_name="quick",
        spec=spec,
        resume=False,
        database_url=url,
        client_factory=lambda: client,
    )
    assert summary["implemented"] is True
    assert summary["matches_upserted"] >= 2
    with session_scope(url) as session:
        count = session.scalar(select(func.count()).select_from(Match))
        completed = session.scalar(
            select(func.count()).select_from(Match).where(Match.status == "completed")
        )
        upcoming = session.scalar(
            select(func.count()).select_from(Match).where(Match.status == "upcoming")
        )
    assert count == 2
    assert completed == 1
    assert upcoming == 1
    report = coverage_report(database_url=url)
    assert report["match_count"] == 2
    assert report["missing_score_count"] == 1


def test_upcoming_profile_skips_finished(tmp_path) -> None:
    db = tmp_path / "esports.db"
    url = f"sqlite:///{db}"
    client = FakeClient(FIXTURE.read_text(encoding="utf-8"))
    spec = profile("upcoming")
    summary = run_sync(
        profile_name="upcoming",
        spec=spec,
        resume=False,
        database_url=url,
        client_factory=lambda: client,
    )
    assert summary["matches_upserted"] == 1
    with session_scope(url) as session:
        statuses = list(session.scalars(select(Match.status)))
    assert statuses == ["upcoming"]
