from core.data_loader import load_all_data
from core.risk_engine import calculate_scenario_risk
from experiments.baseline_methods import METHODS,MethodInput
from experiments.proposed_method import ProposedMethod
from experiments.experiment_config import ExperimentConfig

def context(scores=None,recent=None,risk=None):
 d=load_all_data(); s=d["scenarios"]["S1"]; scores=scores or {k:.4 for k in d["competencies"]}
 return MethodInput(s,d["scenarios"],scores,{k:0 for k in scores},2,[],recent or [],
  {"scenario_risk":risk if risk is not None else .3},ExperimentConfig(episodes_per_run=2,repetitions=1),
  True,[("eye_protection_selection",1)])
def test_static_fixed_and_deterministic():
 a=METHODS["static"].decide(context()); b=METHODS["static"].decide(context())
 assert a==b and a["next_scenario"]=="S2" and a["selected_rule"]=="fixed_sequence"
def test_score_thresholds():
 assert METHODS["score_adaptive"].decide(context(recent=[.9]))["next_difficulty"]==3
 assert METHODS["score_adaptive"].decide(context(recent=[.2]))["next_difficulty"]==1
def test_competence_largest_gap_and_ignores_risk():
 scores={k:.7 for k in load_all_data()["competencies"]}; scores["respiratory_protection_selection"]=.2
 a=METHODS["competence_adaptive"].decide(context(scores,risk=.1)); b=METHODS["competence_adaptive"].decide(context(scores,risk=.9))
 assert a["highest_priority_competence"]=="respiratory_protection_selection" and a==b

def test_proposed_bounds_consecutive_remediation_repeats():
 c=context(); c=MethodInput(c.scenario,c.scenarios,c.competence_scores,
  {**c.repeated_errors,"eye_protection_selection":3},2,["S1","S1"],
  c.recent_scores,{"scenario_risk":.8},c.config,False,c.priority_ranking)
 result=ProposedMethod().decide(c)
 assert result["next_scenario"]!="S1"
 assert result["repeat_required"] is False
 assert "bounded_remediation_rotation" in result["active_rules"]

def test_proposed_bounds_priority_reselection_without_repeat_flag():
 d=load_all_data(); s=d["scenarios"]["S5"]; scores={k:.8 for k in d["competencies"]}
 c=MethodInput(s,d["scenarios"],scores,{k:0 for k in scores},2,["S5","S5"],[],
  {"scenario_risk":.8},ExperimentConfig(episodes_per_run=2,repetitions=1),
  True,[("chemical_ppe_selection",1)])
 result=ProposedMethod().decide(c)
 assert result["next_scenario"]!="S5"
 assert result["repeat_required"] is False
 assert "bounded_remediation_rotation" in result["active_rules"]
