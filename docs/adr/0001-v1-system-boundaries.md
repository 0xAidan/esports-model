# ADR 0001 — v1 system boundaries

**Status:** accepted  
**Date:** 14 August 2026

## Context

We are building an in-house esports model in the same family as [mma-model](https://github.com/0xAidan/mma-model) and [golf-model](https://github.com/0xAidan/golf-model). Those repos already have a research culture: point-in-time features, walk-forward backtests, EV vs a real market, and honest empty states.

This repo starts empty. It is easy to accidentally build a trading bot, a six-game dashboard, or a paid-data warehouse. This ADR locks what v1 is and is not.

## Decision

v1 is a **signal and research system** for **Counter-Strike 2 series winners**, compared to **Polymarket** prices, stored in **SQLite**, operated from a **CLI** (plus a tiny snapshot page).

| In | Out |
|---|---|
| One title: CS2 | LoL / Dota / Valorant / R6 models |
| Liquipedia MediaWiki ingest | HLTV as source of truth, paid GRID/PandaScore |
| Pre-match series winner | Live round model, player props, tournament outrights as BET |
| Polymarket Gamma + CLOB | Kalshi execution, sportsbook betting, The Odds API (no esports keys) |
| Suggested fractional Kelly | Any order placement, wallet, copytrade |
| Walk-forward backtest + calibration | Fake paper PnL when we lack historical prices |
| SQLite | Postgres, Redis |
| FastAPI snapshot + small HTML table | Golf-style dashboard / autoresearch control plane |

## Why these boundaries

1. **Accuracy first.** One title with leaked-safe features beats six thin models.
2. **Liquidity second.** CS2 is the title a person can actually fill on Polymarket this week. See [title-selection-scorecard.md](../research/title-selection-scorecard.md).
3. **Honesty.** If there is no edge after fees, the scanner says PASS. Zero BET rows is a valid done state.
4. **Cost.** The free Liquipedia path works. We do not pay $99/month to skip politeness.
5. **Sister-repo fit.** Copy mma-model’s research pipeline, not golf-model’s deployment sprawl.

## Lookahead rule

Features for match T may only use information available **before match T starts**. Roster changes after T, series score while predicting the series, and post-match stats are illegal. Tests must fail the build if a fixture leaks.

## Consequences

- Identity mismatches never become bets.
- Historical Polymarket coverage will be incomplete; model metrics and paper-trade metrics stay separate.
- Adding a second title is a new ADR, not a flag flip.
- Adding Kalshi or order placement is a new ADR, and order placement is out of scope for this product family unless the user explicitly changes the product.
