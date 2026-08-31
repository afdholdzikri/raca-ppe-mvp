# Canonical V15 Experiment Report

This is a matched synthetic Monte Carlo evaluation, not a human-subject study.

- Runs: 24
- Base seed: 42
- Episodes: 5
- Repetitions: 2
- Profiles: T1, T2
- Methods: static, random, score_adaptive, competence_adaptive, proposed, oracle

## State separation

The deployable learner estimate `l[j,t]` is updated only from observable score
`z=wA*A+wR*r+wH*h`. Simulation-owned `theta_star[j,t]` generates responses and
evolves using equations (15)-(16): challenge-based practice growth and decay for
unpracticed competencies. Correctness and assistance do not directly increase
latent competence. Only the simulation-only Oracle receives latent state.

## Fixed post-test

Every matched run uses the same scenario/item seed design with no assistance,
adaptation, or state updates. CER is the error share on critical-risk post-test
items. CMR is missing required PPE selections divided by required PPE
opportunities.

## Paired reporting

Differences are oriented so positive means Proposed is better. Oracle rows are
marked as privileged references and are not deployable-comparator claims.
