"""Frozen canonical V15 Proposed-framework cross-domain replication engine."""
from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean
import time

from core.priority_engine import calculate_global_priorities
from core.risk_engine import calculate_scenario_risk
from core.scenario_manager import select_initial_scenario
from .baseline_methods import MethodInput
from .canonical_config import CanonicalConfig
from .canonical_cross_domain import RULE_NAME_TO_ID, audit_all_domains, cdrs, rule_execution_valid
from .canonical_engine import _fixed_posttest, _target
from .canonical_latent import LatentState, evolve_latent, generate_observations, observation_score, update_engine_estimate
from .canonical_methods import DeployableContext, decide
from .canonical_metrics import latent_outcomes, posttest_metrics, scenario_oscillation_rate
from .domain_adapter import initialize_domain_learner, load_domain
from .experiment_metrics import competence_contextual_risks, competence_risk_weights
from .synthetic_trainee import load_profiles

PROTOCOL = "canonical_v15_cross_domain"
RULESET = "canonical-R1-R5-corrected"


def cross_domain_run_id(domain, profile, repetition, config):
    return f"v15-cross-domain-s{config.base_seed}-{domain}-{profile}-r{repetition}-proposed"


def run_cross_domain_single(domain, profile_id, repetition, config, experiment_id="cross-domain"):
    data = load_domain(domain); profile = load_profiles()[profile_id]
    estimate, errors = initialize_domain_learner(data, profile)
    latent = LatentState(dict(estimate)); initial_theta = latent.snapshot()
    risk_hat = competence_contextual_risks(data); weights = competence_risk_weights(data)
    sid = select_initial_scenario(data["scenarios"]); difficulty = data["scenarios"][sid].base_difficulty
    assistance = "limited_visual_guidance"; history = []; recent = []; cycles = []; reached_episode = None
    run_id = cross_domain_run_id(domain, profile_id, repetition, config); rep_seed = config.repetition_seed(profile_id, repetition)
    for episode in range(1, config.episodes + 1):
        scenario = data["scenarios"][sid]
        risk = calculate_scenario_risk(scenario.hazards, data["hazards"], scenario.context_modifier)
        obs = generate_observations(latent, scenario, data["ppe"], difficulty, assistance, config,
                                    config.event_seed(profile_id, repetition, episode, f"response-{domain}"),
                                    scenario.time_limit_seconds)
        scores = {}
        for cid in scenario.target_competencies:
            scores[cid] = observation_score(obs["action_accuracy"][cid], obs["response_quality"], obs["independence"], config)
            estimate[cid] = update_engine_estimate(estimate[cid], scores[cid], config.eta)
            errors[cid] = 0 if obs["action_accuracy"][cid] >= 1 else errors[cid] + 1
        priorities = calculate_global_priorities(risk_hat, estimate, errors, data["competencies"],
                                                 config.repetition_weight, config.target_mastery, 3)
        recent.append(mean(scores.values()) if scores else 0.0)
        selected, required = set(obs["selected_ppe"]), set(scenario.required_ppe); correct = selected == required
        method_input = MethodInput(scenario, data["scenarios"], dict(estimate), dict(errors), difficulty,
                                   history + [sid], recent, risk, config, correct,
                                   priorities["priority_ranking"])
        context = DeployableContext(method_input, weights, data["competencies"],
                                    config.event_seed(profile_id, repetition, episode, f"method-{domain}"))
        started = time.perf_counter(); decision = decide("proposed", context); latency = (time.perf_counter() - started) * 1000
        rule = RULE_NAME_TO_ID[decision["selected_rule"]]
        bounded = "bounded_remediation_rotation" in decision["active_rules"]
        cycle = {
            "canonical_cross_domain_run_id": run_id, "domain": domain, "profile": profile_id,
            "repetition": repetition, "repetition_seed": rep_seed, "episode": episode,
            "scenario_id": sid, "scenario_valid": sid in data["scenarios"],
            "scenario_risk": risk["scenario_risk"], "difficulty": difficulty,
            "assistance": assistance, "selected_rule": rule, "adaptation": decision["adaptation"],
            "next_scenario": decision["next_scenario"],
            "next_scenario_valid": decision["next_scenario"] in data["scenarios"],
            "next_difficulty": decision["next_difficulty"], "feedback": decision["feedback"],
            "repeat_required": decision["repeat_required"], "bounded_rotation_triggered": bounded,
            "priority_highest_competence": decision["highest_priority_competence"],
            "adaptation_latency_ms": round(latency, 6),
        }
        cycle["rule_execution_valid"] = rule_execution_valid(cycle, set(data["scenarios"]))
        cycles.append(cycle)
        evolve_latent(latent, set(scenario.target_competencies), difficulty, config)
        if _target(latent.theta_star, data["competencies"], config.target_mastery) and reached_episode is None:
            reached_episode = episode
        history.append(sid); sid = decision["next_scenario"]; difficulty = decision["next_difficulty"]; assistance = decision["assistance"]
    post = _fixed_posttest(latent, data, config, "proposed", profile_id, repetition, run_id)
    fidelity, activated_count, unactivated = cdrs(cycles)
    outcomes = latent_outcomes(initial_theta, latent.theta_star, data["competencies"], weights, config.target_mastery)
    ar = sum(c["next_scenario_valid"] for c in cycles) / len(cycles)
    tc_required = {"canonical_cross_domain_run_id", "domain", "profile", "repetition", "episode", "scenario_id",
                   "scenario_valid", "scenario_risk", "difficulty", "assistance", "selected_rule", "adaptation",
                   "next_scenario", "next_scenario_valid", "next_difficulty", "feedback", "repeat_required",
                   "bounded_rotation_triggered", "priority_highest_competence"}
    tc = sum(len(tc_required & set(c)) / len(tc_required) for c in cycles) / len(cycles)
    valid_run = len(cycles) == config.episodes and all(c["rule_execution_valid"] for c in cycles)
    run = {
        "canonical_cross_domain_run_id": run_id, "domain": domain, "profile": profile_id,
        "repetition": repetition, "repetition_seed": rep_seed, "base_seed": config.base_seed,
        "episodes": config.episodes, "method": "proposed", "protocol": PROTOCOL,
        "ruleset_version": RULESET, "valid_run": valid_run, "AR": round(ar, 6), "DC": 1.0,
        "TC": round(tc, 6), "CDRS": fidelity, "activated_rule_count": activated_count,
        "unactivated_rules": unactivated, "adaptation_latency_ms": round(mean(c["adaptation_latency_ms"] for c in cycles), 6),
        "target_reached": reached_episode is not None, "episodes_to_target": reached_episode or config.episodes,
        "censored": reached_episode is None, "SOR": scenario_oscillation_rate([c["scenario_id"] for c in cycles]),
        **outcomes, **posttest_metrics(post, config.critical_risk_threshold),
    }
    return cycles, run


def run_canonical_cross_domain(config, domains, progress=None):
    audits = audit_all_domains(domains)
    if any(a["execution_readiness"] != "READY" for a in audits):
        raise ValueError("canonical cross-domain execution blocked by NOT_READY schema")
    experiment_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-v15-cross-domain"
    cycles = []; runs = []; total = len(domains) * len(config.profiles) * config.repetitions; done = 0
    for domain in domains:
        for profile in config.profiles:
            for repetition in range(config.repetitions):
                c, r = run_cross_domain_single(domain, profile, repetition, config, experiment_id)
                cycles.extend(c); runs.append(r); done += 1
                if progress: progress(done, total)
    return {"experiment_id": experiment_id, "schema_audits": audits, "cycle_rows": cycles, "run_rows": runs}
