# Esports Model

A local CS2 prediction model that compares its probabilities to **Polymarket** prices and tells you whether a market looks cheap after fees.

It does **not** place bets. It does **not** print money. Some days every row will say PASS. That is a valid result.

Sister projects: [mma-model](https://github.com/0xAidan/mma-model), [golf-model](https://github.com/0xAidan/golf-model).

## What you need

- Python 3.11 or newer
- A real email address (Liquipedia requires one in the User-Agent)
- Optional: about 10–30 minutes for the first `quick` sync

You do **not** need a Polymarket API key. You do **not** need Postgres. You do **not** need The Odds API (it has no esports sports keys right now).

## Install and run

If `git config user.email` is a real address (not `example.com`):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
esports-model bootstrap
esports-model install-agent
```

Then open `http://127.0.0.1:8000`. Leave this Mac awake while it is plugged in. History fills across ticks (Liquipedia allows one request every 2 seconds, so a full library takes hours). You do not type sync / train / pull / scan again.

If git has no real email, put one line in `.env` once:

```text
LIQUIPEDIA_CONTACT_EMAIL=you@your-real-domain.com
```

Then run `esports-model bootstrap` again. We cannot invent that address. Liquipedia requires it.

Manual one-shot commands still work:

```bash
esports-model tick
esports-model scan
```

What each command does:

| Command | Meaning |
|---|---|
| `bootstrap` | Writes `.env` from git email and creates the database |
| `install-agent` | Starts `serve` at login on this Mac |
| `tick` | One pass: Liquipedia sync, Polymarket pull, train if needed, scan |
| `init-db` | Creates a local SQLite file at `data/esports.db` |
| `sync --profile quick` | Downloads a small recent slice of CS2 matches from Liquipedia |
| `backtest` | Walks through history in time order and scores the model |
| `markets pull` | Fetches current Polymarket CS2 markets |
| `scan` | Prints model p vs market p, net EV, and BET / WATCH / PASS |
| `serve` | Tiny table at `http://127.0.0.1:8000` (also what the login agent runs) |

The page rebuilds the table from `/snapshot.json` on a timer. **Refresh markets** runs a full tick. Use `serve --no-refresh` if you only want to look at the last file.

### Leave the Mac on

System Settings → Energy (or Battery): turn on **Prevent automatic sleeping when the display is off** while the laptop is plugged in. The login agent restarts `serve` after reboot, but a sleeping Mac cannot fetch new matches.

## How to read the scan table

| Column | Meaning |
|---|---|
| **model p** | Our calibrated chance the named side wins the series |
| **market p** | Polymarket ask (what you would actually pay) |
| **net EV** | Expected value per $1 of contract after fees and a caution haircut |
| **volume / spread / depth** | Can a real person fill this? |
| **action** | BET, WATCH, or PASS |
| **stake** | Suggested size as a fraction of your bankroll. Advice only. |

- **BET** — every gate passed. Still not a promise.
- **WATCH** — interesting or listed, but liquidity / time / sample size failed.
- **PASS** — no edge after costs, or the model is not confident.

If the table is empty, read the **diagnostic** line:

| Diagnostic | Meaning |
|---|---|
| `no_market_posted_yet` | Pipeline ran. Polymarket has no CS2 series we can use. |
| `market_available_no_edges` | Markets exist. None passed EV + liquidity gates. |
| `pipeline_error` | Something broke. See the error text. |
| `edges_available` | At least one BET row should be visible. |

## Keys and cost

| Item | Required? | How to get it |
|---|---|---|
| `LIQUIPEDIA_CONTACT_EMAIL` | Yes | Your email. Liquipedia uses it if the bot misbehaves. |
| Polymarket key | No | Public APIs |
| `ODDS_API_KEY` | Unused | The Odds API does not list esports as of 14 Aug 2026 |
| Paid CS2 data | No | Rejected for v1 |

Liquipedia data is [CC-BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/). Credit Liquipedia if you republish match history.

## Profiles

| Profile | Use when |
|---|---|
| `quick` | First run / CI-sized smoke |
| `default` | Normal research (~18 months S/A) |
| `full_backfill` | Overnight history. Safe to re-run; it resumes. |
| `upcoming` | Refresh the schedule only |

## Docs

- [ABOUT.md](ABOUT.md) — what this is and is not
- [AGENTS.md](AGENTS.md) — how to run tests
- [Title scorecard](docs/research/title-selection-scorecard.md) — why CS2
- [Data sources](docs/research/data-sources.md)
- [Prediction markets](docs/research/prediction-markets.md)
- [System boundaries](docs/adr/0001-v1-system-boundaries.md)
- [Data contracts / EV math](docs/data-contracts.md)

## Legal / honesty

This is research software. Esports betting and prediction markets are regulated where you live. Nothing here is financial advice. Past Brier scores do not mean future profit.
