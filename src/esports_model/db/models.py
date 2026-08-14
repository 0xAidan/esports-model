"""Core SQLite tables for CS2 history and later market rows."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from esports_model.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    liquipedia_page: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    short_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    home_matches: Mapped[list[Match]] = relationship(
        back_populates="team1",
        foreign_keys="Match.team1_id",
    )
    away_matches: Mapped[list[Match]] = relationship(
        back_populates="team2",
        foreign_keys="Match.team2_id",
    )


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    liquipedia_page: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    nationality: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class RosterEntry(Base):
    __tablename__ = "rosters"
    __table_args__ = (
        UniqueConstraint(
            "team_id",
            "player_id",
            "join_date",
            name="uq_roster_stint",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    join_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    leave_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="liquipedia")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    liquipedia_page: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    tier: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    region: Mapped[str | None] = mapped_column(String(64), nullable=True)
    game_version: Mapped[str] = mapped_column(String(16), default="cs2")
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    matches: Mapped[list[Match]] = relationship(back_populates="event")


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint("liquipedia_match_id", name="uq_matches_lp_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    liquipedia_match_id: Mapped[str] = mapped_column(String(128), index=True)
    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id"), nullable=True)
    team1_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    team2_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    winner_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    format: Mapped[str | None] = mapped_column(String(16), nullable=True)
    score1: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score2: Mapped[int | None] = mapped_column(Integer, nullable=True)
    game_version: Mapped[str] = mapped_column(String(16), default="cs2", index=True)
    offline: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="completed", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    event: Mapped[Event | None] = relationship(back_populates="matches")
    team1: Mapped[Team] = relationship(foreign_keys=[team1_id], back_populates="home_matches")
    team2: Mapped[Team] = relationship(foreign_keys=[team2_id], back_populates="away_matches")
    maps: Mapped[list[MapResult]] = relationship(back_populates="match")


class MapResult(Base):
    __tablename__ = "maps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), index=True)
    map_name: Mapped[str] = mapped_column(String(64), index=True)
    map_number: Mapped[int] = mapped_column(Integer, default=1)
    team1_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    team2_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    winner_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)

    match: Mapped[Match] = relationship(back_populates="maps")


class IngestCursor(Base):
    __tablename__ = "ingest_cursors"
    __table_args__ = (
        UniqueConstraint("source", "cursor_key", name="uq_ingest_cursor"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(64), index=True)
    cursor_key: Mapped[str] = mapped_column(String(64))
    cursor_value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
