"""Fractional Kelly stake advice. Never places an order."""

from __future__ import annotations


def full_kelly(p_star: float, cost: float) -> float:
    if cost >= 1.0 or p_star <= cost:
        return 0.0
    return (p_star - cost) / (1.0 - cost)


def advised_stake_usd(
    *,
    p_star: float,
    cost: float,
    bankroll_usd: float,
    depth_usd: float,
    fractional: float,
    cap_fraction: float,
) -> float:
    fraction = full_kelly(p_star, cost)
    if fraction <= 0 or bankroll_usd <= 0:
        return 0.0
    return min(
        fractional * fraction * bankroll_usd,
        cap_fraction * bankroll_usd,
        max(depth_usd, 0.0),
    )
