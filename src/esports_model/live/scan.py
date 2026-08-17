"""Scan stub."""

from __future__ import annotations


def run_scan(*, database_url: str) -> dict[str, object]:
    return {
        "ok": True,
        "implemented": False,
        "database_url": database_url,
        "diagnostic": "pipeline_error",
        "diagnostic_detail": "Scanner is not implemented in the scaffold.",
        "rows": [],
        "table_text": "diagnostic: pipeline_error\nScanner is not implemented in the scaffold.\n",
    }
