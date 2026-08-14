# Prediction markets

**Date checked:** 14 August 2026  
**Primary venue:** Polymarket (free Gamma + CLOB APIs)  
**Not in v1:** Kalshi trading, sportsbook auto-betting, any wallet or order placement

Prediction-market EV is not sportsbook EV. You buy the **ask**. You pay a **taker fee** on sports/esports. Thin books lie about how much you can actually fill.

## What is live right now

On 14 August 2026, [Polymarket’s esports board](https://polymarket.com/sports/esports/games) showed:

| Title | Example | About |
|---|---|---|
| CS2 | PARIVISION vs 100 Thieves (EWC) | ~$877K volume |
| CS2 | K27 vs MIBR (EWC) | ~$404K volume |
| CS2 | many Challenger / qualifier series | $5 to a few thousand |
| LoL | GIANTX vs Vitality (LEC) | ~$240K |
| Valorant | Joblife vs Fnatic (VCT) | ~$83K |
| Rainbow Six | FaZe vs Geekay (EWC) | ~$598K |
| Dota 2 | — | not on the live board that day |

That is why CS2 is the v1 title. It is also why the scanner must hide thin Challenger books behind WATCH.

Kalshi has real esports volume (CS2-heavy in June 2026). It is documented as a **v1.1** candidate, not built.

## How we ingest (v1)

`esports-model markets pull` searches Gamma (`public-search` for Counter-Strike / CS2) and stores **series winner** books only (`sportsMarketType = moneyline` or `groupItemTitle = Match Winner`). Map winners are parsed so we can ignore them on purpose. Depth comes from the CLOB book around the Gamma ask. Team names go through the identity matcher; unmatched events land in `identity_reviews` and stay quarantined.

## Fees (do not guess)

Official formula from [Polymarket fees](https://docs.polymarket.com/trading/fees):

```text
fee = C × feeRate × p × (1 − p)
```

- `C` = number of shares
- `p` = price of the share (0–1)
- **Makers pay 0.** We assume we are takers (we lift the ask).
- Sports category **taker `feeRate = 0.05`**. Esports is treated as sports unless a market’s own details say otherwise.
- At 50¢, 100 sports shares cost **$1.25** in fees (official table).
- Geopolitics is fee-free. That does **not** apply to esports.

The code reads `feeRate` from market details when present, and falls back to `0.05`. If Polymarket changes the schedule, update `docs/data-contracts.md` and the fallback constant together.

## What “actionable” means here

A row is **BET** only if every gate passes:

1. Identity match confidence = **high**
2. Model sample size ≥ `min_prior_matches`
3. Net EV after fees and uncertainty haircut ≥ `min_ev`
4. 24h or lifetime volume ≥ `min_volume_usd`
5. Bid/ask spread ≤ `max_spread`
6. Book depth within `depth_cents` of the ask ≥ `min_depth_usd`
7. Match start inside the configured time window

Fail liquidity → **WATCH** (you can look; we will not tell you to click).  
Fail identity → **quarantine** (not a bet, not a watch recommendation).  
Fail edge → **PASS**.

A market that dies in four minutes is not the same as one that opens in two days. The time window exists on purpose.

## Historical prices and honesty

Polymarket exposes `/prices-history` per token. We will use it when we can attach a token to a Liquipedia match.

If that join is incomplete — and it will be, at first — we **backtest model quality** (Brier, log loss, calibration) separately from **paper trading quality**. We will not invent a closing line.

## The Odds API

Sister repos use The Odds API for sportsbooks. As of 14 August 2026 its [sports list](https://the-odds-api.com/sports-odds-data/sports-apis.html) has **no CS2 / LoL / Dota / Valorant keys**. v1 does not take an `ODDS_API_KEY`. Revisit if they add esports.

## What this product will never do

- Hold a wallet key
- Place, cancel, or copy an order
- Tell you a BET is “guaranteed”
- Show a BET on an unmatched or illiquid market
