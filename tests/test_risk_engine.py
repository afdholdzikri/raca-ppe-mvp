import pytest

from core.risk_engine import calculate_contextual_risk
from core.risk_engine import calculate_scenario_risk, risk_category
from core.data_loader import load_all_data


def test_high_risk_is_greater_than_low_risk():
    assert calculate_contextual_risk(5, 5, 5) > calculate_contextual_risk(1, 1, 1)


@pytest.mark.parametrize("values", [(1, 1, 1, 0.1), (5, 5, 5, 10)])
def test_normalized_risk_is_bounded(values):
    assert 0 <= calculate_contextual_risk(*values) <= 1


def test_invalid_probability_raises():
    with pytest.raises(ValueError):
        calculate_contextual_risk(0, 3, 3)


def test_invalid_severity_raises():
    with pytest.raises(ValueError):
        calculate_contextual_risk(3, 6, 3)


def test_invalid_exposure_raises():
    with pytest.raises(ValueError):
        calculate_contextual_risk(3, 3, 0)


def test_invalid_context_modifier_raises():
    with pytest.raises(ValueError):
        calculate_contextual_risk(3, 3, 3, 0)

def test_multiple_hazard_risk_uses_maximum():
    d=load_all_data(); r=calculate_scenario_risk(["sharp_surface","flying_fragment"],d["hazards"],1)
    assert r["scenario_risk"]==max(r["hazard_risk_values"].values())
    assert 0<=r["mean_risk"]<=1

@pytest.mark.parametrize("value,category",[(0,"Low"),(.2499,"Low"),(.25,"Medium"),(.4999,"Medium"),(.5,"High"),(.7499,"High"),(.75,"Critical"),(1,"Critical")])
def test_category_boundaries(value,category): assert risk_category(value)==category
