from __future__ import annotations

from pathlib import Path

import pytest

from esports_model.jobs.bootstrap import is_real_email, run_bootstrap

EXAMPLE = Path(__file__).resolve().parents[2] / ".env.example"


def test_example_email_is_rejected() -> None:
    assert is_real_email("you@example.com") is False
    assert is_real_email("ada@cs2.test") is True


def test_bootstrap_refuses_example_git_email(tmp_path) -> None:
    (tmp_path / ".env.example").write_text(EXAMPLE.read_text(encoding="utf-8"))
    with pytest.raises(RuntimeError, match="real LIQUIPEDIA_CONTACT_EMAIL"):
        run_bootstrap(
            project_root=tmp_path,
            database_url=f"sqlite:///{tmp_path / 'boot.db'}",
            git_email_fn=lambda: "ada@example.com",
        )


def test_bootstrap_writes_env_from_git_email(tmp_path) -> None:
    (tmp_path / ".env.example").write_text(EXAMPLE.read_text(encoding="utf-8"))
    url = f"sqlite:///{tmp_path / 'boot.db'}"
    summary = run_bootstrap(
        project_root=tmp_path,
        database_url=url,
        git_email_fn=lambda: "operator@cs2.test",
    )
    text = (tmp_path / ".env").read_text(encoding="utf-8")
    assert summary["ok"] is True
    assert summary["email_source"] == "git"
    assert "LIQUIPEDIA_CONTACT_EMAIL=operator@cs2.test" in text
    assert "example.com" not in text.split("LIQUIPEDIA_CONTACT_EMAIL=")[1].splitlines()[0]
    assert (tmp_path / "boot.db").exists()
