"""Tests for the write_scratchpad MCP tool + the max_loop_iterations setting.

The scratchpad tool is invoked indirectly via its factory; we call the
returned async callables directly because the MCP server runtime isn't
needed for validating the file-write + whitelist behavior."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from mat.config import TeamConfig, LeadConfig, TeamSettings, TeammateConfig, load_team_config
from mat.tools.status import DEFAULT_SCRATCHPAD_FILES, make_scratchpad_tool


def _call(tool_fn, **kwargs):
    """Unwrap the @tool decorator to get the underlying async handler.

    The claude_agent_sdk `@tool` decorator returns an object with the
    handler stored in a known slot — we invoke it the same way the MCP
    runtime would."""
    # The SDK stores the handler under .handler; fall back to calling the
    # object itself if future versions flatten the wrapper.
    handler = getattr(tool_fn, "handler", tool_fn)
    return asyncio.run(handler(kwargs))


def test_write_scratchpad_writes_whitelisted_file(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    [tool_fn] = make_scratchpad_tool(workspace)

    result = _call(tool_fn, filename="DONE_CRITERIA.md", content="- be concrete\n")
    assert not result.get("is_error")

    target = workspace / "DONE_CRITERIA.md"
    assert target.exists()
    assert target.read_text(encoding="utf-8") == "- be concrete\n"


def test_write_scratchpad_rejects_non_whitelisted_name(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    [tool_fn] = make_scratchpad_tool(workspace)

    result = _call(tool_fn, filename="secret.md", content="nope")
    assert result.get("is_error") is True
    assert not (workspace / "secret.md").exists()


def test_write_scratchpad_rejects_path_components(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    [tool_fn] = make_scratchpad_tool(
        workspace, allowed_filenames=frozenset({"../escape.md"})
    )
    # Even if somehow whitelisted, path components must be rejected.
    result = _call(tool_fn, filename="../escape.md", content="nope")
    assert result.get("is_error") is True


def test_write_scratchpad_rejects_absolute_like(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    # Use a filename containing a separator — should be refused at the
    # bare-filename check regardless of whitelist.
    [tool_fn] = make_scratchpad_tool(
        workspace, allowed_filenames=frozenset({"sub/x.md"})
    )
    result = _call(tool_fn, filename="sub/x.md", content="nope")
    assert result.get("is_error") is True


def test_write_scratchpad_overwrites(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    [tool_fn] = make_scratchpad_tool(workspace)

    _call(tool_fn, filename="DONE_CRITERIA.md", content="v1")
    _call(tool_fn, filename="DONE_CRITERIA.md", content="v2")
    assert (workspace / "DONE_CRITERIA.md").read_text(encoding="utf-8") == "v2"


def test_default_whitelist_has_done_criteria():
    assert "DONE_CRITERIA.md" in DEFAULT_SCRATCHPAD_FILES


def test_max_loop_iterations_defaults_to_20():
    cfg = TeamConfig(
        name="t", lead=LeadConfig(),
        teammates=[TeammateConfig(name="a", model="m", description="")],
    )
    assert cfg.settings.max_loop_iterations == 20


def test_refactor_team_yaml_loads_with_new_settings():
    cfg = load_team_config(Path(__file__).resolve().parent.parent / "teams" / "refactor_loop_team.yaml")
    assert cfg.name == "refactor-loop"
    assert cfg.settings.max_loop_iterations == 40
    assert cfg.settings.stall_timeout_seconds == 600
    assert [t.name for t in cfg.teammates] == ["poc_dev", "critic", "refactor_dev"]
