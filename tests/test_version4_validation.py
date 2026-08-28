from copy import deepcopy
from pathlib import Path

import pytest

from experiments.ablation_config import ABLATIONS
from experiments.ablation_engine import run_ablation
from experiments.domain_adapter import DOMAIN_REGISTRY,load_domain,validate_all_domains
from experiments.replication_engine import core_algorithm_hashes,run_cross_domain_replication
from experiments.sensitivity_config import BASE_VALUES,ofat_configuration
from experiments.sensitivity_engine import run_sensitivity
from experiments.statistical_analysis import holm_correction,paired_comparison
from experiments.trace_audit import TOLERANCE,audit_trace
from experiments.validation_export import serialize_outputs


def test_all_domains_load_and_references_validate():
    loaded=validate_all_domains()
    assert set(loaded)==set(DOMAIN_REGISTRY)
    assert all(data["scenarios"] and data["scenario_risks"] for data in loaded.values())


@pytest.mark.parametrize("domain",DOMAIN_REGISTRY)
def test_one_cycle_per_domain(domain):
    result=run_cross_domain_replication([domain],["T1"],1,1,42)
    assert len(result["cycle_results"])==1
    assert result["run_results"][0]["CDRS"]==1.0
    assert result["cycle_results"][0]["next_scenario"] in load_domain(domain)["scenarios"]


def test_core_hashes_are_complete_and_sha256():
    hashes=core_algorithm_hashes()
    assert len(hashes)==5
    assert all(len(value)==64 for value in hashes.values())


def test_ablation_flags_remove_only_one_feature():
    full=ABLATIONS["FULL"].features()
    for name,setting in ABLATIONS.items():
        changed=[key for key,value in setting.features().items() if value!=full[key]]
        expected={
          "A1_NO_RISK_WEIGHTING":"risk_weighting","A2_NO_DYNAMIC_CONTEXT":"dynamic_context",
          "A3_NO_ERROR_HISTORY":"error_history","A4_NO_ADAPTIVE_ASSISTANCE":"adaptive_assistance",
          "A5_NO_DECISION_TRACE":"decision_trace"}
        assert changed==([] if name=="FULL" else [expected[name]])


def test_sensitivity_is_one_factor_at_a_time():
    varied=ofat_configuration("learning_rate",.3)
    assert varied["learning_rate"]==.3
    assert sum(varied[key]!=BASE_VALUES[key] for key in BASE_VALUES)==1
    result=run_sensitivity("learning_rate",[.1,.2],1,1,42,["T1"])
    assert {row["value"] for row in result["run_results"]}=={.1,.2}


def test_trace_recomputation_and_corruption_detection():
    replication=run_cross_domain_replication(["manufacturing"],["T1"],1,1,42)
    trace=replication["cycle_results"][0]
    assert audit_trace(trace)["audit_status"]=="PASS"
    corrupted=deepcopy(trace);corrupted["scenario_risk"]=0
    result=audit_trace(corrupted)
    assert result["audit_status"]=="FAIL" and "scenario_risk" in result["inconsistent_fields"]
    missing=deepcopy(trace);missing.pop("competence_after")
    assert audit_trace(missing)["completeness_score"]<1
    assert TOLERANCE==1e-4


def test_seed_reproducibility_and_variation():
    def scientific(seed):
        result=run_cross_domain_replication(["construction"],["T1"],3,1,seed)
        rows=deepcopy(result["cycle_results"])
        for row in rows:row.pop("adaptation_latency_ms",None)
        return rows
    assert scientific(42)==scientific(42)
    assert scientific(42)!=scientific(43)


def test_statistics_and_zero_variance_handling():
    result=paired_comparison([1,2,3],[0,1,2])
    assert result["synthetic_outcomes"] is True
    zero=paired_comparison([1,1,1],[1,1,1])
    assert zero["cohens_dz"]==0
    corrected=holm_correction([{"p_value":.01},{"p_value":.04}])
    assert all("holm_adjusted_p" in row for row in corrected)


def test_validation_outputs_serialize():
    result=run_ablation(1,1,42,["T1"])
    binary=serialize_outputs(result["files"])
    assert binary and all(isinstance(value,bytes) for value in binary.values())
    assert {"ablation_by_profile.csv","ablation_figure_data.csv","ablation_report.md"}<=set(binary)
    assert len(result["by_profile"])==len(ABLATIONS)*len(result["summary"])//len(ABLATIONS)
    assert {"configuration","profile","metric","mean","std","ci95_lower","ci95_upper"}<=set(result["by_profile"][0])
    assert {"configuration","metric","mean","standard_deviation",
      "confidence_interval_lower","confidence_interval_upper","difference_from_FULL",
      "percentage_difference_from_FULL"}<=set(result["figure_data"][0])
