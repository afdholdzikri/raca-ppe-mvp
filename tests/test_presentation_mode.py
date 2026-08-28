"""Tests for publication-safe presentation helpers."""
from __future__ import annotations

from copy import deepcopy

import pytest

import presentation_mode


def _trace():
    return {
        "session_id": "private-session-id",
        "trainee_id": "Participant 17",
        "scenario_id": "S1",
        "risk_category": "Medium",
        "scenario_risk": 0.32,
        "selected_ppe": ["vest", "shoes"],
        "required_ppe": ["vest", "shoes"],
        "correct": True,
        "competence_after": {"visibility": 0.62},
        "competence_gaps": {"visibility": 0.18},
        "selected_rule": "default_reinforcement",
        "adaptation": "reinforcement_adaptation",
        "assistance": "limited_visual_guidance",
        "next_difficulty": 1,
        "next_scenario": "S6",
        "explanation": "Existing scientific explanation.",
    }


def test_anonymization_is_display_only():
    trace = _trace()
    before = deepcopy(trace)
    assert presentation_mode.display_trainee_identifier(trace["trainee_id"], True) == "Trainee T1"
    assert presentation_mode.display_trainee_identifier(trace["trainee_id"], False) == "Participant 17"
    assert trace == before


def test_screenshot_summary_omits_identifiers_and_preserves_values():
    trace = _trace()
    before = deepcopy(trace)
    summary = presentation_mode.build_screenshot_summary("manufacturing", "S1", None, trace)
    assert "session_id" not in summary
    assert "trainee_id" not in summary
    assert summary["risk_score"] == trace["scenario_risk"]
    assert summary["competence"] == trace["competence_after"]
    assert summary["adaptation"] == trace["adaptation"]
    assert trace == before


@pytest.mark.parametrize(
    ("domain", "scenario_id"),
    [("manufacturing", "S1"), ("chemical_laboratory", "CL1"), ("construction", "C1")],
)
def test_screenshot_summary_supports_all_domains(domain, scenario_id):
    summary = presentation_mode.build_screenshot_summary(domain, scenario_id, None, None)
    assert summary["domain"] != "Unknown Domain"
    assert summary["scenario_id"] == scenario_id

