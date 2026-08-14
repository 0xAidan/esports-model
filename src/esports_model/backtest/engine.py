"""Backtest stub."""

from __future__ import annotations

import json
from pathlib import Path


def run_backtest(
    *,
    database_url: str,
    min_train: int,
    omit_predictions: bool,
    output_path: str,
) -> dict[str, object]:
    report = {
        "ok": True,
        "implemented": False,
        "database_url": database_url,
        "min_train": min_train,
        "omit_predictions": omit_predictions,
        "message": "Walk-forward backtest lands after features are built.",
    }
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report
