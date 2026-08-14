"""BET / WATCH / PASS / quarantine rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, assert_never

Action = Literal["BET", "WATCH", "PASS", "quarantine"]


@dataclass(frozen=True)
class GateInputs:
    identity_status: str
    identity_confidence: str
    match_id: int | None
    ev_net: float | None
    volume: float | None
    spread: float | None
    depth_usd: float | None
    hours_to_start: float | None
    prior_matches_min: int | None
    ask: float | None


@dataclass(frozen=True)
class GateDecision:
    action: Action
    reasons: tuple[str, ...]


def decide_action(inputs: GateInputs, flags: dict[str, object]) -> GateDecision:
    if _is_quarantine(inputs):
        return GateDecision("quarantine", ("identity",))

    liquidity = _liquidity_reasons(inputs, flags)
    if inputs.match_id is None or inputs.identity_status != "matched":
        return GateDecision("WATCH", ("no_liquipedia_match", *liquidity))
    if inputs.ask is None or inputs.ev_net is None:
        return GateDecision("WATCH", ("no_price_or_model", *liquidity))

    has_edge = inputs.ev_net >= float(flags.get("min_ev", 0.03))
    if has_edge and not liquidity:
        return GateDecision("BET", ("edge",))
    if has_edge and liquidity:
        return GateDecision("WATCH", liquidity)
    if liquidity:
        return GateDecision("WATCH", ("no_edge", *liquidity))
    return GateDecision("PASS", ("no_edge",))


def _is_quarantine(inputs: GateInputs) -> bool:
    if inputs.identity_status == "quarantine":
        return True
    return inputs.identity_confidence != "high"


def _liquidity_reasons(inputs: GateInputs, flags: dict[str, object]) -> tuple[str, ...]:
    reasons: list[str] = []
    volume = inputs.volume if inputs.volume is not None else 0.0
    if volume < float(flags.get("min_volume_usd", 5000)):
        reasons.append("volume")
    spread = inputs.spread
    if spread is None or spread > float(flags.get("max_spread", 0.06)):
        reasons.append("spread")
    depth = inputs.depth_usd if inputs.depth_usd is not None else 0.0
    if depth < float(flags.get("min_depth_usd", 200)):
        reasons.append("depth")
    hours = inputs.hours_to_start
    min_hours = float(flags.get("min_hours_to_start", 0.25))
    max_hours = float(flags.get("max_hours_to_start", 168))
    if hours is None or hours < min_hours or hours > max_hours:
        reasons.append("time_window")
    prior = inputs.prior_matches_min if inputs.prior_matches_min is not None else 0
    if prior < int(flags.get("min_prior_matches", 8)):
        reasons.append("sample")
    return tuple(reasons)


def action_rank(action: Action) -> int:
    if action == "BET":
        return 0
    if action == "WATCH":
        return 1
    if action == "PASS":
        return 2
    if action == "quarantine":
        return 3
    assert_never(action)
