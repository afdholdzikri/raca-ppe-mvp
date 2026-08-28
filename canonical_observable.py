"""Deployable Canonical V15 observation and learner-estimate operations.

This module deliberately contains no simulation-only latent state.  Both the
experiment engine and the public reviewer adapter import these functions so
there is one authoritative implementation of equations z and l.
"""
from __future__ import annotations


def observation_score(
    action_accuracy: float,
    response_quality: float,
    independence: float,
    config: object,
) -> float:
    """Return the canonical observable score using configured V15 weights."""
    return max(
        0.0,
        min(
            1.0,
            config.w_action * action_accuracy
            + config.w_response * response_quality
            + config.w_independence * independence,
        ),
    )


def update_engine_estimate(estimate: float, observation: float, eta: float) -> float:
    """Update the deployable learner estimate from observable evidence only."""
    return max(0.0, min(1.0, (1 - eta) * estimate + eta * observation))
