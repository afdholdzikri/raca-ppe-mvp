"""Canonical V15 ablation specifications and priority calculation."""
from __future__ import annotations
from dataclasses import asdict,dataclass

@dataclass(frozen=True)
class CanonicalAblationSpec:
    id:str
    use_risk:bool=True
    use_gap:bool=True
    use_history:bool=True
    use_urgency:bool=True
    adaptive_assistance:bool=True
    decision_trace:bool=True
    rule_engine:bool=True

ABLATIONS={spec.id:spec for spec in (
 CanonicalAblationSpec("complete_framework"),
 CanonicalAblationSpec("risk_only",use_gap=False,use_history=False),
 CanonicalAblationSpec("without_risk",use_risk=False),
 CanonicalAblationSpec("without_history",use_history=False),
 CanonicalAblationSpec("without_urgency",use_urgency=False),
 CanonicalAblationSpec("without_assistance",adaptive_assistance=False),
 CanonicalAblationSpec("without_trace",decision_trace=False),
 CanonicalAblationSpec("without_rule_engine",rule_engine=False),
)}

def ablation_priorities(spec,risk_hat,scores,errors,definitions,target,repetition_weight):
    """Return Q and ranking without access to simulation-owned latent state."""
    values={}
    for cid,definition in definitions.items():
        r=risk_hat.get(cid,0.0) if spec.use_risk else 1.0
        gap=max(0,target-scores[cid]) if spec.use_gap else 1.0
        phi=1+repetition_weight*min(1,errors.get(cid,0)/3) if spec.use_history else 1.0
        urgency=definition.urgency if spec.use_urgency else 1.0
        values[cid]=round(r*gap*phi*urgency,4)
    return values,sorted(values.items(),key=lambda item:(-item[1],item[0]))

def manifest(): return {key:asdict(value) for key,value in ABLATIONS.items()}
