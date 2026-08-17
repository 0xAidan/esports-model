"""Build leaked-safe features as-of match start."""

from __future__ import annotations

import math
from collections import defaultdict, deque
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from esports_model.db.models import Event, MapResult, Match, RosterEntry
from esports_model.features.elo import DEFAULT_ELO, update_elo
from esports_model.features.spec import FEATURE_NAMES, FeatureRow

TIER_S = {"S-Tier", "S"}
TIER_A = {"A-Tier", "A"}


def load_completed_matches(session: Session) -> list[Match]:
    rows = session.scalars(
        select(Match)
        .options(selectinload(Match.maps), selectinload(Match.event))
        .where(Match.start_time.is_not(None))
        .order_by(Match.start_time.asc(), Match.id.asc())
    ).all()
    return list(rows)


def build_feature_row(session: Session, match: Match) -> FeatureRow | None:
    if match.start_time is None:
        return None
    history = [
        row
        for row in load_completed_matches(session)
        if row.start_time is not None and _is_strictly_before(row, match)
    ]
    return _features_from_history(session, match, history)


def build_live_feature_row(
    session: Session,
    match: Match,
    history: list[Match],
) -> FeatureRow | None:
    if match.start_time is None:
        return None
    priors = [
        row
        for row in history
        if row.start_time is not None and _is_strictly_before(row, match)
    ]
    return _features_from_history(session, match, priors)


def build_feature_table(session: Session) -> list[FeatureRow]:
    matches = load_completed_matches(session)
    rows: list[FeatureRow] = []
    history: list[Match] = []
    for match in matches:
        built = _features_from_history(session, match, history)
        if built is not None:
            rows.append(built)
        history.append(match)
    return rows


def _is_strictly_before(prior: Match, current: Match) -> bool:
    if prior.id == current.id:
        return False
    if prior.start_time is None or current.start_time is None:
        return False
    if prior.start_time < current.start_time:
        return True
    if prior.start_time == current.start_time:
        return prior.id < current.id
    return False


def _features_from_history(
    session: Session,
    match: Match,
    history: list[Match],
) -> FeatureRow | None:
    if match.team1_id == match.team2_id:
        return None
    elo: dict[int, float] = defaultdict(lambda: DEFAULT_ELO)
    form: dict[int, deque[int]] = defaultdict(lambda: deque(maxlen=10))
    last_played: dict[int, datetime] = {}
    prior_count: dict[int, int] = defaultdict(int)
    map_wins: dict[int, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    h2h: dict[tuple[int, int], int] = defaultdict(int)

    for prior in history:
        if prior.winner_id is None or prior.score1 is None or prior.score2 is None:
            continue
        winner = prior.winner_id
        loser = prior.team2_id if winner == prior.team1_id else prior.team1_id
        if loser == winner:
            continue
        new_win, new_lose = update_elo(elo[winner], elo[loser])
        elo[winner] = new_win
        elo[loser] = new_lose
        form[winner].append(1)
        form[loser].append(0)
        if prior.start_time is not None:
            last_played[prior.team1_id] = prior.start_time
            last_played[prior.team2_id] = prior.start_time
        prior_count[prior.team1_id] += 1
        prior_count[prior.team2_id] += 1
        h2h[(winner, loser)] += 1
        for map_row in prior.maps:
            if map_row.winner_id is None or not map_row.map_name:
                continue
            map_wins[map_row.winner_id][map_row.map_name].append(1)
            other = (
                prior.team2_id if map_row.winner_id == prior.team1_id else prior.team1_id
            )
            map_wins[other][map_row.map_name].append(0)

    team1 = match.team1_id
    team2 = match.team2_id
    form5_1 = _mean(list(form[team1])[-5:])
    form5_2 = _mean(list(form[team2])[-5:])
    form10_1 = _mean(list(form[team1]))
    form10_2 = _mean(list(form[team2]))
    rest1 = _rest_days(match.start_time, last_played.get(team1))
    rest2 = _rest_days(match.start_time, last_played.get(team2))
    prior_min = min(prior_count[team1], prior_count[team2])
    event = match.event
    if event is None and match.event_id is not None:
        event = session.get(Event, match.event_id)
    tier = event.tier if event is not None else None
    values = {
        "elo_diff": elo[team1] - elo[team2],
        "form5_diff": form5_1 - form5_2,
        "form10_diff": form10_1 - form10_2,
        "map_wr_diff": _map_wr(map_wins[team1]) - _map_wr(map_wins[team2]),
        "h2h_diff": float(h2h[(team1, team2)] - h2h[(team2, team1)]),
        "rest_days_diff": rest1 - rest2,
        "prior_log_min": math.log1p(prior_min),
        "tier_s": 1.0 if tier in TIER_S else 0.0,
        "tier_a": 1.0 if tier in TIER_A else 0.0,
        "is_bo1": 1.0 if match.format == "bo1" else 0.0,
        "is_bo3": 1.0 if match.format == "bo3" else 0.0,
        "is_bo5": 1.0 if match.format == "bo5" else 0.0,
        "is_offline": 1.0 if match.offline else 0.0,
        "roster_stability_diff": _roster_stability(
            session, team1, match.start_time
        )
        - _roster_stability(session, team2, match.start_time),
    }
    label = None
    if match.winner_id == team1:
        label = 1
    elif match.winner_id == team2:
        label = 0
    return FeatureRow(
        match_id=match.id,
        team1_id=team1,
        team2_id=team2,
        label=label,
        prior_matches_min=prior_min,
        values=values,
    )


def _mean(values: list[int]) -> float:
    if not values:
        return 0.5
    return sum(values) / len(values)


def _map_wr(by_map: dict[str, list[int]]) -> float:
    rates: list[float] = []
    for results in by_map.values():
        if len(results) < 3:
            continue
        rates.append(sum(results) / len(results))
    if not rates:
        return 0.5
    return sum(rates) / len(rates)


def _rest_days(start: datetime | None, last: datetime | None) -> float:
    if start is None or last is None:
        return 7.0
    return max((start - last).total_seconds() / 86400.0, 0.0)


def _roster_stability(session: Session, team_id: int, as_of: datetime | None) -> float:
    if as_of is None:
        return 0.0
    as_of_date = as_of.date()
    rows = session.scalars(select(RosterEntry).where(RosterEntry.team_id == team_id)).all()
    if not rows:
        return 0.0
    active = [
        row
        for row in rows
        if (row.join_date is None or row.join_date <= as_of_date)
        and (row.leave_date is None or row.leave_date > as_of_date)
    ]
    if not active:
        return 0.0
    joins = [row.join_date for row in active if row.join_date is not None]
    if not joins:
        return 90.0
    newest = max(joins)
    return float((as_of_date - newest).days)


def attach_maps(session: Session, matches: list[Match]) -> None:
    if not matches:
        return
    ids = [row.id for row in matches]
    maps = session.scalars(select(MapResult).where(MapResult.match_id.in_(ids))).all()
    by_match: dict[int, list[MapResult]] = defaultdict(list)
    for item in maps:
        by_match[item.match_id].append(item)
    for match in matches:
        match.maps = by_match.get(match.id, [])


__all__ = [
    "FEATURE_NAMES",
    "attach_maps",
    "build_feature_row",
    "build_feature_table",
    "build_live_feature_row",
    "load_completed_matches",
]
