from __future__ import annotations

from esports_model.cli import main


def test_help_exits_zero() -> None:
    try:
        main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0


def test_init_db(tmp_path, monkeypatch) -> None:
    db = tmp_path / "esports.db"
    monkeypatch.setenv("ESPORTS_DATABASE_URL", f"sqlite:///{db}")
    from esports_model.config import reset_settings

    reset_settings()
    assert main(["init-db", "--database-url", f"sqlite:///{db}"]) == 0
    assert db.exists()


def test_sync_refuses_example_email(tmp_path, monkeypatch) -> None:
    db = tmp_path / "esports.db"
    url = f"sqlite:///{db}"
    monkeypatch.setenv("LIQUIPEDIA_CONTACT_EMAIL", "you@example.com")
    monkeypatch.setenv("LIQUIPEDIA_USER_AGENT", "")
    from esports_model.config import reset_settings

    reset_settings()
    assert main(["init-db", "--database-url", url]) == 0
    try:
        main(["sync", "--profile", "quick", "--database-url", url])
    except RuntimeError as exc:
        assert "LIQUIPEDIA_CONTACT_EMAIL" in str(exc)
    else:
        raise AssertionError("expected sync to refuse example.com contact email")


def test_unknown_profile_fails(tmp_path) -> None:
    db = tmp_path / "esports.db"
    url = f"sqlite:///{db}"
    assert main(["init-db", "--database-url", url]) == 0
    try:
        main(["sync", "--profile", "not-a-profile", "--database-url", url])
    except KeyError as exc:
        assert "not-a-profile" in str(exc)
    else:
        raise AssertionError("expected unknown profile to raise")
