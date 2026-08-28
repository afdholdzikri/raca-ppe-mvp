"""Scientific invariants for canonical V15 sensitivity and robustness."""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict

import pytest

from core.data_loader import load_all_data
from experiments.canonical_config import CanonicalConfig
from experiments.canonical_sensitivity import (
    LATENT_REGIMES,
    deterministic_urgency,
    effective_urgencies,
    final_conditions,
    smoke_conditions,
)
from experiments.canonical_sensitivity_engine import (
    run_canonical_sensitivity,
    run_sensitivity_single,
    sensitivity_priorities,
)
from experiments.canonical_sensitivity_export import save_canonical_sensitivity


def _base(**changes):
    values = dict(methods=["proposed"], profiles=["T1", "T2"], episodes=5,
                  repetitions=2, base_seed=42)
    values.update(changes)
    return CanonicalConfig(**values)


def test_ofat_conditions_change_only_declared_configuration_fields():
    base = _base()
    permitted = {
        "eta": {"eta"}, "rho": {"rho"}, "kappa": {"kappa"},
        "repetition_weight": {"repetition_weight"}, "sigma_g": {"sigma_g"},
        "observation_weights": {"w_action", "w_response", "w_independence"},
        "latent_dynamics": {"practice_rate", "sigma_g", "latent_decay"},
        "urgency": set(), "r1_risk": set(), "r2_risk": set(),
        "r3_mastery": set(),
    }
    original = base.to_dict()
    for condition in final_conditions():
        changed = {key for key, value in condition.config(base).to_dict().items()
                   if original.get(key) != value}
        assert changed <= permitted[condition.parameter_name]


def test_canonical_grid_values_come_from_canonical_configuration():
    base = _base()
    conditions = {c.id: c for c in final_conditions()}
    assert conditions["eta_0p2"].config(base).eta == base.eta
    assert conditions["rho_0p18"].config(base).rho == base.rho
    assert conditions["kappa_0p12"].config(base).kappa == base.kappa
    assert conditions["weights_canonical"].config(base).w_action == base.w_action
    assert conditions["latent_canonical"].config(base).practice_rate == base.practice_rate


@pytest.mark.parametrize("condition_id,expected", [
    ("kappa_0p08", .32), ("kappa_0p12", .44), ("kappa_0p16", .56),
    ("weights_canonical", .44), ("weights_balanced", .32),
])
def test_derived_assistance_coefficient_is_recalculated(condition_id, expected):
    condition = next(c for c in final_conditions() if c.id == condition_id)
    assert condition.config(_base()).assistance_independence_coefficient == pytest.approx(expected)


def test_observation_weight_regimes_sum_to_one():
    for condition in final_conditions():
        if condition.parameter_name == "observation_weights":
            config = condition.config(_base())
            assert config.w_action + config.w_response + config.w_independence == pytest.approx(1.0)


def test_urgency_perturbation_is_deterministic_and_bounded():
    data = load_all_data()["competencies"]
    first, deltas = effective_urgencies(data, "perturbed", 42)
    second, _ = effective_urgencies(data, "perturbed", 42)
    assert first == second
    assert all(-.15 <= delta <= .15 for delta in deltas.values())
    assert all(.5 <= value <= 1.5 for value in first.values())
    assert deterministic_urgency(1.0, "eye_protection", 42) == deterministic_urgency(1.0, "eye_protection", 42)


def test_priority_applies_urgency_exactly_once_and_bounds_phi():
    definitions = load_all_data()["competencies"]
    risks = {key: .8 for key in definitions}; scores = {key: .4 for key in definitions}
    errors = {key: 99 for key in definitions}; urgency = {key: 1.2 for key in definitions}
    values, _ = sensitivity_priorities(risks, scores, errors, definitions, urgency, .8, .5)
    # .8 risk * .4 gap * bounded phi 1.5 * urgency 1.2
    assert all(value == pytest.approx(.576) for value in values.values())


def test_latent_regimes_change_only_declared_latent_parameters():
    base = _base(); original = base.to_dict()
    for condition in final_conditions():
        if condition.parameter_name != "latent_dynamics":
            continue
        config = condition.config(base).to_dict()
        changed = {key for key, value in config.items() if original.get(key) != value}
        expected = set() if condition.regime_name == "canonical" else {
            key for key, value in zip(("practice_rate", "sigma_g", "latent_decay"),
                                      LATENT_REGIMES[condition.regime_name])
            if original[key] != value
        }
        assert changed == expected


def test_deployable_sensitivity_records_do_not_expose_latent_state():
    condition = next(c for c in smoke_conditions() if c.id == "eta_0p2")
    row, post = run_sensitivity_single(condition, "proposed", "T1", 0, _base(repetitions=1))
    assert not any("theta" in key.lower() for key in row)
    assert all(not any("theta" in key.lower() for key in item) for item in post)


def test_matched_profile_repetition_seeds_are_preserved_across_methods():
    conditions = [next(c for c in smoke_conditions() if c.id == "eta_0p2")]
    result = run_canonical_sensitivity(_base(), conditions)
    seeds = defaultdict(set)
    for row in result["run_rows"]:
        seeds[(row["profile"], row["repetition"])].add(row["repetition_seed"])
    assert all(len(values) == 1 for values in seeds.values())


def test_fixed_posttest_remains_unassisted_and_state_is_not_exported():
    condition = next(c for c in smoke_conditions() if c.id == "latent_canonical")
    _, post = run_sensitivity_single(condition, "oracle", "T1", 0, _base(repetitions=1))
    assert len(post) == 18
    assert {row["assistance"] for row in post} == {"none"}
    assert all(not any(name in row for name in ("theta_star", "learner_estimate", "l")) for row in post)


def test_smoke_cardinality_exports_and_run_identity(tmp_path):
    config = _base(); conditions = smoke_conditions()
    assert sum(len(c.methods) for c in conditions) * 2 * 2 == 332
    result = run_canonical_sensitivity(config, conditions)
    assert len(result["run_rows"]) == 332
    assert len({r["canonical_sensitivity_run_id"] for r in result["run_rows"]}) == 332
    folder = save_canonical_sensitivity(result, config, conditions,
                                        load_all_data()["competencies"], tmp_path)
    required = {
        "canonical_sensitivity_configuration.json", "canonical_sensitivity_manifest.json",
        "canonical_sensitivity_run_results.csv", "canonical_sensitivity_summary.csv",
        "canonical_sensitivity_profile_summary.csv", "canonical_sensitivity_paired_differences.csv",
        "canonical_sensitivity_rank_stability.csv", "canonical_sensitivity_target_attainment.csv",
        "canonical_sensitivity_fixed_posttest_results.csv", "canonical_sensitivity_figure_data.csv",
        "canonical_robustness_summary.csv", "canonical_robustness_paired_differences.csv",
        "canonical_sensitivity_report.md",
    }
    assert {path.name for path in folder.iterdir()} == required
    for path in folder.glob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))
    with (folder / "canonical_sensitivity_run_results.csv").open(newline="", encoding="utf-8") as handle:
        exported = list(csv.DictReader(handle))
    assert len(exported) == 332
    assert Counter(row["method"] for row in exported)["oracle"] == 12


def test_metric_names_and_canonical_reference_rwcs_are_preserved():
    condition = next(c for c in smoke_conditions() if c.id == "latent_slower_narrower")
    row, _ = run_sensitivity_single(condition, "proposed", "T1", 0, _base(repetitions=1))
    required = {"CCG_star", "canonical_reference_RWCS_star", "regime_RWCS_star",
                "CER", "CMR", "TAR", "SOR", "AR", "DC", "TC",
                "episodes_to_target", "adaptation_latency_ms"}
    assert required <= row.keys()
    assert row["RWCS_star"] == row["canonical_reference_RWCS_star"]
