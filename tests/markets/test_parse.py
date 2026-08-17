from __future__ import annotations

from esports_model.markets.parse import depth_from_book, parse_event, parse_teams_from_title


def test_parse_cs2_title() -> None:
    left, right = parse_teams_from_title(
        "Counter-Strike: FURIA vs 9z (BO3) - Esports World Cup Group D"
    )
    assert left == "FURIA"
    assert right == "9z"


def test_parse_event_keeps_only_cs2_and_flags_series() -> None:
    parsed = parse_event(
        {
            "id": "1",
            "slug": "cs2-furia-9z-2026-08-15",
            "title": "Counter-Strike: FURIA vs 9z (BO3)",
            "markets": [
                {
                    "conditionId": "c1",
                    "sportsMarketType": "moneyline",
                    "groupItemTitle": "Match Winner",
                    "outcomes": ["FURIA", "9z"],
                    "clobTokenIds": ["a", "b"],
                    "bestAsk": 0.66,
                    "bestBid": 0.64,
                    "feeSchedule": {"rate": 0.05},
                }
            ],
        }
    )
    assert parsed is not None
    assert parsed.team_left == "FURIA"
    assert parsed.markets[0].is_series_winner is True
    assert parse_event({"title": "Will Bitcoin hit 200k?", "slug": "btc"}) is None


def test_depth_near_ask() -> None:
    asks = [
        {"price": "0.66", "size": "100"},
        {"price": "0.68", "size": "50"},
        {"price": "0.90", "size": "999"},
    ]
    assert depth_from_book(asks, 0.66, 0.03) == 0.66 * 100 + 0.68 * 50
