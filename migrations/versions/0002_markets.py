"""Polymarket markets and identity quarantine.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-14
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "market_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("provider_event_id", sa.String(64), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("start_time", sa.DateTime(), nullable=True),
        sa.Column("volume", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_market_events_provider_event_id", "market_events", ["provider_event_id"], unique=True)
    op.create_index("ix_market_events_slug", "market_events", ["slug"])

    op.create_table(
        "markets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("market_events.id"), nullable=False),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id"), nullable=True),
        sa.Column("condition_id", sa.String(128), nullable=False),
        sa.Column("question", sa.String(512), nullable=False),
        sa.Column("market_type", sa.String(64), nullable=False),
        sa.Column("outcome_name", sa.String(128), nullable=False),
        sa.Column("token_id", sa.String(128), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("identity_confidence", sa.String(16), nullable=False),
        sa.Column("identity_status", sa.String(24), nullable=False),
        sa.Column("identity_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("provider", "token_id", name="uq_markets_token"),
    )
    op.create_index("ix_markets_event_id", "markets", ["event_id"])
    op.create_index("ix_markets_condition_id", "markets", ["condition_id"])
    op.create_index("ix_markets_identity_status", "markets", ["identity_status"])

    op.create_table(
        "orderbook_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("market_id", sa.Integer(), sa.ForeignKey("markets.id"), nullable=False),
        sa.Column("bid", sa.Float(), nullable=True),
        sa.Column("ask", sa.Float(), nullable=True),
        sa.Column("spread", sa.Float(), nullable=True),
        sa.Column("depth_usd", sa.Float(), nullable=True),
        sa.Column("volume_24h", sa.Float(), nullable=True),
        sa.Column("volume_lifetime", sa.Float(), nullable=True),
        sa.Column("fee_rate", sa.Float(), nullable=False),
        sa.Column("captured_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_orderbook_snapshots_market_id", "orderbook_snapshots", ["market_id"])
    op.create_index("ix_orderbook_snapshots_captured_at", "orderbook_snapshots", ["captured_at"])

    op.create_table(
        "identity_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("market_event_id", sa.Integer(), sa.ForeignKey("market_events.id"), nullable=False),
        sa.Column("left_name", sa.String(128), nullable=False),
        sa.Column("right_name", sa.String(128), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_identity_reviews_market_event_id", "identity_reviews", ["market_event_id"])


def downgrade() -> None:
    op.drop_table("identity_reviews")
    op.drop_table("orderbook_snapshots")
    op.drop_table("markets")
    op.drop_table("market_events")
