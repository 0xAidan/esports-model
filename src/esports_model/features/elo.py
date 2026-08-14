"""Elo updates that only move forward in time."""

from __future__ import annotations

DEFAULT_ELO = 1500.0
K_FACTOR = 24.0


def expected_score(elo_self: float, elo_opp: float) -> float:
    return 1.0 / (1.0 + 10 ** ((elo_opp - elo_self) / 400.0))


def update_elo(winner_elo: float, loser_elo: float, *, k: float = K_FACTOR) -> tuple[float, float]:
    exp_win = expected_score(winner_elo, loser_elo)
    exp_lose = expected_score(loser_elo, winner_elo)
    return winner_elo + k * (1.0 - exp_win), loser_elo + k * (0.0 - exp_lose)
