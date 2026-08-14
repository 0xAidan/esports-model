"""Naive probability baselines."""

from __future__ import annotations

from esports_model.features.elo import expected_score
from esports_model.features.spec import FeatureRow


def coin_flip(_row: FeatureRow) -> float:
    return 0.5


def elo_only(row: FeatureRow) -> float:
    elo_diff = row.values["elo_diff"]
    elo1 = 1500.0 + elo_diff / 2.0
    elo2 = 1500.0 - elo_diff / 2.0
    return expected_score(elo1, elo2)
