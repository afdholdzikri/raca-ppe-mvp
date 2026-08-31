"""Filterable, backward-compatible current-session trace inspection."""
from __future__ import annotations

import html
import json

import pandas as pd
import streamlit as st

import assets_manager
import scenario_visual_map
import trace_visuals
import ui_visuals
import canonical_streamlit_adapter as canonical_ui


st.set_page_config(page_title="Decision Trace", page_icon="🔎", layout="wide")
ui_visuals.inject_game_css()
domain = st.session_state.get("active_domain", "manufacturing")
data = canonical_ui.load_canonical_domain(domain)
if "decision_traces" not in st.session_state:
    st.session_state.decision_traces = []
traces = st.session_state.decision_traces
ui_visuals.render_page_header("🔎", "Decision Trace", "Filterable, backward-compatible current-session trace inspection.")
if not traces:
    st.info("No decision traces exist in this session. Complete a Serious Game episode to inspect its explanation flow.")
    st.stop()


def options(key: str) -> list[str]:
    return ["All"] + sorted({str(trace_visuals.trace_filter_value(trace, key)) for trace in traces})


columns = st.columns(3)
scenario_filter = columns[0].selectbox("Scenario ID", options("scenario_id"))
correct_filter = columns[1].selectbox("Correctness", ["All", "True", "False"])
risk_filter = columns[2].selectbox("Risk category", options("risk_category"))
columns2 = st.columns(3)
adaptation_filter = columns2[0].selectbox("Adaptation", options("adaptation"))
rule_filter = columns2[1].selectbox("Selected rule", options("selected_rule"))
target_filter = columns2[2].selectbox("Target competence", options("highest_priority_competence"))

filtered = [
    trace
    for trace in traces
    if (scenario_filter == "All" or str(trace_visuals.trace_filter_value(trace, "scenario_id")) == scenario_filter)
    and (correct_filter == "All" or str(trace_visuals.trace_filter_value(trace, "correct")) == correct_filter)
    and (risk_filter == "All" or str(trace_visuals.trace_filter_value(trace, "risk_category")) == risk_filter)
    and (adaptation_filter == "All" or str(trace_visuals.trace_filter_value(trace, "adaptation")) == adaptation_filter)
    and (rule_filter == "All" or str(trace_visuals.trace_filter_value(trace, "selected_rule")) == rule_filter)
    and (target_filter == "All" or str(trace_visuals.trace_filter_value(trace, "highest_priority_competence")) == target_filter)
]

summary = pd.DataFrame(
    [
        {
            "episode": trace_visuals.trace_filter_value(trace, "episode"),
            "scenario": trace_visuals.trace_filter_value(trace, "scenario_id"),
            "correct": trace_visuals.trace_filter_value(trace, "correct"),
            "risk": trace_visuals.trace_filter_value(trace, "risk_category"),
            "target": trace_visuals.trace_filter_value(trace, "highest_priority_competence"),
            "rule": trace_visuals.trace_filter_value(trace, "selected_rule"),
            "adaptation": trace_visuals.trace_filter_value(trace, "adaptation"),
            "next": trace_visuals.trace_filter_value(trace, "next_scenario"),
        }
        for trace in filtered
    ]
)
st.dataframe(summary, use_container_width=True, hide_index=True)

for trace in filtered:
    episode = trace_visuals.trace_filter_value(trace, "episode")
    scenario_id = str(trace_visuals.trace_filter_value(trace, "scenario_id"))
    selected_rule = str(trace_visuals.trace_filter_value(trace, "selected_rule"))
    with st.expander(f"Episode {episode} — {scenario_id} — {selected_rule}"):
        domain = trace_visuals.infer_trace_domain(trace)
        visual = scenario_visual_map.get_scenario_visual_config(domain, scenario_id, trace.get("task"))
        image_column, context_column = st.columns([2, 3])
        with image_column:
            ui_visuals.render_scenario_chip(domain, visual["visual_title"], visual["caption"])
        with context_column:
            risk_category = str(trace_visuals.trace_filter_value(trace, "risk_category"))
            ui_visuals.render_risk_badge_chip(risk_category)
            st.markdown(
                f'<span class="status-badge">Domain: {html.escape(str(visual["domain_label"]))}</span> '
                f'<span class="status-badge">Rule: {html.escape(selected_rule)}</span>',
                unsafe_allow_html=True,
            )
            st.write(str(trace.get("explanation") or "No human-readable explanation was stored in this trace."))

        ui_visuals.render_adaptation_panel(
            target_competencies=[trace_visuals.trace_filter_value(trace, "highest_priority_competence")],
            difficulty=trace_visuals.trace_value(trace, "next_difficulty", default="Unavailable"),
            assistance_mode=trace_visuals.trace_value(trace, "assistance", default="Unavailable"),
            adaptation_rule=selected_rule,
            next_scenario=trace_visuals.trace_filter_value(trace, "next_scenario"),
        )

        completeness = trace_visuals.trace_completeness_display(trace)
        st.progress(
            completeness["ratio"],
            text=f"Trace completeness: {completeness['percentage']:.1f}% ({completeness['schema']})",
        )
        if completeness["missing_fields"]:
            st.caption("Missing historical fields: " + ", ".join(completeness["missing_fields"]))

        st.markdown("**Visual explanation flow**")
        flow = trace_visuals.build_visual_explanation_flow(trace)
        flow_columns = st.columns(len(flow))
        for index, item in enumerate(flow):
            with flow_columns[index]:
                st.markdown(f"**{item['stage']}**")
                st.caption(item["value"])
                if index < len(flow) - 1:
                    st.caption("→")
        st.markdown("**Raw trace**")
        st.json(trace)

st.download_button("Download filtered CSV", summary.to_csv(index=False).encode(), "filtered_traces.csv", "text/csv")
st.download_button("Download filtered JSON", json.dumps(filtered, indent=2).encode(), "filtered_traces.json", "application/json")
