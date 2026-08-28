# Canonical V15 Manuscript–Source Consistency Audit

## Audit basis

Executable source and `canonical_parameter_manifest.json` from smoke run
`20260821T120917852312Z-v15` were treated as implementation evidence. No
algorithm, parameter, completed result, ablation, sensitivity analysis, or
900-run experiment was changed or executed.

| Item | Manuscript value/formula | Source value/formula | Status | Required manuscript correction | Source evidence |
|---|---|---|---|---|---|
| Target mastery | 0.80 | 0.80 | MATCH | None | `experiments/canonical_config.py:15` |
| Learner rate | eta=0.20 | 0.20 | MATCH | None | `canonical_config.py:15` |
| Observation weights | 0.60/0.20/0.20 | 0.60/0.20/0.20; validated to sum to 1 | MATCH | None | `canonical_config.py:15,24` |
| Response parameters | rho=0.18, kappa=0.12 | 0.18, 0.12 | MATCH | None | `canonical_config.py:16` |
| Latent parameters | rp=0.12, sigma=0.35, decay=0.002 | same | MATCH | None | `canonical_config.py:16` |
| Difficulty encoding | 0/0.5/1 | `{1:0,2:0.5,3:1}` | MATCH | None | `canonical_latent.py:8` |
| Assistance encoding | 0/0.25/0.5/1 | same | MATCH | None | `canonical_latent.py:7` |
| Assistance lambda | manuscript 0.30 | corrected full-channel derivation and source execute 0.44 | MANUSCRIPT_UPDATE_REQUIRED | Use 0.44 and include the response-quality assistance term in the derivation. | `canonical_latent.py:29-33`; `canonical_assistance_neutrality_derivation.md` |
| R1 | risk>=0.75, mastery<0.60, possibly unsafe | risk>=0.75 and mastery<0.60; no unsafe-decision condition | MANUSCRIPT_UPDATE_REQUIRED | Remove unsafe-decision condition if present. | `core/adaptation_engine.py:95,101-104` |
| R2 | risk>=0.50 and errors>=2 | exact | MATCH | None | `adaptation_engine.py:96,104` |
| R3 | mastery>=0.80, risk>=0.50, correct | exact | MATCH | None | `adaptation_engine.py:97-98,105` |
| R4 | mastery>=0.65 and correct | exact | MATCH | None | `adaptation_engine.py:99,106` |
| R5 | otherwise | unconditional default appended last | MATCH | None | `adaptation_engine.py:100-107` |
| Observation score | weighted A/r/h | clipped weighted sum | MATCH | State clipping explicitly. | `canonical_latent.py:39-41` |
| Learner update | `(1-eta)l+eta*z` | same, clipped to [0,1] | MATCH | State clipping explicitly. | `canonical_latent.py:43` |
| Response model | `clip(theta-rho*d+kappa*a)` | exact | MATCH | None | `canonical_latent.py:16-24` |
| Eq. 15 unpracticed | appears `lambda*theta` | `(1-0.002)*theta` | MANUSCRIPT_UPDATE_REQUIRED | Write `(1-lambda)theta` when lambda denotes decay rate. | `canonical_latent.py:45-57` |
| Eq. 16 growth | denominator sigma²; global rp | denominator `0.35²`; global `practice_rate=0.12` | MATCH | Explicitly exclude factor 2 and profile learning rates. | `canonical_latent.py:48-55` |
| Proposed gap | `max(0,T-l)` | exact | MATCH | None | `priority_engine.py:21-24` |
| Proposed error factor | `1+w_F*min(1,e/3)` | exact, with `w_F=0.50` and cap 1.5 | MATCH | None | `priority_engine.py`; `canonical_engine.py` |
| Proposed priority urgency | `R_hat*G*phi*U` | exact; canonical priority receives raw `R_hat`, urgency applied once | MATCH | None | `experiment_metrics.py`; `canonical_engine.py`; `priority_engine.py` |
| Oracle priority | risk*latent gap*U | exact after corrective patch; U once | MATCH | None | `canonical_methods.py:23-26`; `canonical_engine.py:58-59` |
| Oracle privilege | Oracle only | only `OracleContext` holds theta; deployables reject it | MATCH | None | `canonical_methods.py:10-21,32-41` |
| Oracle difficulty | challenge-aware | nearest of 0/0.5/1 to selected theta | MATCH | State deterministic lower-level tie break. | `canonical_methods.py:28-30,38` |
| CCG* | critical latent competence gain | mean gain over 7 `high_risk_related` competencies | MATCH | State the seven-competence scope. | `canonical_metrics.py:9-14`; `data/competencies.json` |
| RWCS* | urgency-only weighted latent score | weights are max mapped contextual risk × urgency | MANUSCRIPT_UPDATE_REQUIRED | **MANUSCRIPT EQUATION MUST BE REVISED** to use source weight W. | `canonical_metrics.py:12`; `experiment_metrics.py:4-19` |
| TAR | target attainment | all 10 latent competencies at >=0.80 | MATCH | State denominator 10. | `canonical_metrics.py:13` |
| target_reached | potentially all scoped competencies | only 7 high-risk-related competencies | MANUSCRIPT_UPDATE_REQUIRED | Distinguish critical-target attainment from TAR. | `canonical_engine.py:17,61-62` |
| episodes-to-target | first attainment/censoring | first critical-subset attainment; episode limit when censored | MATCH | Name scope and censoring explicitly. | `canonical_engine.py:75-77` |
| CER | critical-item error rate | incorrect / critical post-test items, risk>=0.75 | MATCH | State that only manufacturing S5 qualifies. | `canonical_metrics.py:16-25`; `canonical_engine.py:33` |
| CMR | missing rate | missing required PPE / all required-PPE opportunities | MATCH | State denominator is PPE opportunities, not items. | `canonical_metrics.py:24-25` |
| Figure 1 | deployable architecture | required mapping | MATCH | Use canonical caption map. | `canonical_figure_reference_map.md` |
| Figure 2 | simulation-engine separation | required mapping | MATCH | Never call this Figure 3. | `canonical_figure_reference_map.md` |
| Figure 3 | paired differences | required mapping | MATCH | Do not use separation caption. | `canonical_figure_reference_map.md` |
| Figure 4 | decision trace | required mapping | MATCH | Do not caption as paired differences. | `canonical_figure_reference_map.md` |
| Malformed cross-references | specified malformed forms | no editable manuscript and no matches in scoped repository text | AMBIGUOUS | Audit the actual manuscript source when supplied. | Repository file/search audit |

## Manuscript-ready Table 3

Rules are evaluated R1 through R5; all difficulty changes are clamped to 1–3.

| Rule | Exact activation | Difficulty | Assistance | Feedback | Scenario behavior |
|---|---|---:|---|---|---|
| R1 | `risk >= 0.75 AND mastery < 0.60` | -1 | full visual guidance | immediate corrective | request repeat; bounded rotation prevents a third consecutive presentation by choosing a different priority-valid scenario |
| R2 | `risk >= 0.50 AND repeated_errors >= 2` | -1 | limited visual guidance | immediate explanation | request repeat; same bounded rotation applies |
| R3 | `mastery >= 0.80 AND risk >= 0.50 AND recent_correct` | +1 | none | delayed reflective | least-used scenario practicing highest-priority competence |
| R4 | `mastery >= 0.65 AND recent_correct` | +1 | minimal | summary | least-used scenario practicing highest-priority competence |
| R5 | otherwise | 0 | limited visual guidance | direct explanation | least-used scenario practicing highest-priority competence |

R1 does not require an unsafe/incorrect current decision. Multiple eligible rules
are recorded, but the first eligible rule in precedence order is selected.

## UI and simulation assistance consistency

The UI and deployable adaptation layer exchange the same string labels. The UI
formats them for display (`Guided`, `Intensive`) but performs no numeric
conversion. Numeric conversion occurs only in `canonical_latent.py` for synthetic
evaluation. Therefore label identity is consistent; the numeric simulation model
has no UI equivalent.

## Required manuscript actions before canonical ablation/sensitivity

1. Update assistance neutrality to the complete executed derivation, lambda=0.44,
   including response-quality `+0.08a`.
2. Correct Eq. (15) to use `(1-lambda)theta_star` for unpracticed competence.
3. Replace urgency-only RWCS* with the risk×urgency weighted source equation.
4. State R1 without an unsafe-decision predicate.
5. Distinguish all-ten TAR from seven-critical-competence `target_reached`.
6. State clipping in observation and learner updates.
7. Use the canonical Figure 1–4 map and audit the actual editable manuscript once
   it is supplied.

## Source-defect disposition

No known **SOURCE_DEFECT** remains from this consistency correction. This statement
does not constitute performance validation and does not authorize ablation or
sensitivity execution.
