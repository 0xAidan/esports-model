# Title selection scorecard

**Date checked:** 14 August 2026  
**Question:** which one game should v1 model?  
**Answer:** **Counter-Strike 2**. Runner-up: League of Legends.

This is not a vibe pick. Each title was scored 1–5 on the four things this product actually cares about, in this order: accuracy with free data, prediction-market liquidity, findable edge, data cost.

## How to read a score

| Score | Meaning |
|---|---|
| 5 | Best we found. You can run this week without paying. |
| 3 | Usable, with a real hole (seasonal markets, missing stats, or thin books). |
| 1 | Do not build v1 on this. |

## Scores

| Title | Accuracy (free data) | PM liquidity | Findable edge | Data cost | Total |
|---|---|---|---|---|---|
| **CS2 (primary)** | 4 | 5 | 3 | 4 | **16** |
| Dota 2 | 5 | 2 | 3 | 5 | 15 |
| League of Legends (runner-up) | 4 | 3 | 3 | 4 | 14 |
| Valorant | 3 | 3 | 3 | 3 | 12 |
| Rainbow Six Siege (wildcard) | 2 | 4 | 3 | 2 | 11 |

## What “5” would look like

| Criterion | A 5 looks like |
|---|---|
| Modelable accuracy with free data | Long public match history, stable IDs, roster/map/context features, little missingness |
| Prediction-market liquidity | Regular Polymarket (or Kalshi) markets with real volume, tight spreads, depth a person can fill |
| Findable edge | Markets that are not fully efficient: Bo1 upsets, regional gaps, roster-change lag, map pools |
| Data cost | Official or high-quality free APIs; scrape only if legal, polite, and reliable |

## Evidence, title by title

### CS2 — primary

**Liquidity (5).** On 14 August 2026 the [Polymarket esports board](https://polymarket.com/sports/esports/games) listed many CS2 series. Two Esports World Cup group matches showed about **$877K** and **$404K** volume. Lower-tier cups sat at a few hundred dollars. That is the shape we want: a liquid top and a thin tail we can filter out. Kalshi also showed CS2 as about **66%** of a **$36M** esports week in early June 2026 ([Esports.net](https://www.esports.net/news/cs2-dominates-esports-markets-kalshi)).

**Accuracy / data (4, not 5).** There is no official HLTV API. Community scrapers are often Cloudflare-blocked ([EsportsOdds writeup](https://esportsodds.gg/alternatives/hltv-api)). Paid CS2 APIs start around $99/month. We will not pay that for v1. [Liquipedia’s MediaWiki API](https://liquipedia.net/api-terms-of-use) is free if we stay polite (1 request / 2 seconds, named User-Agent, attribution). That is enough for results, scores, event tier, rosters, and map names. It is weaker than HLTV rating 2.1. A strong Elo + form + map-pool + roster model is still possible.

**Edge (3).** Big EWC / Major books are often efficient. Challenger books are mispriced more often and also fail our liquidity gates. The honest thesis is roster-change lag, map-pool mismatch, and tier gaps — proved in backtest, not assumed.

**Cost (4).** MediaWiki is free. Commercial LiquipediaDB, PandaScore, GRID, and HLTV scrape-as-primary are rejected.

### Dota 2 — close second on data, loses on markets

**Accuracy / cost (5 / 5).** [OpenDota](https://www.opendota.com/) is the best free esports API we found. If this product only cared about model quality, Dota would win.

**Liquidity (2).** The same Polymarket board on 14 August 2026 did **not** show live Dota 2 match markets. Dota liquidity is real around The International and then goes quiet. Priority 2 is “a real person could actually fill.” CS2 wins that this week.

### League of Legends — runner-up

**Accuracy / cost (4 / 4).** Leaguepedia (Liquipedia LoL wiki) plus the official Riot API. Riot’s public API is player-centric, not a pro-league dump, so pro history still comes from the wiki.

**Liquidity (3).** One LEC series (GIANTX vs Vitality) showed about **$240K** the same day. That is real. The catalog was thinner than CS2. Worlds will be liquid; off-weeks may not.

### Valorant

One VCT series showed about **$83K**. Riot has an API. Pro history and map/agent features are messier than CS2. Fine as a later title, not v1.

### Rainbow Six Siege (wildcard)

FaZe vs Geekay at Esports World Cup showed about **$598K**. Liquidity can spike. Free historical stats and identity matching are worse. Not v1.

## Locked v1 scope

| Decision | Choice | Why |
|---|---|---|
| Primary title | CS2 | Highest total. Liquidity is not close. |
| Runner-up | League of Legends | Official-ish data path and regular-region markets |
| Horizon | Pre-match only | No free live stats feed we trust |
| Market type | Series winner (Bo1/Bo3/Bo5) | Deepest books. Map/totals can sit on a watch list. |
| Tournament outrights | Not in v1 | Different model, long-dated, easy to fool yourself |

## What this does *not* mean

CS2 being first does **not** mean “CS2 is easy money.” It means: we can get history for free, and there are books a person could actually trade. If the model cannot beat a naive baseline out of sample, the scanner must say so.
