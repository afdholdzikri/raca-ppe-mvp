"""Presentation-only domain and scenario mappings for the RACA PPE UI."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping


PROJECT_ROOT = Path(__file__).resolve().parent
_ASSET_DIRECTORIES = {
    "background": PROJECT_ROOT / "assets" / "backgrounds",
    "character": PROJECT_ROOT / "assets" / "characters",
}
_FALLBACKS = {
    "background": PROJECT_ROOT / "assets" / "placeholders" / "missing_background.png",
    "character": PROJECT_ROOT / "assets" / "placeholders" / "missing_character.png",
}
_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")


DOMAIN_VISUAL_CONFIG: dict[str, dict[str, str | None]] = {
    "manufacturing": {
        "display_name": "Manufacturing",
        "default_background": "manufacturing_default",
        "neutral_character": "manufacturing_worker_neutral",
        "safe_character": "manufacturing_worker_safe",
        "warning_character": "manufacturing_worker_warning",
        "domain_icon": None,
    },
    "chemical_laboratory": {
        "display_name": "Chemical Laboratory",
        "default_background": "chemical_laboratory_default",
        "neutral_character": "chemical_laboratory_worker_neutral",
        "safe_character": "chemical_laboratory_worker_safe",
        "warning_character": "chemical_laboratory_worker_warning",
        "domain_icon": None,
    },
    "construction": {
        "display_name": "Construction",
        "default_background": "construction_default",
        "neutral_character": "construction_worker_neutral",
        "safe_character": "construction_worker_safe",
        "warning_character": "construction_worker_warning",
        "domain_icon": None,
    },
}


def _scene(
    scenario_id: str,
    visual_title: str,
    background_key: str,
    scene_caption: str,
    visual_hints: list[str],
    aliases: list[str] | None = None,
) -> dict[str, Any]:
    """Build one presentation record without scientific scenario content."""
    return {
        "scenario_id": scenario_id,
        "visual_title": visual_title,
        "background_key": background_key,
        "character_state_default": "neutral",
        "scene_caption": scene_caption,
        "visual_hints": visual_hints,
        "aliases": aliases or [],
    }


SCENARIO_VISUAL_CONFIG: dict[str, dict[str, dict[str, Any]]] = {
    "manufacturing": {
        "S1": _scene("S1", "Material Handling", "material_handling", "Active warehouse material-handling lane.", ["Observe traffic boundaries and work-zone visibility."], ["material handling near vehicle traffic"]),
        "S2": _scene("S2", "Material Cutting", "material_cutting", "Industrial cutting and trimming workstation.", ["Inspect the cutting interface and exposed material edges."], ["cutting industrial material", "cutting and trimming industrial material"]),
        "S3": _scene("S3", "Welding Operation", "welding_area", "Designated welding work area.", ["Observe the active work envelope and nearby exposure points."], ["performing a welding operation", "welding"]),
        "S4": _scene("S4", "Dusty Equipment Inspection", "dusty_manufacturing_zone", "Manufacturing equipment in an airborne-dust zone.", ["Observe airborne material around the inspection point."], ["inspecting dusty equipment", "inspecting equipment under airborne dust exposure"]),
        "S5": _scene("S5", "Chemical Mixing", "volatile_solvent_mixing", "Chemical-mixing station with limited ventilation.", ["Observe the mixing vessel and ventilation context."], ["mixing chemical materials", "mixing chemical materials under low ventilation"]),
        "S6": _scene("S6", "Machinery Inspection", "machinery_inspection", "Industrial machinery inspection area.", ["Observe machinery boundaries and overhead activity."], ["inspecting machinery", "inspecting industrial machinery"]),
    },
    "chemical_laboratory": {
        "CL1": _scene("CL1", "Corrosive-Liquid Transfer", "corrosive_liquid_transfer", "Wet-chemistry liquid-transfer station.", ["Observe vessel position and the transfer boundary."], ["transferring corrosive liquid"]),
        "CL2": _scene("CL2", "Volatile-Solvent Mixing", "volatile_solvent_mixing", "Solvent preparation and mixing bench.", ["Observe the open-work area and ventilation context."], ["mixing volatile solvents"]),
        "CL3": _scene("CL3", "Contaminated Glassware Cleanup", "contaminated_glassware", "Laboratory cleanup area with damaged glassware.", ["Observe the cleanup boundary and contaminated materials."], ["cleaning contaminated broken glassware"]),
        "CL4": _scene("CL4", "Chemical-Splash Response", "chemical_splash_response", "Controlled response area for a small chemical splash.", ["Observe the affected surface and response perimeter."], ["responding to a small chemical splash"]),
        "CL5": _scene("CL5", "Low-Ventilation Laboratory", "low_ventilation_lab", "Chemical work area with reduced ventilation.", ["Observe the airflow context and active handling zone."], ["handling chemicals under low ventilation"]),
    },
    "construction": {
        "C1": _scene("C1", "Ground Site Inspection", "ground_site_inspection", "Ground-level inspection in an active construction site.", ["Observe overhead activity and ground conditions."], ["ground level site inspection"]),
        "C2": _scene("C2", "Construction Material Cutting", "material_cutting", "Construction material-cutting zone.", ["Observe debris direction and material edges."], ["material cutting"]),
        "C3": _scene("C3", "Moving Equipment Zone", "moving_equipment_zone", "Work area adjacent to mobile construction equipment.", ["Observe equipment routes and separation boundaries."], ["working near moving equipment"]),
        "C4": _scene("C4", "Drilling Zone", "drilling_zone", "Dust-producing construction drilling area.", ["Observe dust and debris around the drilling point."], ["dust producing drilling"]),
        "C5": _scene("C5", "Work at Height", "work_at_height", "Elevated construction work area.", ["Observe elevation edges and the work envelope."], ["working at height"]),
        "C6": _scene("C6", "High-Noise Operation", "high_noise_operation", "Construction plant and high-noise operating zone.", ["Observe operating equipment and marked work boundaries."], ["high noise equipment operation"]),
    },
}


def _normalize(value: Any) -> str:
    normalized = str(value).strip().lower().replace("-", " ")
    normalized = re.sub(r"\s+", "_", normalized)
    normalized = re.sub(r"[^a-z0-9_]", "", normalized)
    return re.sub(r"_+", "_", normalized).strip("_")


def _relative_asset(path: Path) -> str:
    """Return a portable project-relative asset path."""
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def _resolve_visual_asset(category: str, asset_key: Any) -> Path:
    """Resolve an internal visual key without depending on the public manager."""
    directory = _ASSET_DIRECTORIES[category]
    safe_key = _normalize(asset_key)
    for extension in _EXTENSIONS:
        candidate = directory / f"{safe_key}{extension}"
        if candidate.is_file() and candidate.stat().st_size > 0:
            return candidate
    return _FALLBACKS[category]


def _find_scene(domain_key: str, scenario_id: str | None, scenario_name: str | None) -> dict[str, Any] | None:
    scenes = SCENARIO_VISUAL_CONFIG.get(domain_key, {})
    if scenario_id:
        requested_id = str(scenario_id).strip().upper()
        if requested_id in scenes:
            return scenes[requested_id]
    if scenario_name:
        requested_name = _normalize(scenario_name)
        for scene in scenes.values():
            names = [scene["visual_title"], scene["scene_caption"], *scene.get("aliases", [])]
            if requested_name in {_normalize(name) for name in names}:
                return scene
    return None


def get_scenario_visual_config(
    domain: str,
    scenario_id: str | None = None,
    scenario_name: str | None = None,
) -> dict[str, Any]:
    """Resolve presentation assets with domain-default and placeholder fallbacks."""
    domain_key = _normalize(domain)
    domain_config = DOMAIN_VISUAL_CONFIG.get(domain_key)
    scene = _find_scene(domain_key, scenario_id, scenario_name)

    if domain_config is None:
        background = _FALLBACKS["background"]
        character = _FALLBACKS["character"]
        result = {
            "background": _relative_asset(background),
            "character": _relative_asset(character),
            "caption": "Visual context unavailable.",
            "domain_label": "Unknown Domain",
            "visual_status": "fallback",
            "visual_title": str(scenario_name or scenario_id or "Scenario"),
            "visual_hints": [],
        }
    else:
        background_key = scene["background_key"] if scene else domain_config["default_background"]
        background = _resolve_visual_asset("background", background_key)
        character = _resolve_visual_asset("character", domain_config["neutral_character"])
        result = {
            "background": _relative_asset(background),
            "character": _relative_asset(character),
            "caption": scene["scene_caption"] if scene else f"{domain_config['display_name']} training context.",
            "domain_label": domain_config["display_name"],
            "visual_status": "mapped" if scene else "domain_default",
            "visual_title": scene["visual_title"] if scene else str(scenario_name or scenario_id or "Scenario"),
            "visual_hints": list(scene["visual_hints"]) if scene else [],
        }
    json.dumps(result)
    return result


def determine_character_state(
    evaluation_result: Any = None,
    risk_category: str | None = None,
    missing_ppe: list[Any] | None = None,
) -> str:
    """Choose a presentation state without changing any scientific result."""
    if missing_ppe:
        return "warning"
    if isinstance(evaluation_result, Mapping):
        evaluation_result = evaluation_result.get("correct", evaluation_result.get("status"))
    if evaluation_result is True:
        return "safe"
    if evaluation_result is False:
        return "warning"
    result_key = _normalize(evaluation_result or "")
    if result_key in {"correct", "safe", "passed", "pass"}:
        return "safe"
    if result_key in {"incorrect", "warning", "failed", "fail", "partial", "partially_correct"}:
        return "warning"
    if _normalize(risk_category or "") in {"high", "critical"}:
        return "warning"
    return "neutral"


def _scenario_ids(values: Any) -> set[str]:
    if isinstance(values, Mapping):
        return {str(value) for value in values.keys()}
    if isinstance(values, str):
        return {values}
    return {str(getattr(value, "id", value)) for value in values}


def validate_visual_mapping(
    known_domains: Iterable[str],
    known_scenarios: Mapping[str, Any] | Iterable[str],
) -> dict[str, Any]:
    """Validate coverage and referenced assets against externally known IDs."""
    domains = [_normalize(domain) for domain in known_domains]
    if isinstance(known_scenarios, Mapping):
        scenarios_by_domain = {
            _normalize(domain): _scenario_ids(values)
            for domain, values in known_scenarios.items()
        }
    else:
        scenarios_by_domain = {domain: _scenario_ids(known_scenarios) for domain in domains}

    mapped: list[str] = []
    unmapped: list[str] = []
    unknown_assets: list[str] = []
    fallback_usage: list[str] = []
    for domain in domains:
        domain_config = DOMAIN_VISUAL_CONFIG.get(domain)
        if domain_config is None:
            fallback_usage.append(f"{domain}:domain")
        else:
            for field, category in (("default_background", "background"), ("neutral_character", "character"), ("safe_character", "character"), ("warning_character", "character")):
                key = str(domain_config[field])
                resolved = _resolve_visual_asset(category, key)
                expected_directory = _ASSET_DIRECTORIES[category]
                if resolved.parent.resolve() != expected_directory.resolve() or resolved.stem != key:
                    unknown_assets.append(f"{domain}:{field}:{key}")
        for scenario_id in sorted(scenarios_by_domain.get(domain, set())):
            reference = f"{domain}:{scenario_id}"
            scene = SCENARIO_VISUAL_CONFIG.get(domain, {}).get(scenario_id.upper())
            if scene is None:
                unmapped.append(reference)
                fallback_usage.append(reference)
                continue
            mapped.append(reference)
            background_key = str(scene["background_key"])
            background = _resolve_visual_asset("background", background_key)
            if background.parent.resolve() != _ASSET_DIRECTORIES["background"].resolve() or background.stem != background_key:
                unknown_assets.append(f"{reference}:background:{background_key}")

    report = {
        "mapped_scenarios": mapped,
        "unmapped_scenarios": unmapped,
        "unknown_assets": sorted(set(unknown_assets)),
        "fallback_usage": sorted(set(fallback_usage)),
        "status": "ok" if not unmapped and not unknown_assets and not fallback_usage else "warning",
    }
    json.dumps(report)
    return report
