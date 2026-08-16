"""Snapshot API plus a small operator HTML table."""

from __future__ import annotations

import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from esports_model.config import feature_flags, get_settings
from esports_model.ingest.sync import ClientFactory as LiquipediaFactory
from esports_model.jobs.tick import run_tick
from esports_model.live.html import render_operator_html
from esports_model.live.refresh import start_refresh_thread
from esports_model.live.scan import run_scan
from esports_model.live.snapshot import default_snapshot_path, read_snapshot
from esports_model.markets.pull import ClientFactory


def create_app(
    *,
    database_url: str | None = None,
    snapshot_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    enable_refresh: bool = False,
    client_factory: ClientFactory | None = None,
    liquipedia_factory: LiquipediaFactory | None = None,
) -> FastAPI:
    settings = get_settings()
    db_url = database_url or settings.esports_database_url
    snap = Path(snapshot_path) if snapshot_path is not None else default_snapshot_path()
    out = Path(output_dir) if output_dir is not None else Path("output")
    flags = feature_flags()
    refresh_sec = int(flags.get("refresh_near_start_sec", 30))
    stop_event = threading.Event()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        if not snap.exists():
            run_scan(database_url=db_url, snapshot_path=snap, output_dir=out)
        if enable_refresh:
            start_refresh_thread(
                database_url=db_url,
                snapshot_path=snap,
                output_dir=out,
                stop_event=stop_event,
                client_factory=client_factory,
                liquipedia_factory=liquipedia_factory,
            )
        yield
        stop_event.set()

    app = FastAPI(title="esports-model", version="0.1.0", lifespan=lifespan)
    app.state.database_url = db_url
    app.state.snapshot_path = snap
    app.state.output_dir = out

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/snapshot.json")
    def snapshot_json() -> JSONResponse:
        payload = read_snapshot(snap)
        if payload is None:
            payload = run_scan(database_url=db_url, snapshot_path=snap, output_dir=out)
        return JSONResponse(payload)

    @app.post("/refresh")
    def refresh() -> JSONResponse:
        payload = run_tick(
            database_url=db_url,
            pull_books=True,
            sync_liquipedia=True,
            market_factory=client_factory,
            liquipedia_factory=liquipedia_factory,
            snapshot_path=snap,
            output_dir=out,
        )
        return JSONResponse(payload)

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        payload = read_snapshot(snap)
        if payload is None:
            payload = run_scan(database_url=db_url, snapshot_path=snap, output_dir=out)
        return HTMLResponse(render_operator_html(payload, refresh_sec=refresh_sec))

    return app
