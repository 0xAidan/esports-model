#!/usr/bin/env python3
"""Write output/coverage.json for the local database."""

from __future__ import annotations

import argparse

from esports_model.config import get_settings
from esports_model.ingest.coverage import write_coverage


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit CS2 match coverage in SQLite")
    parser.add_argument("--output", default="output/coverage.json")
    parser.add_argument("--database-url", default=None)
    args = parser.parse_args()
    url = args.database_url or get_settings().esports_database_url
    path = write_coverage(database_url=url, output_path=args.output)
    print(path)


if __name__ == "__main__":
    main()
