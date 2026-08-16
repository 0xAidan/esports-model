from __future__ import annotations

from esports_model.jobs.agent import LABEL, install_agent, render_plist


def test_plist_keeps_alive(tmp_path) -> None:
    (tmp_path / "deploy" / "macos").mkdir(parents=True)
    script = tmp_path / "deploy" / "macos" / "run-serve.sh"
    script.write_text("#!/bin/bash\n", encoding="utf-8")
    text = render_plist(tmp_path)
    assert LABEL in text
    assert "KeepAlive" in text
    assert "RunAtLoad" in text
    assert str(tmp_path.resolve()) in text


def test_install_agent_writes_plist_without_launchctl(tmp_path) -> None:
    (tmp_path / "deploy" / "macos").mkdir(parents=True)
    script = tmp_path / "deploy" / "macos" / "run-serve.sh"
    script.write_text("#!/bin/bash\n", encoding="utf-8")
    home = tmp_path / "home"
    summary = install_agent(project_root=tmp_path, home=home, load=False)
    dest = home / "Library" / "LaunchAgents" / f"{LABEL}.plist"
    assert summary["ok"] is True
    assert dest.exists()
    assert "KeepAlive" in dest.read_text(encoding="utf-8")
    assert summary["loaded"] is False
