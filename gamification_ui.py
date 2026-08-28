"""Deterministic, display-only gamification helpers for the Serious Game UI."""
from __future__ import annotations

import html
from collections.abc import Mapping, Sequence
from typing import Any

import streamlit as st

import assets_manager


def _achievement(identifier: str, label: str, description: str) -> dict[str, str]:
    return {
        "id": identifier,
        "label": label,
        "description": description,
        "status": "earned",
    }


def _is_mastery_reached(record: Mapping[str, Any]) -> bool:
    gaps = record.get("competence_gaps")
    if isinstance(gaps, Mapping):
        for value in gaps.values():
            try:
                if float(value) <= 0:
                    return True
            except (TypeError, ValueError):
                continue
    try:
        return "competence_gap" in record and float(record["competence_gap"]) <= 0
    except (TypeError, ValueError):
        return False


def calculate_display_achievements(history: Sequence[Mapping[str, Any]] | None) -> list[dict[str, str]]:
    """Derive earned display badges from trace history without mutating it."""
    records = [record for record in (history or []) if isinstance(record, Mapping)]
    if not records:
        return []

    achievements: list[dict[str, str]] = []
    correct_values = [record.get("correct") is True for record in records]
    if any(correct_values):
        achievements.append(
            _achievement("first_safe_decision", "First Safe Decision", "Completed the first fully correct PPE decision.")
        )

    longest_streak = 0
    current_streak = 0
    for correct in correct_values:
        current_streak = current_streak + 1 if correct else 0
        longest_streak = max(longest_streak, current_streak)
    if longest_streak >= 2:
        achievements.append(
            _achievement(
                "consecutive_safe_decisions",
                "Consecutive Safe Decisions",
                f"Achieved a safe-decision streak of {longest_streak}.",
            )
        )

    if any(
        record.get("correct") is True
        and assets_manager.normalize_asset_key(str(record.get("risk_category", ""))) == "critical"
        for record in records
    ):
        achievements.append(
            _achievement(
                "critical_hazard_handled",
                "Critical Hazard Correctly Handled",
                "Completed a fully correct decision in a critical-risk context.",
            )
        )

    if any(_is_mastery_reached(record) for record in records):
        achievements.append(
            _achievement("mastery_target_reached", "Mastery Target Reached", "Reached at least one recorded competence target.")
        )
    return achievements


def format_difficulty_badge(value: Any) -> dict[str, str | int | None]:
    """Format an existing difficulty value as a presentation badge."""
    normalized = assets_manager.normalize_asset_key(str(value or ""))
    aliases = {
        "1": (1, "Beginner"),
        "beginner": (1, "Beginner"),
        "2": (2, "Intermediate"),
        "intermediate": (2, "Intermediate"),
        "3": (3, "Advanced"),
        "advanced": (3, "Advanced"),
    }
    level, label = aliases.get(normalized, (None, "Unspecified"))
    return {"label": label, "level": level, "css_class": "difficulty-badge"}


def format_assistance_badge(value: Any) -> dict[str, str]:
    """Map existing assistance modes to concise display-only labels."""
    normalized = assets_manager.normalize_asset_key(str(value or ""))
    label = {
        "none": "None",
        "minimal": "Low",
        "low": "Low",
        "limited_visual_guidance": "Guided",
        "guided": "Guided",
        "full_visual_guidance": "Intensive",
        "intensive": "Intensive",
    }.get(normalized, "Unspecified")
    return {"label": label, "source_value": normalized, "css_class": "assistance-badge"}


def format_performance_status(result: Any) -> dict[str, str]:
    """Format an existing evaluation result as correct, partial, or incorrect."""
    if isinstance(result, Mapping):
        correct = result.get("correct") is True
        selected = set(result.get("selected_ppe") or [])
        required = set(result.get("required_ppe") or [])
        explicit = assets_manager.normalize_asset_key(str(result.get("status", "")))
        partial = not correct and (bool(selected & required) or explicit in {"partial", "partially_correct"})
    else:
        correct = result is True or assets_manager.normalize_asset_key(str(result or "")) == "correct"
        explicit = assets_manager.normalize_asset_key(str(result or ""))
        partial = explicit in {"partial", "partially_correct"}
    if correct:
        return {"status": "correct", "label": "Correct", "css_class": "feedback-correct"}
    if partial:
        return {"status": "partial", "label": "Partially Correct", "css_class": "feedback-warning"}
    return {"status": "incorrect", "label": "Incorrect", "css_class": "feedback-incorrect"}


def render_achievement_badges(achievements: Sequence[Mapping[str, Any]]) -> None:
    """Render earned achievement badges without changing application state."""
    if not achievements:
        st.caption("No display achievements earned yet.")
        return
    columns = st.columns(min(4, len(achievements)))
    for index, achievement in enumerate(achievements):
        label = html.escape(str(achievement.get("label", "Achievement")), quote=True)
        description = html.escape(str(achievement.get("description", "")), quote=True)
        with columns[index % len(columns)]:
            with st.container(border=True):
                st.markdown(f'<span class="status-badge">Achievement: {label}</span>', unsafe_allow_html=True)
                if description:
                    st.caption(description)

