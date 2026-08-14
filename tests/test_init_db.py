from __future__ import annotations

from sqlalchemy import inspect, text

from esports_model.db.session import get_engine, init_db


def test_init_db_creates_core_tables(tmp_path, monkeypatch) -> None:
    db = tmp_path / "esports.db"
    url = f"sqlite:///{db}"
    monkeypatch.setenv("ESPORTS_DATABASE_URL", url)
    from esports_model.config import reset_settings

    reset_settings()
    init_db(url)
    engine = get_engine(url)
    names = set(inspect(engine).get_table_names())
    assert {
        "teams",
        "players",
        "rosters",
        "events",
        "matches",
        "maps",
        "ingest_cursors",
        "market_events",
        "markets",
        "orderbook_snapshots",
        "identity_reviews",
        "alembic_version",
    } <= names
    with engine.connect() as conn:
        version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert version == "0002"
    engine.dispose()
