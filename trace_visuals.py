"""Read-only compatibility helpers for dashboard and decision-trace visuals."""
from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import assets_manager
from core.trace_manager import REQUIRED_TRACE_FIELDS, V2_REQUIRED_TRACE_FIELDS


def trace_value(trace: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    """Return the first present, non-null trace value without modifying the trace."""
    for key in keys:
        if key in trace and trace[key] is not None:
            return trace[key]
    return default


def infer_trace_domain(trace: Mapping[str, Any]) -> str:
    """Infer a presentation domain from explicit metadata or scenario ID."""
    explicit = assets_manager.normalize_asset_key(str(trace.get("domain", "")))
    if explicit in {"manufacturing", "chemical_laboratory", "construction"}:
        return explicit
    scenario_id = str(trace.get("scenario_id", trace.get("current_scenario", ""))).strip().upper()
    if scenario_id.startswith("CL"):
        return "chemical_laboratory"
    if scenario_id.startswith("C"):
        return "construction"
    return "manufacturing"


def trace_completeness_display(trace: Mapping[str, Any]) -> dict[str, Any]:
    """Measure display completeness against the existing V1 or V2 trace schema."""
    is_v2 = any(key in trace for key in ("scenario_risk", "selected_rule", "affected_competencies"))
    required = V2_REQUIRED_TRACE_FIELDS if is_v2 else REQUIRED_TRACE_FIELDS
    present = sorted(key for key in required if key in trace and trace[key] is not None)
    missing = sorted(required - set(present))
    ratio = len(present) / len(required) if required else 1.0
    result = {
        "schema": "V2" if is_v2 else "V1",
        "present_fields": len(present),
        "required_fields": len(required),
        "missing_fields": missing,
        "ratio": round(ratio, 4),
        "percentage": round(ratio * 100.0, 1),
        "status": "complete" if not missing else "partial",
    }
    json.dumps(result)
    return result


def build_visual_explanation_flow(trace: Mapping[str, Any]) -> list[dict[str, str]]:
    """Build a presentation flow from existing trace values only."""
    scenario = str(trace_value(trace, "scenario_id", "current_scenario", default="Unknown"))
    zone = str(trace_value(trace, "zone", default="Context unavailable"))
    risk_category = str(trace_value(trace, "risk_category", default="Unclassified"))
    risk_score = trace_value(trace, "scenario_risk", "normalized_risk")
    gap_value = trace_value(trace, "competence_gaps", "competence_gap", default="Unavailable")
    priority = trace_value(
        trace,
        "highest_priority_competence",
        "training_priority",
        default="Unavailable",
    )
    adaptation = str(trace_value(trace, "adaptation", default="Unavailable"))
    next_scenario = str(trace_value(trace, "next_scenario", default="Unavailable"))
    risk_text = risk_category if risk_score is None else f"{risk_category} ({risk_score})"
    flow = [
        {"stage": "Context", "value": f"{scenario}: {zone}"},
        {"stage": "Risk", "value": risk_text},
        {"stage": "Competence gap", "value": str(gap_value)},
        {"stage": "Priority", "value": str(priority)},
        {"stage": "Adaptation", "value": adaptation},
        {"stage": "Next scenario", "value": next_scenario},
    ]
    json.dumps(flow)
    return flow


def trace_filter_value(trace: Mapping[str, Any], field: str) -> Any:
    """Return compatible values for Decision Trace filters and summaries."""
    aliases = {
        "scenario_id": ("scenario_id", "current_scenario"),
        "risk_category": ("risk_category",),
        "adaptation": ("adaptation",),
        "selected_rule": ("selected_rule", "active_rule"),
        "highest_priority_competence": ("highest_priority_competence",),
        "next_scenario": ("next_scenario",),
        "correct": ("correct",),
        "episode": ("episode",),
    }
    return trace_value(trace, *aliases.get(field, (field,)), default="Unavailable")

