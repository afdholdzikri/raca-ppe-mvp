"""Streamlit integration checks for the visual Serious Game page."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


PAGE = Path(__file__).resolve().parents[1] / "pages" / "1_Serious_Game.py"


def _run_page() -> AppTest:
    app = AppTest.from_file(str(PAGE), default_timeout=20)
    return app.run()


def test_serious_game_page_imports_and_renders_visual_layout():
    app = _run_page()
    assert not app.exception
    labels = {item.value for item in app.subheader}
    assert {
        "Workplace Context",
        "Contextual Risk",
        "Select Personal Protective Equipment",
        "Target Competence Progress",
        "Display Achievements",
        "Next Adaptation",
    } <= labels
    assert len(app.checkbox) > 0


def test_visual_ppe_keys_are_stable_and_session_scenario_scoped():
    app = _run_page()
    session_key = app.session_state["session_id"].replace("-", "_").lower()
    scenario_key = app.session_state["current_scenario_id"].lower()
    keys_before = [checkbox.key for checkbox in app.checkbox if str(checkbox.key).startswith("ppe_select_")]
    assert all(key.startswith(f"ppe_select_{session_key}_{scenario_key}__ppe__") for key in keys_before)
    app.run()
    assert [checkbox.key for checkbox in app.checkbox if str(checkbox.key).startswith("ppe_select_")] == keys_before
    assert not app.exception


def test_evaluation_runs_once_produces_trace_and_preserves_selection_list():
    with patch("core.trace_manager.append_trace_jsonl", return_value=True):
        app = _run_page()
        for checkbox in app.checkbox:
            if checkbox.label in {"Safety Vest", "Safety Shoes"}:
                checkbox.check()
        next(button for button in app.button if button.label == "Evaluate PPE Decision").click().run()

        assert not app.exception
        assert app.session_state["submission_processed"] is True
        assert isinstance(app.session_state["ppe_selection"], list)
        assert set(app.session_state["ppe_selection"]) == {"vest", "shoes"}
        assert len(app.session_state["decision_traces"]) == 1
        assert app.session_state["last_trace"]["correct"] is True
        assert any("first fully correct PPE decision" in item.value for item in app.caption)

        app.run()
        assert not app.exception
        assert len(app.session_state["decision_traces"]) == 1


def test_invalid_scenario_has_friendly_empty_state():
    app = AppTest.from_file(str(PAGE), default_timeout=20)
    app.session_state["current_scenario_id"] = "NOT_A_SCENARIO"
    app.run()
    assert not app.exception
    assert any("No valid training scenario" in item.value for item in app.error)


def _submit_correct(app):
    for checkbox in app.checkbox:
        if checkbox.label in {"Safety Vest", "Safety Shoes"}:
            checkbox.check()
    with patch("core.trace_manager.append_trace_jsonl", return_value=True):
        next(button for button in app.button if button.label == "Evaluate PPE Decision").click().run()
    return app


def test_screenshot_mode_is_presentation_only_and_keeps_normal_controls():
    normal = _run_page()
    assert any(button.label == "Evaluate PPE Decision" for button in normal.button)
    assert any(expander.label == "Why did the framework choose this adaptation?" for expander in normal.expander)

    scientific_keys = (
        "session_id", "trainee_id", "current_scenario_id", "current_difficulty",
        "competence_scores", "repeated_errors", "decision_traces", "assistance",
    )
    before = {key: normal.session_state[key] for key in scientific_keys}
    next(box for box in normal.checkbox if box.label == "Paper Screenshot Mode").check().run()
    after = {key: normal.session_state[key] for key in scientific_keys}
    assert before == after
    assert not normal.exception
    assert any(item.value == "Explainable Decision" for item in normal.subheader)
    assert not any(expander.label == "Why did the framework choose this adaptation?" for expander in normal.expander)


def test_anonymization_does_not_modify_stored_trainee_identifier():
    app = _run_page()
    stored = app.session_state["trainee_id"]
    next(box for box in app.checkbox if box.label == "Anonymize trainee identifiers").check().run()
    assert app.session_state["trainee_id"] == stored
    displayed = [item.value for item in app.caption] + [item.value for item in app.markdown]
    assert any("Trainee T1" in str(value) for value in displayed)


def test_screenshot_mode_does_not_change_scientific_outputs():
    normal = _submit_correct(_run_page())
    screenshot = _run_page()
    next(box for box in screenshot.checkbox if box.label == "Paper Screenshot Mode").check().run()
    screenshot = _submit_correct(screenshot)
    fields = {
        "scenario_id", "active_hazards", "hazard_risk_values", "scenario_risk",
        "mean_risk", "risk_category", "response_score", "independence_score",
        "selected_ppe", "required_ppe", "missing_ppe", "unnecessary_ppe", "correct",
        "affected_competencies", "competence_before", "observation_scores",
        "competence_after", "repeated_errors", "competence_gaps",
        "priority_by_competence", "highest_priority_competence", "highest_priority_value",
        "active_rules", "selected_rule", "adaptation", "assistance", "distractor_level",
        "feedback", "repeat_required", "current_difficulty", "next_difficulty",
        "current_scenario", "next_scenario",
    }
    normal_trace = normal.session_state["last_trace"]
    screenshot_trace = screenshot.session_state["last_trace"]
    assert {key: normal_trace[key] for key in fields} == {key: screenshot_trace[key] for key in fields}
    assert not screenshot.exception
