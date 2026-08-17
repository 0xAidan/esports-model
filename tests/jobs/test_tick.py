from __future__ import annotations

from esports_model.jobs.tick import run_tick
from esports_model.live.scan import run_scan
from esports_model.model.train import train_model
from tests.helpers import seed_linear_matches
from tests.ingest.test_sync import FIXTURE, FakeClient
from tests.markets.test_pull import FakePolymarket


def _lp() -> FakeClient:
    return FakeClient(FIXTURE.read_text(encoding="utf-8"))


def test_thin_db_resumes_default_sync(tmp_path) -> None:
    url = f"sqlite:///{tmp_path / 'thin.db'}"
    snapshot = run_tick(
        database_url=url,
        output_dir=tmp_path / "output",
        snapshot_path=tmp_path / "snapshot.json",
        model_path=str(tmp_path / "model.joblib"),
        liquipedia_factory=_lp,
        market_factory=FakePolymarket,
    )
    report = snapshot["tick_report"]
    assert report["sync_profile"] == "default"
    assert report["sync"]["resume"] is True
    assert (tmp_path / "output" / "tick.json").exists()


def test_fat_db_uses_upcoming_sync(tmp_path) -> None:
    url = f"sqlite:///{tmp_path / 'fat.db'}"
    seed_linear_matches(url, n=100)
    snapshot = run_tick(
        database_url=url,
        output_dir=tmp_path / "output",
        snapshot_path=tmp_path / "snapshot.json",
        model_path=str(tmp_path / "model.joblib"),
        liquipedia_factory=_lp,
        market_factory=FakePolymarket,
    )
    assert snapshot["tick_report"]["sync_profile"] == "upcoming"
    assert snapshot["tick_report"]["sync"]["resume"] is False


def test_scan_loads_saved_model(tmp_path) -> None:
    url = f"sqlite:///{tmp_path / 'model.db'}"
    seed_linear_matches(url, n=40)
    path = tmp_path / "model.joblib"
    train_model(database_url=url, output_path=str(path), min_prior_matches=0)
    snapshot = run_scan(
        database_url=url,
        model_path=str(path),
        snapshot_path=tmp_path / "snapshot.json",
        output_dir=tmp_path / "output",
    )
    assert snapshot["model_available"] is True
    assert path.exists()
