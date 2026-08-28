"""Contextual occupational-risk calculation."""

MAXIMUM_RISK = 5 * 5 * 5 * 1.5


def _validate_scale(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number between 1 and 5")
    if not 1 <= value <= 5:
        raise ValueError(f"{name} must be between 1 and 5")


def calculate_contextual_risk(
    probability: float,
    severity: float,
    exposure: float,
    context_modifier: float = 1.0,
) -> float:
    """Return contextual risk normalized to [0, 1]."""
    _validate_scale("probability", probability)
    _validate_scale("severity", severity)
    _validate_scale("exposure", exposure)
    if (
        isinstance(context_modifier, bool)
        or not isinstance(context_modifier, (int, float))
        or context_modifier <= 0
    ):
        raise ValueError("context_modifier must be greater than 0")

    raw_risk = probability * severity * exposure * context_modifier
    return round(max(0.0, min(1.0, raw_risk / MAXIMUM_RISK)), 4)


def risk_category(risk: float) -> str:
    """Map a normalized value to non-overlapping categories."""
    if not 0 <= risk <= 1: raise ValueError("risk must be between 0 and 1")
    if risk < .25: return "Low"
    if risk < .50: return "Medium"
    if risk < .75: return "High"
    return "Critical"


def calculate_scenario_risk(hazard_ids, hazards, context_modifier=1.0) -> dict:
    """Return per-hazard, maximum, mean, and categorical scenario risk."""
    if not hazard_ids: raise ValueError("at least one hazard is required")
    values = {}
    for hazard_id in hazard_ids:
        if hazard_id not in hazards: raise ValueError(f"unknown hazard: {hazard_id}")
        h = hazards[hazard_id]
        values[hazard_id] = calculate_contextual_risk(
            h.probability, h.severity, h.base_exposure, context_modifier
        )
    maximum = max(values.values())
    return {"hazard_risk_values": values, "scenario_risk": maximum,
            "mean_risk": round(sum(values.values()) / len(values), 4),
            "risk_category": risk_category(maximum)}
