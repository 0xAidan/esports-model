# Data sources

**Date checked:** 14 August 2026  
**Goal:** cheap or free data that is good enough to train an honest CS2 model.

We only ingest what we can defend. If a source needs a paid key, it is out of v1 unless the free path fails and the cost is tiny. The free path did not fail.

## What we use in v1

### Liquipedia MediaWiki API (Counter-Strike wiki) — primary stats + schedule

- **URL:** `https://liquipedia.net/counterstrike/api.php`
- **Cost:** free
- **Gives us:** tournaments, match results, scores, map names, event tier, team pages, rosters, upcoming matches
- **Does not give us:** HLTV rating, detailed per-round stats
- **Rules we follow** ([API terms](https://liquipedia.net/api-terms-of-use)):
  - at most **1 request every 2 seconds**
  - `action=parse` at most **1 request every 30 seconds**
  - custom User-Agent that names this project and a real contact email
  - accept gzip
  - cache results; do not refetch the same page
  - attribute Liquipedia (content is CC-BY-SA 3.0)

We do **not** use the commercial LiquipediaDB / `api.liquipedia.net` REST product. That one is enterprise / limited free and is a different contract.

v1 reads tournament **wikitext** through `action=query&prop=revisions` (1 request / 2 seconds) and parses `{{Infobox league}}` plus `{{Match}}` templates. We do not scrape generated HTML pages — Liquipedia forbids automated access to non-API endpoints. The old “upcoming matches” page is a Lua widget, so upcoming rows come from `Category:Live Tournaments` instead.

Set `LIQUIPEDIA_CONTACT_EMAIL` in `.env`. The client will refuse to run without it.

### Polymarket Gamma + CLOB — primary market

- **Gamma:** market metadata, volume, event titles, team names, end dates
- **CLOB:** best bid/ask, spread, depth, trades
- **History:** `GET https://clob.polymarket.com/prices-history` when we have a token id
- **Cost:** free, no API key
- **Docs:** [docs.polymarket.com](https://docs.polymarket.com/)

See [prediction-markets.md](prediction-markets.md) for fees and “actionable” rules.

## What we evaluated and rejected for v1

| Source | Why it looked good | Why it is out |
|---|---|---|
| HLTV scrape / unofficial HLTV APIs | Best CS stats culture | No official API; scrapers often Cloudflare-blocked; ToS risk |
| LiquipediaDB commercial REST | Clean JSON | Enterprise / not a free production feed |
| PandaScore | Clean esports API | Paid per game; free tier too small |
| GRID / Abios | Operator-grade | Paid, sales-led |
| EsportsOdds | CS2 JSON API | About $99/month |
| GGScore | “Free CS2 API” | Free tier is a handful of requests per day |
| FACEIT / Steam | Official-ish | FACEIT is not the pro circuit we are pricing |
| OpenDota / STRATZ | Excellent | Dota only |
| Riot Games API | Official, free key | LoL/Valorant; not CS2. Keep in mind for the runner-up. |
| The Odds API | Used by golf-model and mma-model | [Published sports list](https://the-odds-api.com/sports-odds-data/sports-apis.html) has **no esports keys** as of 14 August 2026 |
| Kalshi | Real CS2 volume | Optional later. v1 market is Polymarket. |

## Identity matching (names will not line up)

The same team will show up as:

- `Natus Vincere` on Liquipedia
- `NAVI` or `NaVi` on Polymarket
- `ex-MANA eSports` after a roster/org change

v1 has an explicit matcher plus a manual alias file. Unmatched markets go to a quarantine list. They **never** become BET rows.

## Attribution

Match history in this project is derived from Liquipedia and is used under [CC-BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/). When you publish numbers that came from the wiki, credit Liquipedia.
