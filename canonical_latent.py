"""Simulation-only latent competence and canonical synthetic responses."""
from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
from .canonical_observable import observation_score, update_engine_estimate

ASSISTANCE_ENCODING={"none":0.0,"minimal":.25,"limited_visual_guidance":.5,"full_visual_guidance":1.0}
DIFFICULTY_ENCODING={1:0.0,2:.5,3:1.0}

@dataclass
class LatentState:
    """Environment-owned theta_star; never pass this object to deployable methods."""
    theta_star:dict[str,float]
    def snapshot(self): return dict(self.theta_star)

def response_probability(theta_star,difficulty,assistance,rho,kappa):
    return max(0.0,min(1.0,float(theta_star)-rho*DIFFICULTY_ENCODING[difficulty]+kappa*ASSISTANCE_ENCODING[assistance]))

def generate_observations(state,scenario,ppe,difficulty,assistance,config,seed,time_limit):
    """Generate observable A, r, h and events exclusively from theta_star."""
    rng=np.random.default_rng(seed); accuracy={}; selected=[]
    for cid in scenario.target_competencies:
        probability=response_probability(state.theta_star[cid],difficulty,assistance,config.rho,config.kappa)
        accuracy[cid]=1.0 if rng.random()<probability else 0.0
    for pid in scenario.required_ppe:
        cid=ppe[pid].associated_competence_id
        practiced=accuracy.get(cid,sum(accuracy.values())/len(accuracy))
        if practiced>=.5:selected.append(pid)
    # Assistance makes observable action easier but reduces independence; this
    # is the canonical assistance-neutrality calibration in z.
    a=ASSISTANCE_ENCODING[assistance]
    response_quality=max(0.0,min(1.0,float(np.mean(list(state.theta_star[c] for c in scenario.target_competencies))-.12*DIFFICULTY_ENCODING[difficulty]+config.response_assistance_coefficient*a+rng.normal(0,.06))))
    independence=max(0.0,min(1.0,1.0-config.assistance_independence_coefficient*a))
    response_time=round(time_limit*(1.15-.65*response_quality),4)
    return {"action_accuracy":accuracy,"selected_ppe":sorted(selected),"response_quality":round(response_quality,6),
      "independence":round(independence,6),"response_time":response_time,
      "events":{"difficulty_encoding":DIFFICULTY_ENCODING[difficulty],"assistance_encoding":a}}

def evolve_latent(state,practiced,difficulty,config):
    """Equations (15)-(16): challenge growth for practice, canonical decay otherwise.

    g=theta+rp(1-theta)exp(-(d-theta)^2/sigma_g^2). Correctness and
    assistance are not inputs. Practiced competencies take g; all others decay.
    """
    d=DIFFICULTY_ENCODING[difficulty]; updated={}
    for cid,theta in state.theta_star.items():
        if cid in practiced:
            value=theta+config.practice_rate*(1-theta)*math.exp(-((d-theta)**2)/(config.sigma_g**2))
        else:value=theta*(1-config.latent_decay)
        updated[cid]=max(0.0,min(1.0,value))
    state.theta_star=updated
