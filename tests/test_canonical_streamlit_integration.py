"""Integration contract between the public UI adapter and Canonical V15."""
from __future__ import annotations

import inspect
import json
from pathlib import Path
from statistics import mean

import pytest
from streamlit.testing.v1 import AppTest

import canonical_streamlit_adapter as adapter
import ui_visuals
from core.priority_engine import calculate_global_priorities
from experiments.baseline_methods import MethodInput
from experiments.canonical_config import CanonicalConfig
from experiments.canonical_observable import observation_score, update_engine_estimate
from experiments.experiment_metrics import competence_contextual_risks
from experiments.proposed_method import ProposedMethod


CONFIG = CanonicalConfig(methods=["proposed"], profiles=["T1"])


def _evaluate(domain="manufacturing", scenario_id=None, **overrides):
    data = adapter.load_canonical_domain(domain)
    state = adapter.initial_deployable_state(data)
    scenario_id = scenario_id or state["current_scenario_id"]
    scenario = data["scenarios"][scenario_id]
    values = {
        "domain_data": data,
        "scenario_id": scenario_id,
        "selected_ppe": list(scenario.required_ppe),
        "competence_scores": state["competence_scores"],
        "repeated_errors": state["repeated_errors"],
        "current_difficulty": scenario.base_difficulty,
        "scenario_history": [],
        "recent_scores": [],
        "response_time_seconds": 10.0,
        "time_limit_seconds": scenario.time_limit_seconds,
        "hint_used": False,
        "session_id": "integration-session",
        "episode": 1,
        "config": CONFIG,
    }
    values.update(overrides)
    return data, adapter.evaluate_decision(**values)


def _scientific_projection(result):
    trace = result["trace"]
    return {
        "risk_hat": trace["risk_hat"],
        "learner_estimate_after": trace["learner_estimate_after"],
        "repeated_errors": trace["repeated_errors"],
        "competence_gap": trace["competence_gap"],
        "repetition_factor": trace["repetition_factor"],
        "urgency": trace["urgency"],
        "priority_q": trace["priority_q"],
        "selected_rule": trace["selected_rule"],
        "applied_action": trace["applied_action"],
        "next_scenario": trace["next_scenario"],
    }


def test_adapter_imports_canonical_backend_without_simulation_module():
    source = inspect.getsource(adapter)
    assert "canonical_latent" not in source
    assert "theta_star" not in source
    assert "simulation_only_state_exposed" in source


def test_three_canonical_domains_load_and_validate():
    assert adapter.available_domains() == (
        "manufacturing", "chemical_laboratory", "construction"
    )
    for domain in adapter.available_domains():
        data = adapter.load_canonical_domain(domain)
        assert data["scenarios"] and data["ppe"] and data["hazards"]


@pytest.mark.parametrize("domain", adapter.available_domains())
def test_serious_game_switches_to_each_canonical_domain(domain):
    page = Path(__file__).resolve().parents[1] / "pages" / "1_Serious_Game.py"
    app = AppTest.from_file(str(page), default_timeout=20).run()
    selector = next(item for item in app.selectbox if item.label == "Canonical domain")
    selector.select(domain).run()
    assert not app.exception
    assert app.session_state["active_domain"] == domain
    assert app.session_state["current_scenario_id"] in adapter.load_canonical_domain(domain)["scenarios"]


def test_priority_is_authoritative_and_urgency_occurs_once():
    data, result = _evaluate("manufacturing", "S5", selected_ppe=["goggles", "gloves"])
    trace = result["trace"]
    direct = calculate_global_priorities(
        competence_contextual_risks(data),
        result["competence_scores"],
        result["repeated_errors"],
        data["competencies"],
        CONFIG.repetition_weight,
        CONFIG.target_mastery,
        3,
    )
    assert trace["priority_q"] == direct["priority_by_competence"]
    for competence_id, q_value in trace["priority_q"].items():
        expected = round(
            trace["risk_hat"][competence_id]
            * trace["competence_gap"][competence_id]
            * trace["repetition_factor"][competence_id]
            * trace["urgency"][competence_id],
            4,
        )
        assert q_value == expected
        assert trace["repetition_factor"][competence_id] <= 1.5


def test_learner_update_matches_canonical_observable_engine():
    data, result = _evaluate("manufacturing", "S1")
    trace = result["trace"]
    for competence_id in data["scenarios"]["S1"].target_competencies:
        accuracy = 1.0 if trace["observable_response_features"]["action_accuracy"][competence_id] else 0.0
        z_value = observation_score(accuracy, 1.0, 1.0, CONFIG)
        expected = update_engine_estimate(
            trace["learner_estimate_before"][competence_id], z_value, CONFIG.eta
        )
        assert trace["observation_scores"][competence_id] == z_value
        assert trace["learner_estimate_after"][competence_id] == expected


def test_direct_proposed_policy_and_adapter_are_identical():
    data, result = _evaluate(
        "manufacturing",
        "S5",
        selected_ppe=["goggles", "gloves"],
        scenario_history=["S5", "S5"],
    )
    trace = result["trace"]
    observations = trace["observation_scores"]
    method_input = MethodInput(
        data["scenarios"]["S5"],
        data["scenarios"],
        result["competence_scores"],
        result["repeated_errors"],
        data["scenarios"]["S5"].base_difficulty,
        ["S5", "S5", "S5"],
        [mean(observations.values())],
        data["scenario_risks"]["S5"],
        CONFIG,
        False,
        result["priorities"]["priority_ranking"],
    )
    direct = ProposedMethod().decide(method_input)
    assert trace["selected_rule"] == direct["selected_rule"]
    assert trace["next_difficulty"] == direct["next_difficulty"]
    assert trace["next_assistance"] == direct["assistance"]
    assert trace["feedback"] == direct["feedback"]
    assert trace["repeat_required"] == direct["repeat_required"]
    assert trace["next_scenario"] == direct["next_scenario"]
    assert trace["bounded_rotation_flag"] == direct["bounded_rotation_triggered"]


@pytest.mark.parametrize(
    ("scenario_id", "score", "errors", "selection_mode", "expected_rule"),
    [
        ("S5", 0.40, 0, "missing", "critical_risk_low_mastery"),
        ("S5", 0.70, 2, "missing", "high_risk_repeated_error"),
        ("S5", 0.90, 0, "correct", "high_mastery_high_risk_correct"),
        ("S1", 0.70, 0, "correct", "stable_mastery_correct"),
        ("S1", 0.40, 0, "correct", "default_reinforcement"),
    ],
)
def test_all_r1_to_r5_modes_match_canonical_rule_precedence(
    scenario_id, score, errors, selection_mode, expected_rule
):
    data = adapter.load_canonical_domain("manufacturing")
    state = adapter.initial_deployable_state(data)
    scores = {competence_id: score for competence_id in state["competence_scores"]}
    error_state = {competence_id: errors for competence_id in state["repeated_errors"]}
    scenario = data["scenarios"][scenario_id]
    selected = list(scenario.required_ppe)
    if selection_mode == "missing":
        selected = selected[:-1]
    _, result = _evaluate(
        "manufacturing",
        scenario_id,
        selected_ppe=selected,
        competence_scores=scores,
        repeated_errors=error_state,
    )
    assert result["trace"]["selected_rule"] == expected_rule


@pytest.mark.parametrize("domain", adapter.available_domains())
def test_returned_scenario_is_valid_for_active_domain(domain):
    data, result = _evaluate(domain)
    assert result["trace"]["next_scenario"] in data["scenarios"]


def test_trace_contract_and_no_simulation_state():
    _, result = _evaluate()
    trace = result["trace"]
    assert adapter.CANONICAL_TRACE_FIELDS <= trace.keys()
    assert trace["simulation_only_state_exposed"] is False
    assert "theta_star" not in json.dumps(trace)


def test_reviewer_mode_and_animation_do_not_change_science():
    _, play = _evaluate(reviewer_mode=False, animation_state={"selected_ppe": []})
    _, audit = _evaluate(
        reviewer_mode=True,
        animation_state={"selected_ppe": ["helmet"], "frame": 999},
    )
    assert _scientific_projection(play) == _scientific_projection(audit)


def test_serious_game_page_contains_no_scientific_equations():
    page = (Path(__file__).resolve().parents[1] / "pages" / "1_Serious_Game.py").read_text(
        encoding="utf-8"
    )
    assert "calculate_global_priorities" not in page
    assert "choose_adaptation_v2" not in page
    assert "update_engine_estimate" not in page
    assert "theta_star" not in page


def test_bounded_rotation_matches_canonical_behavior():
    _, result = _evaluate(
        "manufacturing",
        "S5",
        selected_ppe=[],
        scenario_history=["S5", "S5"],
    )
    trace = result["trace"]
    assert trace["bounded_rotation_flag"] is True
    assert trace["requested_action"]["next_scenario"] == "S5"
    assert trace["applied_action"]["next_scenario"] != "S5"


def test_trace_can_be_persisted(tmp_path):
    destination = tmp_path / "trace.jsonl"
    _, result = _evaluate(trace_path=destination)
    assert result["trace"]["persisted_to_file"] is True
    assert json.loads(destination.read_text(encoding="utf-8"))["engine_version"] == adapter.ENGINE_VERSION


def test_dynamic_ppe_overlay_positions_are_presentation_only():
    layers = ui_visuals._ppe_overlay_model(
        ["helmet", "goggles", "respirator", "vest", "gloves", "shoes"]
    )
    assert {layer["ppe_id"] for layer in layers} == {
        "helmet", "goggles", "respirator", "vest", "gloves", "shoes"
    }
    assert all(layer["left"].endswith("%") and layer["top"].endswith("%") for layer in layers)


@pytest.mark.parametrize(
    "page_name", ["2_Training_Dashboard.py", "3_Decision_Trace.py"]
)
def test_canonical_trace_remains_readable_on_existing_pages(page_name):
    data, result = _evaluate()
    page = Path(__file__).resolve().parents[1] / "pages" / page_name
    app = AppTest.from_file(str(page), default_timeout=20)
    app.session_state["active_domain"] = "manufacturing"
    app.session_state["decision_traces"] = [result["trace"]]
    app.session_state["competence_scores"] = result["competence_scores"]
    app.session_state["trainee_id"] = "Anonymous Reviewer"
    app.run()
    assert not app.exception

def test_reviewer_audit_mode_renders_completed_trace_without_exception():
    data, result = _evaluate("manufacturing")
    page = Path(__file__).resolve().parents[1] / "pages" / "1_Serious_Game.py"

    app = AppTest.from_file(str(page), default_timeout=20)

    app.session_state["active_domain"] = "manufacturing"
    app.session_state["decision_traces"] = [result["trace"]]
    app.session_state["last_trace"] = result["trace"]
    app.session_state["competence_scores"] = result["competence_scores"]
    app.session_state["repeated_errors"] = result["repeated_errors"]
    app.session_state["recent_scores"] = result["recent_scores"]
    app.session_state["trainee_id"] = "Anonymous Reviewer"
    app.session_state["submission_processed"] = True

    app.run()

    mode = next(
        item for item in app.radio
        if item.label == "Interface mode"
    )
    mode.set_value("Reviewer / Audit Mode").run()

    assert not app.exception