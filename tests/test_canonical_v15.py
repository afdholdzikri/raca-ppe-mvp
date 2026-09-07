"""Canonical V15 protocol safeguards and outcome tests."""
from copy import deepcopy
import json
import pytest
from core.data_loader import load_all_data
from core.adaptation_engine import choose_adaptation_v2
from core.priority_engine import calculate_priorities
from experiments.baseline_methods import MethodInput
from experiments.canonical_config import CANONICAL_METHODS,DEPLOYABLE_METHODS,CanonicalConfig,METHOD_REGISTRY
from experiments.canonical_engine import _fixed_posttest,_target,canonical_run_id,run_canonical,run_single
from experiments.canonical_export import save_canonical
from experiments.canonical_latent import (ASSISTANCE_ENCODING,DIFFICULTY_ENCODING,LatentState,
 evolve_latent,generate_observations,observation_score,update_engine_estimate)
from experiments.canonical_methods import (
 DeployableContext,OracleContext,RWUCB1Context,
 calculate_oracle_priorities,calculate_rw_ucb1_indices,
 choose_oracle_difficulty,decide)
from experiments.canonical_metrics import (HIGHER_BETTER,LOWER_BETTER,latent_outcomes,
 paired_differences,posttest_metrics,scenario_oscillation_rate)
from experiments.experiment_metrics import competence_contextual_risks,competence_risk_weights

def test_theta_star_is_separate_from_engine_estimate():
 state=LatentState({"c":.4});estimate={"c":.4};evolve_latent(state,{"c"},2,CanonicalConfig(episodes=1,repetitions=1))
 assert state.theta_star["c"]!=estimate["c"] and state.theta_star is not estimate

def test_deployable_context_has_no_theta_and_oracle_registry_is_privileged():
 assert "theta_star" not in DeployableContext.__dataclass_fields__
 assert all(not METHOD_REGISTRY[m]["theta_star_access"] for m in DEPLOYABLE_METHODS)
 assert METHOD_REGISTRY["oracle"]=={"label":"Oracle (privileged reference)","simulation_only":True,"theta_star_access":True}

def test_rw_ucb1_is_deployable_and_has_no_theta_access():
 assert "rw_ucb1" in DEPLOYABLE_METHODS
 assert "theta_star" not in RWUCB1Context.__dataclass_fields__
 assert METHOD_REGISTRY["rw_ucb1"]=={
  "label":"Risk-Weighted UCB1 (RW-UCB1)",
  "simulation_only":False,
  "theta_star_access":False,
 }

def test_deployable_rejects_oracle_context_and_oracle_accepts_it():
 data=load_all_data();cfg=CanonicalConfig(episodes=1,repetitions=1);s=data["scenarios"]["S1"]
 mi=MethodInput(s,data["scenarios"],{c:.4 for c in data["competencies"]},{c:0 for c in data["competencies"]},1,["S1"],[],{"scenario_risk":.4},cfg,False,[(next(iter(data["competencies"])),1)])
 dep=DeployableContext(mi,{c:.4 for c in data["competencies"]},data["competencies"],42);oracle=OracleContext(dep,{c:.4 for c in data["competencies"]},{c:.4 for c in data["competencies"]})
 with pytest.raises(PermissionError):decide("proposed",oracle)
 assert decide("oracle",oracle)["selected_rule"]=="oracle_latent_priority"

def test_rw_ucb1_requires_observable_state_context():
 data=load_all_data();cfg=CanonicalConfig(episodes=1,repetitions=1);s=data["scenarios"]["S1"]
 mi=MethodInput(s,data["scenarios"],{c:.4 for c in data["competencies"]},{c:0 for c in data["competencies"]},1,["S1"],[],{"scenario_risk":.4},cfg,False,[(next(iter(data["competencies"])),1)])
 dep=DeployableContext(mi,competence_risk_weights(data),data["competencies"],42)
 with pytest.raises(PermissionError):decide("rw_ucb1",dep)

def test_random_deterministic_and_seed_sensitive():
 data=load_all_data();cfg=CanonicalConfig(episodes=1,repetitions=1);s=data["scenarios"]["S1"]
 mi=MethodInput(s,data["scenarios"],{c:.4 for c in data["competencies"]},{c:0 for c in data["competencies"]},1,["S1"],[],{"scenario_risk":.4},cfg,False,[(next(iter(data["competencies"])),1)])
 def sequence(seed):return [decide("random",DeployableContext(mi,{},data["competencies"],seed+i))["next_scenario"] for i in range(8)]
 assert sequence(10)==sequence(10) and sequence(10)!=sequence(11)

def test_response_uses_theta_and_engine_update_uses_z():
 data=load_all_data();cfg=CanonicalConfig(episodes=1,repetitions=1);s=data["scenarios"]["S1"]
 low=generate_observations(LatentState({c:.0 for c in data["competencies"]}),s,data["ppe"],1,"none",cfg,1,60)
 high=generate_observations(LatentState({c:1.0 for c in data["competencies"]}),s,data["ppe"],1,"none",cfg,1,60)
 assert sum(high["action_accuracy"].values())>sum(low["action_accuracy"].values())
 z=observation_score(1,.5,.5,cfg);assert update_engine_estimate(.2,z,cfg.eta)==pytest.approx((1-cfg.eta)*.2+cfg.eta*z)

def test_latent_outcomes_use_supplied_latent_values():
 data=load_all_data();weights=competence_risk_weights(data);initial={c:.2 for c in data["competencies"]};final={c:.8 for c in data["competencies"]}
 out=latent_outcomes(initial,final,data["competencies"],weights,.8);assert out["CCG_star"]==.6 and out["TAR"]==1 and out["RWCS_star"]==.8

def test_fixed_posttest_updates_neither_state_and_metrics():
 data=load_all_data();cfg=CanonicalConfig(episodes=1,repetitions=1,posttest_repetitions=1);state=LatentState({c:.7 for c in data["competencies"]});before=deepcopy(state.theta_star)
 estimate={c:.3 for c in data["competencies"]};estimate_before=deepcopy(estimate);run_id=canonical_run_id("static","T1",0,cfg)
 rows=_fixed_posttest(state,data,cfg,"static","T1",0,run_id)
 assert state.theta_star==before and estimate==estimate_before and all(r["assistance"]=="none" for r in rows)
 assert {"method","canonical_run_id","repetition_seed"}<=set(rows[0])
 m=posttest_metrics([{"scenario_risk":.9,"correct":False,"required_ppe":[1,2],"missing_ppe":[1]}]);assert m=={"CER":1.0,"CMR":.5}

def test_sor_and_censored_target():
 assert scenario_oscillation_rate(["A","B","A","B"])==1
 _,run,_=run_single("static","T1",0,CanonicalConfig(methods=["static"],profiles=["T1"],episodes=1,repetitions=1))
 assert run["censored"] is True and run["episodes_to_target"]==1

def test_seven_methods_and_matched_seeds():
 assert CANONICAL_METHODS==("static","random","score_adaptive","competence_adaptive","rw_ucb1","proposed","oracle")
 cfg=CanonicalConfig(episodes=1,repetitions=1,profiles=["T1"],methods=list(CANONICAL_METHODS));result=run_canonical(cfg)
 assert len(result["run_rows"])==7 and len({r["repetition_seed"] for r in result["run_rows"]})==1

def test_rw_ucb1_index_matches_canonical_formula():
 from math import log,sqrt
 risk_weights={"c1":.8,"c2":.4};counts={"c1":4,"c2":2};sums={"c1":.4,"c2":.3}
 values=calculate_rw_ucb1_indices(risk_weights,counts,sums,10,c=1.0)
 assert values["c1"]==pytest.approx(.8*((.4/4)+sqrt(2*log(10)/4)))
 assert values["c2"]==pytest.approx(.4*((.3/2)+sqrt(2*log(10)/2)))

def test_rw_ucb1_unvisited_first_and_fixed_configuration():
 data=load_all_data();cfg=CanonicalConfig(episodes=1,repetitions=1);s=data["scenarios"]["S1"]
 ids=sorted(data["competencies"]);scores={c:.4 for c in ids};errors={c:0 for c in ids}
 mi=MethodInput(s,data["scenarios"],scores,errors,s.base_difficulty,["S1"],[],{"scenario_risk":.4},cfg,False,[(ids[0],1)])
 dep=DeployableContext(mi,competence_risk_weights(data),data["competencies"],42)
 counts={c:1 for c in ids};counts[ids[0]]=0
 ctx=RWUCB1Context(dep,counts,{c:0.0 for c in ids},5)
 decision=decide("rw_ucb1",ctx)
 assert decision["highest_priority_competence"]==ids[0]
 assert decision["selected_rule"]=="rw_ucb1_unvisited"
 assert decision["assistance"]=="limited_visual_guidance"
 assert decision["distractor_level"]=="low"
 assert decision["feedback"]=="direct_explanation"
 assert decision["next_difficulty"]==data["scenarios"][decision["next_scenario"]].base_difficulty

def test_positive_paired_orientation():
 base={"profile":"T1","repetition":0,"AR":1,"DC":1,"TC":1,"CDRS":1,"CCG_star":1,"RWCS_star":1,"TAR":1,"CER":0,"CMR":0,"SOR":0,"episodes_to_target":1}
 rows=[{**base,"method":"proposed"},{**base,"method":"static","CCG_star":0,"CER":1,"episodes_to_target":2}]
 values=paired_differences(rows);assert all(r["mean_paired_difference"]>=0 for r in values)

def test_canonical_deterministic_science():
 cfg=CanonicalConfig(episodes=2,repetitions=1,profiles=["T1"],methods=["static","random","rw_ucb1","proposed","oracle"])
 a=run_canonical(cfg);b=run_canonical(cfg)
 for rows in (a["cycle_rows"],b["cycle_rows"]):
  for row in rows:row.pop("experiment_id",None);row.pop("adaptation_latency_ms",None)
 for rows in (a["run_rows"],b["run_rows"]):
  for row in rows:row.pop("experiment_id",None);row.pop("adaptation_latency_ms",None)
 assert a["cycle_rows"]==b["cycle_rows"] and a["run_rows"]==b["run_rows"] and a["posttest_rows"]==b["posttest_rows"]

def test_canonical_output_serialization(tmp_path):
 cfg=CanonicalConfig(episodes=1,repetitions=1,profiles=["T1"],methods=list(CANONICAL_METHODS),posttest_repetitions=1)
 result=run_canonical(cfg);folder=save_canonical(result,cfg,tmp_path)
 expected={"canonical_cycle_results.csv","canonical_run_results.csv","canonical_summary.csv","canonical_profile_summary.csv",
  "canonical_paired_differences.csv","canonical_fixed_posttest_results.csv","canonical_target_attainment.csv",
  "canonical_metadata.json","canonical_configuration.json","canonical_method_registry.json","canonical_parameter_manifest.json","canonical_report.md"}
 assert {p.name for p in folder.iterdir()}==expected
 for path in folder.glob("*.json"):json.loads(path.read_text(encoding="utf-8"))

def test_fixed_posttest_smoke_traceability_and_counts(tmp_path):
 import csv
 from collections import Counter
 cfg=CanonicalConfig(episodes=5,repetitions=2,profiles=["T1","T2"],methods=list(CANONICAL_METHODS))
 result=run_canonical(cfg);folder=save_canonical(result,cfg,tmp_path)
 with (folder/"canonical_fixed_posttest_results.csv").open(encoding="utf-8",newline="") as stream:
  rows=list(csv.DictReader(stream))
 required={"canonical_run_id","method","profile","repetition","repetition_seed","scenario_id","item","assistance",
  "scenario_risk","selected_ppe","required_ppe","missing_ppe","correct","critical_error","critical_miss"}
 assert required<=set(rows[0]) and len(rows)==504
 assert Counter(r["method"] for r in rows)==Counter({method:72 for method in CANONICAL_METHODS})
 run_counts=Counter(r["canonical_run_id"] for r in rows)
 assert len(run_counts)==28 and set(run_counts.values())=={18}
 for profile in ("T1","T2"):
  for repetition in ("0","1"):
   matched={r["repetition_seed"] for r in rows if r["profile"]==profile and r["repetition"]==repetition}
   assert len(matched)==1

def test_posttest_metrics_reject_cross_method_mixing_and_use_own_outcomes():
 static=[{"canonical_run_id":"static-run","method":"static","scenario_risk":.9,"correct":False,
          "required_ppe":["a","b"],"missing_ppe":["a"]}]
 proposed=[{"canonical_run_id":"proposed-run","method":"proposed","scenario_risk":.9,"correct":True,
            "required_ppe":["a","b"],"missing_ppe":[]}]
 assert posttest_metrics(static)=={"CER":1.0,"CMR":.5}
 assert posttest_metrics(proposed)=={"CER":0.0,"CMR":0.0}
 with pytest.raises(ValueError):posttest_metrics(static+proposed)

def test_oracle_priority_applies_urgency_once_and_matches_formula():
 data=load_all_data();cid="helmet_selection";risk_hat={c:.4 for c in data["competencies"]};theta={c:.3 for c in data["competencies"]}
 values=calculate_oracle_priorities(risk_hat,theta,data["competencies"],.8)
 expected=.4*(.8-.3)*data["competencies"][cid].urgency
 assert values[cid]==pytest.approx(expected)

def test_oracle_difficulty_is_challenge_aware_and_not_fixed_at_one():
 assert choose_oracle_difficulty(.1)==1
 assert choose_oracle_difficulty(.55)==2
 assert choose_oracle_difficulty(.9)==3
 cfg=CanonicalConfig(methods=["oracle"],profiles=["T3"],episodes=5,repetitions=1)
 cycles,_,_=run_single("oracle","T3",0,cfg)
 assert {row["next_difficulty"] for row in cycles}!={1}

def test_every_competence_has_valid_scenario_mapping():
 data=load_all_data()
 for cid in data["competencies"]:
  matches=[scenario for scenario in data["scenarios"].values() if cid in scenario.target_competencies]
  assert matches and all(cid in scenario.target_competencies for scenario in matches)

def test_canonical_metric_definitions_are_unchanged():
 assert HIGHER_BETTER==("CCG_star","RWCS_star","TAR","AR","DC","TC","CDRS")
 assert LOWER_BETTER==("CER","CMR","SOR","episodes_to_target")

def test_canonical_encodings_and_current_assistance_coefficient():
 assert DIFFICULTY_ENCODING=={1:0.0,2:.5,3:1.0}
 assert ASSISTANCE_ENCODING=={"none":0.0,"minimal":.25,"limited_visual_guidance":.5,"full_visual_guidance":1.0}
 cfg=CanonicalConfig(episodes=1,repetitions=1)
 assert cfg.w_action*cfg.kappa/cfg.w_independence==pytest.approx(.36)
 assert cfg.assistance_independence_coefficient==pytest.approx(.44)
 data=load_all_data();state=LatentState({c:.5 for c in data["competencies"]})
 obs=generate_observations(state,data["scenarios"]["S1"],data["ppe"],1,"full_visual_guidance",cfg,42,60)
 assert obs["independence"]==pytest.approx(.56)

def test_canonical_rule_threshold_boundaries_and_precedence():
 assert choose_adaptation_v2(.75,.599999,0,0,False,2,False)["selected_rule"]=="critical_risk_low_mastery"
 assert choose_adaptation_v2(.50,.60,2,0,False,2,False)["selected_rule"]=="high_risk_repeated_error"
 assert choose_adaptation_v2(.50,.80,0,0,False,2,True)["selected_rule"]=="high_mastery_high_risk_correct"
 assert choose_adaptation_v2(.49,.65,0,0,False,2,True)["selected_rule"]=="stable_mastery_correct"
 assert choose_adaptation_v2(.49,.649999,0,0,False,2,True)["selected_rule"]=="default_reinforcement"
 assert choose_adaptation_v2(.75,.59,2,0,False,2,False)["selected_rule"]=="critical_risk_low_mastery"

def test_canonical_latent_decay_and_challenge_growth_equations():
 import math
 cfg=CanonicalConfig(episodes=1,repetitions=1);state=LatentState({"practiced":.4,"idle":.4})
 evolve_latent(state,{"practiced"},2,cfg)
 expected=.4+cfg.practice_rate*(1-.4)*math.exp(-((.5-.4)**2)/(cfg.sigma_g**2))
 assert state.theta_star["practiced"]==pytest.approx(expected)
 assert state.theta_star["idle"]==pytest.approx(.4*(1-cfg.latent_decay))

def test_canonical_ccg_rwcs_tar_and_target_scopes():
 data=load_all_data();weights=competence_risk_weights(data);critical=[c for c,d in data["competencies"].items() if d.high_risk_related]
 assert len(data["competencies"])==10 and len(critical)==7
 initial={c:.2 for c in data["competencies"]};final={c:(.8 if c in critical else .1) for c in data["competencies"]}
 out=latent_outcomes(initial,final,data["competencies"],weights,.8)
 assert out["CCG_star"]==.6 and out["TAR"]==.7
 assert out["RWCS_star"]==pytest.approx(round(sum(final[c]*weights[c] for c in final)/sum(weights.values()),6))
 assert _target(final,data["competencies"],.8) is True

def test_canonical_bounded_error_factor_and_cap():
 data=load_all_data();cid="eye_protection_selection";scores={c:.4 for c in data["competencies"]}
 factors=[]
 for errors in (0,1,2,3,4,100):
  result=calculate_priorities(1,[cid],scores,{cid:errors},data["competencies"],.5,.8,3)
  q=result["priority_by_competence"][cid]
  factors.append(q/(.4*data["competencies"][cid].urgency))
 assert factors==pytest.approx([1,1+1/6,1+1/3,1.5,1.5,1.5])

def test_canonical_proposed_priority_uses_raw_risk_and_urgency_once():
 data=load_all_data();risks=competence_contextual_risks(data);cid="visibility_protection_selection"
 scores={c:.4 for c in data["competencies"]};errors={c:2 for c in data["competencies"]}
 actual=calculate_priorities(risks[cid],[cid],scores,errors,data["competencies"],.5,.8,3)["priority_by_competence"][cid]
 phi=1+.5*min(1,2/3);expected=round(risks[cid]*(.8-.4)*phi*data["competencies"][cid].urgency,4)
 assert actual==expected
 assert competence_risk_weights(data)[cid]==pytest.approx(risks[cid]*data["competencies"][cid].urgency)

def test_expected_observation_assistance_is_neutral_without_clipping():
 cfg=CanonicalConfig(episodes=1,repetitions=1);base_action=.4;base_response=.5
 values=[]
 for a in ASSISTANCE_ENCODING.values():
  action=base_action+cfg.kappa*a
  response=base_response+cfg.response_assistance_coefficient*a
  independence=1-cfg.assistance_independence_coefficient*a
  values.append(observation_score(action,response,independence,cfg))
 assert values==pytest.approx([values[0]]*4)
