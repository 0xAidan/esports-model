"""Platt scaling fitted only on earlier out-of-sample scores."""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression


def fit_platt(raw_scores: list[float], labels: list[int]) -> LogisticRegression | None:
    if len(raw_scores) < 20 or len(set(labels)) < 2:
        return None
    model = LogisticRegression(max_iter=200)
    x = np.asarray(raw_scores, dtype=float).reshape(-1, 1)
    y = np.asarray(labels, dtype=int)
    model.fit(x, y)
    return model


def apply_platt(model: LogisticRegression | None, raw: float) -> float:
    if model is None:
        return _clip(raw)
    proba = model.predict_proba(np.asarray([[raw]], dtype=float))[0, 1]
    return _clip(float(proba))


def _clip(value: float) -> float:
    return min(max(value, 1e-6), 1.0 - 1e-6)
