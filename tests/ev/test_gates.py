from __future__ import annotations

from esports_model.config import feature_flags
from esports_model.ev.gates import GateInputs, decide_action


def _ok(**overrides: object) -> GateInputs:
    payload = {
        "identity_status": "matched",
        "identity_confidence": "high",
        "match_id": 1,
        "ev_net": 0.10,
        "volume": 20000.0,
        "spread": 0.02,
        "depth_usd": 400.0,
        "hours_to_start": 12.0,
        "prior_matches_min": 12,
        "ask": 0.40,
    }
    payload.update(overrides)
    return GateInputs(**payload)  # type: ignore[arg-type]


def test_all_gates_pass_is_bet() -> None:
    decision = decide_action(_ok(), feature_flags())
    assert decision.action == "BET"


def test_identity_failure_never_bets() -> None:
    flags = feature_flags()
    low = decide_action(_ok(identity_confidence="low", ev_net=0.40), flags)
    assert low.action == "quarantine"
    quarantined = decide_action(_ok(identity_status="quarantine", ev_net=0.40), flags)
    assert quarantined.action == "quarantine"


def test_thin_book_is_watch() -> None:
    decision = decide_action(_ok(volume=100.0), feature_flags())
    assert decision.action == "WATCH"
    assert "volume" in decision.reasons


def test_no_edge_on_liquid_book_is_pass() -> None:
    decision = decide_action(_ok(ev_net=0.001), feature_flags())
    assert decision.action == "PASS"
