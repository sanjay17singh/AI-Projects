"""Red-flag precision — prevents an agent from over-flagging (marking
everything as a red flag to maximize recall). Like red_flag_recall, the
semantic "is this agent flag actually correct" judgment comes from
judges/red_flag_judge.py; this module only computes the ratio."""

from app.schemas.analysis import RedFlag


def red_flag_precision(agent_red_flags: list[RedFlag], correct_agent_flag_ids: set[str]) -> float:
    """Correct agent red flags / all agent red flags. No red flags reported
    -> vacuous 1.0 (nothing incorrect was reported)."""
    if not agent_red_flags:
        return 1.0
    correct = sum(1 for f in agent_red_flags if (f.red_flag_id or "") in correct_agent_flag_ids)
    return round(correct / len(agent_red_flags), 4)
