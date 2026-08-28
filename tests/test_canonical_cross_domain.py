"""Canonical V15 cross-domain portability and fidelity invariants."""
from __future__ import annotations

import csv
import json

import pytest

from core.priority_engine import calculate_global_priorities
from core.risk_engine import calculate_scenario_risk
from experiments.canonical_config import CANONICAL_RULE_DEFINITIONS, CanonicalConfig
from experiments.canonical_cross_domain import DOMAINS, RULE_IDS, audit_all_domains, cdrs
from experiments.canonical_cross_domain_engine import run_canonical_cross_domain, run_cross_domain_single
from experiments.canonical_cross_domain_export import save_cross_domain
from experiments.domain_adapter import load_domain
from experiments.experiment_metrics import competence_contextual_risks


def _config(**updates):
    values = dict(methods=["proposed"], profiles=["T1", "T2"], episodes=5,
                  repetitions=2, base_seed=42)
    values.update(updates)
    return CanonicalConfig(**values)


def test_all_canonical_cross_domain_knowledge_bases_are_ready():
    audits = audit_all_domains()
    assert {a["domain"] for a in audits} == set(DOMAINS)
    assert {a["execution_readiness"] for a in audits} == {"READY"}
    assert all(not a["invalid_references"] and not a["duplicate_ids"] for a in audits)


@pytest.mark.parametrize("domain", DOMAINS)
def test_cross_domain_references_urgency_and_risk(domain):
    data = load_domain(domain)
    assert all(0 <= c.urgency <= 1 for c in data["competencies"].values())
    for scenario in data["scenarios"].values():
        assert set(scenario.target_competencies) <= set(data["competencies"])
        assert set(scenario.required_ppe + scenario.distractor_pool) <= set(data["ppe"])
        assert set(scenario.hazards) <= set(data["hazards"])
        risk = calculate_scenario_risk(scenario.hazards, data["hazards"], scenario.context_modifier)
        assert 0 <= risk["scenario_risk"] <= 1


def test_cross_domain_priority_is_exact_canonical_formula_once_and_bounded():
    data = load_domain("construction"); risks = competence_contextual_risks(data)
    scores = {cid: .4 for cid in data["competencies"]}; errors = {cid: 99 for cid in scores}
    result = calculate_global_priorities(risks, scores, errors, data["competencies"], .5, .8, 3)
    for cid, value in result["priority_by_competence"].items():
        expected = risks[cid] * .4 * 1.5 * data["competencies"][cid].urgency
        assert value == pytest.approx(round(expected, 4))


def test_cross_domain_rules_are_the_frozen_r1_to_r5_definitions():
    assert tuple(CANONICAL_RULE_DEFINITIONS) == RULE_IDS
    assert CANONICAL_RULE_DEFINITIONS["R1"]["risk_gte"] == .75
    assert CANONICAL_RULE_DEFINITIONS["R2"]["risk_gte"] == .50
    assert CANONICAL_RULE_DEFINITIONS["R3"]["mastery_gte"] == .80
    assert CANONICAL_RULE_DEFINITIONS["R4"]["mastery_gte"] == .65


@pytest.mark.parametrize("domain", DOMAINS)
def test_deployable_cycle_trace_is_valid_bounded_and_latent_free(domain):
    cycles, run = run_cross_domain_single(domain, "T1", 0, _config(repetitions=1))
    data = load_domain(domain)
    assert all(c["next_scenario"] in data["scenarios"] for c in cycles)
    assert all(1 <= c["next_difficulty"] <= 3 for c in cycles)
    assert all(not any("theta" in key.lower() for key in c) for c in cycles)
    assert not any("theta" in key.lower() for key in run)


def test_cdrs_excludes_unactivated_rules_from_denominator():
    rows = [{"selected_rule": "R1", "rule_execution_valid": True},
            {"selected_rule": "R1", "rule_execution_valid": False},
            {"selected_rule": "R5", "rule_execution_valid": True}]
    value, count, missing = cdrs(rows)
    assert value == .75 and count == 2 and set(missing) == {"R2", "R3", "R4"}


def test_cross_domain_matched_seed_design():
    result = run_canonical_cross_domain(_config(episodes=1), DOMAINS)
    for profile in ("T1", "T2"):
        for repetition in range(2):
            seeds = {r["repetition_seed"] for r in result["run_rows"]
                     if r["profile"] == profile and r["repetition"] == repetition}
            assert len(seeds) == 1


def test_cross_domain_smoke_cardinality_traceability_and_exports(tmp_path):
    config = _config(); result = run_canonical_cross_domain(config, DOMAINS)
    assert len(result["run_rows"]) == 12 and len(result["cycle_rows"]) == 60
    assert len({r["canonical_cross_domain_run_id"] for r in result["run_rows"]}) == 12
    assert all(r["valid_run"] for r in result["run_rows"])
    run_required = {"canonical_cross_domain_run_id", "domain", "profile", "repetition", "repetition_seed",
                    "base_seed", "episodes", "method", "protocol", "ruleset_version", "valid_run",
                    "AR", "DC", "TC", "CDRS", "adaptation_latency_ms"}
    cycle_required = {"canonical_cross_domain_run_id", "domain", "profile", "repetition", "episode",
                      "scenario_id", "scenario_valid", "scenario_risk", "difficulty", "assistance",
                      "selected_rule", "adaptation", "next_scenario", "next_scenario_valid",
                      "next_difficulty", "feedback", "repeat_required", "bounded_rotation_triggered",
                      "priority_highest_competence"}
    assert all(run_required <= r.keys() for r in result["run_rows"])
    assert all(cycle_required <= r.keys() for r in result["cycle_rows"])
    folder = save_cross_domain(result, config, DOMAINS, tmp_path)
    assert len(list(folder.iterdir())) == 12
    for path in folder.glob("*.json"): json.loads(path.read_text(encoding="utf-8"))
    for path in folder.glob("*.csv"):
        with path.open(newline="", encoding="utf-8") as handle: list(csv.DictReader(handle))


def test_cross_domain_secondary_metrics_keep_canonical_names():
    _, run = run_cross_domain_single("manufacturing", "T1", 0, _config(repetitions=1))
    assert {"CCG_star", "RWCS_star", "TAR", "CER", "CMR", "SOR", "episodes_to_target", "censored"} <= run.keys()
