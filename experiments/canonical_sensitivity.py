"""Predeclared canonical V15 sensitivity and robustness conditions."""
from __future__ import annotations
from dataclasses import asdict,dataclass,field,replace
import hashlib
from .canonical_config import CanonicalConfig

@dataclass(frozen=True)
class SensitivityCondition:
    id:str;study_type:str;parameter_name:str;parameter_value:str;regime_name:str
    overrides:dict=field(default_factory=dict);urgency_regime:str="nominal"
    r1_risk:float=.75;r2_risk:float=.50;r3_mastery:float=.80
    methods:tuple=tuple(("static","random","score_adaptive","competence_adaptive","proposed"))
    def config(self,base):return replace(base,**self.overrides)

OFAT_GRIDS={"eta":[.10,.20,.30],"r1_risk":[.65,.75,.85],"r2_risk":[.40,.50,.60],"r3_mastery":[.70,.80,.90],
 "repetition_weight":[.25,.50,.75],"rho":[.12,.18,.24],"kappa":[.08,.12,.16],"sigma_g":[.25,.35,.45]}
WEIGHT_REGIMES={"canonical":(.60,.20,.20),"accuracy_heavy":(.70,.15,.15),"balanced":(.50,.25,.25)}
LATENT_REGIMES={"canonical":(.12,.35,.002),"slower_narrower":(.09,.28,.003),"faster_broader":(.15,.42,.001)}
URGENCY_REGIMES=("nominal","uniform","perturbed")

def deterministic_urgency(nominal,competence_id,base_seed):
    raw=hashlib.sha256(f"urgency|{base_seed}|{competence_id}".encode()).digest();unit=int.from_bytes(raw[:8],"big")/(2**64-1)
    delta=-.15+.30*unit;return round(delta,12),max(.5,min(1.5,nominal*(1+delta)))

def effective_urgencies(definitions,regime,base_seed):
    if regime=="nominal":return {cid:d.urgency for cid,d in definitions.items()},{cid:0.0 for cid in definitions}
    if regime=="uniform":return {cid:1.0 for cid in definitions},{cid:None for cid in definitions}
    if regime!="perturbed":raise ValueError("invalid urgency regime")
    values={};deltas={}
    for cid,d in definitions.items():deltas[cid],values[cid]=deterministic_urgency(d.urgency,cid,base_seed)
    return values,deltas

def _condition(name,value):
    cid=f"{name}_{str(value).replace('.','p')}";overrides={};kwargs={}
    if name in ("r1_risk","r2_risk","r3_mastery"):kwargs[name]=value
    else:overrides[name]=value
    return SensitivityCondition(cid,"policy_sensitivity",name,str(value),cid,overrides=overrides,**kwargs)

def final_conditions():
    out=[]
    for name,values in OFAT_GRIDS.items():out.extend(_condition(name,v) for v in values)
    for name,(wa,wr,wh) in WEIGHT_REGIMES.items():out.append(SensitivityCondition(f"weights_{name}","policy_sensitivity","observation_weights",name,name,{"w_action":wa,"w_response":wr,"w_independence":wh}))
    for name in URGENCY_REGIMES:out.append(SensitivityCondition(f"urgency_{name}","urgency_robustness","urgency",name,name,urgency_regime=name))
    for name,(rp,sg,decay) in LATENT_REGIMES.items():out.append(SensitivityCondition(f"latent_{name}","latent_robustness","latent_dynamics",name,name,{"practice_rate":rp,"sigma_g":sg,"latent_decay":decay},methods=("static","random","score_adaptive","competence_adaptive","proposed","oracle")))
    return out

def smoke_conditions():
    names=("eta","rho","kappa");out=[]
    for name in names:out.extend(_condition(name,v) for v in OFAT_GRIDS[name])
    for name in ("canonical","balanced"):
      wa,wr,wh=WEIGHT_REGIMES[name];out.append(SensitivityCondition(f"weights_{name}","policy_sensitivity","observation_weights",name,name,{"w_action":wa,"w_response":wr,"w_independence":wh}))
    for name in ("nominal","uniform"):out.append(SensitivityCondition(f"urgency_{name}","urgency_robustness","urgency",name,name,urgency_regime=name))
    for name,(rp,sg,decay) in LATENT_REGIMES.items():out.append(SensitivityCondition(f"latent_{name}","latent_robustness","latent_dynamics",name,name,{"practice_rate":rp,"sigma_g":sg,"latent_decay":decay},methods=("static","random","score_adaptive","competence_adaptive","proposed","oracle")))
    return out

def condition_manifest(conditions,base_config,definitions):
    rows=[]
    for c in conditions:
      cfg=c.config(base_config);urgency,deltas=effective_urgencies(definitions,c.urgency_regime,base_config.base_seed)
      rows.append({**asdict(c),"resolved_config":cfg.to_dict(),"resolved_lambda_a":cfg.assistance_independence_coefficient,
        "nominal_urgency":{cid:d.urgency for cid,d in definitions.items()},"effective_urgency":urgency,"urgency_delta":deltas})
    return rows
