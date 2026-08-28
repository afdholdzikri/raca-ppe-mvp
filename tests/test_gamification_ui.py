"""Tests for deterministic display-only gamification helpers."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import gamification_ui as game


def test_empty_history_has_no_achievements():
    assert game.calculate_display_achievements([]) == []
    assert game.calculate_display_achievements(None) == []


def test_first_safe_decision():
    achievements = game.calculate_display_achievements([{"correct": True, "risk_category": "medium"}])
    assert [item["id"] for item in achievements] == ["first_safe_decision"]


def test_consecutive_safe_decisions():
    history = [{"correct": False}, {"correct": True}, {"correct": True}]
    identifiers = {item["id"] for item in game.calculate_display_achievements(history)}
    assert {"first_safe_decision", "consecutive_safe_decisions"} <= identifiers


def test_mastery_reached():
    history = [{"correct": False, "competence_gaps": {"eye_protection": 0.0, "hand_protection": 0.2}}]
    identifiers = {item["id"] for item in game.calculate_display_achievements(history)}
    assert "mastery_target_reached" in identifiers


def test_critical_hazard_correctly_handled():
    history = [{"correct": True, "risk_category": "Critical"}]
    identifiers = {item["id"] for item in game.calculate_display_achievements(history)}
    assert "critical_hazard_handled" in identifiers


def test_badge_formatters_are_deterministic():
    assert game.format_difficulty_badge(1)["label"] == "Beginner"
    assert game.format_difficulty_badge("advanced")["level"] == 3
    assert game.format_assistance_badge("limited_visual_guidance")["label"] == "Guided"
    assert game.format_assistance_badge("full_visual_guidance")["label"] == "Intensive"


def test_performance_status_supports_partial_result():
    result = {"correct": False, "selected_ppe": ["goggles"], "required_ppe": ["goggles", "respirator"]}
    assert game.format_performance_status(True)["status"] == "correct"
    assert game.format_performance_status(result)["status"] == "partial"
    assert game.format_performance_status(False)["status"] == "incorrect"


def test_helpers_do_not_mutate_scientific_state():
    history = [{
        "correct": True,
        "risk_category": "critical",
        "competence_gaps": {"eye_protection": 0.0},
        "competence_after": {"eye_protection": 0.8},
        "adaptation": "challenge_adaptation",
        "next_scenario": "S3",
    }]
    before = deepcopy(history)
    game.calculate_display_achievements(history)
    game.format_performance_status(history[0])
    assert history == before


def test_module_has_no_scientific_engine_imports():
    source = Path(game.__file__).read_text(encoding="utf-8")
    assert "core.risk_engine" not in source
    assert "core.learner_model" not in source
    assert "core.adaptation_engine" not in source

