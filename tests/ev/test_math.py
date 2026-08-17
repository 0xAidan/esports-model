from __future__ import annotations

from esports_model.ev.kelly import advised_stake_usd, full_kelly
from esports_model.ev.math import ev_net, fee_per_share, haircut_prob, share_cost


def test_docs_worked_example() -> None:
    fee = fee_per_share(0.40, 0.05)
    cost = share_cost(0.40, 0.05)
    edge = ev_net(0.50, cost)
    assert abs(fee - 0.012) < 1e-12
    assert abs(cost - 0.412) < 1e-12
    assert abs(edge - 0.088) < 1e-12
    assert abs(fee * 100 - 1.20) < 1e-12


def test_kelly_zero_without_edge() -> None:
    assert full_kelly(0.40, 0.412) == 0.0
    assert advised_stake_usd(
        p_star=0.40,
        cost=0.412,
        bankroll_usd=1000,
        depth_usd=500,
        fractional=0.25,
        cap_fraction=0.05,
    ) == 0.0


def test_kelly_capped_by_fraction_and_depth() -> None:
    cost = share_cost(0.40, 0.05)
    p_star = haircut_prob(0.50, 0.0)
    fraction = full_kelly(p_star, cost)
    assert abs(fraction - (0.088 / 0.588)) < 1e-9
    stake = advised_stake_usd(
        p_star=p_star,
        cost=cost,
        bankroll_usd=1000,
        depth_usd=20,
        fractional=0.25,
        cap_fraction=0.05,
    )
    assert stake == 20
