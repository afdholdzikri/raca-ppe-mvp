"""Current-session dashboard, visual summaries, and unchanged raw downloads."""
from __future__ import annotations

import json
import html

import pandas as pd
import plotly.express as px
import streamlit as st

import assets_manager
import gamification_ui
import scenario_visual_map
import trace_visuals
import ui_visuals
import canonical_streamlit_adapter as canonical_ui
from core.metrics_engine import calculate_session_metrics


st.set_page_config(page_title="Training Dashboard", page_icon="📊", layout="wide")
ui_visuals.inject_game_css()
domain = st.session_state.get("active_domain", "manufacturing")
data = canonical_ui.load_canonical_domain(domain)
if "decision_traces" not in st.session_state:
    st.session_state.decision_traces = []
if "competence_scores" not in st.session_state:
    st.session_state.competence_scores = canonical_ui.initial_deployable_state(data)["competence_scores"]
if "trainee_id" not in st.session_state:
    st.session_state.trainee_id = "Anonymous Reviewer"
traces = st.session_state.decision_traces

domain = trace_visuals.infer_trace_domain(traces[-1]) if traces else domain
domain_config = scenario_visual_map.DOMAIN_VISUAL_CONFIG.get(domain, {})
domain_label = html.escape(str(domain_config.get("display_name", "Unknown Domain")), quote=True)
trainee_label = html.escape(str(st.session_state.trainee_id), quote=True)
ui_visuals.render_page_header("📊", "Training Dashboard", "Current-session summaries, mastery, and unchanged raw downloads.")
st.markdown(
    f'<span class="status-badge">Domain: {domain_label}</span> '
    f'<span class="status-badge">Trainee: {trainee_label}</span>',
    unsafe_allow_html=True,
)

if not traces:
    st.info(
        "No training data is available yet. Complete an episode on the Serious Game page "
        "to populate mastery, risk, scenario, and achievement summaries."
    )
    st.stop()

raw_rows = pd.DataFrame(traces)
v2_metric_fields = {
    "correct", "scenario_risk", "competence_after", "risk_category", "hint_used",
    "response_time_seconds", "adaptation_latency_ms", "adaptation", "scenario_id",
}
metrics_available = all(v2_metric_fields <= set(trace) for trace in traces)
if metrics_available:
    metrics = calculate_session_metrics(traces, st.session_state.competence_scores)
    cards = st.columns(5)
    for column, (label, key) in zip(
        cards,
        [
            ("Episodes", "total_episodes"),
            ("Correct rate", "correct_decision_rate"),
            ("Mean competence", "mean_competence"),
            ("RWCI*", "risk_weighted_competence_indicator"),
            ("Critical errors", "critical_error_count"),
        ],
    ):
        column.metric(label, metrics[key] if "rate" not in key else f"{metrics[key]:.0%}")
    cards2 = st.columns(4)
    for column, (label, key) in zip(
        cards2,
        [
            ("Hint usage", "hint_usage_rate"),
            ("Avg response (s)", "mean_response_time"),
            ("Avg latency (ms)", "mean_adaptation_latency"),
            ("Incorrect rate", "incorrect_decision_rate"),
        ],
    ):
        column.metric(label, f"{metrics[key]:.2f}" if "rate" not in key else f"{metrics[key]:.0%}")
    st.caption("*Session-level risk-weighted competence indicator; not the final experimental RWCS.")
else:
    st.warning("Some older traces do not contain the Version 2 fields required for advanced session metrics. Raw traces remain available below.")
    basic = st.columns(2)
    basic[0].metric("Episodes", len(traces))
    basic[1].metric("Correct decisions", sum(trace.get("correct") is True for trace in traces))

st.subheader("Mastery Overview")
mastery_view = {
    competence_id: {
        "display_name": definition.display_name,
        "mastery": st.session_state.competence_scores.get(competence_id),
        "target_mastery": definition.target_mastery,
        "gap_remaining": max(0.0, definition.target_mastery - st.session_state.competence_scores.get(competence_id, 0.0)),
    }
    for competence_id, definition in data["competencies"].items()
}
ui_visuals.render_mastery_progress(mastery_view)

st.subheader("Risk-Category Distribution")
risk_counts: dict[str, int] = {}
for trace in traces:
    category = str(trace.get("risk_category") or "Unknown")
    risk_counts[category] = risk_counts.get(category, 0) + 1
risk_distribution = pd.DataFrame(
    [{"risk_category": category, "episodes": count} for category, count in sorted(risk_counts.items())]
)
st.plotly_chart(
    px.bar(risk_distribution, x="risk_category", y="episodes", color="risk_category", title="Episodes by recorded risk category"),
    use_container_width=True,
)

st.subheader("Most Recent Scenario")
recent = traces[-1]
recent_domain = trace_visuals.infer_trace_domain(recent)
recent_scenario = str(trace_visuals.trace_filter_value(recent, "scenario_id"))
recent_visual = scenario_visual_map.get_scenario_visual_config(recent_domain, recent_scenario, recent.get("task"))
preview, details = st.columns([2, 3])
with preview:
    ui_visuals.render_domain_scene_preview(recent_domain, recent_visual["caption"], height=260)
with details:
    st.write(f"**{recent_visual['visual_title']}**")
    st.write(f"Scenario: {recent_scenario} · Episode: {recent.get('episode', 'Unavailable')}")
    st.write(f"Recorded status: {gamification_ui.format_performance_status(recent)['label']}")

st.subheader("Recent Achievements and Status")
gamification_ui.render_achievement_badges(gamification_ui.calculate_display_achievements(traces))

if metrics_available:
    competence_rows = []
    for trace in traces:
        for competence_id, value in trace["competence_after"].items():
            competence_rows.append({"episode": trace["episode"], "competence": competence_id, "mastery": value})
    competence_frame = pd.DataFrame(competence_rows)
    chart1, chart2 = st.columns(2)
    if not competence_frame.empty:
        chart1.plotly_chart(
            px.line(competence_frame, x="episode", y="mastery", color="competence", title="Competence development"),
            use_container_width=True,
        )
    chart2.plotly_chart(
        px.line(raw_rows, x="episode", y="scenario_risk", color="scenario_id", markers=True, title="Scenario risk"),
        use_container_width=True,
    )
    chart3, chart4 = st.columns(2)
    chart3.plotly_chart(px.histogram(raw_rows, x="adaptation", title="Adaptation distribution"), use_container_width=True)
    profile = pd.DataFrame(
        {"competence": list(st.session_state.competence_scores), "mastery": list(st.session_state.competence_scores.values())}
    )
    chart4.plotly_chart(px.bar(profile, x="competence", y="mastery", title="Current competence profile"), use_container_width=True)
    st.plotly_chart(px.pie(raw_rows, names="correct", title="Correct versus incorrect"), use_container_width=True)

st.download_button("Download session CSV", raw_rows.to_csv(index=False).encode(), "raca_session.csv", "text/csv")
st.download_button("Download session JSON", json.dumps(traces, indent=2).encode(), "raca_session.json", "application/json")
st.download_button(
    "Download traces JSONL",
    ("\n".join(json.dumps(trace) for trace in traces) + "\n").encode(),
    "decision_traces.jsonl",
    "application/x-jsonlines",
)
