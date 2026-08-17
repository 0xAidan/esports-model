"""Pull books and rewrite the snapshot. Used by serve and tests."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from esports_model.config import feature_flags
from esports_model.live.predict import PredictFn
from esports_model.live.scan import run_scan
from esports_model.live.snapshot import default_snapshot_path
from esports_model.markets.pull import ClientFactory, pull_markets


def refresh_once(
    *,
    database_url: str,
    pull: bool = False,
    client_factory: ClientFactory | None = None,
    snapshot_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    predict_fn: PredictFn | None = None,
) -> dict[str, Any]:
    pull_summary = None
    if pull:
        pull_summary = pull_markets(
            database_url=database_url,
            client_factory=client_factory,
        )
    snapshot = run_scan(
        database_url=database_url,
        snapshot_path=snapshot_path or default_snapshot_path(),
        output_dir=output_dir,
        predict_fn=predict_fn,
    )
    snapshot["last_pull"] = pull_summary
    return snapshot


def start_refresh_thread(
    *,
    database_url: str,
    snapshot_path: str | Path,
    output_dir: str | Path,
    stop_event: threading.Event,
    interval_sec: float | None = None,
) -> threading.Thread:
    flags = feature_flags()
    wait = (
        interval_sec
        if interval_sec is not None
        else float(flags.get("refresh_upcoming_sec", 120))
    )

    def _loop() -> None:
        while not stop_event.wait(wait):
            try:
                refresh_once(
                    database_url=database_url,
                    pull=True,
                    snapshot_path=snapshot_path,
                    output_dir=output_dir,
                )
            except Exception:
                continue

    thread = threading.Thread(target=_loop, name="esports-refresh", daemon=True)
    thread.start()
    return thread
