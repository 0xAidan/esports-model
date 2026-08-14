"""Coverage audit for the local match database."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import func, select

from esports_model.db.models import Event, MapResult, Match
from esports_model.db.session import get_engine, session_scope


def coverage_report(*, database_url: str) -> dict[str, object]:
    engine = get_engine(database_url)
    try:
        with session_scope(database_url) as session:
            match_count = session.scalar(select(func.count()).select_from(Match)) or 0
            event_count = session.scalar(select(func.count()).select_from(Event)) or 0
            map_count = session.scalar(select(func.count()).select_from(MapResult)) or 0
            missing_score = session.scalar(
                select(func.count()).select_from(Match).where(Match.score1.is_(None))
            ) or 0
            missing_start = session.scalar(
                select(func.count()).select_from(Match).where(Match.start_time.is_(None))
            ) or 0
            earliest = session.scalar(select(func.min(Match.start_time)))
            latest = session.scalar(select(func.max(Match.start_time)))
            by_tier_rows = session.execute(
                select(Event.tier, func.count(Match.id))
                .join(Match, Match.event_id == Event.id, isouter=True)
                .group_by(Event.tier)
            ).all()
            by_version = session.execute(
                select(Match.game_version, func.count()).group_by(Match.game_version)
            ).all()
            by_status = session.execute(
                select(Match.status, func.count()).group_by(Match.status)
            ).all()
    finally:
        engine.dispose()
    return {
        "ok": True,
        "implemented": True,
        "database_url": database_url,
        "match_count": match_count,
        "event_count": event_count,
        "map_count": map_count,
        "missing_score_count": missing_score,
        "missing_start_time_count": missing_start,
        "earliest_start": earliest.isoformat() if earliest else None,
        "latest_start": latest.isoformat() if latest else None,
        "by_tier": {str(tier or "unknown"): count for tier, count in by_tier_rows},
        "by_game_version": {str(version): count for version, count in by_version},
        "by_status": {str(status): count for status, count in by_status},
        "attribution": "Match data derived from Liquipedia (CC-BY-SA 3.0).",
    }


def write_coverage(*, database_url: str, output_path: str) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = coverage_report(database_url=database_url)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return str(path)
