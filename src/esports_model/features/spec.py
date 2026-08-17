"""Feature row contract."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

FEATURE_NAMES: tuple[str, ...] = (
    "elo_diff",
    "form5_diff",
    "form10_diff",
    "map_wr_diff",
    "h2h_diff",
    "rest_days_diff",
    "prior_log_min",
    "tier_s",
    "tier_a",
    "is_bo1",
    "is_bo3",
    "is_bo5",
    "is_offline",
    "roster_stability_diff",
)


@dataclass(frozen=True)
class FeatureRow:
    match_id: int
    team1_id: int
    team2_id: int
    label: int | None
    prior_matches_min: int
    values: dict[str, float]

    def vector(self) -> list[float]:
        return [float(self.values[name]) for name in FEATURE_NAMES]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["feature_names"] = list(FEATURE_NAMES)
        return payload
