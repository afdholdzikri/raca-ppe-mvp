"""Shared loading and validation for Version 4 safety domains."""
from __future__ import annotations
import json
from dataclasses import asdict
from pathlib import Path
from core.models import PPEItem,Hazard,Competence,Scenario
from core.risk_engine import calculate_scenario_risk

DATA_ROOT=Path(__file__).resolve().parent.parent/"data"
DOMAIN_REGISTRY={
    "manufacturing":DATA_ROOT/"manufacturing",
    "chemical_laboratory":DATA_ROOT/"chemical_laboratory",
    "construction":DATA_ROOT/"construction",
}
DOMAIN_FILES=("ppe.json","hazards.json","competencies.json","scenarios.json","safety_rules.json")

def resolve_domain_path(domain:str)->Path:
    try:return DOMAIN_REGISTRY[domain]
    except KeyError:raise ValueError(f"unknown domain {domain!r}; choose from {', '.join(DOMAIN_REGISTRY)}") from None

def _records(path:Path)->list[dict]:
    try:value=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as exc:raise ValueError(f"unable to load {path}: {exc}") from exc
    if not isinstance(value,list):raise ValueError(f"{path.name} must contain a JSON list")
    ids=[item.get("id") for item in value]
    if any(not isinstance(item,str) or not item for item in ids):raise ValueError(f"{path.name} contains an invalid id")
    if len(ids)!=len(set(ids)):raise ValueError(f"{path.name} contains duplicate ids")
    return value

def load_domain(domain:str)->dict:
    root=resolve_domain_path(domain)
    raw={name:_records(root/name) for name in DOMAIN_FILES}
    ppe={x.id:x for x in (PPEItem(**v) for v in raw["ppe.json"])}
    hazards={x.id:x for x in (Hazard(**v) for v in raw["hazards.json"])}
    competencies={x.id:x for x in (Competence(**v) for v in raw["competencies.json"])}
    scenarios={x.id:x for x in (Scenario(**v) for v in raw["scenarios.json"])}
    for item in ppe.values():
        if item.associated_competence_id not in competencies:raise ValueError(f"PPE {item.id} references unknown competence {item.associated_competence_id}")
    for hazard in hazards.values():
        if hazard.associated_competence_id not in competencies:raise ValueError(f"Hazard {hazard.id} references unknown competence {hazard.associated_competence_id}")
        for item in hazard.associated_ppe:
            if item not in ppe:raise ValueError(f"Hazard {hazard.id} references unknown PPE {item}")
    for scenario in scenarios.values():
        for item in scenario.required_ppe+scenario.distractor_pool:
            if item not in ppe:raise ValueError(f"Scenario {scenario.id} references unknown PPE {item}")
        for hazard in scenario.hazards:
            if hazard not in hazards:raise ValueError(f"Scenario {scenario.id} references unknown hazard {hazard}")
        for competence in scenario.target_competencies:
            if competence not in competencies:raise ValueError(f"Scenario {scenario.id} references unknown competence {competence}")
    rules=raw["safety_rules.json"]
    for rule in rules:
        for scenario in rule.get("scenario_ids",[]):
            if scenario not in scenarios:raise ValueError(f"Safety rule {rule['id']} references unknown scenario {scenario}")
        for item in rule.get("required_ppe",[]):
            if item not in ppe:raise ValueError(f"Safety rule {rule['id']} references unknown PPE {item}")
    risks={sid:calculate_scenario_risk(s.hazards,hazards,s.context_modifier) for sid,s in scenarios.items()}
    if not any(value["scenario_risk"]>=.65 for value in risks.values()):raise ValueError(f"{domain} requires at least one high-risk scenario")
    return {"domain":domain,"path":root,"ppe":ppe,"hazards":hazards,"competencies":competencies,
      "scenarios":scenarios,"safety_rules":rules,"scenario_risks":risks}

def initialize_domain_learner(domain_data,profile)->tuple[dict[str,float],dict[str,int]]:
    values=profile["initial_competence_scores"];default=float(values.get("default",.4))
    scores={cid:float(values.get(cid,c.initial_mastery if "default" not in values else default)) for cid,c in domain_data["competencies"].items()}
    return scores,{cid:0 for cid in scores}

def domain_snapshot(domain_data)->dict:
    return {"domain":domain_data["domain"],"ppe":[asdict(x) for x in domain_data["ppe"].values()],
      "hazards":[asdict(x) for x in domain_data["hazards"].values()],
      "competencies":[asdict(x) for x in domain_data["competencies"].values()],
      "scenarios":[asdict(x) for x in domain_data["scenarios"].values()],
      "safety_rules":domain_data["safety_rules"]}

def validate_all_domains()->dict[str,dict]:
    return {domain:load_domain(domain) for domain in DOMAIN_REGISTRY}
