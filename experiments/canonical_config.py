"""Configuration and registry for the canonical V15 simulation protocol."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
import hashlib

CANONICAL_METHODS=("static","random","score_adaptive","competence_adaptive","proposed","oracle")
DEPLOYABLE_METHODS=CANONICAL_METHODS[:-1]
PROFILES=("T1","T2","T3","T4","T5")

@dataclass(frozen=True)
class CanonicalConfig:
    methods:list[str]=field(default_factory=lambda:list(CANONICAL_METHODS))
    profiles:list[str]=field(default_factory=lambda:list(PROFILES))
    episodes:int=30; repetitions:int=30; base_seed:int=42
    target_mastery:float=.8; eta:float=.2; w_action:float=.6; w_response:float=.2; w_independence:float=.2
    rho:float=.18; kappa:float=.12; practice_rate:float=.12; sigma_g:float=.35; latent_decay:float=.002
    response_assistance_coefficient:float=.08
    repetition_weight:float=.5; critical_risk_threshold:float=.75
    minimum_difficulty:int=1; maximum_difficulty:int=3
    posttest_repetitions:int=3
    def __post_init__(self):
        if not self.methods or not set(self.methods)<=set(CANONICAL_METHODS): raise ValueError("invalid canonical methods")
        if not self.profiles or not set(self.profiles)<=set(PROFILES): raise ValueError("invalid profiles")
        if self.episodes<1 or self.repetitions<1 or self.posttest_repetitions<1: raise ValueError("counts must be positive")
        if abs(self.w_action+self.w_response+self.w_independence-1)>1e-9: raise ValueError("observation weights must sum to one")
        if not 0<self.eta<=1 or self.sigma_g<=0 or self.practice_rate<0 or self.latent_decay<0: raise ValueError("invalid dynamics")
    def to_dict(self): return asdict(self)
    @property
    def assistance_independence_coefficient(self):
        """Neutralize first-order A and r assistance contributions in z."""
        return round((self.w_action*self.kappa+self.w_response*self.response_assistance_coefficient)/self.w_independence,12)
    def repetition_seed(self,profile,repetition):
        raw=f"v15|{self.base_seed}|{profile}|{repetition}".encode()
        return int.from_bytes(hashlib.sha256(raw).digest()[:8],"big")%(2**32)
    def event_seed(self,profile,repetition,episode,stream):
        raw=f"v15|{self.repetition_seed(profile,repetition)}|{episode}|{stream}".encode()
        return int.from_bytes(hashlib.sha256(raw).digest()[:8],"big")%(2**32)

METHOD_REGISTRY={
 "static":{"label":"Static","simulation_only":False,"theta_star_access":False},
 "random":{"label":"Random","simulation_only":False,"theta_star_access":False},
 "score_adaptive":{"label":"Score-Adaptive","simulation_only":False,"theta_star_access":False},
 "competence_adaptive":{"label":"Competence-Adaptive","simulation_only":False,"theta_star_access":False},
 "proposed":{"label":"Proposed Framework","simulation_only":False,"theta_star_access":False},
 "oracle":{"label":"Oracle (privileged reference)","simulation_only":True,"theta_star_access":True},
}

CANONICAL_RULE_DEFINITIONS={
 "R1":{"risk_gte":.75,"mastery_lt":.60,"adaptation":"priority_remediation"},
 "R2":{"risk_gte":.50,"repeated_errors_gte":2,"adaptation":"targeted_remediation"},
 "R3":{"mastery_gte":.80,"risk_gte":.50,"recent_correct":True,"adaptation":"challenge_adaptation"},
 "R4":{"mastery_gte":.65,"recent_correct":True,"adaptation":"progressive_adaptation"},
 "R5":{"adaptation":"reinforcement_adaptation"},
}
