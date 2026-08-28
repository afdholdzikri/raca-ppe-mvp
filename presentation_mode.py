"""Pure helpers for publication-safe Serious Game presentation views."""
from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import gamification_ui
import scenario_visual_map


def display_trainee_identifier(identifier: Any, anonymize: bool = False) -> str:
    """Return an anonymized display label without changing the stored identifier."""
    if anonymize:
        return "Trainee T1"
    value = str(identifier or "").strip()
    return value or "Anonymous Trainee"


def build_screenshot_summary(
    domain: str,
    scenario_id: str | None,
    scenario_name: str | None,
    trace: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Build a compact, identifier-free summary from existing presentation data."""
    visual = scenario_visual_map.get_scenario_visual_config(domain, scenario_id, scenario_name)
    record = trace or {}
    performance = gamification_ui.format_performance_status(record) if trace else {
        "status": "pending", "label": "Awaiting Decision", "css_class": "feedback-warning"
    }
    summary = {
        "domain": visual["domain_label"],
        "scenario_id": str(scenario_id or record.get("scenario_id") or "Unavailable"),
        "scenario": visual["visual_title"],
        "risk_category": record.get("risk_category", "Unavailable"),
        "risk_score": record.get("scenario_risk", record.get("normalized_risk")),
        "selected_ppe": list(record.get("selected_ppe") or []),
        "performance": performance["label"],
        "competence": dict(record.get("competence_after") or {}) if isinstance(record.get("competence_after"), Mapping) else record.get("competence_after"),
        "competence_gap": record.get("competence_gaps", record.get("competence_gap")),
        "selected_rule": record.get("selected_rule", record.get("active_rule", "Awaiting decision")),
        "adaptation": record.get("adaptation", "Awaiting decision"),
        "assistance": record.get("assistance", "Unavailable"),
        "next_difficulty": record.get("next_difficulty", "Unavailable"),
        "next_scenario": record.get("next_scenario", "Unavailable"),
        "explanation": record.get("explanation", "Evaluate the PPE decision to generate an explanation."),
    }
    json.dumps(summary)
    return summary

