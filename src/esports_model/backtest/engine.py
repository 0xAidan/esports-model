"""Chronological walk-forward backtest."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

from esports_model.backtest.metrics import summarize
from esports_model.config import feature_flags
from esports_model.db.session import init_db, session_scope
from esports_model.features.builder import build_feature_table
from esports_model.features.spec import FeatureRow
from esports_model.model.baselines import coin_flip, elo_only
from esports_model.model.calibration import apply_platt, fit_platt
from esports_model.model.train import eligible_rows, fit_logistic


def run_backtest(
    *,
    database_url: str,
    min_train: int,
    omit_predictions: bool,
    output_path: str,
    min_prior_matches: int | None = None,
) -> dict[str, object]:
    init_db(database_url)
    min_prior = min_prior_matches
    if min_prior is None:
        min_prior = int(feature_flags().get("min_prior_matches", 8))
    with session_scope(database_url) as session:
        rows = eligible_rows(build_feature_table(session), min_prior)

    if len(rows) <= min_train:
        report = {
            "ok": True,
            "implemented": True,
            "n_eligible": len(rows),
            "min_train": min_train,
            "message": (
                f"Not enough eligible matches for walk-forward "
                f"(have {len(rows)}, need more than {min_train})."
            ),
            "metrics": {},
            "predictions": [],
        }
        _write(output_path, report)
        return report

    predictions: list[dict[str, object]] = []
    y_true: list[int] = []
    p_model: list[float] = []
    p_elo: list[float] = []
    p_flat: list[float] = []
    raw_history: list[float] = []
    label_history: list[int] = []

    for index in range(min_train, len(rows)):
        train = rows[:index]
        current = rows[index]
        if current.label is None:
            continue
        if len({row.label for row in train}) < 2:
            continue
        fitted = fit_logistic(train)
        raw = _predict(fitted, current)
        calibrated = apply_platt(fit_platt(raw_history, label_history), raw)
        y_true.append(current.label)
        p_model.append(calibrated)
        p_elo.append(elo_only(current))
        p_flat.append(coin_flip(current))
        raw_history.append(raw)
        label_history.append(current.label)
        if not omit_predictions:
            predictions.append(
                {
                    "match_id": current.match_id,
                    "label": current.label,
                    "p_model": calibrated,
                    "p_raw": raw,
                    "p_elo": p_elo[-1],
                    "p_coin": 0.5,
                    "prior_matches_min": current.prior_matches_min,
                }
            )

    report: dict[str, object] = {
        "ok": True,
        "implemented": True,
        "n_eligible": len(rows),
        "n_scored": len(y_true),
        "min_train": min_train,
        "min_prior_matches": min_prior,
        "lookahead": False,
        "metrics": {
            "model": summarize("model", y_true, p_model),
            "elo_only": summarize("elo_only", y_true, p_elo),
            "coin_flip": summarize("coin_flip", y_true, p_flat),
        },
        "notes": [
            "Model quality is scored separately from paper trading.",
            "Market-price baseline is omitted until a historical Polymarket token is joined.",
        ],
        "predictions": [] if omit_predictions else predictions,
    }
    _write(output_path, report)
    return report


def _predict(model: LogisticRegression, row: FeatureRow) -> float:
    proba = model.predict_proba(np.asarray([row.vector()], dtype=float))[0, 1]
    return float(proba)


def _write(output_path: str, report: dict[str, object]) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
