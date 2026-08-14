"""Core CS2 history schema.

Revision ID: 0001
Revises:
Create Date: 2026-08-14
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("liquipedia_page", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("short_name", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_teams_liquipedia_page", "teams", ["liquipedia_page"], unique=True)
    op.create_index("ix_teams_name", "teams", ["name"])

    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("liquipedia_page", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("nationality", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_players_liquipedia_page", "players", ["liquipedia_page"], unique=True)
    op.create_index("ix_players_name", "players", ["name"])

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("liquipedia_page", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("tier", sa.String(32), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("region", sa.String(64), nullable=True),
        sa.Column("game_version", sa.String(16), nullable=False),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_events_liquipedia_page", "events", ["liquipedia_page"], unique=True)
    op.create_index("ix_events_name", "events", ["name"])
    op.create_index("ix_events_tier", "events", ["tier"])

    op.create_table(
        "rosters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
        sa.Column("join_date", sa.Date(), nullable=True),
        sa.Column("leave_date", sa.Date(), nullable=True),
        sa.Column("role", sa.String(64), nullable=True),
        sa.Column("source", sa.String(32), nullable=False),
        sa.UniqueConstraint("team_id", "player_id", "join_date", name="uq_roster_stint"),
    )
    op.create_index("ix_rosters_team_id", "rosters", ["team_id"])
    op.create_index("ix_rosters_player_id", "rosters", ["player_id"])

    op.create_table(
        "matches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("liquipedia_match_id", sa.String(128), nullable=False),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id"), nullable=True),
        sa.Column("team1_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("team2_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("winner_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("start_time", sa.DateTime(), nullable=True),
        sa.Column("format", sa.String(16), nullable=True),
        sa.Column("score1", sa.Integer(), nullable=True),
        sa.Column("score2", sa.Integer(), nullable=True),
        sa.Column("game_version", sa.String(16), nullable=False),
        sa.Column("offline", sa.Boolean(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("liquipedia_match_id", name="uq_matches_lp_id"),
    )
    op.create_index("ix_matches_liquipedia_match_id", "matches", ["liquipedia_match_id"])
    op.create_index("ix_matches_team1_id", "matches", ["team1_id"])
    op.create_index("ix_matches_team2_id", "matches", ["team2_id"])
    op.create_index("ix_matches_start_time", "matches", ["start_time"])
    op.create_index("ix_matches_game_version", "matches", ["game_version"])
    op.create_index("ix_matches_status", "matches", ["status"])

    op.create_table(
        "maps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id"), nullable=False),
        sa.Column("map_name", sa.String(64), nullable=False),
        sa.Column("map_number", sa.Integer(), nullable=False),
        sa.Column("team1_score", sa.Integer(), nullable=True),
        sa.Column("team2_score", sa.Integer(), nullable=True),
        sa.Column("winner_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=True),
    )
    op.create_index("ix_maps_match_id", "maps", ["match_id"])
    op.create_index("ix_maps_map_name", "maps", ["map_name"])

    op.create_table(
        "ingest_cursors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("cursor_key", sa.String(64), nullable=False),
        sa.Column("cursor_value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("source", "cursor_key", name="uq_ingest_cursor"),
    )
    op.create_index("ix_ingest_cursors_source", "ingest_cursors", ["source"])


def downgrade() -> None:
    op.drop_table("ingest_cursors")
    op.drop_table("maps")
    op.drop_table("matches")
    op.drop_table("rosters")
    op.drop_table("events")
    op.drop_table("players")
    op.drop_table("teams")
