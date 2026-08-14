# Data contracts

Plain-language definitions for the numbers this repo writes down.

## Match

A **match** is one series (Bo1 / Bo3 / Bo5), not one map.

| Field | Meaning |
|---|---|
| `start_time` | Scheduled start, UTC. Features freeze here. |
| `game_version` | `csgo` or `cs2` |
| `format` | `bo1`, `bo3`, `bo5` |
| `offline` | LAN if true, online if false |
| `score1` / `score2` | Maps won. Null until the series is over. |

A **map** row is one played map inside that series. Map-pool features for match T may only count maps from earlier matches.

## Feature as-of

Every feature row is tagged with `as_of = match.start_time`. If a computation reads a later match, that is a bug. The fixture test in `tests/features/` is the contract.

## Model probability

`p` is a calibrated P(team1 wins the series). Team1 is the Liquipedia “left” team, stored as `matches.team1_id`.

`p* = clip(p − uncertainty_haircut, 0.01, 0.99)`

The haircut is a caution buffer, not a second model. Default `0.02` in `feature_flags.yaml`.

## Polymarket contract

A YES share pays **$1** if that team wins the series, else **$0**.

We always assume we **buy the ask** (taker).

### Fees

From [Polymarket](https://docs.polymarket.com/trading/fees), checked 14 August 2026:

```text
fee_per_share = feeRate × ask × (1 − ask)
```

Sports / esports fallback: `feeRate = 0.05`. Makers pay 0. If a market object includes its own fee rate, use that.

### Net EV (per $1 of face, one share)

```text
cost = ask + fee_per_share
ev_net = p_star − cost
```

Equivalent: you pay `cost`, receive $1 with probability `p*`, else $0.

### Worked example

100 YES shares, ask `0.40`, `p* = 0.50`, sports `feeRate = 0.05`.

| Step | Number |
|---|---|
| Fee per share | `0.05 × 0.40 × 0.60 = 0.012` |
| Fee for 100 shares | `$1.20` |
| Cash outlay | `$40.00 + $1.20 = $41.20` |
| `ev_net` per share | `0.50 − 0.412 = +0.088` |
| `ev_net` on 100 shares | `+$8.80` |

That row is still not a BET until volume, spread, depth, time, identity, and sample-size gates pass.

### Kelly (advice only)

```text
full_kelly = (p_star − cost) / (1 − cost)
stake = min(
  kelly_fractional × full_kelly × bankroll,
  kelly_max_fraction_of_bankroll × bankroll,
  depth_usd
)
```

Defaults: `kelly_fractional = 0.25`, cap `0.05` of bankroll. Never larger than displayed depth near the ask.

If `p_star ≤ cost`, full Kelly is 0. We do not emit a negative “short” in v1.

## Actions

| Action | Rule |
|---|---|
| BET | High identity + sample floor + `ev_net ≥ min_ev` + all liquidity gates |
| WATCH | Market matched, but a liquidity / time / sample gate failed |
| PASS | Matched and liquid enough, but no edge |
| quarantine | Identity not high. Never BET. |

## Diagnostics

Copied from golf-model’s honesty states:

| State | Meaning |
|---|---|
| `no_market_posted_yet` | No usable CS2 series markets |
| `market_available_no_edges` | Markets exist; none are BET |
| `pipeline_error` | Ingest, match, or model failed |
| `edges_available` | At least one BET row |

## Backtest vs paper trade

- **Model quality:** accuracy, log loss, Brier, calibration vs 50/50 and Elo-only. Always reported.
- **Paper EV / CLV:** only when a historical Polymarket token is actually joined to that match. Missing prices stay missing. We do not invent a close.
