"""Multi-Agent Team orchestrator on top of the Claude Agent SDK."""

from mat.config import LeadConfig, TeamConfig, TeammateConfig, load_team_config
from mat.lead import TeamLead
from mat.logging import format_cost_summary
from mat.orchestrator import Orchestrator
from mat.teammate import Teammate

# Note: `mat.report.generate_reports` is intentionally NOT re-exported here.
# Doing so causes a RuntimeWarning when `python -m mat.report` is invoked,
# because the submodule ends up in sys.modules before __main__ loads it.
# Import it directly: `from mat.report import generate_reports`.

__all__ = [
    "LeadConfig",
    "Orchestrator",
    "TeamConfig",
    "TeamLead",
    "Teammate",
    "TeammateConfig",
    "format_cost_summary",
    "load_team_config",
]
