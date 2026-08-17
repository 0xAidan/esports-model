from __future__ import annotations

from fastapi.testclient import TestClient

from esports_model.api.app import create_app
from esports_model.db.models import Team
from esports_model.db.session import init_db, session_scope
from esports_model.live.refresh import refresh_once
from tests.markets.test_pull import FakePolymarket


def test_health_and_html_table(tmp_path) -> None:
    url = f"sqlite:///{tmp_path / 'api.db'}"
    init_db(url)
    app = create_app(
        database_url=url,
        snapshot_path=tmp_path / "snapshot.json",
        output_dir=tmp_path / "output",
        enable_refresh=False,
        client_factory=FakePolymarket,
    )
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"
        page = client.get("/")
        assert page.status_code == 200
        assert "handleRefresh" in page.text
        assert "<table" in page.text
        assert "role=\"status\"" in page.text
        snap = client.get("/snapshot.json")
        assert snap.status_code == 200
        assert snap.json()["diagnostic"] == "no_market_posted_yet"


def test_refresh_endpoint_uses_injected_client(tmp_path) -> None:
    url = f"sqlite:///{tmp_path / 'pull.db'}"
    init_db(url)
    with session_scope(url) as session:
        session.add(Team(liquipedia_page="furia", name="FURIA"))
        session.add(Team(liquipedia_page="9z", name="9z"))
    app = create_app(
        database_url=url,
        snapshot_path=tmp_path / "snapshot.json",
        output_dir=tmp_path / "output",
        enable_refresh=False,
        client_factory=FakePolymarket,
    )
    with TestClient(app) as client:
        response = client.post("/refresh")
    assert response.status_code == 200
    body = response.json()
    assert body["last_pull"]["implemented"] is True
    assert body["diagnostic"] in {
        "market_available_no_edges",
        "no_market_posted_yet",
        "edges_available",
    }


def test_refresh_once_without_pull_skips_network(tmp_path) -> None:
    url = f"sqlite:///{tmp_path / 'ref.db'}"
    snapshot = refresh_once(
        database_url=url,
        pull=False,
        snapshot_path=tmp_path / "snapshot.json",
        output_dir=tmp_path / "output",
    )
    assert snapshot["last_pull"] is None
    assert snapshot["diagnostic"] == "no_market_posted_yet"
