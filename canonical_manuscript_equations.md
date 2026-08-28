# Canonical V15 Manuscript Equations from Executable Source

Let `d(1)=0`, `d(2)=0.5`, `d(3)=1`, and let assistance be encoded as
`a(none)=0`, `a(minimal)=0.25`, `a(limited)=0.5`, `a(full)=1`.

## Observable response and learner estimate

\[
P(A_{j,t}=1)=\operatorname{clip}_{[0,1]}(\theta^*_{j,t}-0.18d_t+0.12a_t).
\]

The simulation uses NumPy `default_rng(event_seed)` and draws
`A=1[rng.random() < P]`. The matched event seed is SHA-256-derived from base
seed, profile, repetition, episode/item, and stream name.

\[
z_{j,t}=0.60A_{j,t}+0.20r_t+0.20h_t,
\qquad
l_{j,t+1}=\operatorname{clip}_{[0,1]}(0.80l_{j,t}+0.20z_{j,t}).
\]

Both functions clip to `[0,1]`. `theta_star` is absent from their signatures.
Only the simulation first generates observable `A`, `r`, and `h` from latent
state.

The executed independence function is

\[
h(a)=\operatorname{clip}_{[0,1]}(1-0.50a).
\]

Because response quality also contains `+0.08a`, neutrality across all executed
observable channels gives `lambda_a=(0.60*0.12+0.20*0.08)/0.20=0.44`. The
corrected source executes `h(a)=clip(1-0.44a)`.

## Latent dynamics: exact Equations (15) and (16)

For practiced competence (`I_{j,t}=1`):

\[
g_{j,t}=\theta^*_{j,t}+0.12(1-\theta^*_{j,t})
\exp\left(-\frac{(d_t-\theta^*_{j,t})^2}{0.35^2}\right).
\]

The denominator is `sigma_g^2`, not `2 sigma_g^2`; `r_p=0.12` is global and
not profile-specific.

The exact combined update is

\[
\theta^*_{j,t+1}=\operatorname{clip}_{[0,1]}\left[
I_{j,t}g_{j,t}+(1-I_{j,t})(1-0.002)\theta^*_{j,t}
\right].
\]

Thus the manuscript must use `(1-lambda)theta_star` if `lambda=0.002` denotes
the decay rate. Writing `lambda theta_star` would describe different behavior.

## Proposed and Oracle priorities

The executed deployable priority is

\[
Q_{j,t}=\hat R_j\max(0,0.8-l_{j,t})
\left(1+0.50\min(1,e_{j,t}/3)\right)U_j,
\]

where `R_hat` excludes urgency. The error factor is bounded at 1.5 and urgency
is applied exactly once.

After the corrective Oracle patch, its source equation is exactly

\[
Q^{oracle}_{j,t}=\hat R_j\max(0,0.8-\theta^*_{j,t})U_j,
\]

with urgency applied once. Only `OracleContext` contains `theta_star`.

## Outcomes

\[
CCG^*=\frac{1}{7}\sum_{j\in C_{critical}}
(\theta^*_{j,T}-\theta^*_{j,0}).
\]

\[
RWCS^*=\frac{\sum_{j=1}^{10}W_j\theta^*_{j,T}}{\sum_{j=1}^{10}W_j},
\quad W_j=\max(\text{mapped contextual risk}_j)U_j.
\]

The manuscript urgency-only RWCS* equation must be revised.

\[
TAR=\frac{1}{10}\sum_{j=1}^{10}\mathbf 1[\theta^*_{j,T}\ge0.8].
\]

`target_reached` is separate: all seven `high_risk_related` competencies must
reach 0.8. Unreached runs store the episode limit and `censored=true`.

CER is incorrect critical fixed-post-test items divided by all critical
fixed-post-test items (`risk>=0.75`; only manufacturing S5). CMR is total missing
required PPE divided by total required-PPE opportunities over all fixed-post-test
items.
