"""Capability-restricted V15 comparator decisions."""
from __future__ import annotations
import numpy as np
from core.priority_engine import calculate_global_priorities
from .baseline_methods import METHODS,MethodInput
from .canonical_latent import DIFFICULTY_ENCODING
from .canonical_deployable import DeployableContext,decide_proposed
from dataclasses import dataclass

@dataclass(frozen=True)
class OracleContext:
    deployable:DeployableContext
    theta_star:dict
    risk_hat:dict

def calculate_oracle_priorities(risk_hat,theta_star,definitions,target_mastery):
    """Canonical privileged Q: risk * latent gap * urgency, exactly once."""
    return {cid:risk_hat.get(cid,0)*max(0,target_mastery-theta_star[cid])*definitions[cid].urgency
            for cid in theta_star}

def choose_oracle_difficulty(theta_star):
    """Choose the level whose canonical challenge encoding is nearest latent mastery."""
    return min(DIFFICULTY_ENCODING,key=lambda level:(abs(DIFFICULTY_ENCODING[level]-theta_star),level))

def decide(method_id,context):
    if method_id=="oracle":
        if not isinstance(context,OracleContext):raise PermissionError("Oracle requires privileged simulation context")
        c=context.deployable; theta=context.theta_star
        priority=calculate_oracle_priorities(context.risk_hat,theta,c.definitions,c.method_input.config.target_mastery)
        target=min(priority,key=lambda cid:(-priority[cid],cid)); candidates=[s.id for s in c.method_input.scenarios.values() if target in s.target_competencies]
        nxt=min(candidates or list(c.method_input.scenarios));difficulty=choose_oracle_difficulty(theta[target])
        result=_decision(nxt,difficulty,"none","oracle_latent_priority",target)
        return {**result,"oracle_priority":priority[target]}
    if isinstance(context,OracleContext):raise PermissionError("deployable comparator cannot receive theta_star context")
    c=context.method_input
    if method_id=="random":
        rng=np.random.default_rng(context.event_seed); nxt=sorted(c.scenarios)[int(rng.integers(len(c.scenarios)))]
        return _decision(nxt,c.scenarios[nxt].base_difficulty,"limited_visual_guidance","uniform_valid_scenario","none")
    if method_id=="proposed":return decide_proposed(context)
    return METHODS[method_id].decide(c)

def _decision(nxt,difficulty,assistance,rule,target):
    return {"next_scenario":nxt,"next_difficulty":difficulty,"assistance":assistance,"distractor_level":"low",
      "feedback":"direct_explanation","repeat_required":False,"active_rules":[rule],"selected_rule":rule,
      "adaptation":rule,"highest_priority_competence":target}
