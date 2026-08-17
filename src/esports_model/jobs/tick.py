"""One idempotent pass: sync, pull books, train if needed, scan."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib

from esports_model.config import feature_flags, profile
from esports_model.db.session import init_db
from esports_model.ingest.sync import ClientFactory as LiquipediaFactory
from esports_model.ingest.sync import run_sync
from esports_model.live.predict import DEFAULT_MODEL_PATH
from esports_model.live.scan import run_scan
from esports_model.live.snapshot import default_snapshot_path, utc_now, write_snapshot
from esports_model.markets.pull import ClientFactory as MarketFactory
from esports_model.markets.pull import pull_markets
from esports_model.model.train import count_eligible, train_model


def run_tick(
    *,
    database_url: str,
    output_dir: str | Path | None = None,
    snapshot_path: str | Path | None = None,
    model_path: str | None = None,
    sync_liquipedia: bool = True,
    pull_books: bool = True,
    liquipedia_factory: LiquipediaFactory | None = None,
    market_factory: MarketFactory | None = None,
    predict_fn: Any = None,
) -> dict[str, Any]:
    init_db(database_url)
    flags = feature_flags()
    out_dir = Path(output_dir) if output_dir is not None else Path("output")
    snap = Path(snapshot_path) if snapshot_path is not None else default_snapshot_path()
    saved_model = model_path or str(flags.get("model_path") or DEFAULT_MODEL_PATH)
    thin_floor = int(flags.get("min_eligible_for_upcoming", 80))
    errors: list[str] = []
    sync_summary: dict[str, Any] | None = None
    pull_summary: dict[str, Any] | None = None
    train_summary: dict[str, Any] | None = None
    snapshot: dict[str, Any]
    eligible: int | None = None

    try:
        eligible = count_eligible(database_url)
        sync_profile = "upcoming"
        if eligible < thin_floor:
            sync_profile = "default"
        if sync_liquipedia:
            sync_summary = run_sync(
                profile_name=sync_profile,
                spec=profile(sync_profile),
                resume=sync_profile == "default",
                database_url=database_url,
                client_factory=liquipedia_factory,
            )
            eligible = count_eligible(database_url)
        if pull_books:
            pull_summary = pull_markets(
                database_url=database_url,
                client_factory=market_factory,
            )
        train_summary = _maybe_train(
            database_url=database_url,
            model_path=saved_model,
            eligible=eligible,
        )
        snapshot = run_scan(
            database_url=database_url,
            model_path=saved_model,
            snapshot_path=snap,
            output_dir=out_dir,
            predict_fn=predict_fn,
        )
    except Exception as exc:  # noqa: BLE001
        errors.append(str(exc))
        snapshot = {
            "ok": False,
            "implemented": True,
            "generated_at": utc_now().isoformat(timespec="seconds"),
            "database_url": database_url,
            "diagnostic": "pipeline_error",
            "diagnostic_detail": str(exc),
            "counts": {"BET": 0, "WATCH": 0, "PASS": 0, "quarantine": 0},
            "rows": [],
            "table_text": f"diagnostic: pipeline_error\n{exc}\n",
        }
        write_snapshot(snap, snapshot)

    report = {
        "ok": not errors and bool(snapshot.get("ok", True)),
        "implemented": True,
        "sync_profile": None if not sync_liquipedia else (sync_summary or {}).get("profile"),
        "sync": sync_summary,
        "last_pull": pull_summary,
        "train": train_summary,
        "eligible_matches": eligible,
        "errors": errors,
        "diagnostic": snapshot.get("diagnostic"),
        "diagnostic_detail": snapshot.get("diagnostic_detail"),
        "counts": snapshot.get("counts"),
        "snapshot_path": str(snap),
    }
    snapshot["last_pull"] = pull_summary
    snapshot["tick"] = {
        "sync_profile": report["sync_profile"],
        "train": train_summary,
        "errors": errors,
    }
    write_snapshot(snap, snapshot)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "tick.json").write_text(
        json.dumps(report, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    snapshot["tick_report"] = report
    return snapshot


def _maybe_train(
    *,
    database_url: str,
    model_path: str,
    eligible: int,
) -> dict[str, Any]:
    if eligible < 10:
        return {"trained": False, "reason": "not_enough", "n_eligible": eligible}
    path = Path(model_path)
    if path.exists():
        try:
            payload = joblib.load(path)
            stored = payload.get("n_train", 0) if isinstance(payload, dict) else 0
            if int(stored) >= eligible:
                return {
                    "trained": False,
                    "reason": "fresh",
                    "n_eligible": eligible,
                    "n_train": int(stored),
                }
        except Exception:  # noqa: BLE001
            pass
    try:
        written = train_model(
            database_url=database_url,
            output_path=model_path,
            min_prior_matches=None,
        )
    except RuntimeError as exc:
        return {"trained": False, "reason": str(exc), "n_eligible": eligible}
    return {"trained": True, "n_eligible": eligible, "path": written}
