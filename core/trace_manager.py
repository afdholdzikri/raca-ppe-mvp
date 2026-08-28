"""Creation and resilient JSON Lines persistence of decision traces."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUIRED_TRACE_FIELDS = {
    "session_id", "timestamp_utc", "episode", "scenario_id", "zone", "task",
    "hazards", "selected_ppe", "required_ppe", "missing_ppe", "unnecessary_ppe",
    "correct", "probability", "severity", "exposure", "context_modifier",
    "normalized_risk", "competence_before", "observation_score",
    "competence_after", "repeated_errors", "competence_gap", "training_priority",
    "active_rule", "adaptation", "current_difficulty", "next_difficulty",
    "assistance", "feedback", "repeat_required", "adaptation_latency_ms",
    "explanation",
}

V2_REQUIRED_TRACE_FIELDS = {
    "session_id","trainee_id","timestamp_utc","episode","scenario_id","zone","task",
    "narrative","difficulty","active_hazards","hazard_risk_values","scenario_risk",
    "mean_risk","risk_category","time_limit_seconds","response_time_seconds",
    "response_score","hint_used","independence_score","selected_ppe","required_ppe",
    "missing_ppe","unnecessary_ppe","correct","affected_competencies",
    "competence_before","observation_scores","competence_after","repeated_errors",
    "competence_gaps","priority_by_competence","highest_priority_competence",
    "highest_priority_value","active_rules","selected_rule","adaptation","assistance",
    "distractor_level","feedback","repeat_required","current_difficulty",
    "next_difficulty","current_scenario","next_scenario","adaptation_latency_ms",
    "explanation",
}


def build_explanation(trace: dict[str, Any]) -> str:
    """Produce a concise human-readable account of the selected rule."""
    reasons = {
        "high_risk_low_competence":
            "the chemical-exposure risk was high and learner competence was below the required level",
        "high_risk_repeated_error":
            "the task risk was high and the learner made repeated errors",
        "high_competence_high_risk":
            "learner competence was high despite the high-risk context",
        "stable_competence":
            "learner competence was stable enough for progression",
        "default_reinforcement":
            "the evidence supported continued reinforcement",
    }
    reason = reasons.get(trace["active_rule"], "the active adaptation rule matched")
    direction = {
        -1: "reduces difficulty",
        0: "maintains difficulty",
        1: "increases difficulty",
    }.get(trace["next_difficulty"] - trace["current_difficulty"], "adjusts difficulty")
    adaptation = trace["adaptation"].replace("_", " ")
    assistance = trace["assistance"].replace("_", " ")
    return (
        f"The system selected {adaptation} because {reason}. "
        f"The next episode {direction} and activates {assistance}."
    )


def create_decision_trace(**values: Any) -> dict[str, Any]:
    """Create a complete trace, adding timestamp, competence gap, and explanation."""
    trace = dict(values)
    trace.setdefault("timestamp_utc", datetime.now(timezone.utc).isoformat())
    if "competence_after" in trace:
        trace.setdefault("competence_gap", round(1 - trace["competence_after"], 4))
    trace.setdefault("explanation", "")
    missing = REQUIRED_TRACE_FIELDS - trace.keys()
    if missing:
        raise ValueError(f"Missing required trace fields: {', '.join(sorted(missing))}")
    if not trace["explanation"]:
        trace["explanation"] = build_explanation(trace)
    return trace


def append_trace_jsonl(
    trace: dict[str, Any],
    path: str | Path = Path("storage") / "decision_traces.jsonl",
) -> bool:
    """Append a trace as JSON Lines; return False instead of crashing on I/O failure."""
    try:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(trace, ensure_ascii=False) + "\n")
        return True
    except (OSError, TypeError, ValueError):
        return False


def create_v2_trace(**values: Any) -> dict[str, Any]:
    trace = dict(values)
    trace.setdefault("timestamp_utc", datetime.now(timezone.utc).isoformat())
    missing = V2_REQUIRED_TRACE_FIELDS - trace.keys() - {"explanation"}
    if missing: raise ValueError(f"Missing required Version 2 trace fields: {', '.join(sorted(missing))}")
    if not trace.get("explanation"):
        status = "correct" if trace["correct"] else "incorrect"
        trace["explanation"] = (
            f"The PPE decision was {status}. Risk was {trace['risk_category']} "
            f"({trace['scenario_risk']:.4f}), so {trace['highest_priority_competence']} "
            f"was prioritized. Rule {trace['selected_rule']} selected "
            f"{trace['adaptation']}; next the system will use scenario "
            f"{trace['next_scenario']} at difficulty {trace['next_difficulty']} "
            f"with {trace['assistance']}."
        )
    return trace
