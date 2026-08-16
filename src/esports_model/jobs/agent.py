"""Install a macOS login agent that keeps serve running."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from esports_model.config import get_settings

LABEL = "com.0xaidan.esports-model.serve"
PLIST_NAME = f"{LABEL}.plist"


def render_plist(project_root: Path) -> str:
    root = project_root.resolve()
    script = root / "deploy" / "macos" / "run-serve.sh"
    log = root / "output" / "serve.log"
    err = root / "output" / "serve.err.log"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>{LABEL}</string>
  <key>WorkingDirectory</key>
  <string>{root}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>{script}</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>{log}</string>
  <key>StandardErrorPath</key>
  <string>{err}</string>
</dict>
</plist>
"""


def install_agent(
    *,
    project_root: Path | None = None,
    home: Path | None = None,
    load: bool = True,
) -> dict[str, Any]:
    root = (project_root or get_settings().project_root).resolve()
    (root / "output").mkdir(parents=True, exist_ok=True)
    script = root / "deploy" / "macos" / "run-serve.sh"
    if not script.exists():
        raise RuntimeError(f"Missing {script}")
    script.chmod(script.stat().st_mode | 0o111)
    dest_dir = (home or Path.home()) / "Library" / "LaunchAgents"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / PLIST_NAME
    dest.write_text(render_plist(root), encoding="utf-8")
    loaded = False
    load_error = None
    if load:
        try:
            subprocess.run(
                ["launchctl", "unload", str(dest)],
                capture_output=True,
                check=False,
            )
            result = subprocess.run(
                ["launchctl", "load", str(dest)],
                capture_output=True,
                text=True,
                check=False,
            )
            loaded = result.returncode == 0
            if not loaded:
                load_error = (result.stderr or result.stdout or "").strip()
        except OSError as exc:
            load_error = str(exc)
    return {
        "ok": True,
        "plist_path": str(dest),
        "loaded": loaded,
        "load_error": load_error,
        "message": (
            "Login agent installed. Keep this Mac awake while plugged in. "
            "Open http://127.0.0.1:8000"
        ),
    }
