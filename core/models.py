"""Validated dataclasses used by the Version 2 prototype."""
from dataclasses import dataclass, field
from typing import Any


def _id(value: str, name: str = "id") -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must not be empty")


def _unit(value: float, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        raise ValueError(f"{name} must be between 0 and 1")


@dataclass(frozen=True)
class PPEItem:
    id: str
    display_name: str
    description: str
    associated_competence_id: str
    def __post_init__(self):
        _id(self.id); _id(self.display_name, "display_name"); _id(self.associated_competence_id, "associated_competence_id")


@dataclass(frozen=True)
class Hazard:
    id: str
    display_name: str
    description: str
    probability: float
    severity: float
    base_exposure: float
    criticality: str
    associated_ppe: list[str]
    associated_competence_id: str
    def __post_init__(self):
        _id(self.id)
        for name in ("probability", "severity", "base_exposure"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 1 <= value <= 5:
                raise ValueError(f"{name} must be between 1 and 5")
        if self.criticality not in {"medium", "high", "critical"}:
            raise ValueError("criticality must be medium, high, or critical")


@dataclass(frozen=True)
class Competence:
    id: str
    display_name: str
    description: str
    target_mastery: float = .8
    urgency: float = .8
    high_risk_related: bool = False
    initial_mastery: float = .4
    def __post_init__(self):
        _id(self.id)
        _unit(self.target_mastery, "target_mastery"); _unit(self.urgency, "urgency")
        _unit(self.initial_mastery, "initial_mastery")


@dataclass(frozen=True)
class Scenario:
    id: str
    zone: str
    task: str
    narrative: str
    hazards: list[str]
    required_ppe: list[str]
    target_competencies: list[str]
    base_risk_category: str
    base_difficulty: int
    context_modifier: float
    time_limit_seconds: int
    distractor_pool: list[str]
    hint_text: str
    feedback_text: str
    def __post_init__(self):
        _id(self.id)
        if self.base_difficulty not in (1, 2, 3): raise ValueError("base_difficulty must be between 1 and 3")
        if self.context_modifier <= 0: raise ValueError("context_modifier must be greater than 0")
        if self.time_limit_seconds <= 0: raise ValueError("time_limit_seconds must be positive")


@dataclass
class LearnerState:
    competence_scores: dict[str, float]
    repeated_errors: dict[str, int]
    def __post_init__(self):
        for value in self.competence_scores.values(): _unit(value, "mastery")


@dataclass(frozen=True)
class AdaptationDecision:
    active_rules: list[str]
    selected_rule: str
    adaptation: str
    current_difficulty: int
    next_difficulty: int
    assistance: str
    distractor_level: str
    feedback: str
    repeat_required: bool


@dataclass
class DecisionTrace:
    values: dict[str, Any] = field(default_factory=dict)
