# Canonical Assistance-Neutrality Derivation

For an unclipped interior observation, the canonical response model contributes
`kappa*a` to expected action accuracy and the retained response-quality model
contributes `beta_r*a`, where `kappa=0.12` and `beta_r=0.08`.

With

\[
z=w_AA+w_Rr+w_Hh,
\qquad h(a)=1-\lambda_a a,
\]

the first-order assistance contribution is

\[
\Delta z(a)=a(w_A\kappa+w_R\beta_r-w_H\lambda_a).
\]

Neutrality requires

\[
\lambda_a=\frac{w_A\kappa+w_R\beta_r}{w_H}
=\frac{0.60(0.12)+0.20(0.08)}{0.20}
=\frac{0.088}{0.20}=0.44.
\]

Therefore the corrected executed independence function is

\[
h(a)=\operatorname{clip}_{[0,1]}(1-0.44a).
\]

For `a={0,0.25,0.5,1}`, the linear assistance terms cancel exactly before
clipping. At probability or response-quality boundaries, clipping can break
first-order equality; that boundary effect is explicitly excluded from the
neutrality claim. The response-quality assistance term is retained because the
source explicitly treated it as part of the canonical assistance calibration.
