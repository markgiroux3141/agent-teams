"""YAML team definitions → validated dataclasses (spec §7)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class LeadConfig:
    model: str = "claude-sonnet-4-6"
    max_turns: int = 200
    extra_instructions: str = ""


@dataclass
class TeammateConfig:
    name: str
    model: str
    description: str
    allowed_tools: list[str] = field(default_factory=list)
    system_prompt_file: str | None = None
    system_prompt: str | None = None


@dataclass
class TeamSettings:
    workspace_readonly_for_lead: bool = True
    max_parallel_teammates: int = 3
    stall_timeout_seconds: int = 300
    cc_lead_on_messages: bool = True
    unread_backpressure_threshold: int = 5
    max_loop_iterations: int = 20


@dataclass
class TeamConfig:
    name: str
    lead: LeadConfig
    teammates: list[TeammateConfig]
    settings: TeamSettings = field(default_factory=TeamSettings)


def load_team_config(path: Path) -> TeamConfig:
    """Load a team YAML and inline any `system_prompt_file` references."""
    path = Path(path)
    base = path.parent
    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    lead_raw = raw.get("lead", {}) or {}
    lead = LeadConfig(
        model=lead_raw.get("model", "claude-sonnet-4-6"),
        max_turns=lead_raw.get("max_turns", 200),
        extra_instructions=lead_raw.get("extra_instructions", ""),
    )

    teammates: list[TeammateConfig] = []
    for t in raw.get("teammates", []):
        prompt = t.get("system_prompt")
        prompt_file = t.get("system_prompt_file")
        if not prompt and prompt_file:
            prompt = (base / prompt_file).read_text(encoding="utf-8")
        teammates.append(
            TeammateConfig(
                name=t["name"],
                model=t.get("model", "claude-sonnet-4-6"),
                description=t.get("description", ""),
                allowed_tools=list(t.get("allowed_tools", [])),
                system_prompt_file=prompt_file,
                system_prompt=prompt,
            )
        )

    settings_raw = raw.get("settings", {}) or {}
    settings = TeamSettings(
        workspace_readonly_for_lead=settings_raw.get("workspace_readonly_for_lead", True),
        max_parallel_teammates=settings_raw.get("max_parallel_teammates", 3),
        stall_timeout_seconds=settings_raw.get("stall_timeout_seconds", 300),
        cc_lead_on_messages=settings_raw.get("cc_lead_on_messages", True),
        unread_backpressure_threshold=settings_raw.get("unread_backpressure_threshold", 5),
        max_loop_iterations=settings_raw.get("max_loop_iterations", 20),
    )

    return TeamConfig(
        name=raw["name"],
        lead=lead,
        teammates=teammates,
        settings=settings,
    )
