"""Env settings plus YAML profiles and feature flags."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    esports_database_url: str = Field(
        default="sqlite:///data/esports.db",
        alias="ESPORTS_DATABASE_URL",
    )
    liquipedia_contact_email: str = Field(default="", alias="LIQUIPEDIA_CONTACT_EMAIL")
    liquipedia_user_agent: str = Field(default="", alias="LIQUIPEDIA_USER_AGENT")
    liquipedia_min_interval_sec: float = Field(
        default=2.0,
        alias="LIQUIPEDIA_MIN_INTERVAL_SEC",
    )
    bankroll_usd: float = Field(default=1000.0, alias="BANKROLL_USD")
    project_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[2])

    def liquipedia_headers(self) -> dict[str, str]:
        email = self.liquipedia_contact_email.strip()
        if not email or email.endswith("example.com"):
            raise RuntimeError(
                "Set LIQUIPEDIA_CONTACT_EMAIL in .env to a real address before syncing."
            )
        agent = self.liquipedia_user_agent.strip()
        if not agent:
            agent = (
                f"esports-model/0.1 (https://github.com/0xAidan/esports-model; {email})"
            )
        return {
            "User-Agent": agent,
            "Accept-Encoding": "gzip",
            "Accept": "application/json",
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings() -> None:
    get_settings.cache_clear()


def load_yaml(name: str) -> dict[str, Any]:
    path = get_settings().project_root / name
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"{name} must be a mapping")
    return loaded


def feature_flags() -> dict[str, Any]:
    return load_yaml("feature_flags.yaml")


def profile(name: str) -> dict[str, Any]:
    data = load_yaml("profiles.yaml")
    if name not in data:
        known = ", ".join(sorted(data)) or "(none)"
        raise KeyError(f"unknown profile {name!r}; known: {known}")
    row = data[name]
    if not isinstance(row, dict):
        raise ValueError(f"profile {name!r} must be a mapping")
    return row
