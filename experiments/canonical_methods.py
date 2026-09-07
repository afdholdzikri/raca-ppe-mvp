"""Capability-restricted Canonical V15 comparator decisions."""
from __future__ import annotations

from dataclasses import dataclass
from math import log, sqrt

import numpy as np

from core.scenario_manager import select_next_scenario
from .baseline_methods import METHODS, MethodInput
from .canonical_latent import DIFFICULTY_ENCODING
from .canonical_deployable import DeployableContext, decide_proposed


@dataclass(frozen=True)
class OracleContext:
    """Privileged simulation-only context for the Oracle comparator."""

    deployable: DeployableContext
    theta_star: dict
    risk_hat: dict


@dataclass(frozen=True)
class RWUCB1Context:
    """
    Observable state required by the canonical Risk-Weighted UCB1 policy.

    Parameters
    ----------
    deployable:
        Standard deployable policy context. It contains only observable
        engine-side information and domain definitions.

    practice_counts:
        Number of previous practice opportunities for each competence.

    reward_sums:
        Cumulative observable learning-progress rewards for each competence,
        using the canonical reward:
            max(0, l_{j,t+1} - l_{j,t})

    episode:
        Current 1-based training episode index.
    """

    deployable: DeployableContext
    practice_counts: dict
    reward_sums: dict
    episode: int


def calculate_oracle_priorities(
    risk_hat,
    theta_star,
    definitions,
    target_mastery,
):
    """
    Canonical privileged Oracle priority.

    Q_oracle[j,t] =
        risk_hat[j]
        * max(0, target_mastery - theta_star[j,t])
        * urgency[j]
    """
    return {
        cid: (
            risk_hat.get(cid, 0)
            * max(0, target_mastery - theta_star[cid])
            * definitions[cid].urgency
        )
        for cid in theta_star
    }


def choose_oracle_difficulty(theta_star):
    """
    Choose the available canonical difficulty whose encoded challenge level
    is nearest to the selected competence's latent mastery.

    Ties are resolved deterministically by the difficulty identifier.
    """
    return min(
        DIFFICULTY_ENCODING,
        key=lambda level: (
            abs(DIFFICULTY_ENCODING[level] - theta_star),
            level,
        ),
    )


def calculate_rw_ucb1_indices(
    risk_weights,
    practice_counts,
    reward_sums,
    episode,
    c=1.0,
):
    """
    Calculate the canonical Risk-Weighted UCB1 selection index.

    For each already-visited competence j:

        I_j,t =
            risk_weights[j]
            * (
                mean_reward[j]
                + c * sqrt(2 * ln(t) / N_j,t)
              )

    where:
        risk_weights[j] = R_hat_j * U_j
        mean_reward[j] = reward_sums[j] / practice_counts[j]
        c = 1 in the canonical configuration

    This function is intentionally called only after all competences have
    at least one previous practice opportunity. Unvisited competences are
    handled separately by deterministic identifier ordering.
    """
    t = max(1, int(episode))
    indices = {}

    for cid in sorted(practice_counts):
        n = practice_counts[cid]

        if n <= 0:
            raise ValueError(
                "RW-UCB1 index calculation requires all competences "
                "to have at least one practice opportunity."
            )

        mean_reward = reward_sums.get(cid, 0.0) / n
        exploration = c * sqrt(2.0 * log(t) / n)

        indices[cid] = (
            risk_weights.get(cid, 0.0)
            * (mean_reward + exploration)
        )

    return indices


def decide_rw_ucb1(context: RWUCB1Context):
    """
    Return one canonical deployable Risk-Weighted UCB1 decision.

    Canonical behavior:
    - unvisited competences are selected first;
    - unvisited ties use deterministic competence-identifier ordering;
    - after all competences are visited, selection uses the exact
      risk-weighted UCB1 index;
    - the selected competence is mapped to a valid linked scenario using
      the existing canonical scenario-selection mechanism;
    - instructional settings remain fixed at:
        * selected scenario base difficulty,
        * limited visual guidance,
        * low distractor level,
        * direct explanatory feedback;
    - no latent competence or future outcome information is used.
    """
    deploy = context.deployable
    method_input = deploy.method_input

    competence_ids = sorted(
        method_input.competence_scores
    )

    unvisited = [
        cid
        for cid in competence_ids
        if context.practice_counts.get(cid, 0) == 0
    ]

    if unvisited:
        target = unvisited[0]
        selected_rule = "rw_ucb1_unvisited"
        selected_index = None

        # select_next_scenario() expects a descending ranking.  A single
        # deterministic target is sufficient during forced initial visits.
        ranking = [(target, float("inf"))]

    else:
        indices = calculate_rw_ucb1_indices(
            risk_weights=deploy.risk_weights,
            practice_counts=context.practice_counts,
            reward_sums=context.reward_sums,
            episode=context.episode,
            c=1.0,
        )

        # Highest index first; equal values are resolved by identifier.
        target = min(
            indices,
            key=lambda cid: (
                -indices[cid],
                cid,
            ),
        )

        selected_index = indices[target]
        selected_rule = "rw_ucb1_index"
        ranking = [(target, selected_index)]

    next_scenario = select_next_scenario(
        method_input.scenario.id,
        method_input.scenarios,
        ranking,
        method_input.scenario_history,
        False,
    )

    result = _decision(
        next_scenario,
        method_input.scenarios[
            next_scenario
        ].base_difficulty,
        "limited_visual_guidance",
        selected_rule,
        target,
    )

    # Extra diagnostic fields are observable-only and do not alter
    # the canonical decision interface.
    result["rw_ucb1_index"] = selected_index
    result["rw_ucb1_practice_count"] = (
        context.practice_counts.get(
            target,
            0,
        )
    )

    return result


def decide(method_id, context):
    """
    Dispatch a canonical comparator decision while enforcing capability
    separation between deployable and privileged policies.
    """
    if method_id == "oracle":
        if not isinstance(
            context,
            OracleContext,
        ):
            raise PermissionError(
                "Oracle requires privileged simulation context."
            )

        deploy = context.deployable
        method_input = deploy.method_input

        priorities = calculate_oracle_priorities(
            context.risk_hat,
            context.theta_star,
            deploy.definitions,
            method_input.config.target_mastery,
        )

        target = min(
            priorities,
            key=lambda cid: (
                -priorities[cid],
                cid,
            ),
        )

        candidates = [
            scenario.id
            for scenario
            in method_input.scenarios.values()
            if target
            in scenario.target_competencies
        ]

        next_scenario = min(
            candidates
            or list(
                method_input.scenarios
            )
        )

        difficulty = choose_oracle_difficulty(
            context.theta_star[target]
        )

        result = _decision(
            next_scenario,
            difficulty,
            "none",
            "oracle_latent_priority",
            target,
        )

        result["oracle_priority"] = (
            priorities[target]
        )

        return result

    if method_id == "rw_ucb1":
        if not isinstance(
            context,
            RWUCB1Context,
        ):
            raise PermissionError(
                "RW-UCB1 requires observable RW-UCB1 state."
            )

        return decide_rw_ucb1(
            context
        )

    # Prevent privileged state from leaking into a deployable comparator.
    if isinstance(
        context,
        OracleContext,
    ):
        raise PermissionError(
            "Deployable comparator cannot receive theta_star context."
        )

    # Prevent RW-UCB1 policy state from being silently reused by another
    # comparator.
    if isinstance(
        context,
        RWUCB1Context,
    ):
        raise PermissionError(
            "Non-RW-UCB1 comparator cannot receive RW-UCB1 context."
        )

    method_input = context.method_input

    if method_id == "random":
        rng = np.random.default_rng(
            context.event_seed
        )

        scenario_ids = sorted(
            method_input.scenarios
        )

        next_scenario = scenario_ids[
            int(
                rng.integers(
                    len(
                        scenario_ids
                    )
                )
            )
        ]

        return _decision(
            next_scenario,
            method_input.scenarios[
                next_scenario
            ].base_difficulty,
            "limited_visual_guidance",
            "uniform_valid_scenario",
            "none",
        )

    if method_id == "proposed":
        return decide_proposed(
            context
        )

    if method_id not in METHODS:
        raise KeyError(
            f"Unknown canonical method: {method_id}"
        )

    return METHODS[
        method_id
    ].decide(
        method_input
    )


def _decision(
    next_scenario,
    difficulty,
    assistance,
    rule,
    target,
):
    """
    Build the standard canonical comparator decision payload.
    """
    return {
        "next_scenario": next_scenario,
        "next_difficulty": difficulty,
        "assistance": assistance,
        "distractor_level": "low",
        "feedback": "direct_explanation",
        "repeat_required": False,
        "active_rules": [rule],
        "selected_rule": rule,
        "adaptation": rule,
        "highest_priority_competence": target,
    }
