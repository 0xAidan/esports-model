"""Engine, sessions, and Alembic init-db."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session, sessionmaker

from esports_model.config import get_settings


def apply_sqlite_pragmas(connection: Connection) -> None:
    if connection.dialect.name != "sqlite":
        return
    connection.execute(text("PRAGMA foreign_keys=ON"))
    db_api = connection.connection.dbapi_connection
    raw_path = ""
    if hasattr(db_api, "execute"):
        row = db_api.execute("PRAGMA database_list").fetchone()
        if row is not None and len(row) >= 3:
            raw_path = row[2] or ""
    if raw_path and raw_path != ":memory:":
        connection.execute(text("PRAGMA journal_mode=WAL"))


def sqlite_connect_pragmas(dbapi_conn, _connection_record) -> None:
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    row = dbapi_conn.execute("PRAGMA database_list").fetchone()
    raw_path = row[2] if row is not None and len(row) >= 3 else ""
    if raw_path and raw_path != ":memory:":
        cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def _attach_sqlite_listeners(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return
    if getattr(engine, "_esports_sqlite_pragmas", False):
        return
    event.listen(engine, "connect", sqlite_connect_pragmas)
    engine._esports_sqlite_pragmas = True  # type: ignore[attr-defined]


def get_engine(url: str | None = None) -> Engine:
    settings = get_settings()
    resolved = url or settings.esports_database_url
    if resolved.startswith("sqlite:///"):
        path = resolved.removeprefix("sqlite:///")
        if path and path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(resolved, echo=False, future=True)
    _attach_sqlite_listeners(engine)
    return engine


def _alembic_config(url: str | None = None) -> Config:
    settings = get_settings()
    root = settings.project_root
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url or settings.esports_database_url)
    return cfg


def init_db(url: str | None = None) -> None:
    import esports_model.db.models  # noqa: F401

    command.upgrade(_alembic_config(url), "head")


@contextmanager
def session_scope(url: str | None = None) -> Generator[Session, None, None]:
    engine = get_engine(url)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        engine.dispose()
