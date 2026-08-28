"""Validity safeguards for the final canonical V15 ablation protocol."""
from collections import Counter
import csv,json
import pytest
from core.data_loader import load_all_data
from experiments.canonical_ablation import ABLATIONS,ablation_priorities
from experiments.canonical_ablation_engine import run_ablation_single,run_canonical_ablation
from experiments.canonical_ablation_export import save_canonical_ablation
from experiments.canonical_config import CanonicalConfig
from experiments.canonical_metrics import HIGHER_BETTER,LOWER_BETTER
from experiments.experiment_metrics import competence_contextual_risks

def _case(configuration,error=2):
 data=load_all_data();cid="eye_protection_selection";spec=ABLATIONS[configuration]
 risks={c:.4 for c in data["competencies"]};scores={c:.3 for c in data["competencies"]};errors={c:error for c in data["competencies"]}
 values,_=ablation_priorities(spec,risks,scores,errors,data["competencies"],.8,.5)
 return values[cid],risks[cid],.5,1+.5*min(1,error/3),data["competencies"][cid].urgency

@pytest.mark.parametrize("configuration,terms",[
 ("complete_framework",("r","g","p","u")),("risk_only",("r","u")),
 ("without_risk",("g","p","u")),("without_history",("r","g","u")),
 ("without_urgency",("r","g","p")),("without_assistance",("r","g","p","u")),
 ("without_trace",("r","g","p","u")),("without_rule_engine",("r","g","p","u"))])
def test_canonical_ablation_priority_equations(configuration,terms):
 actual,r,g,p,u=_case(configuration);lookup={"r":r,"g":g,"p":p,"u":u};expected=1
 for term in terms:expected*=lookup[term]
 assert actual==round(expected,4)

def test_canonical_ablation_phi_is_capped_and_urgency_once():
 for e,phi in ((0,1),(1,1+1/6),(2,1+1/3),(3,1.5),(99,1.5)):
  actual,r,g,_,u=_case("complete_framework",e);assert actual==round(r*g*phi*u,4)

def test_canonical_ablation_context_has_no_theta():
 assert "theta_star" not in ABLATIONS["complete_framework"].__dataclass_fields__
 assert all("theta" not in key for spec in ABLATIONS.values() for key in spec.__dataclass_fields__)

def test_without_assistance_and_without_rule_engine_behaviors():
 cfg=CanonicalConfig(methods=["proposed"],profiles=["T1"],episodes=3,repetitions=1)
 cycles,_,_=run_ablation_single("without_assistance","T1",0,cfg)
 assert {r["assistance"] for r in cycles}=={"none"}
 neutral,_,_=run_ablation_single("without_rule_engine","T1",0,cfg)
 assert {r["selected_rule"] for r in neutral}=={"rule_engine_disabled"}
 assert all(r["priority_by_competence"] for r in neutral)

def test_without_trace_policy_equivalence_and_fidelity_only():
 cfg=CanonicalConfig(methods=["proposed"],profiles=["T1"],episodes=5,repetitions=1)
 complete,cr,_=run_ablation_single("complete_framework","T1",0,cfg)
 no_trace,nr,_=run_ablation_single("without_trace","T1",0,cfg)
 fields=("scenario_id","difficulty","assistance","selected_ppe","correct","engine_estimate_after","priority_by_competence","selected_rule","adaptation","next_scenario","next_difficulty","theta_star_after")
 assert [[r[f] for f in fields] for r in complete]==[[r[f] for f in fields] for r in no_trace]
 assert cr["TC"]==1 and nr["TC"]==0
 for metric in ("CCG_star","RWCS_star","TAR","CER","CMR","SOR","episodes_to_target"):
  assert cr[metric]==nr[metric]

def test_canonical_ablation_smoke_cardinality_matching_and_exports(tmp_path):
 cfg=CanonicalConfig(methods=["proposed"],profiles=["T1","T2"],episodes=5,repetitions=2)
 result=run_canonical_ablation(cfg);folder=save_canonical_ablation(result,cfg,tmp_path)
 assert len(result["run_rows"])==32 and len(result["cycle_rows"])==160 and len(result["posttest_rows"])==576
 assert Counter(r["configuration"] for r in result["run_rows"])==Counter({c:4 for c in ABLATIONS})
 for profile in cfg.profiles:
  for repetition in range(cfg.repetitions):
   assert len({r["repetition_seed"] for r in result["run_rows"] if r["profile"]==profile and r["repetition"]==repetition})==1
 assert all(sum(r["canonical_ablation_run_id"]==rid for r in result["posttest_rows"])==18 for rid in {r["canonical_ablation_run_id"] for r in result["run_rows"]})
 trace=list(csv.DictReader((folder/"canonical_ablation_trace_fidelity.csv").open(encoding="utf-8")))
 assert all("theta" not in key for row in trace for key in row)
 assert (folder/"canonical_ablation_paired_differences.csv").stat().st_size>0
 json.loads((folder/"canonical_ablation_manifest.json").read_text())

def test_canonical_ablation_metric_definitions_invariant():
 assert HIGHER_BETTER==("CCG_star","RWCS_star","TAR","AR","DC","TC","CDRS")
 assert LOWER_BETTER==("CER","CMR","SOR","episodes_to_target")
 assert len(competence_contextual_risks(load_all_data()))==10
