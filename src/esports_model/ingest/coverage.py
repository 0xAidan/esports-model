"""Coverage audit stub."""

from __future__ import annotations

import json
from pathlib import Path


def write_coverage(*, database_url: str, output_path: str) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ok": True,
        "implemented": False,
        "database_url": database_url,
        "match_count": 0,
        "message": "Coverage audit lands with the Liquipedia ETL.",
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return str(path)
