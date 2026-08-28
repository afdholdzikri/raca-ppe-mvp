"""Capability-safe adapter from Streamlit observations to Canonical V15.

The module contains orchestration and serialization only.  Risk, observation,
learner-estimate, priority, R1--R5, and bounded scenario rotation are delegated
to the same modules used by the canonical experiment engine.  It intentionally
does not import simulation-only latent-state modules.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from statistics import mean
import time
import uuid
from typing import Any, Mapping

from core.learner_model import (
    calculate_independence_score,
    calculate_response_score,
    competence_correctness,
)
from core.priority_engine import calculate_global_priorities
from core.scenario_manager import difficulty_behavior, select_initial_scenario
from core.trace_manager import append_trace_jsonl
from experiments.baseline_methods import MethodInput
from experiments.canonical_config import CanonicalConfig
from experiments.canonical_deployable import DeployableContext, decide_proposed
from experiments.canonical_observable import observation_score, update_engine_estimate
from experiments.domain_adapter import DOMAIN_REGISTRY, domain_snapshot, load_domain
from experiments.experiment_metrics import competence_contextual_risks, competence_risk_weights


ENGINE_VERSION = "canonical_v15"
RULESET_VERSION = "canonical-R1-R5-corrected"
PARAMETER_MANIFEST = Path(__file__).resolve().parent / "canonical_parameter_manifest.json"

CANONICAL_TRACE_FIELDS = frozenset(
    {
        "trace_id", "session_id", "timestamp_utc", "episode", "domain",
        "scenario_id", "risk_hat", "scenario_risk", "risk_category",
        "competence", "selected_ppe", "required_ppe", "missing_ppe",
        "unnecessary_ppe", "correct", "observable_response_features",
        "learner_estimate_before", "learner_estimate_after", "repeated_errors",
        "competence_gap", "repetition_factor", "urgency", "priority_q",
        "priority_ranking", "eligible_rules", "selected_rule",
        "requested_action", "applied_action", "next_difficulty",
        "next_assistance", "feedback", "repeat_required", "next_scenario",
        "bounded_rotation_flag", "engine_version", "parameter_version",
        "ruleset_version", "knowledge_base_version",
        "simulation_only_state_exposed", "adaptation_latency_ms",
        "explanation",
    }
)


def available_domains() -> tuple[str, ...]:
    """Return canonical knowledge-base identifiers in registry order."""
    return tuple(DOMAIN_REGISTRY)


def load_canonical_domain(domain: str) -> dict[str, Any]:
    """Load and validate an authoritative canonical domain knowledge base."""
    return load_domain(domain)


def _content_version(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def knowledge_base_version(domain_data: Mapping[str, Any]) -> str:
    """Return a deterministic presentation identifier for loaded KB content."""
    return f"{domain_data['domain']}:{_content_version(domain_snapshot(domain_data))}"


def parameter_version() -> str:
    """Return a deterministic identifier for the frozen canonical manifest."""
    try:
        payload = json.loads(PARAMETER_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = CanonicalConfig().to_dict()
    return f"canonical-v15:{_content_version(payload)}"


def initial_deployable_state(domain_data: Mapping[str, Any]) -> dict[str, Any]:
    """Build a fresh observable-only reviewer state from canonical definitions."""
    scores = {
        competence_id: float(definition.initial_mastery)
        for competence_id, definition in domain_data["competencies"].items()
    }
    scenario_id = select_initial_scenario(domain_data["scenarios"])
    return {
        "current_scenario_id": scenario_id,
        "current_difficulty": domain_data["scenarios"][scenario_id].base_difficulty,
        "assistance": "limited_visual_guidance",
        "distractor_level": "low",
        "competence_scores": scores,
        "repeated_errors": {competence_id: 0 for competence_id in scores},
        "scenario_history": [],
        "recent_scores": [],
    }


def prepare_scenario(
    domain_data: Mapping[str, Any],
    scenario_id: str,
    difficulty: int,
    distractor_level: str,
) -> dict[str, Any]:
    """Return canonical scenario risk and difficulty behavior for presentation."""
    scenario = domain_data["scenarios"].get(scenario_id)
    if scenario is None:
        raise ValueError(f"unknown scenario {scenario_id!r} for {domain_data['domain']}")
    return {
        "scenario": scenario,
        "risk": domain_data["scenario_risks"][scenario_id],
        "behavior": difficulty_behavior(
            scenario, difficulty, distractor_level, domain_data["ppe"].keys()
        ),
    }


def _explanation(trace: Mapping[str, Any]) -> str:
    target = str(trace["competence"]).replace("_", " ")
    rotation = " Bounded rotation changed the requested scenario." if trace["bounded_rotation_flag"] else ""
    return (
        f"Canonical priority selected {target} (Q={trace['priority_q'][trace['competence']]:.4f}). "
        f"Rule {trace['selected_rule']} applied {trace['applied_action']['adaptation']} and "
        f"returned {trace['next_scenario']} at difficulty {trace['next_difficulty']} with "
        f"{trace['next_assistance']}.{rotation}"
    )


def evaluate_decision(
    *,
    domain_data: Mapping[str, Any],
    scenario_id: str,
    selected_ppe: list[str],
    competence_scores: Mapping[str, float],
    repeated_errors: Mapping[str, int],
    current_difficulty: int,
    scenario_history: list[str],
    recent_scores: list[float],
    response_time_seconds: float,
    time_limit_seconds: float,
    hint_used: bool,
    session_id: str,
    episode: int,
    assistance: str = "limited_visual_guidance",
    distractor_level: str = "low",
    reviewer_mode: bool = False,
    animation_state: Mapping[str, Any] | None = None,
    trace_path: str | Path | None = None,
    config: CanonicalConfig | None = None,
) -> dict[str, Any]:
    """Evaluate one human-observable PPE decision with the canonical backend.

    ``reviewer_mode`` and ``animation_state`` are accepted only to make their
    presentation-only nature explicit; neither is read by the scientific path.
    """
    del reviewer_mode, animation_state, assistance
    canonical = config or CanonicalConfig(methods=["proposed"], profiles=["T1"])
    prepared = prepare_scenario(
        domain_data, scenario_id, current_difficulty, distractor_level
    )
    scenario = prepared["scenario"]
    risk = prepared["risk"]
    selected = set(selected_ppe)
    unknown = selected - set(domain_data["ppe"])
    if unknown:
        raise ValueError(f"unknown PPE selection: {', '.join(sorted(unknown))}")
    required = set(scenario.required_ppe)
    correct = selected == required
    response_quality = calculate_response_score(response_time_seconds, time_limit_seconds)
    independence = calculate_independence_score(hint_used)
    accuracy = competence_correctness(scenario, selected, domain_data["ppe"])

    before = dict(competence_scores)
    after = dict(before)
    errors_after = dict(repeated_errors)
    observations: dict[str, float] = {}
    for competence_id in scenario.target_competencies:
        action_accuracy = 1.0 if accuracy.get(competence_id, False) else 0.0
        z_value = observation_score(action_accuracy, response_quality, independence, canonical)
        observations[competence_id] = z_value
        after[competence_id] = update_engine_estimate(before[competence_id], z_value, canonical.eta)
        errors_after[competence_id] = (
            0 if action_accuracy >= 1.0 else errors_after.get(competence_id, 0) + 1
        )

    risk_hat = competence_contextual_risks(domain_data)
    priorities = calculate_global_priorities(
        risk_hat,
        after,
        errors_after,
        domain_data["competencies"],
        canonical.repetition_weight,
        canonical.target_mastery,
        3,
    )
    updated_recent = list(recent_scores)
    updated_recent.append(mean(observations.values()) if observations else 0.0)
    method_input = MethodInput(
        scenario,
        domain_data["scenarios"],
        after,
        errors_after,
        current_difficulty,
        list(scenario_history) + [scenario_id],
        updated_recent,
        risk,
        canonical,
        correct,
        priorities["priority_ranking"],
    )
    started = time.perf_counter()
    deployable_context = DeployableContext(
        method_input,
        competence_risk_weights(domain_data),
        domain_data["competencies"],
        0,
    )
    decision = decide_proposed(deployable_context)
    latency_ms = round((time.perf_counter() - started) * 1000, 6)
    if decision["next_scenario"] not in domain_data["scenarios"]:
        raise ValueError("canonical policy returned a scenario outside the active domain")

    components = priorities["priority_components"]
    target = decision["highest_priority_competence"]
    requested = {
        **decision["requested_action"],
        "adaptation": decision["adaptation"],
    }
    applied = {
        **decision["applied_action"],
        "adaptation": decision["adaptation"],
    }
    trace: dict[str, Any] = {
        "trace_id": str(uuid.uuid4()),
        "session_id": session_id,
        "trainee_id": "Anonymous Reviewer",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "episode": episode,
        "domain": domain_data["domain"],
        "scenario_id": scenario_id,
        "zone": scenario.zone,
        "task": scenario.task,
        "narrative": scenario.narrative,
        "difficulty": current_difficulty,
        "current_difficulty": current_difficulty,
        "active_hazards": list(scenario.hazards),
        "risk_hat": risk_hat,
        "scenario_risk": risk["scenario_risk"],
        "risk_category": risk["risk_category"],
        "hazard_risk_values": risk["hazard_risk_values"],
        "mean_risk": risk["mean_risk"],
        "competence": target,
        "selected_ppe": sorted(selected),
        "required_ppe": list(scenario.required_ppe),
        "missing_ppe": sorted(required - selected),
        "unnecessary_ppe": sorted(selected - required),
        "correct": correct,
        "observable_response_features": {
            "action_accuracy": accuracy,
            "response_quality": response_quality,
            "independence": independence,
            "response_time_seconds": round(response_time_seconds, 3),
            "hint_used": hint_used,
        },
        "time_limit_seconds": time_limit_seconds,
        "response_time_seconds": round(response_time_seconds, 3),
        "response_score": response_quality,
        "hint_used": hint_used,
        "independence_score": independence,
        "observation_scores": observations,
        "affected_competencies": list(scenario.target_competencies),
        "competence_before": {
            cid: before[cid] for cid in scenario.target_competencies
        },
        "competence_after": {
            cid: after[cid] for cid in scenario.target_competencies
        },
        "learner_estimate_before": before,
        "learner_estimate_after": after,
        "repeated_errors": errors_after,
        "competence_gap": {cid: values["competence_gap"] for cid, values in components.items()},
        "competence_gaps": {cid: values["competence_gap"] for cid, values in components.items()},
        "repetition_factor": {cid: values["repetition_factor"] for cid, values in components.items()},
        "urgency": {cid: values["urgency"] for cid, values in components.items()},
        "priority_q": priorities["priority_by_competence"],
        "priority_by_competence": priorities["priority_by_competence"],
        "highest_priority_competence": target,
        "highest_priority_value": priorities["highest_priority_value"],
        "priority_ranking": priorities["priority_ranking"],
        "eligible_rules": decision["active_rules"],
        "active_rules": decision["active_rules"],
        "selected_rule": decision["selected_rule"],
        "adaptation": decision["adaptation"],
        "requested_action": requested,
        "applied_action": applied,
        "next_difficulty": decision["next_difficulty"],
        "next_assistance": decision["assistance"],
        "assistance": decision["assistance"],
        "distractor_level": decision["distractor_level"],
        "next_distractor_level": decision["distractor_level"],
        "feedback": decision["feedback"],
        "repeat_required": decision["repeat_required"],
        "next_scenario": decision["next_scenario"],
        "current_scenario": scenario_id,
        "bounded_rotation_flag": decision["bounded_rotation_triggered"],
        "engine_version": ENGINE_VERSION,
        "parameter_version": parameter_version(),
        "ruleset_version": RULESET_VERSION,
        "knowledge_base_version": knowledge_base_version(domain_data),
        "simulation_only_state_exposed": False,
        "adaptation_latency_ms": latency_ms,
    }
    trace["explanation"] = _explanation(trace)
    missing_fields = CANONICAL_TRACE_FIELDS - trace.keys()
    if missing_fields:
        raise ValueError(f"incomplete canonical UI trace: {sorted(missing_fields)}")
    if trace_path is not None:
        trace["persisted_to_file"] = append_trace_jsonl(trace, trace_path)
    return {
        "trace": trace,
        "competence_scores": after,
        "repeated_errors": errors_after,
        "recent_scores": updated_recent,
        "decision": decision,
        "priorities": priorities,
    }


def new_session_id() -> str:
    """Return a unique public reviewer session identifier."""
    return str(uuid.uuid4())
