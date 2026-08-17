"""Create .env and the database without hitting the live wiki."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from esports_model.config import get_settings, reset_settings
from esports_model.db.session import init_db

EmailFn = Callable[[], str]


def is_real_email(email: str) -> bool:
    cleaned = email.strip()
    if not cleaned or "@" not in cleaned:
        return False
    return not cleaned.lower().endswith("example.com")


def read_git_email(cwd: Path | None = None) -> str:
    try:
        result = subprocess.run(
            ["git", "config", "user.email"],
            capture_output=True,
            text=True,
            check=False,
            cwd=cwd,
        )
    except OSError:
        return ""
    return (result.stdout or "").strip()


def run_bootstrap(
    *,
    project_root: Path | None = None,
    database_url: str | None = None,
    git_email_fn: EmailFn | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    root = project_root or settings.project_root
    example = root / ".env.example"
    if not example.exists():
        example = settings.project_root / ".env.example"
    env_path = root / ".env"
    existing = ""
    if env_path.exists():
        existing = env_path.read_text(encoding="utf-8")
    current = _env_value(existing, "LIQUIPEDIA_CONTACT_EMAIL")
    if is_real_email(current):
        email = current.strip()
        source = "env"
    else:
        getter = git_email_fn or (lambda: read_git_email(root))
        email = getter().strip()
        source = "git"
        if not is_real_email(email):
            raise RuntimeError(
                "Need a real LIQUIPEDIA_CONTACT_EMAIL. "
                "Set git config user.email or put one line in .env. "
                "example.com addresses are rejected."
            )
    if not env_path.exists():
        if not example.exists():
            raise RuntimeError(f"Missing {example}")
        env_path.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
        existing = env_path.read_text(encoding="utf-8")
    text = _upsert_env(existing, "LIQUIPEDIA_CONTACT_EMAIL", email)
    agent = (
        f"esports-model/0.1 (https://github.com/0xAidan/esports-model; {email})"
    )
    text = _upsert_env(text, "LIQUIPEDIA_USER_AGENT", agent)
    env_path.write_text(text, encoding="utf-8")
    reset_settings()
    url = database_url or get_settings().esports_database_url
    init_db(url)
    return {
        "ok": True,
        "env_path": str(env_path),
        "email_source": source,
        "database_url": url,
        "message": "Database ready. Live wiki sync is not started by bootstrap.",
    }


def _env_value(text: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}=(.*)$", text, flags=re.M)
    if not match:
        return ""
    return match.group(1).strip()


def _upsert_env(text: str, key: str, value: str) -> str:
    pattern = re.compile(rf"^{re.escape(key)}=.*$", flags=re.M)
    line = f"{key}={value}"
    if pattern.search(text):
        return pattern.sub(line, text)
    if text and not text.endswith("\n"):
        text += "\n"
    return text + line + "\n"
