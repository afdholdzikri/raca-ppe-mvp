"""Schema audit and invariant helpers for canonical V15 domain replication."""
from __future__ import annotations

from core.risk_engine import calculate_scenario_risk
from .domain_adapter import DOMAIN_REGISTRY, load_domain

DOMAINS = tuple(DOMAIN_REGISTRY)
RULE_IDS = ("R1", "R2", "R3", "R4", "R5")
RULE_NAME_TO_ID = {
    "critical_risk_low_mastery": "R1",
    "high_risk_repeated_error": "R2",
    "high_mastery_high_risk_correct": "R3",
    "stable_mastery_correct": "R4",
    "default_reinforcement": "R5",
}


def audit_domain_schema(domain: str) -> dict:
    """Independently report reference and execution readiness for one domain."""
    data = load_domain(domain)
    ppe, hazards, competencies, scenarios = (data[k] for k in
                                              ("ppe", "hazards", "competencies", "scenarios"))
    invalid = []
    for item in ppe.values():
        if item.associated_competence_id not in competencies:
            invalid.append(f"PPE {item.id}: competence {item.associated_competence_id}")
    for hazard in hazards.values():
        if hazard.associated_competence_id not in competencies:
            invalid.append(f"hazard {hazard.id}: competence {hazard.associated_competence_id}")
        invalid.extend(f"hazard {hazard.id}: PPE {pid}" for pid in hazard.associated_ppe if pid not in ppe)
    missing_risk = []
    for scenario in scenarios.values():
        invalid.extend(f"scenario {scenario.id}: competence {cid}" for cid in scenario.target_competencies if cid not in competencies)
        invalid.extend(f"scenario {scenario.id}: PPE {pid}" for pid in scenario.required_ppe + scenario.distractor_pool if pid not in ppe)
        invalid.extend(f"scenario {scenario.id}: hazard {hid}" for hid in scenario.hazards if hid not in hazards)
        try:
            calculate_scenario_risk(scenario.hazards, hazards, scenario.context_modifier)
        except (KeyError, ValueError) as exc:
            missing_risk.append(f"{scenario.id}: {exc}")
    missing_urgency = [cid for cid, value in competencies.items() if not 0 <= value.urgency <= 1]
    ready = bool(scenarios) and not invalid and not missing_risk and not missing_urgency
    return {
        "domain": domain, "scenario_count": len(scenarios), "hazard_count": len(hazards),
        "ppe_count": len(ppe), "competence_count": len(competencies),
        "duplicate_ids": [], "invalid_references": invalid,
        "missing_urgency": missing_urgency, "missing_risk_components": missing_risk,
        "execution_readiness": "READY" if ready else "NOT_READY",
    }


def audit_all_domains(domains=DOMAINS) -> list[dict]:
    return [audit_domain_schema(domain) for domain in domains]


def rule_execution_valid(cycle: dict, scenario_ids: set[str]) -> bool:
    """Validate one canonical adaptation without treating unexercised rules as valid."""
    return (
        cycle.get("selected_rule") in RULE_IDS
        and cycle.get("next_scenario") in scenario_ids
        and 1 <= int(cycle.get("next_difficulty", 0)) <= 3
        and cycle.get("assistance") in {"none", "minimal", "limited_visual_guidance", "full_visual_guidance"}
        and bool(cycle.get("adaptation")) and bool(cycle.get("feedback"))
    )


def cdrs(cycles: list[dict]) -> tuple[float, int, list[str]]:
    """Mean valid execution rate over activated rules only."""
    activated = sorted({cycle["selected_rule"] for cycle in cycles})
    rates = []
    for rule in activated:
        rows = [cycle for cycle in cycles if cycle["selected_rule"] == rule]
        rates.append(sum(bool(row["rule_execution_valid"]) for row in rows) / len(rows))
    return (round(sum(rates) / len(rates), 6) if rates else 0.0,
            len(activated), [rule for rule in RULE_IDS if rule not in activated])
