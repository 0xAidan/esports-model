# About this project

## What this is

An always-on (if you leave `serve` running) CS2 research scanner.

It:

- pulls professional match history from Liquipedia,
- builds features that only use information from **before** a match starts,
- trains a simple calibrated probability model,
- compares that probability to Polymarket’s ask, after fees,
- writes a snapshot you can read in the terminal or a small web table.

## Why it exists

Sportsbook screens and Polymarket pages do not tell you whether a price is cheap **for your model**, after spread and fees. This repo does that one job, then stops.

## What this is not

- Not a magic money printer
- Not an auto-trader (no wallet, no orders, no copytrading)
- Not a six-game esports terminal
- Not a clone of the golf-model dashboard

If the model is wrong, the scanner will be wrong. If the market is efficient, you should see PASS.

## How data flows

1. Liquipedia → SQLite (matches, teams, rosters, maps)
2. Point-in-time features → model → calibrated `p`
3. Polymarket Gamma/CLOB → matched markets
4. Net EV + liquidity gates → BET / WATCH / PASS
5. Snapshot JSON → CLI table and `/`

## Intended audience

You. One operator, one laptop or small server, iterating on a model. If you do not understand a number on the scan table, the README explains it. If the README is still unclear, that is a bug in the docs.
