"""Seeded synthetic-participant action generator."""
from dataclasses import dataclass,asdict
import json
from pathlib import Path
import numpy as np
import hashlib

@dataclass(frozen=True)
class SyntheticAction:
    selected_ppe:list[str]; response_time:float; hint_used:bool
    correct_probability:float; missing_probability:float; unnecessary_probability:float
    def to_dict(self): return asdict(self)

def load_profiles(path=None):
    path=Path(path) if path else Path(__file__).resolve().parent.parent/"data"/"trainee_profiles.json"
    values=json.loads(path.read_text(encoding="utf-8")); result={}
    for p in values:
        if not p["id"] or not 0<=p["hint_probability"]<=1: raise ValueError("invalid trainee profile")
        for key in ("unnecessary_ppe_probability","timeout_probability"):
            if not 0<=p[key]<=1: raise ValueError(f"{key} must be between 0 and 1")
        result[p["id"]]=p
    return result

def initial_scores(profile,competencies):
    values=profile["initial_competence_scores"]; default=values.get("default",.4)
    return {cid:float(values.get(cid,default)) for cid in competencies}

def episode_seed(run_seed,episode):
    """Derive a paired per-episode event stream, preventing cross-episode drift."""
    payload=f"{run_seed}|episode|{episode}".encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8],"big")%(2**32)

class SyntheticTrainee:
    def __init__(self,profile,seed): self.profile=profile; self.rng=np.random.default_rng(seed)
    def act(self,scenario,ppe,competence_scores,difficulty,assistance,scenario_risk,repeated_errors,time_limit):
        affected=[competence_scores[c] for c in scenario.target_competencies]
        mastery=sum(affected)/len(affected)
        bonus={"full_visual_guidance":.20,"limited_visual_guidance":.10,"minimal":.04,"none":0}[assistance]
        critical=self.profile["critical_error_bias"] if scenario_risk>=.75 else 0
        repeat=0
        rc=self.profile.get("repeated_error_competence")
        if rc in scenario.target_competencies:
            repeat=self.profile["repeated_error_bias"]*(1+min(2,repeated_errors.get(rc,0))*.25)
        probability=max(.05,min(.95,mastery-.08*(difficulty-1)+bonus+self.profile["base_accuracy_modifier"]-critical-repeat))
        selected=[]
        for pid in scenario.required_ppe:
            item=ppe[pid]; item_p=probability
            if item.associated_competence_id==rc: item_p=max(.05,item_p-self.profile["repeated_error_bias"])
            if self.rng.random()<item_p: selected.append(pid)
        unnecessary=[x for x in ppe if x not in scenario.required_ppe]
        if unnecessary and self.rng.random()<self.profile["unnecessary_ppe_probability"]:
            selected.append(unnecessary[int(self.rng.integers(len(unnecessary)))])
        hint_p=max(0,min(1,self.profile["hint_probability"]*(1-.4*mastery)))
        hint=bool(self.rng.random()<hint_p)
        base=(.9-.35*mastery+.12*(difficulty-1)-.12*bonus-self.profile["response_speed_modifier"])
        response=max(.1,float(time_limit*max(.2,base+self.rng.normal(0,.1))))
        if self.rng.random()<self.profile["timeout_probability"]: response=max(response,time_limit*(1.05+self.rng.random()*.3))
        return SyntheticAction(sorted(set(selected)),round(response,4),hint,round(probability,4),
            round(1-probability,4),self.profile["unnecessary_ppe_probability"])
