"""Polymarket taker fee, haircut, and net EV. Numbers must match the docs."""

from __future__ import annotations

DEFAULT_SPORTS_FEE_RATE = 0.05


def clip_prob(value: float, low: float = 0.01, high: float = 0.99) -> float:
    return min(max(value, low), high)


def fee_per_share(ask: float, fee_rate: float = DEFAULT_SPORTS_FEE_RATE) -> float:
    return fee_rate * ask * (1.0 - ask)


def share_cost(ask: float, fee_rate: float = DEFAULT_SPORTS_FEE_RATE) -> float:
    return ask + fee_per_share(ask, fee_rate)


def haircut_prob(raw_p: float, haircut: float) -> float:
    return clip_prob(raw_p - haircut)


def ev_net(p_star: float, cost: float) -> float:
    return p_star - cost
