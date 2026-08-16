"""Load a saved model or fit one from local history."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import joblib
from sklearn.linear_model import LogisticRegression
from sqlalchemy.orm import Session

from esports_model.config import feature_flags
from esports_model.features.builder import build_feature_table
from esports_model.features.spec import FeatureRow
from esports_model.model.train import eligible_rows, fit_logistic

PredictFn = Callable[[FeatureRow], float]
DEFAULT_MODEL_PATH = "data/model_logistic.joblib"


def predict_with_model(model: LogisticRegression, row: FeatureRow) -> float:
    proba = model.predict_proba([row.vector()])[0, 1]
    return float(proba)


def load_saved_predictor(path: Path) -> PredictFn | None:
    if not path.exists():
        return None
    payload = joblib.load(path)
    model = payload.get("model") if isinstance(payload, dict) else payload
    if not isinstance(model, LogisticRegression):
        return None

    def _predict(row: FeatureRow) -> float:
        return predict_with_model(model, row)

    return _predict


def fit_predictor(session: Session, min_prior: int | None = None) -> PredictFn | None:
    floor = min_prior
    if floor is None:
        floor = int(feature_flags().get("min_prior_matches", 8))
    rows = eligible_rows(build_feature_table(session), floor)
    if len(rows) < 10 or len({row.label for row in rows}) < 2:
        return None
    model = fit_logistic(rows)
    return lambda row: predict_with_model(model, row)


def resolve_predictor(
    session: Session,
    *,
    model_path: str | None,
    override: PredictFn | None,
) -> PredictFn | None:
    if override is not None:
        return override
    path = Path(model_path) if model_path else Path(DEFAULT_MODEL_PATH)
    saved = load_saved_predictor(path)
    if saved is not None:
        return saved
    return fit_predictor(session)
