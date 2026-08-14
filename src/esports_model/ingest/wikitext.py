"""Parse Liquipedia tournament wikitext into structured rows."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from dateutil import parser as date_parser

TZ_OFFSETS: dict[str, int] = {
    "UTC": 0,
    "GMT": 0,
    "CEST": 2,
    "CET": 1,
    "EEST": 3,
    "EET": 2,
    "BST": 1,
    "EDT": -4,
    "EST": -5,
    "CDT": -5,
    "CST": -6,
    "PDT": -7,
    "PST": -8,
    "MSK": 3,
    "SGT": 8,
    "KST": 9,
    "JST": 9,
    "AEST": 10,
    "AEDT": 11,
    "BRT": -3,
    "BRST": -2,
}


@dataclass(frozen=True)
class ParsedMap:
    map_name: str
    map_number: int
    team1_score: int | None
    team2_score: int | None
    skipped: bool


@dataclass(frozen=True)
class ParsedMatch:
    team1_slug: str
    team2_slug: str
    start_time: datetime | None
    finished: bool
    maps: tuple[ParsedMap, ...]
    hltv_id: str | None
    score1: int | None
    score2: int | None
    format: str | None

    @property
    def winner_side(self) -> int | None:
        if self.score1 is None or self.score2 is None:
            return None
        if self.score1 > self.score2:
            return 1
        if self.score2 > self.score1:
            return 2
        return None


@dataclass
class ParsedEvent:
    name: str
    tier: str | None
    start_date: str | None
    end_date: str | None
    game_version: str
    offline: bool | None
    location: str | None
    matches: list[ParsedMatch] = field(default_factory=list)


def extract_templates(source: str, name: str) -> list[str]:
    token = "{{" + name
    found: list[str] = []
    start = 0
    while True:
        index = source.find(token, start)
        if index < 0:
            return found
        end = _matching_braces(source, index)
        if end < 0:
            return found
        found.append(source[index:end])
        start = index + 2


def _matching_braces(source: str, start: int) -> int:
    depth = 0
    index = start
    length = len(source)
    while index < length:
        if source.startswith("{{", index):
            depth += 1
            index += 2
            continue
        if source.startswith("}}", index):
            depth -= 1
            index += 2
            if depth == 0:
                return index
            continue
        index += 1
    return -1


def parse_template(raw: str) -> tuple[str, list[str], dict[str, str]]:
    inner = raw.strip()
    if inner.startswith("{{"):
        inner = inner[2:]
    if inner.endswith("}}"):
        inner = inner[:-2]
    parts = _split_top_level(inner, "|")
    if not parts:
        return "", [], {}
    name = parts[0].strip()
    positionals: list[str] = []
    kwargs: dict[str, str] = {}
    for part in parts[1:]:
        if "=" in part:
            key, value = part.split("=", 1)
            kwargs[key.strip().lower()] = value.strip()
        else:
            positionals.append(part.strip())
    return name, positionals, kwargs


def _split_top_level(source: str, sep: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    depth = 0
    index = 0
    while index < len(source):
        if source.startswith("{{", index):
            depth += 1
            buf.append("{{")
            index += 2
            continue
        if source.startswith("}}", index):
            depth = max(0, depth - 1)
            buf.append("}}")
            index += 2
            continue
        char = source[index]
        if char == sep and depth == 0:
            parts.append("".join(buf))
            buf = []
            index += 1
            continue
        buf.append(char)
        index += 1
    parts.append("".join(buf))
    return parts


def _clean_comment(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def normalize_tier(raw: str | None) -> str | None:
    if not raw:
        return None
    compact = raw.strip().replace(" ", "").replace("_", "-")
    lowered = compact.lower()
    if lowered.startswith("s"):
        return "S-Tier"
    if lowered.startswith("a"):
        return "A-Tier"
    if lowered.startswith("b"):
        return "B-Tier"
    if lowered.startswith("c"):
        return "C-Tier"
    return compact


def normalize_game(raw: str | None) -> str:
    value = (raw or "cs2").strip().lower()
    if value in {"csgo", "cs:go", "counter-strike: global offensive"}:
        return "csgo"
    return "cs2"


def parse_infobox(source: str) -> dict[str, str]:
    boxes = extract_templates(source, "Infobox league")
    if not boxes:
        boxes = extract_templates(source, "Infobox League")
    if not boxes:
        return {}
    _, _, kwargs = parse_template(boxes[0])
    return kwargs


def parse_match_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    cleaned = _clean_comment(raw)
    cleaned = re.sub(r"\{\{[^}]+\}\}", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -")
    if not cleaned:
        return None
    tz_name = None
    for name in TZ_OFFSETS:
        if re.search(rf"\b{name}\b", cleaned, flags=re.I):
            tz_name = name
            cleaned = re.sub(rf"\b{name}\b", "", cleaned, flags=re.I).strip(" -")
            break
    try:
        parsed = date_parser.parse(cleaned, fuzzy=True)
    except (ValueError, OverflowError, TypeError):
        return None
    if parsed.tzinfo is None:
        hours = TZ_OFFSETS.get(tz_name or "UTC", 0)
        parsed = parsed.replace(tzinfo=timezone(timedelta(hours=hours)))
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


def _int_or_none(raw: str | None) -> int | None:
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _parse_team_opponent(raw: str | None) -> tuple[str | None, int | None]:
    if not raw:
        return None, None
    _, positionals, kwargs = parse_template(raw)
    slug = (positionals[0] if positionals else kwargs.get("team") or kwargs.get("name") or "").strip()
    if not slug:
        return None, None
    return slug.lower(), _int_or_none(kwargs.get("score"))


def _parse_map(raw: str, number: int) -> ParsedMap | None:
    _, _, kwargs = parse_template(raw)
    skipped = kwargs.get("finished", "").lower() == "skip"
    name = (kwargs.get("map") or "").strip()
    t1 = _sum_rounds(kwargs.get("t1t"), kwargs.get("t1ct"), kwargs.get("score1"))
    t2 = _sum_rounds(kwargs.get("t2t"), kwargs.get("t2ct"), kwargs.get("score2"))
    if skipped or (not name and t1 is None and t2 is None):
        return ParsedMap("", number, None, None, True)
    return ParsedMap(name or f"map{number}", number, t1, t2, False)


def _sum_rounds(*parts: str | None) -> int | None:
    values = [_int_or_none(part) for part in parts]
    present = [value for value in values if value is not None]
    if not present:
        return None
    # Prefer explicit score1/score2 when half-scores are missing.
    if values[-1] is not None and values[0] is None and values[1] is None:
        return values[-1]
    halves = [value for value in values[:2] if value is not None]
    if halves:
        return sum(halves)
    return values[-1]


def parse_match(raw: str) -> ParsedMatch | None:
    _, _, kwargs = parse_template(raw)
    team1, series1 = _parse_team_opponent(kwargs.get("opponent1"))
    team2, series2 = _parse_team_opponent(kwargs.get("opponent2"))
    if not team1 or not team2:
        return None
    maps: list[ParsedMap] = []
    for index in range(1, 8):
        blob = kwargs.get(f"map{index}")
        if not blob:
            continue
        parsed_map = _parse_map(blob, index)
        if parsed_map is not None and not parsed_map.skipped:
            maps.append(parsed_map)
    finished = kwargs.get("finished", "").lower() == "true"
    if series1 is None or series2 is None:
        series1, series2 = _scores_from_maps(maps)
    fmt = _infer_format(kwargs, maps)
    return ParsedMatch(
        team1_slug=team1,
        team2_slug=team2,
        start_time=parse_match_date(kwargs.get("date")),
        finished=finished,
        maps=tuple(maps),
        hltv_id=(kwargs.get("hltv") or None),
        score1=series1,
        score2=series2,
        format=fmt,
    )


def _scores_from_maps(maps: list[ParsedMap]) -> tuple[int | None, int | None]:
    played = [
        item
        for item in maps
        if item.team1_score is not None and item.team2_score is not None
    ]
    if not played:
        return None, None
    wins1 = sum(1 for item in played if item.team1_score > item.team2_score)
    wins2 = sum(1 for item in played if item.team2_score > item.team1_score)
    return wins1, wins2


def _infer_format(kwargs: dict[str, str], maps: list[ParsedMap]) -> str | None:
    raw = (kwargs.get("bestof") or kwargs.get("bo") or "").lower()
    if raw in {"1", "bo1"}:
        return "bo1"
    if raw in {"3", "bo3"}:
        return "bo3"
    if raw in {"5", "bo5"}:
        return "bo5"
    slots = sum(1 for index in range(1, 8) if kwargs.get(f"map{index}"))
    if slots >= 5:
        return "bo5"
    if slots >= 2:
        return "bo3"
    if maps:
        return "bo1"
    return None


def parse_event_page(title: str, source: str) -> ParsedEvent:
    text = _clean_comment(source)
    info = parse_infobox(text)
    location_parts = [info.get("city"), info.get("country")]
    location = ", ".join(part for part in location_parts if part) or None
    offline = None
    kind = (info.get("type") or "").lower()
    if kind == "offline":
        offline = True
    elif kind == "online":
        offline = False
    event = ParsedEvent(
        name=info.get("name") or title,
        tier=normalize_tier(info.get("liquipediatier") or info.get("tier")),
        start_date=info.get("sdate") or None,
        end_date=info.get("edate") or None,
        game_version=normalize_game(info.get("game")),
        offline=offline,
        location=location,
    )
    for blob in extract_templates(text, "Match"):
        parsed = parse_match(blob)
        if parsed is not None:
            event.matches.append(parsed)
    return event


def match_id(event_page: str, match: ParsedMatch) -> str:
    if match.hltv_id:
        return f"hltv:{match.hltv_id}"
    stamp = match.start_time.isoformat() if match.start_time else "undated"
    return f"{event_page}:{match.team1_slug}:{match.team2_slug}:{stamp}"


def event_to_dict(event: ParsedEvent) -> dict[str, Any]:
    return {
        "name": event.name,
        "tier": event.tier,
        "start_date": event.start_date,
        "end_date": event.end_date,
        "game_version": event.game_version,
        "offline": event.offline,
        "match_count": len(event.matches),
    }
