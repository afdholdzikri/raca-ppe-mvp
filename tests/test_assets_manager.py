"""Tests for safe visual-asset resolution."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import assets_manager as assets


def test_known_character_resolution():
    path = assets.get_domain_character("Manufacturing", "safe")
    assert path.name == "manufacturing_worker_safe.png"
    assert assets.image_exists(path)


def test_unknown_character_uses_fallback():
    path = assets.get_domain_character("unknown domain", "warning")
    assert path == assets.PLACEHOLDERS_DIR / "missing_character.png"


def test_known_background_mapping():
    assert assets.get_scenario_background("construction", "C5").name == "work_at_height.png"
    assert assets.get_scenario_background("chemical_laboratory", "CL1").name == "corrosive_liquid_transfer.png"


def test_unknown_scenario_uses_domain_default():
    path = assets.get_scenario_background("construction", "not-a-scenario")
    assert path.name == "construction_default.png"


@pytest.mark.parametrize(
    ("alias", "filename"),
    [
        ("safety helmet", "helmet.png"),
        ("boots", "safety_footwear.png"),
        ("goggles", "safety_goggles.png"),
        ("lab-coat", "laboratory_coat.png"),
    ],
)
def test_ppe_alias_resolution(alias, filename):
    assert assets.get_ppe_icon(alias).name == filename


def test_unknown_hazard_uses_fallback():
    path = assets.get_hazard_icon("unmapped radiation source")
    assert path == assets.PLACEHOLDERS_DIR / "missing_hazard_icon.png"


def test_corrupt_image_is_not_treated_as_existing(tmp_path):
    corrupt = tmp_path / "corrupt.png"
    corrupt.write_bytes(b"not an image")
    assert not assets.image_exists(corrupt)


@pytest.mark.parametrize("value", ["../risk_low", "folder/risk_low", r"folder\risk_low", "C:asset"])
def test_path_traversal_rejected(value):
    with pytest.raises(ValueError):
        assets.resolve_asset_path("badge", value)


def test_manifest_is_json_serializable_and_relative():
    manifest = assets.build_asset_manifest()
    json.dumps(manifest)
    assert manifest["assets"]
    assert all(not Path(item["path"]).is_absolute() for item in manifest["assets"])


def test_asset_validation():
    report = assets.validate_asset_catalog()
    assert report["status"] == "ok"
    assert report["total_assets"] == 64
    assert report["valid_assets"] == 64
    assert report["missing_assets"] == []
    assert report["invalid_assets"] == []
    assert report["duplicate_normalized_keys"] == []


def test_source_has_no_hard_coded_absolute_windows_path():
    source = Path(assets.__file__).read_text(encoding="utf-8")
    assert "C:\\Users\\" not in source
