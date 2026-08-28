"""Capability-restricted deployable Canonical V15 Proposed-policy entrypoint."""
from __future__ import annotations

from dataclasses import dataclass

from .baseline_methods import MethodInput
from .proposed_method import ProposedMethod


@dataclass(frozen=True)
class DeployableContext:
    """Inputs observable by deployable canonical methods."""

    method_input: MethodInput
    risk_weights: dict
    definitions: dict
    event_seed: int


def decide_proposed(context: DeployableContext) -> dict:
    """Apply the canonical Proposed policy to a deployable-only context."""
    if not isinstance(context, DeployableContext):
        raise TypeError("Proposed policy requires a DeployableContext")
    return ProposedMethod().decide(context.method_input)
