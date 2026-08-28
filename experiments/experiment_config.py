"""Validated experiment configuration and stable child seeds."""
from dataclasses import asdict, dataclass, field
import hashlib, json

VALID_METHODS=("static","score_adaptive","competence_adaptive","proposed")
VALID_PROFILES=("T1","T2","T3","T4","T5")

@dataclass(frozen=True)
class ExperimentConfig:
    methods:list[str]=field(default_factory=lambda:list(VALID_METHODS))
    trainee_profiles:list[str]=field(default_factory=lambda:list(VALID_PROFILES))
    episodes_per_run:int=30
    repetitions:int=30
    random_seed:int=42
    target_mastery:float=.8
    learning_rate:float=.2
    repetition_weight:float=.5
    maximum_difficulty:int=3
    minimum_difficulty:int=1
    competence_threshold:float=.75
    critical_risk_threshold:float=.75
    save_episode_logs:bool=True
    save_decision_traces:bool=True
    def __post_init__(self):
        if not self.methods or not set(self.methods)<=set(VALID_METHODS): raise ValueError("invalid methods")
        if not self.trainee_profiles or not set(self.trainee_profiles)<=set(VALID_PROFILES): raise ValueError("invalid trainee_profiles")
        if self.episodes_per_run<1 or self.repetitions<1: raise ValueError("episodes and repetitions must be >= 1")
        if isinstance(self.random_seed,bool) or not isinstance(self.random_seed,int): raise ValueError("random_seed must be an integer")
        if not 0<=self.target_mastery<=1: raise ValueError("target_mastery must be between 0 and 1")
        if not 0<self.learning_rate<=1: raise ValueError("learning_rate must be > 0 and <= 1")
        if self.repetition_weight<0: raise ValueError("repetition_weight must be non-negative")
        if not 1<=self.minimum_difficulty<=self.maximum_difficulty<=3: raise ValueError("difficulty bounds must satisfy 1 <= min <= max <= 3")
    def to_dict(self): return asdict(self)
    def child_seed(self,method,profile,repetition):
        payload=f"{self.random_seed}|{method}|{profile}|{repetition}".encode()
        return int.from_bytes(hashlib.sha256(payload).digest()[:8],"big")%(2**32)
    def paired_seed(self,profile,repetition):
        payload=f"{self.random_seed}|paired|{profile}|{repetition}".encode()
        return int.from_bytes(hashlib.sha256(payload).digest()[:8],"big")%(2**32)
    def config_hash(self): return hashlib.sha256(json.dumps(self.to_dict(),sort_keys=True).encode()).hexdigest()[:10]
