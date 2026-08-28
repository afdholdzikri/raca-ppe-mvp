"""Explainable, ordered adaptation rules."""


def _validate_unit(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        raise ValueError(f"{name} must be between 0 and 1")


def calculate_training_priority(
    normalized_risk: float,
    competence: float,
    repeated_errors: int,
    urgency: float = 1.0,
) -> float:
    """Calculate risk-aware training priority."""
    _validate_unit("normalized_risk", normalized_risk)
    _validate_unit("competence", competence)
    if isinstance(repeated_errors, bool) or not isinstance(repeated_errors, int) or repeated_errors < 0:
        raise ValueError("repeated_errors must be a non-negative integer")
    if isinstance(urgency, bool) or not isinstance(urgency, (int, float)) or urgency <= 0:
        raise ValueError("urgency must be greater than 0")
    competence_gap = 1 - competence
    repetition_factor = 1 + 0.50 * repeated_errors
    return round(normalized_risk * competence_gap * repetition_factor * urgency, 4)


def choose_adaptation(
    normalized_risk: float,
    competence: float,
    repeated_errors: int,
    current_difficulty: int,
) -> dict:
    """Select the first matching adaptation rule and bound difficulty to [1, 3]."""
    _validate_unit("normalized_risk", normalized_risk)
    _validate_unit("competence", competence)
    if isinstance(repeated_errors, bool) or not isinstance(repeated_errors, int) or repeated_errors < 0:
        raise ValueError("repeated_errors must be a non-negative integer")
    if isinstance(current_difficulty, bool) or not isinstance(current_difficulty, int):
        raise ValueError("current_difficulty must be an integer")
    if not 1 <= current_difficulty <= 3:
        raise ValueError("current_difficulty must be between 1 and 3")

    if normalized_risk >= 0.65 and competence < 0.60:
        rule = ("high_risk_low_competence", "priority_remediation", -1,
                "full_visual_guidance", "immediate_corrective", True)
    elif normalized_risk >= 0.50 and repeated_errors >= 2:
        rule = ("high_risk_repeated_error", "targeted_remediation", -1,
                "limited_visual_guidance", "immediate_explanation", True)
    elif competence >= 0.80 and normalized_risk >= 0.50:
        rule = ("high_competence_high_risk", "challenge_adaptation", 1,
                "none", "delayed_reflective", False)
    elif competence >= 0.65:
        rule = ("stable_competence", "progressive_adaptation", 1,
                "minimal", "summary", False)
    else:
        rule = ("default_reinforcement", "reinforcement_adaptation", 0,
                "limited_visual_guidance", "direct_explanation", False)

    active_rule, adaptation, delta, assistance, feedback, repeat_required = rule
    return {
        "active_rule": active_rule,
        "adaptation": adaptation,
        "current_difficulty": current_difficulty,
        "next_difficulty": max(1, min(3, current_difficulty + delta)),
        "assistance": assistance,
        "feedback": feedback,
        "repeat_required": repeat_required,
        "training_priority": calculate_training_priority(
            normalized_risk, competence, repeated_errors
        ),
    }


def choose_adaptation_v2(risk: float, target_mastery: float, repeated_errors: int,
                         response_time: float, hint_used: bool, current_difficulty: int,
                         recent_correct: bool, recent_trend: float = 0.0) -> dict:
    """Evaluate all matching rules and select the first deterministic rule."""
    _validate_unit("risk", risk); _validate_unit("target_mastery", target_mastery)
    if (
        isinstance(repeated_errors, bool)
        or not isinstance(repeated_errors, int)
        or repeated_errors < 0
    ):
        raise ValueError("repeated_errors must be a non-negative integer")
    if (
        isinstance(response_time, bool)
        or not isinstance(response_time, (int, float))
        or response_time < 0
    ):
        raise ValueError("response_time must be a non-negative number")
    if not isinstance(hint_used, bool) or not isinstance(recent_correct, bool):
        raise ValueError("hint_used and recent_correct must be boolean")
    if current_difficulty not in (1, 2, 3): raise ValueError("current_difficulty must be between 1 and 3")
    active = []
    if risk >= .75 and target_mastery < .60: active.append("critical_risk_low_mastery")
    if risk >= .50 and repeated_errors >= 2: active.append("high_risk_repeated_error")
    if target_mastery >= .80 and risk >= .50 and recent_correct:
        active.append("high_mastery_high_risk_correct")
    if target_mastery >= .65 and recent_correct: active.append("stable_mastery_correct")
    active.append("default_reinforcement")
    selected = active[0]
    rules = {
        "critical_risk_low_mastery": ("priority_remediation",-1,"full_visual_guidance","none","immediate_corrective",True),
        "high_risk_repeated_error": ("targeted_remediation",-1,"limited_visual_guidance","low","immediate_explanation",True),
        "high_mastery_high_risk_correct": ("challenge_adaptation",1,"none","high","delayed_reflective",False),
        "stable_mastery_correct": ("progressive_adaptation",1,"minimal","medium","summary",False),
        "default_reinforcement": ("reinforcement_adaptation",0,"limited_visual_guidance","low","direct_explanation",False),
    }
    adaptation, delta, assistance, distractors, feedback, repeat = rules[selected]
    return {"active_rules": active, "selected_rule": selected, "adaptation": adaptation,
            "current_difficulty": current_difficulty,
            "next_difficulty": max(1, min(3, current_difficulty + delta)),
            "assistance": assistance, "distractor_level": distractors,
            "feedback": feedback, "repeat_required": repeat,
            "response_time_seconds": response_time, "hint_used": hint_used,
            "recent_performance_trend": recent_trend}
