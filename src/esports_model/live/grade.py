"""Post-settle grading hook. Tracks calibration after matches finish."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import select

from esports_model.db.models import Match
from esports_model.db.session import session_scope

PENDING_NAME = "pending_grades.jsonl"
GRADES_NAME = "grades.json"


def pending_path(output_dir: str | Path) -> Path:
    return Path(output_dir) / PENDING_NAME


def grades_path(output_dir: str | Path) -> Path:
    return Path(output_dir) / GRADES_NAME


def upsert_pending(output_dir: str | Path, rows: list[dict[str, Any]]) -> Path:
    path = pending_path(output_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, dict[str, Any]] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            key = str(item.get("token_id") or "")
            if key:
                existing[key] = item
    for row in rows:
        key = str(row.get("token_id") or "")
        if not key or row.get("match_id") is None or row.get("model_p") is None:
            continue
        existing[key] = {
            "token_id": key,
            "match_id": row["match_id"],
            "team_id": row.get("team_id"),
            "side": row.get("side"),
            "model_p": row["model_p"],
            "ask": row.get("ask"),
            "action": row.get("action"),
        }
    path.write_text(
        "".join(json.dumps(item, default=str) + "\n" for item in existing.values()),
        encoding="utf-8",
    )
    return path


def grade_settled(*, database_url: str, output_dir: str | Path) -> dict[str, Any]:
    pending_file = pending_path(output_dir)
    items: list[dict[str, Any]] = []
    if pending_file.exists():
        for line in pending_file.read_text(encoding="utf-8").splitlines():
            if line.strip():
                items.append(json.loads(line))

    still_open: list[dict[str, Any]] = []
    graded: list[dict[str, Any]] = []
    with session_scope(database_url) as session:
        matches = {row.id: row for row in session.scalars(select(Match))}
        for item in items:
            match = matches.get(int(item["match_id"]))
            if match is None or match.winner_id is None or item.get("team_id") is None:
                still_open.append(item)
                continue
            won = 1 if match.winner_id == int(item["team_id"]) else 0
            model_p = float(item["model_p"])
            graded.append(
                {
                    **item,
                    "won": won,
                    "brier": (model_p - won) ** 2,
                }
            )

    pending_file.parent.mkdir(parents=True, exist_ok=True)
    pending_file.write_text(
        "".join(json.dumps(item, default=str) + "\n" for item in still_open),
        encoding="utf-8",
    )

    brier = None
    if graded:
        brier = sum(float(row["brier"]) for row in graded) / len(graded)
    report = {
        "ok": True,
        "n_graded": len(graded),
        "n_pending": len(still_open),
        "mean_brier": brier,
        "rows": graded,
    }
    target = grades_path(output_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    return report
