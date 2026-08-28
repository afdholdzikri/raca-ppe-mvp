"""Tests for backward-compatible, read-only trace presentation helpers."""
from __future__ import annotations

import json
from copy import deepcopy

from core.trace_manager import REQUIRED_TRACE_FIELDS
import trace_visuals


def _old_trace():
    trace = {key: "value" for key in REQUIRED_TRACE_FIELDS}
    trace.update(
        {
            "scenario_id": "S5",
            "zone": "Chemical Mixing Area",
            "normalized_risk": 0.8,
            "competence_gap": 0.3,
            "training_priority": 0.24,
            "active_rule": "high_risk_low_competence",
            "adaptation": "priority_remediation",
            "correct": False,
            "episode": 1,
        }
    )
    return trace


def test_old_v1_trace_remains_readable():
    trace = _old_trace()
    completeness = trace_visuals.trace_completeness_display(trace)
    flow = trace_visuals.build_visual_explanation_flow(trace)
    assert completeness["schema"] == "V1"
    assert completeness["status"] == "complete"
    assert trace_visuals.trace_filter_value(trace, "selected_rule") == "high_risk_low_competence"
    assert [item["stage"] for item in flow] == [
        "Context", "Risk", "Competence gap", "Priority", "Adaptation", "Next scenario"
    ]


def test_missing_visual_metadata_is_tolerated():
    trace = {"episode": 1, "scenario_id": "CL2", "correct": True}
    assert trace_visuals.infer_trace_domain(trace) == "chemical_laboratory"
    assert trace_visuals.trace_completeness_display(trace)["status"] == "partial"
    assert trace_visuals.build_visual_explanation_flow(trace)[0]["value"].startswith("CL2")


def test_helpers_do_not_write_scientific_or_visual_fields():
    trace = _old_trace()
    before = deepcopy(trace)
    trace_visuals.trace_completeness_display(trace)
    trace_visuals.build_visual_explanation_flow(trace)
    trace_visuals.infer_trace_domain(trace)
    assert trace == before


def test_helper_outputs_are_json_serializable():
    trace = _old_trace()
    json.dumps(trace_visuals.trace_completeness_display(trace))
    json.dumps(trace_visuals.build_visual_explanation_flow(trace))

