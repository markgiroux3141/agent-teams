"""Canary: every module in the `mat` package imports cleanly and re-exports
the expected public surface. Cheap smoke test for scaffolding health.
"""

from __future__ import annotations

import inspect


def test_package_reexports() -> None:
    import mat

    assert inspect.isclass(mat.Orchestrator)
    assert inspect.isclass(mat.TeamLead)
    assert inspect.isclass(mat.Teammate)
    assert inspect.isclass(mat.TeamConfig)
    assert inspect.isclass(mat.TeammateConfig)
    assert inspect.isclass(mat.LeadConfig)
    assert callable(mat.load_team_config)


def test_submodules_import() -> None:
    import mat.config  # noqa: F401
    import mat.lead  # noqa: F401
    import mat.logging  # noqa: F401
    import mat.orchestrator  # noqa: F401
    import mat.state.message_bus  # noqa: F401
    import mat.state.task_store  # noqa: F401
    import mat.teammate  # noqa: F401
    import mat.tools  # noqa: F401
    import mat.tools.messaging  # noqa: F401
    import mat.tools.status  # noqa: F401
    import mat.tools.task_board  # noqa: F401
