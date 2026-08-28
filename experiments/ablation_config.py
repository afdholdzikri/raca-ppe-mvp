"""Feature-flag definitions for the Version 4 ablation study."""
from dataclasses import dataclass,asdict

@dataclass(frozen=True)
class AblationConfig:
    id:str;risk_weighting:bool=True;dynamic_context:bool=True;error_history:bool=True
    adaptive_assistance:bool=True;decision_trace:bool=True
    def features(self):
        value=asdict(self);value.pop("id");return value

ABLATIONS={
 "FULL":AblationConfig("FULL"),
 "A1_NO_RISK_WEIGHTING":AblationConfig("A1_NO_RISK_WEIGHTING",risk_weighting=False),
 "A2_NO_DYNAMIC_CONTEXT":AblationConfig("A2_NO_DYNAMIC_CONTEXT",dynamic_context=False),
 "A3_NO_ERROR_HISTORY":AblationConfig("A3_NO_ERROR_HISTORY",error_history=False),
 "A4_NO_ADAPTIVE_ASSISTANCE":AblationConfig("A4_NO_ADAPTIVE_ASSISTANCE",adaptive_assistance=False),
 "A5_NO_DECISION_TRACE":AblationConfig("A5_NO_DECISION_TRACE",decision_trace=False),
}
