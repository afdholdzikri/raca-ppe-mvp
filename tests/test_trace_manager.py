import json

from core.trace_manager import REQUIRED_TRACE_FIELDS, append_trace_jsonl, create_decision_trace
from core.trace_manager import V2_REQUIRED_TRACE_FIELDS, create_v2_trace


def sample_trace():
    return create_decision_trace(
        session_id="session-test", episode=1, scenario_id="S5",
        zone="Chemical Mixing Area", task="Mixing chemical materials",
        hazards=["toxic vapour", "liquid chemical splash"],
        selected_ppe=["safety goggles"], required_ppe=["safety goggles", "respirator"],
        missing_ppe=["respirator"], unnecessary_ppe=[], correct=False,
        probability=4, severity=5, exposure=5, context_modifier=1.0,
        normalized_risk=0.5333, competence_before=0.4, observation_score=0.4,
        competence_after=0.4, repeated_errors=1, training_priority=0.48,
        active_rule="default_reinforcement", adaptation="reinforcement_adaptation",
        current_difficulty=2, next_difficulty=2,
        assistance="limited_visual_guidance", feedback="direct_explanation",
        repeat_required=False, adaptation_latency_ms=0.5,
    )


def test_all_required_fields_exist():
    assert REQUIRED_TRACE_FIELDS <= sample_trace().keys()


def test_explanation_is_not_empty():
    assert sample_trace()["explanation"]


def test_json_lines_serialization_succeeds(tmp_path):
    destination = tmp_path / "traces.jsonl"
    assert append_trace_jsonl(sample_trace(), destination)
    loaded = json.loads(destination.read_text(encoding="utf-8").strip())
    assert loaded["scenario_id"] == "S5"

def test_v2_trace_complete_explained_and_serializable(tmp_path):
    values={key:None for key in V2_REQUIRED_TRACE_FIELDS}
    values.update(session_id="s",trainee_id="anonymous",episode=1,scenario_id="S5",
        correct=False,scenario_risk=.8,risk_category="Critical",
        highest_priority_competence="respiratory_protection_selection",
        selected_rule="critical_risk_low_mastery",adaptation="priority_remediation",
        next_scenario="S5",next_difficulty=2,assistance="full_visual_guidance")
    values.pop("timestamp_utc"); values.pop("explanation")
    trace=create_v2_trace(**values)
    assert V2_REQUIRED_TRACE_FIELDS<=trace.keys()
    assert trace["selected_rule"] in trace["explanation"]
    assert append_trace_jsonl(trace,tmp_path/"v2.jsonl")

def test_storage_failure_is_safe(tmp_path):
    assert append_trace_jsonl(sample_trace(),tmp_path) is False
