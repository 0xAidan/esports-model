"""Match Polymarket team strings to Liquipedia teams."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from esports_model.db.models import Team
from esports_model.identity.normalize import normalize_name, tokens

Confidence = Literal["high", "medium", "low"]


@dataclass(frozen=True)
class NameMatch:
    team_id: int | None
    liquipedia_page: str | None
    query: str
    normalized: str
    confidence: Confidence
    score: float
    via: str


@lru_cache
def load_aliases() -> dict[str, set[str]]:
    path = Path(__file__).with_name("aliases.yaml")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    mapping: dict[str, set[str]] = {}
    if not isinstance(raw, dict):
        return mapping
    for slug, names in raw.items():
        bucket = {normalize_name(str(slug))}
        if isinstance(names, list):
            bucket.update(normalize_name(str(item)) for item in names)
        mapping[str(slug).lower()] = {item for item in bucket if item}
    return mapping


def _team_keys(team: Team) -> set[str]:
    keys = {
        normalize_name(team.liquipedia_page),
        normalize_name(team.name),
        normalize_name(team.short_name or ""),
    }
    keys.discard("")
    return keys


def _db_name_index(teams: list[Team]) -> dict[str, Team]:
    index: dict[str, Team] = {}
    for team in teams:
        for key in _team_keys(team):
            index.setdefault(key, team)
    return index


def _alias_slug(normalized: str) -> str | None:
    for slug, names in load_aliases().items():
        if normalized in names or normalized == slug:
            return slug
    return None


def match_team_name(session: Session, raw: str) -> NameMatch:
    normalized = normalize_name(raw)
    if not normalized:
        return NameMatch(None, None, raw, normalized, "low", 0.0, "empty")

    teams = list(session.scalars(select(Team)))
    by_key = _db_name_index(teams)
    hit = by_key.get(normalized)
    if hit is not None:
        return NameMatch(hit.id, hit.liquipedia_page, raw, normalized, "high", 1.0, "db")

    alias_slug = _alias_slug(normalized)
    if alias_slug:
        for team in teams:
            if team.liquipedia_page == alias_slug or normalize_name(team.name) == alias_slug:
                return NameMatch(team.id, team.liquipedia_page, raw, normalized, "high", 1.0, "alias")

    best: NameMatch | None = None
    for team in teams:
        candidates = _team_keys(team)
        for candidate in candidates:
            if candidate == normalized:
                return NameMatch(team.id, team.liquipedia_page, raw, normalized, "high", 1.0, "exact")
            ratio = SequenceMatcher(None, normalized, candidate).ratio()
            overlap = tokens(normalized) & tokens(candidate)
            if overlap and min(len(tokens(normalized)), len(tokens(candidate))) == len(overlap):
                ratio = max(ratio, 0.93)
            if best is None or ratio > best.score:
                confidence: Confidence = "low"
                if ratio >= 0.92:
                    confidence = "high"
                elif ratio >= 0.8:
                    confidence = "medium"
                best = NameMatch(
                    team.id,
                    team.liquipedia_page,
                    raw,
                    normalized,
                    confidence,
                    ratio,
                    "fuzzy",
                )
    if best is None:
        return NameMatch(None, None, raw, normalized, "low", 0.0, "unmatched")
    return best


def pair_confidence(left: NameMatch, right: NameMatch) -> Confidence:
    if left.team_id is None or right.team_id is None or left.team_id == right.team_id:
        return "low"
    ranks = {"low": 0, "medium": 1, "high": 2}
    worst = min(ranks[left.confidence], ranks[right.confidence])
    if worst >= 2:
        return "high"
    if worst >= 1:
        return "medium"
    return "low"
