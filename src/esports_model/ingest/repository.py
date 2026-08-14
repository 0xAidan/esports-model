"""Upsert parsed Liquipedia rows into SQLite."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from esports_model.db.models import Event, IngestCursor, MapResult, Match, Team
from esports_model.ingest.wikitext import ParsedEvent, ParsedMatch, match_id


def get_or_create_team(session: Session, slug: str) -> Team:
    page = slug.strip().lower()
    team = session.scalar(select(Team).where(Team.liquipedia_page == page))
    if team is not None:
        return team
    team = Team(liquipedia_page=page, name=_display_name(page), short_name=page.upper())
    session.add(team)
    session.flush()
    return team


def _display_name(slug: str) -> str:
    return slug.replace("_", " ").replace("-", " ").title()


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def upsert_event(session: Session, page: str, parsed: ParsedEvent) -> Event:
    event = session.scalar(select(Event).where(Event.liquipedia_page == page))
    if event is None:
        event = Event(liquipedia_page=page, name=parsed.name)
        session.add(event)
    event.name = parsed.name
    event.tier = parsed.tier
    event.start_date = _parse_date(parsed.start_date)
    event.end_date = _parse_date(parsed.end_date)
    event.game_version = parsed.game_version
    event.location = parsed.location
    session.flush()
    return event


def upsert_match(
    session: Session,
    *,
    event: Event,
    event_page: str,
    parsed: ParsedMatch,
    offline: bool | None,
) -> tuple[Match, bool]:
    team1 = get_or_create_team(session, parsed.team1_slug)
    team2 = get_or_create_team(session, parsed.team2_slug)
    external_id = match_id(event_page, parsed)
    row = session.scalar(select(Match).where(Match.liquipedia_match_id == external_id))
    created = row is None
    if row is None:
        row = Match(liquipedia_match_id=external_id, team1_id=team1.id, team2_id=team2.id)
        session.add(row)
    row.event_id = event.id
    row.team1_id = team1.id
    row.team2_id = team2.id
    row.start_time = parsed.start_time
    row.format = parsed.format
    row.score1 = parsed.score1
    row.score2 = parsed.score2
    row.game_version = event.game_version
    row.offline = offline
    row.status = "completed" if parsed.finished else "upcoming"
    if parsed.winner_side == 1:
        row.winner_id = team1.id
    elif parsed.winner_side == 2:
        row.winner_id = team2.id
    else:
        row.winner_id = None
    session.flush()
    session.execute(delete(MapResult).where(MapResult.match_id == row.id))
    for item in parsed.maps:
        session.add(
            MapResult(
                match_id=row.id,
                map_name=item.map_name,
                map_number=item.map_number,
                team1_score=item.team1_score,
                team2_score=item.team2_score,
                winner_id=(
                    team1.id
                    if item.team1_score is not None
                    and item.team2_score is not None
                    and item.team1_score > item.team2_score
                    else team2.id
                    if item.team1_score is not None
                    and item.team2_score is not None
                    and item.team2_score > item.team1_score
                    else None
                ),
            )
        )
    return row, created


def set_cursor(session: Session, source: str, key: str, value: str) -> None:
    row = session.scalar(
        select(IngestCursor).where(
            IngestCursor.source == source,
            IngestCursor.cursor_key == key,
        )
    )
    if row is None:
        row = IngestCursor(source=source, cursor_key=key, cursor_value=value)
        session.add(row)
    else:
        row.cursor_value = value
        row.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)


def get_cursor(session: Session, source: str, key: str) -> str | None:
    row = session.scalar(
        select(IngestCursor).where(
            IngestCursor.source == source,
            IngestCursor.cursor_key == key,
        )
    )
    return row.cursor_value if row is not None else None
