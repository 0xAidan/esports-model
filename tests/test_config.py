from __future__ import annotations

import pytest

from esports_model.config import feature_flags, profile


def test_profiles_exist() -> None:
    for name in ("quick", "default", "full_backfill", "upcoming"):
        spec = profile(name)
        assert "tiers" in spec


def test_feature_flags_have_gates() -> None:
    flags = feature_flags()
    assert flags["kelly_fractional"] == 0.25
    assert flags["bankroll_usd"] == 1000
    assert flags["refresh_schedule_sec"] == 900
    assert flags["min_eligible_for_upcoming"] == 80
    assert flags["min_ev"] > 0
    assert flags["min_volume_usd"] > 0
    assert flags["max_spread"] > 0


def test_unknown_profile() -> None:
    with pytest.raises(KeyError):
        profile("nope")
