"""Tests for presentation-only domain and scenario visual mappings."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import assets_manager
from experiments.domain_adapter import DOMAIN_REGISTRY, load_domain
import scenario_visual_map as visuals


@pytest.fixture(scope="module")
def known_scenarios():
    return {domain: load_domain(domain)["scenarios"] for domain in DOMAIN_REGISTRY}


def test_every_known_domain_has_complete_defaults():
    assert set(DOMAIN_REGISTRY) <= set(visuals.DOMAIN_VISUAL_CONFIG)
    for domain in DOMAIN_REGISTRY:
        config = visuals.DOMAIN_VISUAL_CONFIG[domain]
        assert config["display_name"]
        assert assets_manager.image_exists(assets_manager.resolve_asset_path("background", config["default_background"]))
        for state in ("neutral", "safe", "warning"):
            assert assets_manager.image_exists(assets_manager.resolve_asset_path("character", config[f"{state}_character"]))


def test_every_known_scenario_safely_resolves(known_scenarios):
    for domain, scenarios in known_scenarios.items():
        for scenario in scenarios.values():
            result = visuals.get_scenario_visual_config(domain, scenario.id, scenario.task)
            assert result["visual_status"] == "mapped"
            assert assets_manager.image_exists(assets_manager.PROJECT_ROOT / result["background"])
            assert assets_manager.image_exists(assets_manager.PROJECT_ROOT / result["character"])


def test_unknown_scenario_uses_domain_default():
    result = visuals.get_scenario_visual_config("construction", "UNKNOWN")
    assert result["visual_status"] == "domain_default"
    assert result["background"] == "assets/backgrounds/construction_default.png"
    assert result["domain_label"] == "Construction"


@pytest.mark.parametrize(
    ("evaluation", "risk", "missing", "expected"),
    [
        (True, "critical", [], "safe"),
        (False, "low", [], "warning"),
        (None, "critical", [], "warning"),
        (None, "low", [], "neutral"),
        ({"correct": True}, "low", ["goggles"], "warning"),
    ],
)
def test_character_state_is_presentation_only(evaluation, risk, missing, expected):
    assert visuals.determine_character_state(evaluation, risk, missing) == expected


def test_outputs_are_json_serializable(known_scenarios):
    result = visuals.get_scenario_visual_config("chemical_laboratory", "CL2")
    report = visuals.validate_visual_mapping(DOMAIN_REGISTRY, known_scenarios)
    json.dumps(visuals.DOMAIN_VISUAL_CONFIG)
    json.dumps(visuals.SCENARIO_VISUAL_CONFIG)
    json.dumps(result)
    json.dumps(report)


def test_mapping_validation_has_complete_coverage(known_scenarios):
    report = visuals.validate_visual_mapping(DOMAIN_REGISTRY, known_scenarios)
    assert report["status"] == "ok"
    assert len(report["mapped_scenarios"]) == 17
    assert report["unmapped_scenarios"] == []
    assert report["unknown_assets"] == []
    assert report["fallback_usage"] == []


def test_module_contains_no_scientific_scenario_definitions():
    source = Path(visuals.__file__).read_text(encoding="utf-8")
    for forbidden in ("required_ppe", "target_competencies", "context_modifier", "probability", "severity"):
        assert forbidden not in source

