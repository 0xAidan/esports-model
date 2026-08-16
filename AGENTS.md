# Agent / contributor notes

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Set a real `LIQUIPEDIA_CONTACT_EMAIL` before any live `sync`.

## Tests

```bash
pytest -q
ruff check .
```

CI runs both on every push and pull request.

Live Liquipedia / Polymarket calls are **not** required for pytest. Parsers and the matcher use fixtures under `tests/fixtures/`.

## Commands that must keep working

```bash
esports-model bootstrap
esports-model tick
esports-model init-db
esports-model sync --profile quick
esports-model backtest --omit-predictions
esports-model markets pull
esports-model scan
```

`sync` and `markets pull` talk to the network. Tests should pass without them.

## Rules that are easy to break

- No lookahead. Features for match T use only rows with `start_time < T`.
- Unmatched markets never become BET.
- Do not commit `.env`, `data/*.db`, or scraped dumps.
- Do not add wallet keys or order-placement code.
- Talk to beginners in README / ABOUT / research docs. Do not talk that way in code.

## Layout

```text
src/esports_model/
  cli.py
  db/           SQLite models + Alembic helpers
  ingest/       Liquipedia
  identity/     team name matching
  features/     point-in-time builder
  model/        train + calibrate
  backtest/     walk-forward
  markets/      Polymarket
  ev/           fees, EV, Kelly
  live/         refresh + snapshot
  jobs/         tick, bootstrap, macOS agent
  api/          FastAPI
```
