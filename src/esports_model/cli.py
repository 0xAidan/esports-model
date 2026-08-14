"""Command-line entry point."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from esports_model import __version__
from esports_model.config import get_settings, profile, reset_settings
from esports_model.db.session import init_db


def _add_db_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--database-url",
        default=None,
        help="Override ESPORTS_DATABASE_URL for this command",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="esports-model",
        description="CS2 prediction model and Polymarket +EV scanner (signal only).",
    )
    parser.add_argument("--version", action="version", version=f"esports-model {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init-db", help="Create or upgrade the local SQLite database")
    _add_db_flag(init)

    sync = sub.add_parser("sync", help="Download CS2 history from Liquipedia")
    _add_db_flag(sync)
    sync.add_argument("--profile", default="default", help="quick | default | full_backfill | upcoming")
    sync.add_argument("--resume", action="store_true", help="Continue from the last ingest cursor")

    train = sub.add_parser("train", help="Fit the baseline model on the local database")
    _add_db_flag(train)
    train.add_argument("--output", default="data/model_logistic.joblib")
    train.add_argument("--min-prior-matches", type=int, default=None)

    backtest = sub.add_parser("backtest", help="Walk-forward evaluation without lookahead")
    _add_db_flag(backtest)
    backtest.add_argument("--omit-predictions", action="store_true")
    backtest.add_argument("--min-train", type=int, default=80)
    backtest.add_argument("--output", default="output/backtest.json")

    markets = sub.add_parser("markets", help="Polymarket ingest")
    markets_sub = markets.add_subparsers(dest="markets_command", required=True)
    pull = markets_sub.add_parser("pull", help="Fetch upcoming CS2 markets")
    _add_db_flag(pull)

    scan = sub.add_parser("scan", help="Print model vs market with BET / WATCH / PASS")
    _add_db_flag(scan)
    scan.add_argument("--json", action="store_true")

    serve = sub.add_parser("serve", help="Snapshot API + small operator table")
    _add_db_flag(serve)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument(
        "--no-refresh",
        action="store_true",
        help="Do not pull Polymarket on a timer (HTML still loads the last snapshot)",
    )

    coverage = sub.add_parser("coverage", help="Write a match-history coverage audit")
    _add_db_flag(coverage)
    coverage.add_argument("--output", default="output/coverage.json")

    return parser


def _resolve_url(args: argparse.Namespace) -> str:
    reset_settings()
    if getattr(args, "database_url", None):
        return args.database_url
    return get_settings().esports_database_url


def cmd_init_db(args: argparse.Namespace) -> int:
    url = _resolve_url(args)
    init_db(url)
    print(f"Database ready at {url}")
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    from esports_model.ingest.sync import run_sync

    spec = profile(args.profile)
    summary = run_sync(
        profile_name=args.profile,
        spec=spec,
        resume=args.resume,
        database_url=_resolve_url(args),
    )
    print(json.dumps(summary, indent=2, default=str))
    return 0


def cmd_train(args: argparse.Namespace) -> int:
    from esports_model.model.train import train_model

    path = train_model(
        database_url=_resolve_url(args),
        output_path=args.output,
        min_prior_matches=args.min_prior_matches,
    )
    print(f"Wrote model to {path}")
    return 0


def cmd_backtest(args: argparse.Namespace) -> int:
    from esports_model.backtest.engine import run_backtest

    report = run_backtest(
        database_url=_resolve_url(args),
        min_train=args.min_train,
        omit_predictions=args.omit_predictions,
        output_path=args.output,
    )
    print(json.dumps(report, indent=2, default=str))
    return 0


def cmd_markets(args: argparse.Namespace) -> int:
    from esports_model.markets.pull import pull_markets

    summary = pull_markets(database_url=_resolve_url(args))
    print(json.dumps(summary, indent=2, default=str))
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    from esports_model.live.scan import run_scan

    snapshot = run_scan(database_url=_resolve_url(args))
    if args.json:
        print(json.dumps(snapshot, indent=2, default=str))
        return 0
    print(snapshot.get("table_text") or json.dumps(snapshot, indent=2, default=str))
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    from esports_model.api.app import create_app

    app = create_app(
        database_url=_resolve_url(args),
        enable_refresh=not args.no_refresh,
    )
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


def cmd_coverage(args: argparse.Namespace) -> int:
    from esports_model.ingest.coverage import write_coverage

    path = write_coverage(database_url=_resolve_url(args), output_path=args.output)
    print(f"Wrote coverage to {path}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    command = args.command
    if command == "init-db":
        return cmd_init_db(args)
    if command == "sync":
        return cmd_sync(args)
    if command == "train":
        return cmd_train(args)
    if command == "backtest":
        return cmd_backtest(args)
    if command == "markets":
        return cmd_markets(args)
    if command == "scan":
        return cmd_scan(args)
    if command == "serve":
        return cmd_serve(args)
    if command == "coverage":
        return cmd_coverage(args)
    never: str = command
    raise SystemExit(f"unhandled command: {never}")


if __name__ == "__main__":
    sys.exit(main())
