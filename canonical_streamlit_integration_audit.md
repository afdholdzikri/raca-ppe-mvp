# Canonical V15–Streamlit Integration Audit

## Scope and boundary

This audit covers the public dynamic Streamlit reviewer path only. It does not
regenerate or modify the frozen main experiment, ablation, sensitivity,
cross-domain replication, manuscript tables, figures, or exported results.

```text
CANONICAL_BACKEND_REUSED = YES
DUPLICATE_SCIENTIFIC_IMPLEMENTATION = NO
THETA_STAR_VISIBLE_TO_UI = NO
DOMAIN_KB_REUSED = YES
RULESET_REUSED = YES
TRACE_REUSED = YES
```

`TRACE_REUSED = YES` means the UI performs a lossless serialization of values
returned by the canonical deployable path and persists that object through the
existing resilient JSON Lines writer. It does not recreate a scientific result
from display values.

## Authoritative source map

| Concern | Authoritative implementation used by the UI |
|---|---|
| Canonical parameters | `experiments.canonical_config.CanonicalConfig` |
| Domain loading and reference validation | `experiments.domain_adapter.load_domain` |
| Normalized contextual risk | `core.risk_engine.calculate_contextual_risk` and `calculate_scenario_risk` (called by the domain adapter) |
| Observable score | `experiments.canonical_observable.observation_score` |
| Engine learner estimate | `experiments.canonical_observable.update_engine_estimate` |
| Mapped competence risk R̂ | `experiments.experiment_metrics.competence_contextual_risks` |
| G, φ, U, Q and ranking | `core.priority_engine.calculate_global_priorities` |
| Deployable capability boundary | `experiments.canonical_deployable.DeployableContext` |
| Proposed policy | `experiments.canonical_deployable.decide_proposed` → `experiments.proposed_method.ProposedMethod` |
| R1–R5 precedence | `core.adaptation_engine.choose_adaptation_v2` |
| Scenario selection | `core.scenario_manager.select_next_scenario` |
| Bounded remediation rotation | `experiments.proposed_method.ProposedMethod.decide` and `core.scenario_manager.select_priority_alternative` |
| Scenario/data validity | `experiments.domain_adapter.load_domain` plus adapter result validation |
| Trace persistence | `core.trace_manager.append_trace_jsonl` |

`experiments.canonical_observable` was extracted from the simulation module so
the experiment engine and public adapter import one observable equation source,
while the public import graph contains no simulation-only latent module.

## State and UI separation

- Play Mode and Reviewer/Audit Mode submit the same observable inputs.
- PPE animation state is explicitly discarded before canonical evaluation.
- Domain, scenario, episode, and PPE widget keys are isolated. Domain changes
  use a pending callback value applied before the next widget instantiation.
- A submission guard prevents a Streamlit rerun from storing the same decision
  twice.
- The reviewer trace stores `simulation_only_state_exposed = false` and never
  serializes latent simulation state.
- Continue applies the canonical returned scenario, bounded difficulty,
  assistance, and distractor level automatically.

## Deterministic consistency smoke

Input: manufacturing `S5`, PPE `goggles` + `gloves` (missing `respirator`),
difficulty 3, two preceding `S5` entries, response time 10 seconds, no hint.

| Value | Result |
|---|---:|
| Selected competence | `chemical_ppe_selection` |
| R̂ | 0.8 |
| G | 0.4 |
| φ | 1.1666666666666667 |
| U | 1.0 |
| Q | 0.3733 |
| Selected rule | `critical_risk_low_mastery` |
| Requested next scenario | `S5` |
| Applied bounded scenario | `S4` |
| Next difficulty | 2 |
| Next assistance | `full_visual_guidance` |
| Bounded rotation | true |

The adapter result matched a direct `decide_proposed(DeployableContext(...))`
call for selected rule, difficulty, assistance, feedback, repeat request, next
scenario, and bounded-rotation status.

## Domain and trace checks

- Manufacturing: 6 valid scenarios.
- Chemical laboratory: 5 valid scenarios.
- Construction: 6 valid scenarios.
- The canonical UI trace contract contains every requested audit field plus
  backward-compatible display aliases; the smoke trace contained 69 fields.
- Each returned next-scenario identifier was checked against its active
  canonical domain.

## Scientific result protection

No risk equation, learner equation, parameter, threshold, latent dynamic,
priority equation, method behavior, or experiment output schema was changed.
The extraction of observable functions and deployable context is structural:
the canonical engine imports the same function bodies and existing regression
tests verify unchanged behavior.

## Status

The reviewer frontend is ready for local or Streamlit Community Cloud launch
from `app.py`. No source discrepancy was found between the values exposed by
the integrated UI path and the frozen deployable Canonical V15 policy.

`SOURCE_DEFECT = NONE IDENTIFIED IN THE DEPLOYABLE INTEGRATION PATH`
