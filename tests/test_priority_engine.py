from core.data_loader import load_all_data
from core.priority_engine import calculate_global_priorities,calculate_priorities
import pytest

def test_priority_risk_repetition_urgency_and_ranking():
    d=load_all_data(); targets=["eye_protection_selection","hand_protection_selection"]
    scores={k:.4 for k in d["competencies"]}; errors={k:0 for k in scores}
    base=calculate_priorities(.5,targets,scores,errors,d["competencies"])
    errors["eye_protection_selection"]=2
    repeated=calculate_priorities(.5,targets,scores,errors,d["competencies"])
    highrisk=calculate_priorities(.8,targets,scores,errors,d["competencies"])
    assert repeated["priority_by_competence"]["eye_protection_selection"]>base["priority_by_competence"]["eye_protection_selection"]
    assert highrisk["highest_priority_value"]>repeated["highest_priority_value"]
    assert repeated["priority_ranking"][0][0]==repeated["highest_priority_competence"]

def test_negative_repeated_errors_raise():
    d=load_all_data(); scores={k:.4 for k in d["competencies"]}
    with pytest.raises(ValueError,match="non-negative integer"):
        calculate_priorities(.5,["eye_protection_selection"],scores,
            {"eye_protection_selection":-1},d["competencies"])

def test_global_priority_can_leave_current_scenario():
    d=load_all_data(); scores={k:.8 for k in d["competencies"]}
    scores["respiratory_protection_selection"]=.2
    errors={k:0 for k in scores}
    risks={k:.2 for k in scores}; risks["respiratory_protection_selection"]=.9
    result=calculate_global_priorities(risks,scores,errors,d["competencies"])
    assert result["highest_priority_competence"]=="respiratory_protection_selection"
