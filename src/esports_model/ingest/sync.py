"""Resumable Liquipedia CS2 sync."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from typing import Any

from esports_model.config import get_settings
from esports_model.db.session import init_db, session_scope
from esports_model.ingest.http import PoliteClient
from esports_model.ingest.liquipedia import (
    CATEGORY_BY_VERSION,
    LIVE_CATEGORY,
    fetch_wikitext,
    iter_category_titles,
)
from esports_model.ingest.repository import (
    get_cursor,
    set_cursor,
    upsert_event,
    upsert_match,
)
from esports_model.ingest.wikitext import ParsedEvent, parse_event_page

ClientFactory = Callable[[], PoliteClient]


def _client_factory() -> PoliteClient:
    return PoliteClient(settings=get_settings())


def run_sync(
    *,
    profile_name: str,
    spec: dict[str, Any],
    resume: bool,
    database_url: str,
    client_factory: ClientFactory | None = None,
) -> dict[str, Any]:
    init_db(database_url)
    factory = client_factory or _client_factory
    tiers = {str(item) for item in spec.get("tiers", [])}
    versions = [str(item) for item in spec.get("game_versions", ["cs2"])]
    upcoming_only = bool(spec.get("upcoming_only"))
    include_upcoming = bool(spec.get("include_upcoming", True))
    max_matches = int(spec.get("max_matches_per_run") or 0) or 10_000
    lookback_days = int(spec.get("lookback_days") or 0)
    start_floor = spec.get("start_date")
    today = date.today()
    min_end = today - timedelta(days=lookback_days) if lookback_days else None
    min_start = date.fromisoformat(start_floor) if start_floor else None

    categories: list[str] = []
    if upcoming_only:
        categories.append(LIVE_CATEGORY)
    else:
        if include_upcoming:
            categories.append(LIVE_CATEGORY)
        for version in versions:
            category = CATEGORY_BY_VERSION.get(version)
            if category and category not in categories:
                categories.append(category)

    stored = 0
    pages_seen = 0
    skipped = 0
    errors: list[str] = []

    with factory() as client, session_scope(database_url) as session:
        for category in categories:
            cursor_key = f"{category}:cmcontinue"
            cursor = get_cursor(session, "liquipedia", cursor_key) if resume else None
            for title, next_cursor in iter_category_titles(client, category, cmcontinue=cursor):
                if stored >= max_matches:
                    break
                pages_seen += 1
                try:
                    wikitext = fetch_wikitext(client, title)
                    if not wikitext:
                        skipped += 1
                        continue
                    parsed = parse_event_page(title, wikitext)
                    if not _event_allowed(
                        parsed,
                        tiers=tiers,
                        versions=set(versions),
                        min_end=min_end,
                        min_start=min_start,
                    ):
                        skipped += 1
                        if next_cursor:
                            set_cursor(session, "liquipedia", cursor_key, next_cursor)
                        continue
                    event = upsert_event(session, title, parsed)
                    for match in parsed.matches:
                        if upcoming_only and match.finished:
                            continue
                        if stored >= max_matches:
                            break
                        _row, created = upsert_match(
                            session,
                            event=event,
                            event_page=title,
                            parsed=match,
                            offline=parsed.offline,
                        )
                        if created:
                            stored += 1
                    if next_cursor:
                        set_cursor(session, "liquipedia", cursor_key, next_cursor)
                except Exception as exc:  # noqa: BLE001 — keep the run going
                    errors.append(f"{title}: {exc}")
                    skipped += 1
            if stored >= max_matches:
                break

    return {
        "ok": not errors,
        "implemented": True,
        "profile": profile_name,
        "resume": resume,
        "database_url": database_url,
        "pages_seen": pages_seen,
        "matches_upserted": stored,
        "pages_skipped": skipped,
        "errors": errors[:20],
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "attribution": "Match data derived from Liquipedia (CC-BY-SA 3.0).",
    }


def _event_allowed(
    parsed: ParsedEvent,
    *,
    tiers: set[str],
    versions: set[str],
    min_end: date | None,
    min_start: date | None,
) -> bool:
    if versions and parsed.game_version not in versions:
        return False
    if tiers and parsed.tier and parsed.tier not in tiers:
        return False
    end = _iso_date(parsed.end_date) or _iso_date(parsed.start_date)
    start = _iso_date(parsed.start_date)
    if min_end and end and end < min_end:
        return False
    if min_start and start and start < min_start:
        return False
    return True


def _iso_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None
