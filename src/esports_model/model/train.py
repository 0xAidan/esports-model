"""Fit the baseline logistic model on all eligible history."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import yaml
from sklearn.linear_model import LogisticRegression

from esports_model.config import feature_flags, get_settings
from esports_model.db.session import init_db, session_scope
from esports_model.features.builder import FEATURE_NAMES, build_feature_table
from esports_model.features.spec import FeatureRow


def _min_prior(override: int | None) -> int:
    if override is not None:
        return override
    return int(feature_flags().get("min_prior_matches", 8))


def eligible_rows(rows: list[FeatureRow], min_prior: int) -> list[FeatureRow]:
    return [
        row
        for row in rows
        if row.label is not None and row.prior_matches_min >= min_prior
    ]


def fit_logistic(rows: list[FeatureRow]) -> LogisticRegression:
    x = np.asarray([row.vector() for row in rows], dtype=float)
    y = np.asarray([row.label for row in rows], dtype=int)
    model = LogisticRegression(max_iter=400)
    model.fit(x, y)
    return model


def train_model(
    *,
    database_url: str,
    output_path: str,
    min_prior_matches: int | None,
) -> str:
    init_db(database_url)
    min_prior = _min_prior(min_prior_matches)
    with session_scope(database_url) as session:
        rows = eligible_rows(build_feature_table(session), min_prior)
    if len(rows) < 10 or len({row.label for row in rows}) < 2:
        raise RuntimeError(
            f"Not enough labeled matches to train (have {len(rows)}, need 10 with both outcomes)."
        )
    model = fit_logistic(rows)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    registry = _load_registry()
    joblib.dump(
        {
            "model": model,
            "feature_names": list(FEATURE_NAMES),
            "min_prior_matches": min_prior,
            "registry": registry,
            "n_train": len(rows),
        },
        path,
    )
    return str(path)


def _load_registry() -> dict[str, object]:
    path = get_settings().project_root / "src" / "esports_model" / "model" / "registry.yaml"
    if not path.exists():
        return {"name": "logistic_v1"}
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        return {"name": "logistic_v1"}
    return loaded
