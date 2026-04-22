"""YAML config loader tests."""

from __future__ import annotations

from pathlib import Path

from mat.config import load_team_config

TEAMS_DIR = Path(__file__).parent.parent / "teams"


def test_load_example_team() -> None:
    cfg = load_team_config(TEAMS_DIR / "example_team.yaml")
    assert cfg.name == "research-squad"
    assert cfg.lead.model == "claude-haiku-4-5"
    assert [t.name for t in cfg.teammates] == ["researcher", "analyst", "writer"]
    for t in cfg.teammates:
        assert t.system_prompt, f"{t.name} should have inlined system_prompt"


def test_load_haiku_team() -> None:
    cfg = load_team_config(TEAMS_DIR / "haiku_team.yaml")
    assert cfg.name == "haiku-team"
    assert cfg.lead.model == "claude-haiku-4-5"
    assert len(cfg.teammates) == 1
    assert cfg.teammates[0].name == "haiku_writer"
    assert cfg.teammates[0].system_prompt
    assert "haiku" in cfg.teammates[0].system_prompt.lower()


def test_load_messaging_demo_team() -> None:
    cfg = load_team_config(TEAMS_DIR / "messaging_demo_team.yaml")
    assert cfg.name == "messaging-demo"
    assert [t.name for t in cfg.teammates] == ["researcher", "writer"]
    assert cfg.settings.cc_lead_on_messages is True
    assert cfg.settings.unread_backpressure_threshold == 5
    for t in cfg.teammates:
        assert t.system_prompt, f"{t.name} should have inlined system_prompt"
