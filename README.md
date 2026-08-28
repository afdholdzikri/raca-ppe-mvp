# RACA-PPE: Risk-Aware Context-Adaptive PPE Safety Training

Public research artifact and reviewer-facing prototype accompanying the manuscript:

**A Risk-Aware Context-Adaptive Framework for PPE Safety Training: Design and Simulation Evaluation**

## Overview

RACA-PPE is a risk-aware context-adaptive serious-game framework for personal protective equipment (PPE) safety training.

The framework combines:

- contextual risk assessment;
- an engine-side learner estimate;
- competence gaps;
- bounded repeated-error history;
- domain urgency;
- deterministic R1–R5 adaptation rules;
- bounded scenario rotation;
- decision-level traceability.

The public Streamlit application uses the same deployable Canonical V15 backend used by the manuscript experiments.

## Scientific Boundary

The deployable application operates only on engine-visible information.

The simulation-only latent synthetic competence state `theta*` is intentionally excluded from the public decision path.

The public application is a software demonstrator and does not constitute evidence of human learning effectiveness, behavioral transfer, PPE compliance improvement, or accident reduction.

## Canonical Backend Reuse

The reviewer-facing Streamlit UI delegates scientific calculations to the canonical implementation.

The UI does not independently reimplement:

- normalized contextual risk;
- learner-estimate updating;
- competence-gap calculation;
- repeated-error factor;
- urgency weighting;
- global priority;
- R1–R5 decision logic;
- bounded scenario rotation.

The integration audit confirms:

```text
CANONICAL_BACKEND_REUSED = YES
DUPLICATE_SCIENTIFIC_IMPLEMENTATION = NO
THETA_STAR_VISIBLE_TO_UI = NO
DOMAIN_KB_REUSED = YES
RULESET_REUSED = YES
TRACE_REUSED = YES