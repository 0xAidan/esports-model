"""Keep the snapshot current. The background thread runs tick."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

from esports_model.config import feature_flags
from esports_model.ingest.sync import ClientFactory as LiquipediaFactory
from esports_model.jobs.tick import run_tick
from esports_model.live.predict import PredictFn
from esports_model.live.scan import run_scan
from esports_model.live.snapshot import default_snapshot_path, utc_now, write_snapshot
from esports_model.markets.pull import ClientFactory as MarketFactory


def refresh_once(
    *,
    database_url: str,
    pull: bool = False,
    sync_liquipedia: bool = False,
    client_factory: MarketFactory | None = None,
    liquipedia_factory: LiquipediaFactory | None = None,
    snapshot_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    predict_fn: PredictFn | None = None,
) -> dict[str, Any]:
    return run_tick(
        database_url=database_url,
        output_dir=output_dir,
        snapshot_path=snapshot_path or default_snapshot_path(),
        sync_liquipedia=sync_liquipedia,
        pull_books=pull,
        liquipedia_factory=liquipedia_factory,
        market_factory=client_factory,
        predict_fn=predict_fn,
    )


def start_refresh_thread(
    *,
    database_url: str,
    snapshot_path: str | Path,
    output_dir: str | Path,
    stop_event: threading.Event,
    interval_sec: float | None = None,
    client_factory: MarketFactory | None = None,
    liquipedia_factory: LiquipediaFactory | None = None,
) -> threading.Thread:
    flags = feature_flags()
    books_wait = (
        interval_sec
        if interval_sec is not None
        else float(flags.get("refresh_upcoming_sec", 120))
    )
    schedule_wait = float(flags.get("refresh_schedule_sec", 900))

    def _loop() -> None:
        last_schedule = 0.0
        first = True
        while True:
            if not first and stop_event.wait(books_wait):
                return
            first = False
            now = time.monotonic()
            do_sync = last_schedule == 0.0 or (now - last_schedule) >= schedule_wait
            if do_sync:
                last_schedule = now
            try:
                run_tick(
                    database_url=database_url,
                    snapshot_path=snapshot_path,
                    output_dir=output_dir,
                    sync_liquipedia=do_sync,
                    pull_books=True,
                    liquipedia_factory=liquipedia_factory,
                    market_factory=client_factory,
                )
            except Exception as exc:  # noqa: BLE001
                write_snapshot(
                    snapshot_path,
                    {
                        "ok": False,
                        "implemented": True,
                        "generated_at": utc_now().isoformat(timespec="seconds"),
                        "database_url": database_url,
                        "diagnostic": "pipeline_error",
                        "diagnostic_detail": str(exc),
                        "counts": {"BET": 0, "WATCH": 0, "PASS": 0, "quarantine": 0},
                        "rows": [],
                        "table_text": f"diagnostic: pipeline_error\n{exc}\n",
                    },
                )
            if stop_event.is_set():
                return

    thread = threading.Thread(target=_loop, name="esports-refresh", daemon=True)
    thread.start()
    return thread


def scan_if_missing(
    *,
    database_url: str,
    snapshot_path: str | Path,
    output_dir: str | Path,
) -> None:
    path = Path(snapshot_path)
    if not path.exists():
        run_scan(database_url=database_url, snapshot_path=path, output_dir=output_dir)
