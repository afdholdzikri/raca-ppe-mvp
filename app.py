"""Public reviewer landing page for the Canonical V15 RACA-PPE prototype."""
from __future__ import annotations

import streamlit as st

import ui_visuals
from canonical_streamlit_adapter import available_domains, load_canonical_domain


st.set_page_config(page_title="RACA-PPE Canonical V15", page_icon="🦺", layout="wide")
ui_visuals.inject_game_css()

ui_visuals.render_page_header(
    "🦺",
    "A Risk-Aware Context-Adaptive Framework for Serious Game-Based PPE Safety Training",
    "Canonical V15 reviewer demonstration — dynamic Streamlit V3 presentation",
)
st.write(
    "This public research prototype demonstrates transparent PPE decisions through the same "
    "deployable canonical backend used by the manuscript experiments. It does not claim "
    "human-subject learning or accident-reduction effectiveness."
)

domains = {domain: load_canonical_domain(domain) for domain in available_domains()}
columns = st.columns(len(domains))
for column, (domain, data) in zip(columns, domains.items()):
    with column:
        with st.container(border=True):
            theme = ui_visuals.domain_theme(domain)
            st.markdown(
                f'<div style="font-size:1.7rem;line-height:1">{theme["icon"]}</div>',
                unsafe_allow_html=True,
            )
            st.subheader(domain.replace("_", " ").title())
            st.metric("Canonical scenarios", len(data["scenarios"]))
            st.caption(f"{len(data['ppe'])} PPE items · {len(data['hazards'])} hazards")

st.subheader("Reviewer workflow")
st.write(
    "Choose a canonical domain → inspect the hazard context → attach PPE to the worker → "
    "submit observable evidence → inspect learner estimate, R̂, G, φ, U, Q, R1–R5, "
    "bounded action, and the returned next scenario."
)

st.subheader("Scientific boundary")
st.info(
    "The UI has no access to simulation-only latent competence. Risk, observable learner "
    "updating, global priority, rule selection, and bounded scenario rotation are delegated "
    "to the canonical source modules; visual state does not affect decisions."
)

st.subheader("Navigation")
st.write(
    "Open **Serious Game** for Play or Reviewer/Audit mode. Existing Dashboard, Decision "
    "Trace, Experiment Simulator, and Scientific Validation pages remain available from the sidebar."
)
