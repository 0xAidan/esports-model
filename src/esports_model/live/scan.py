"""Score live books and emit BET / WATCH / PASS rows."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal, assert_never

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from esports_model.config import feature_flags, get_settings
from esports_model.db.models import Market, Match, OrderBookSnapshot, Team
from esports_model.db.session import init_db, session_scope
from esports_model.ev.gates import Action, GateInputs, action_rank, decide_action
from esports_model.ev.kelly import advised_stake_usd, full_kelly
from esports_model.ev.math import ev_net, fee_per_share, haircut_prob, share_cost
from esports_model.features.builder import build_live_feature_row, load_completed_matches
from esports_model.features.spec import FeatureRow
from esports_model.live.grade import grade_settled, grades_path, upsert_pending
from esports_model.live.predict import PredictFn, resolve_predictor
from esports_model.live.snapshot import default_snapshot_path, utc_now, write_snapshot

Diagnostic = Literal[
    "no_market_posted_yet",
    "market_available_no_edges",
    "pipeline_error",
    "edges_available",
]


def run_scan(
    *,
    database_url: str,
    now: datetime | None = None,
    predict_fn: PredictFn | None = None,
    model_path: str | None = None,
    snapshot_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    bankroll_usd: float | None = None,
) -> dict[str, Any]:
    init_db(database_url)
    flags = feature_flags()
    clock = now or utc_now()
    out_dir = Path(output_dir) if output_dir is not None else Path("output")
    snap_path = Path(snapshot_path) if snapshot_path is not None else default_snapshot_path()
    bankroll = (
        bankroll_usd
        if bankroll_usd is not None
        else float(flags.get("bankroll_usd", get_settings().bankroll_usd))
    )
    try:
        with session_scope(database_url) as session:
            predictor = resolve_predictor(
                session,
                model_path=model_path,
                override=predict_fn,
            )
            rows = _score_markets(
                session,
                flags=flags,
                now=clock,
                predictor=predictor,
                bankroll=bankroll,
            )
        rows.sort(key=lambda row: (action_rank(row["action"]), -(row.get("ev_net") or -1)))
        counts = _counts(rows)
        diagnostic = _diagnostic(rows, counts)
        pending = upsert_pending(out_dir, rows)
        grades = grade_settled(database_url=database_url, output_dir=out_dir)
        snapshot = {
            "ok": True,
            "implemented": True,
            "generated_at": clock.isoformat(timespec="seconds"),
            "database_url": database_url,
            "diagnostic": diagnostic,
            "diagnostic_detail": _detail(diagnostic, counts, predictor is not None),
            "counts": counts,
            "bankroll_usd": bankroll,
            "model_available": predictor is not None,
            "rows": rows,
            "table_text": render_table(diagnostic, counts, rows),
            "pending_grades": str(pending),
            "grades_path": str(grades_path(out_dir)),
            "grades": {
                "n_graded": grades["n_graded"],
                "n_pending": grades["n_pending"],
                "mean_brier": grades["mean_brier"],
            },
        }
    except Exception as exc:  # noqa: BLE001
        snapshot = {
            "ok": False,
            "implemented": True,
            "generated_at": clock.isoformat(timespec="seconds"),
            "database_url": database_url,
            "diagnostic": "pipeline_error",
            "diagnostic_detail": str(exc),
            "counts": {"BET": 0, "WATCH": 0, "PASS": 0, "quarantine": 0},
            "rows": [],
            "table_text": f"diagnostic: pipeline_error\n{exc}\n",
        }
    write_snapshot(snap_path, snapshot)
    return snapshot


def _score_markets(
    session: Session,
    *,
    flags: dict[str, Any],
    now: datetime,
    predictor: PredictFn | None,
    bankroll: float,
) -> list[dict[str, Any]]:
    markets = list(
        session.scalars(select(Market).options(selectinload(Market.event)))
    )
    books = _latest_books(session)
    history = load_completed_matches(session)
    teams = {row.id: row for row in session.scalars(select(Team))}
    matches = {row.id: row for row in session.scalars(select(Match))}
    haircut = float(flags.get("uncertainty_haircut", 0.02))
    fractional = float(flags.get("kelly_fractional", 0.25))
    cap = float(flags.get("kelly_max_fraction_of_bankroll", 0.05))
    rows: list[dict[str, Any]] = []
    for market in markets:
        book = books.get(market.id)
        match = matches.get(market.match_id) if market.match_id is not None else None
        feature = None
        if match is not None:
            feature = build_live_feature_row(session, match, history)
        rows.append(
            _score_one(
                market=market,
                book=book,
                match=match,
                feature=feature,
                teams=teams,
                flags=flags,
                now=now,
                predictor=predictor,
                haircut=haircut,
                bankroll=bankroll,
                fractional=fractional,
                cap=cap,
            )
        )
    return rows


def _score_one(
    *,
    market: Market,
    book: OrderBookSnapshot | None,
    match: Match | None,
    feature: FeatureRow | None,
    teams: dict[int, Team],
    flags: dict[str, Any],
    now: datetime,
    predictor: PredictFn | None,
    haircut: float,
    bankroll: float,
    fractional: float,
    cap: float,
) -> dict[str, Any]:
    ask = book.ask if book is not None else None
    bid = book.bid if book is not None else None
    spread = book.spread if book is not None else None
    depth = book.depth_usd if book is not None else None
    volume = None
    fee_rate = 0.05
    if book is not None:
        volume = book.volume_24h if book.volume_24h is not None else book.volume_lifetime
        fee_rate = book.fee_rate
    hours = None
    start = match.start_time if match is not None else (market.event.start_time if market.event else None)
    if start is not None:
        hours = (start - now).total_seconds() / 3600.0

    model_p = None
    p_star = None
    cost = None
    edge = None
    fee = None
    if feature is not None and predictor is not None and market.team_id is not None:
        team1_p = predictor(feature)
        model_p = team1_p if market.team_id == feature.team1_id else 1.0 - team1_p
        p_star = haircut_prob(model_p, haircut)
        if ask is not None:
            fee = fee_per_share(ask, fee_rate)
            cost = share_cost(ask, fee_rate)
            edge = ev_net(p_star, cost)

    prior = feature.prior_matches_min if feature is not None else None
    decision = decide_action(
        GateInputs(
            identity_status=market.identity_status,
            identity_confidence=market.identity_confidence,
            match_id=market.match_id,
            ev_net=edge,
            volume=volume,
            spread=spread,
            depth_usd=depth,
            hours_to_start=hours,
            prior_matches_min=prior,
            ask=ask,
        ),
        flags,
    )
    kelly = full_kelly(p_star, cost) if p_star is not None and cost is not None else 0.0
    stake = 0.0
    if decision.action == "BET" and p_star is not None and cost is not None:
        stake = advised_stake_usd(
            p_star=p_star,
            cost=cost,
            bankroll_usd=bankroll,
            depth_usd=depth or 0.0,
            fractional=fractional,
            cap_fraction=cap,
        )

    side = market.outcome_name
    opponent = _opponent(market, match, teams)
    return {
        "event_title": market.event.title if market.event is not None else market.question,
        "slug": market.event.slug if market.event is not None else "",
        "side": side,
        "opponent": opponent,
        "match_id": market.match_id,
        "team_id": market.team_id,
        "token_id": market.token_id,
        "model_p": model_p,
        "p_star": p_star,
        "ask": ask,
        "bid": bid,
        "fee_rate": fee_rate,
        "fee_per_share": fee,
        "cost": cost,
        "ev_net": edge,
        "volume": volume,
        "spread": spread,
        "depth_usd": depth,
        "hours_to_start": hours,
        "prior_matches_min": prior,
        "identity_status": market.identity_status,
        "identity_confidence": market.identity_confidence,
        "action": decision.action,
        "reasons": list(decision.reasons),
        "stake_usd": stake,
        "kelly_full": kelly,
    }


def _opponent(market: Market, match: Match | None, teams: dict[int, Team]) -> str:
    if match is not None and market.team_id is not None:
        other_id = match.team2_id if market.team_id == match.team1_id else match.team1_id
        other = teams.get(other_id)
        if other is not None:
            return other.name
    return ""


def _latest_books(session: Session) -> dict[int, OrderBookSnapshot]:
    latest: dict[int, OrderBookSnapshot] = {}
    rows = session.scalars(
        select(OrderBookSnapshot).order_by(OrderBookSnapshot.captured_at.desc())
    )
    for row in rows:
        if row.market_id not in latest:
            latest[row.market_id] = row
    return latest


def _counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"BET": 0, "WATCH": 0, "PASS": 0, "quarantine": 0}
    for row in rows:
        action: Action = row["action"]
        counts[action] = counts.get(action, 0) + 1
    return counts


def _diagnostic(rows: list[dict[str, Any]], counts: dict[str, int]) -> Diagnostic:
    if not rows:
        return "no_market_posted_yet"
    if counts.get("BET", 0) > 0:
        return "edges_available"
    return "market_available_no_edges"


def _detail(diagnostic: Diagnostic, counts: dict[str, int], model_ok: bool) -> str:
    if diagnostic == "no_market_posted_yet":
        return "Pipeline ran. No CS2 series books are stored yet."
    if diagnostic == "edges_available":
        return f"{counts['BET']} BET row(s). Still not a promise."
    if diagnostic == "market_available_no_edges":
        extra = "" if model_ok else " Model could not be fit from local history."
        return (
            f"Markets exist. BET=0 WATCH={counts['WATCH']} PASS={counts['PASS']} "
            f"quarantine={counts['quarantine']}.{extra}"
        )
    if diagnostic == "pipeline_error":
        return "Scanner failed."
    assert_never(diagnostic)


def render_table(
    diagnostic: Diagnostic,
    counts: dict[str, int],
    rows: list[dict[str, Any]],
) -> str:
    lines = [
        f"diagnostic: {diagnostic}",
        (
            f"BET={counts['BET']}  WATCH={counts['WATCH']}  "
            f"PASS={counts['PASS']}  quarantine={counts['quarantine']}"
        ),
        "",
        (
            f"{'SIDE':<16}{'VS':<14}{'MODEL':>7}{'ASK':>7}{'EV':>8}"
            f"{'VOL':>9}{'SPRD':>7}{'DEPTH':>8}{'ACTION':>12}{'STAKE':>8}"
        ),
    ]
    if not rows:
        lines.append("(no rows)")
        return "\n".join(lines) + "\n"
    for row in rows:
        lines.append(
            (
                f"{_fit(row['side'], 16)}"
                f"{_fit(row.get('opponent') or '-', 14)}"
                f"{_pct(row.get('model_p')):>7}"
                f"{_pct(row.get('ask')):>7}"
                f"{_num(row.get('ev_net')):>8}"
                f"{_money(row.get('volume')):>9}"
                f"{_num(row.get('spread')):>7}"
                f"{_money(row.get('depth_usd')):>8}"
                f"{str(row['action']):>12}"
                f"{_money(row.get('stake_usd')):>8}"
            )
        )
    return "\n".join(lines) + "\n"


def _fit(value: str, width: int) -> str:
    text = value or "-"
    if len(text) <= width:
        return text.ljust(width)
    return text[: width - 1] + "…"


def _pct(value: object) -> str:
    if value is None:
        return "-"
    return f"{float(value):.2f}"


def _num(value: object) -> str:
    if value is None:
        return "-"
    return f"{float(value):+.3f}"


def _money(value: object) -> str:
    if value is None:
        return "-"
    return f"{float(value):.0f}"
