from core.data_loader import load_all_data
from core.scenario_manager import select_next_scenario,select_priority_alternative,difficulty_behavior

def test_repeat_required(): 
    d=load_all_data(); assert select_next_scenario("S5",d["scenarios"],[],[],True)=="S5"

def test_priority_and_least_recently_used():
    d=load_all_data(); rank=[("eye_protection_selection",1)]
    assert select_next_scenario("S2",d["scenarios"],rank,["S2","S2","S3"],False)=="S4"

def test_deterministic_fallback_and_difficulty_behavior():
    d=load_all_data()
    assert select_next_scenario("S1",d["scenarios"],[],[],False)=="S2"
    s=d["scenarios"]["S5"]; easy=difficulty_behavior(s,1,"none",d["ppe"]); hard=difficulty_behavior(s,3,"high",d["ppe"])
    assert easy["time_limit_seconds"]>hard["time_limit_seconds"]
    assert len(hard["ppe_options"])==6

def test_priority_alternative_excludes_current_scenario():
    d=load_all_data()
    result=select_priority_alternative("S5",d["scenarios"],
        [("respiratory_protection_selection",1)],["S5","S5"])
    assert result=="S4"
