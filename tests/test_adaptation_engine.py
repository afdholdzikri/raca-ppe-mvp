from core.adaptation_engine import choose_adaptation
from core.adaptation_engine import choose_adaptation_v2
import pytest


def test_priority_remediation():
    assert choose_adaptation(0.8, 0.4, 0, 2)["adaptation"] == "priority_remediation"


def test_targeted_remediation_when_rule_one_does_not_apply():
    result = choose_adaptation(0.6, 0.6, 2, 2)
    assert result["adaptation"] == "targeted_remediation"


def test_challenge_adaptation():
    assert choose_adaptation(0.6, 0.8, 0, 2)["adaptation"] == "challenge_adaptation"


def test_progressive_adaptation():
    assert choose_adaptation(0.4, 0.7, 0, 2)["adaptation"] == "progressive_adaptation"


def test_default_reinforcement():
    assert choose_adaptation(0.4, 0.5, 0, 2)["adaptation"] == "reinforcement_adaptation"


def test_next_difficulty_never_below_one():
    assert choose_adaptation(0.8, 0.4, 0, 1)["next_difficulty"] == 1


def test_next_difficulty_never_above_three():
    assert choose_adaptation(0.6, 0.8, 0, 3)["next_difficulty"] == 3

def test_v2_all_modes_and_order():
    cases=[((.8,.4,0,2,False),"priority_remediation"),
           ((.6,.6,2,2,False),"targeted_remediation"),
           ((.6,.8,0,2,True),"challenge_adaptation"),
           ((.4,.7,0,2,True),"progressive_adaptation"),
           ((.4,.4,0,2,False),"reinforcement_adaptation")]
    for args,expected in cases:
        r=choose_adaptation_v2(args[0],args[1],args[2],1,False,args[3],args[4])
        assert r["adaptation"]==expected and r["selected_rule"]==r["active_rules"][0]
        assert 1<=r["next_difficulty"]<=3

def test_critical_rule_precedes_repeated_error():
    r=choose_adaptation_v2(.9,.4,3,1,False,2,False)
    assert r["active_rules"][:2]==["critical_risk_low_mastery","high_risk_repeated_error"]

@pytest.mark.parametrize("errors,response,hint,correct",[
    (-1,1,False,False),(0,-1,False,False),(0,1,"yes",False),(0,1,False,1)])
def test_v2_invalid_inputs_raise(errors,response,hint,correct):
    with pytest.raises(ValueError):
        choose_adaptation_v2(.5,.5,errors,response,hint,2,correct)
