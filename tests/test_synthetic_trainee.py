from core.data_loader import load_all_data
from core.risk_engine import calculate_scenario_risk
from experiments.synthetic_trainee import SyntheticTrainee,episode_seed,load_profiles,initial_scores

def action(profile,seed,sid="S5",errors=None):
    d=load_all_data(); s=d["scenarios"][sid]; p=load_profiles()[profile]
    scores=initial_scores(p,d["competencies"]); risk=calculate_scenario_risk(s.hazards,d["hazards"],s.context_modifier)
    return SyntheticTrainee(p,seed).act(s,d["ppe"],scores,s.base_difficulty,"limited_visual_guidance",risk["scenario_risk"],errors or {},s.time_limit_seconds)

def test_same_seed_same_action(): assert action("T1",42)==action("T1",42)
def test_different_seed_changes_action(): assert action("T1",42)!=action("T1",43)
def test_action_fields_valid():
    d=load_all_data(); a=action("T2",4)
    assert .05<=a.correct_probability<=.95 and set(a.selected_ppe)<=set(d["ppe"])
    assert a.response_time>=0 and isinstance(a.hint_used,bool)
def test_t4_eye_failure_probability_lower_than_neutral():
    assert action("T4",1,"S2",{"eye_protection_selection":2}).correct_probability < action("T5",1,"S2").correct_probability
def test_t2_more_critical_error_tendency_than_t3():
    assert action("T2",1).correct_probability < action("T3",1).correct_probability
def test_episode_seeds_are_stable_and_distinct():
    assert episode_seed(42,1)==episode_seed(42,1)
    assert episode_seed(42,1)!=episode_seed(42,2)
