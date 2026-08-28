import pytest

from core.learner_model import calculate_observation_score, update_competence
from core.learner_model import (calculate_response_score,calculate_independence_score,
    initialize_learner,update_multi_competence)
from core.data_loader import load_all_data


def test_correct_observation_score():
    assert calculate_observation_score(True) == 1.0


def test_incorrect_observation_score():
    assert calculate_observation_score(False) == 0.4


def test_competence_update_is_deterministic():
    assert update_competence(0.4, 1.0) == 0.52


@pytest.mark.parametrize("current, observation", [(0.0, 0.0), (1.0, 1.0), (0.4, 1.0)])
def test_competence_remains_bounded(current, observation):
    assert 0 <= update_competence(current, observation) <= 1


def test_invalid_learning_rate_raises():
    with pytest.raises(ValueError):
        update_competence(0.4, 1.0, 0)

def test_initialization_and_multi_update_preserves_unaffected():
    d=load_all_data(); scores,errors=initialize_learner(d["competencies"])
    result=update_multi_competence(scores,errors,["eye_protection_selection"],
        {"eye_protection_selection":True},1,1)
    assert result["competence_scores"]["eye_protection_selection"]>.4
    assert result["competence_scores"]["helmet_selection"]==.4
    assert result["repeated_errors"]["eye_protection_selection"]==0

@pytest.mark.parametrize("elapsed,expected",[(5,1),(60,.8),(80,.6),(110,.3)])
def test_response_scoring(elapsed,expected): assert calculate_response_score(elapsed,100)==expected

def test_hint_independence(): assert calculate_independence_score(True)==.5 and calculate_independence_score(False)==1

def test_incorrect_increments_error_and_stays_bounded():
    d=load_all_data(); scores,errors=initialize_learner(d["competencies"])
    result=update_multi_competence(scores,errors,["eye_protection_selection"],
        {"eye_protection_selection":False},.3,.5)
    assert result["repeated_errors"]["eye_protection_selection"]==1
    assert 0<=result["competence_scores"]["eye_protection_selection"]<=1
