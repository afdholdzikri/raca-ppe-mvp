"""Cached JSON loading with cross-reference validation."""
import json
from functools import lru_cache
from pathlib import Path
from .models import PPEItem, Hazard, Competence, Scenario

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load(name: str, data_dir: Path) -> list[dict]:
    path = data_dir / name
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to load {name}: {exc}") from exc
    if not isinstance(value, list): raise ValueError(f"{name} must contain a JSON list")
    return value


@lru_cache(maxsize=4)
def load_all_data(data_dir: str | Path = DATA_DIR) -> dict:
    root = Path(data_dir)
    ppe = {x.id: x for x in (PPEItem(**v) for v in _load("ppe.json", root))}
    hazards = {x.id: x for x in (Hazard(**v) for v in _load("hazards.json", root))}
    competencies = {x.id: x for x in (Competence(**v) for v in _load("competencies.json", root))}
    scenarios = {x.id: x for x in (Scenario(**v) for v in _load("scenarios.json", root))}
    if len(ppe) != 6: raise ValueError("ppe.json must contain exactly six unique PPE items")
    for item in ppe.values():
        if item.associated_competence_id not in competencies:
            raise ValueError(
                f"PPE {item.id} references unknown competence "
                f"{item.associated_competence_id}"
            )
    for hazard in hazards.values():
        for item in hazard.associated_ppe:
            if item not in ppe: raise ValueError(f"Hazard {hazard.id} references unknown PPE {item}")
        if hazard.associated_competence_id not in competencies:
            raise ValueError(f"Hazard {hazard.id} references unknown competence {hazard.associated_competence_id}")
    for scenario in scenarios.values():
        for item in scenario.required_ppe + scenario.distractor_pool:
            if item not in ppe: raise ValueError(f"Scenario {scenario.id} references unknown PPE {item}")
        for hazard in scenario.hazards:
            if hazard not in hazards: raise ValueError(f"Scenario {scenario.id} references unknown hazard {hazard}")
        for competence in scenario.target_competencies:
            if competence not in competencies: raise ValueError(f"Scenario {scenario.id} references unknown competence {competence}")
    rules = json.loads((root / "adaptation_rules.json").read_text(encoding="utf-8"))
    return {"ppe": ppe, "hazards": hazards, "competencies": competencies, "scenarios": scenarios, "adaptation_rules": rules}
