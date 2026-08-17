"""Train stub."""

from __future__ import annotations

from pathlib import Path


def train_model(
    *,
    database_url: str,
    output_path: str,
    min_prior_matches: int | None,
) -> str:
    del database_url, min_prior_matches
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not-implemented\n", encoding="utf-8")
    return str(path)
