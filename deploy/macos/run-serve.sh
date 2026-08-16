#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
mkdir -p output
if [[ ! -x .venv/bin/esports-model ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -e ".[dev]"
fi
exec .venv/bin/esports-model serve
