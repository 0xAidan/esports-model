from __future__ import annotations

from esports_model.backtest.engine import run_backtest
from esports_model.backtest.metrics import brier, log_loss
from esports_model.model.train import train_model
from tests.helpers import seed_linear_matches


def test_walk_forward_scores_later_matches_only(tmp_path) -> None:
    db = tmp_path / "bt.db"
    url = f"sqlite:///{db}"
    seed_linear_matches(url, n=16)
    report = run_backtest(
        database_url=url,
        min_train=6,
        omit_predictions=False,
        output_path=str(tmp_path / "backtest.json"),
        min_prior_matches=0,
    )
    assert report["implemented"] is True
    assert report["n_scored"] > 0
    assert report["lookahead"] is False
    metrics = report["metrics"]
    assert "model" in metrics
    assert "elo_only" in metrics
    assert "coin_flip" in metrics
    preds = report["predictions"]
    assert isinstance(preds, list)
    assert preds
    ids = [row["match_id"] for row in preds]
    assert ids == sorted(ids)


def test_empty_db_is_honest(tmp_path) -> None:
    db = tmp_path / "empty.db"
    url = f"sqlite:///{db}"
    report = run_backtest(
        database_url=url,
        min_train=80,
        omit_predictions=True,
        output_path=str(tmp_path / "backtest.json"),
    )
    assert report["n_eligible"] == 0
    assert "Not enough eligible matches" in str(report["message"])


def test_train_writes_joblib(tmp_path) -> None:
    db = tmp_path / "tr.db"
    url = f"sqlite:///{db}"
    seed_linear_matches(url, n=20)
    path = train_model(
        database_url=url,
        output_path=str(tmp_path / "model.joblib"),
        min_prior_matches=0,
    )
    assert path.endswith("model.joblib")


def test_metrics_prefer_better_probs() -> None:
    labels = [1, 0, 1, 0]
    good = [0.8, 0.2, 0.7, 0.3]
    bad = [0.51, 0.49, 0.51, 0.49]
    assert brier(labels, good) < brier(labels, bad)
    assert log_loss(labels, good) < log_loss(labels, bad)
