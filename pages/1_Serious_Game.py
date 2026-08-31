"""Dynamic reviewer game backed exclusively by the deployable Canonical V15 path."""
from __future__ import annotations

import json
import logging
from pathlib import Path
import time

import pandas as pd
import streamlit as st

import assets_manager
import canonical_streamlit_adapter as canonical_ui
import gamification_ui
import presentation_mode
import scenario_visual_map
import ui_visuals
from experiments.canonical_config import CanonicalConfig


LOGGER = logging.getLogger(__name__)
CANONICAL_CONFIG = CanonicalConfig(methods=["proposed"], profiles=["T1"])
TRACE_PATH = Path("storage") / "decision_traces.jsonl"

st.set_page_config(page_title="Canonical PPE Serious Game", page_icon="🎯", layout="wide")
ui_visuals.inject_game_css()


def _ppe_prefix() -> str:
    return "ppe_select_{}_{}".format(
        assets_manager.normalize_asset_key(st.session_state.get("session_id", "session")),
        assets_manager.normalize_asset_key(st.session_state.get("current_scenario_id", "scenario")),
    )


def _clear_ppe_widgets() -> None:
    prefix = _ppe_prefix() + "__ppe__"
    for key in list(st.session_state):
        if str(key).startswith(prefix):
            del st.session_state[key]


def _activate_domain(domain: str, *, preserve_traces: bool) -> None:
    data = canonical_ui.load_canonical_domain(domain)
    fresh = canonical_ui.initial_deployable_state(data)
    traces = list(st.session_state.get("decision_traces", [])) if preserve_traces else []
    session_id = st.session_state.get("session_id") if preserve_traces else None
    st.session_state.update(
        {
            "session_id": session_id or canonical_ui.new_session_id(),
            "trainee_id": "Anonymous Reviewer",
            "active_domain": domain,
            "episode": 1,
            "decision_traces": traces,
            "last_trace": None,
            "next_scenario_id": None,
            "submission_processed": False,
            "hint_used": False,
            "ppe_selection": [],
            "scenario_start_time": time.time(),
            "session_status": "active",
            **fresh,
        }
    )


def _domain_changed() -> None:
    st.session_state.pending_domain = st.session_state.canonical_domain_widget


def _use_hint() -> None:
    st.session_state.hint_used = True


def _continue_episode() -> None:
    _clear_ppe_widgets()
    trace = st.session_state.get("last_trace")
    if not trace:
        return
    st.session_state.current_scenario_id = trace["next_scenario"]
    st.session_state.current_difficulty = trace["next_difficulty"]
    st.session_state.assistance = trace["next_assistance"]
    st.session_state.distractor_level = trace["next_distractor_level"]
    st.session_state.episode += 1
    st.session_state.submission_processed = False
    st.session_state.hint_used = False
    st.session_state.ppe_selection = []
    st.session_state.last_trace = None
    st.session_state.next_scenario_id = None
    st.session_state.scenario_start_time = time.time()


def _reset_session() -> None:
    _clear_ppe_widgets()
    _activate_domain(st.session_state.active_domain, preserve_traces=False)


seeded_scenario_id = st.session_state.get("current_scenario_id")
if "pending_domain" in st.session_state:
    pending = st.session_state.pop("pending_domain")
    _clear_ppe_widgets()
    _activate_domain(pending, preserve_traces=True)
if "active_domain" not in st.session_state:
    _activate_domain(canonical_ui.available_domains()[0], preserve_traces=False)
    if seeded_scenario_id is not None:
        st.session_state.current_scenario_id = seeded_scenario_id

with st.sidebar:
    st.subheader("Reviewer Controls")
    domain_options = canonical_ui.available_domains()
    st.selectbox(
        "Canonical domain",
        domain_options,
        index=domain_options.index(st.session_state.active_domain),
        format_func=lambda value: value.replace("_", " ").title(),
        key="canonical_domain_widget",
        on_change=_domain_changed,
    )
    ui_mode = st.radio(
        "Interface mode",
        ("Play Mode", "Reviewer / Audit Mode"),
        key="canonical_ui_mode_widget",
    )
    screenshot_mode = st.checkbox("Paper Screenshot Mode", key="paper_screenshot_mode")
    anonymize = st.checkbox("Anonymize trainee identifiers", key="anonymize_trainee_identifiers")
    st.caption("Scientific engine: Canonical V15 Proposed policy")
    st.caption("Simulation-only latent state is not available to this page.")

try:
    data = canonical_ui.load_canonical_domain(st.session_state.active_domain)
    if st.session_state.current_scenario_id not in data["scenarios"]:
        st.error("No valid training scenario is available for the current session. Reset the session or verify the canonical domain data.")
        st.stop()
    prepared = canonical_ui.prepare_scenario(
        data,
        st.session_state.current_scenario_id,
        st.session_state.current_difficulty,
        st.session_state.distractor_level,
    )
except Exception:
    LOGGER.exception("Unable to prepare canonical reviewer scenario")
    st.error("The canonical domain or scenario could not be loaded. Reset the session and verify the knowledge base.")
    st.stop()

scenario = prepared["scenario"]
risk = prepared["risk"]
behavior = prepared["behavior"]
audit_mode = ui_mode == "Reviewer / Audit Mode"
trace = st.session_state.get("last_trace")
display_trainee = presentation_mode.display_trainee_identifier(
    st.session_state.trainee_id, anonymize=anonymize
)
visual = scenario_visual_map.get_scenario_visual_config(
    st.session_state.active_domain, scenario.id, scenario.task
)
character_state = scenario_visual_map.determine_character_state(
    evaluation_result=trace,
    risk_category=risk["risk_category"],
    missing_ppe=trace.get("missing_ppe") if trace else None,
)

ui_visuals.render_game_status_bar(
    st.session_state.episode,
    CANONICAL_CONFIG.episodes,
    (sum(bool(item["correct"]) for item in st.session_state.decision_traces) / len(st.session_state.decision_traces))
    if st.session_state.decision_traces else None,
    st.session_state.current_difficulty,
    st.session_state.assistance,
)
ui_visuals.render_scenario_header(
    st.session_state.active_domain,
    f"{visual['visual_title']} — {scenario.task}",
    scenario.id,
    st.session_state.current_difficulty,
    display_trainee,
)
st.write(scenario.narrative)
st.caption(f"Canonical KB scenario {scenario.id} · {scenario.zone}")

if st.session_state.assistance != "none" and not st.session_state.submission_processed:
    st.button("View Hint", on_click=_use_hint)
    if st.session_state.hint_used:
        st.info(scenario.hint_text)

ppe_items = [
    {"id": item.id, "display_name": item.display_name, "description": item.description}
    for item in (data["ppe"].get(ppe_id) for ppe_id in behavior["ppe_options"])
    if item is not None
]

visual_column, choice_column = st.columns([3, 2], gap="large")
with choice_column:
    ui_visuals.render_risk_panel(
        risk["scenario_risk"], risk["risk_category"], "canonical per competence", scenario.hazards
    )
    st.subheader("Select Personal Protective Equipment")
    if st.session_state.submission_processed:
        selected_ppe = list(st.session_state.ppe_selection)
        st.info("Submitted: " + (", ".join(selected_ppe) or "None"))
    else:
        selected_ppe = ui_visuals.render_ppe_selection_cards(
            ppe_items, list(st.session_state.get("ppe_selection", [])), _ppe_prefix()
        )
        st.session_state.ppe_selection = selected_ppe

with visual_column:
    st.subheader("Workplace Context")
    ui_visuals.render_scenario_visual(
        assets_manager.PROJECT_ROOT / visual["background"],
        assets_manager.get_domain_character(st.session_state.active_domain, character_state),
        caption=visual["caption"],
        selected_ppe=selected_ppe,
        domain=st.session_state.active_domain,
    )
    hazard_records = [
        {
            "id": hazard.id,
            "display_name": hazard.display_name,
            "severity": hazard.severity,
            "criticality": hazard.criticality,
        }
        for hazard in (data["hazards"].get(hazard_id) for hazard_id in behavior["emphasized_hazards"])
        if hazard is not None
    ]
    ui_visuals.render_hazard_badges(hazard_records)

if st.button(
    "Evaluate PPE Decision",
    type="primary",
    disabled=st.session_state.submission_processed or st.session_state.session_status != "active",
):
    if not st.session_state.submission_processed:
        try:
            result = canonical_ui.evaluate_decision(
                domain_data=data,
                scenario_id=scenario.id,
                selected_ppe=selected_ppe,
                competence_scores=st.session_state.competence_scores,
                repeated_errors=st.session_state.repeated_errors,
                current_difficulty=st.session_state.current_difficulty,
                scenario_history=st.session_state.scenario_history,
                recent_scores=st.session_state.recent_scores,
                response_time_seconds=max(0.0, time.time() - st.session_state.scenario_start_time),
                time_limit_seconds=behavior["time_limit_seconds"],
                hint_used=st.session_state.hint_used,
                session_id=st.session_state.session_id,
                episode=st.session_state.episode,
                assistance=st.session_state.assistance,
                distractor_level=st.session_state.distractor_level,
                reviewer_mode=audit_mode,
                animation_state={"selected_ppe": selected_ppe},
                trace_path=TRACE_PATH,
                config=CANONICAL_CONFIG,
            )
            trace = result["trace"]
            st.session_state.competence_scores = result["competence_scores"]
            st.session_state.repeated_errors = result["repeated_errors"]
            st.session_state.recent_scores = result["recent_scores"]
            st.session_state.scenario_history.append(scenario.id)
            st.session_state.decision_traces.append(trace)
            st.session_state.last_trace = trace
            st.session_state.next_scenario_id = trace["next_scenario"]
            st.session_state.submission_processed = True
            st.rerun()
        except Exception:
            LOGGER.exception("Canonical PPE evaluation failed")
            st.error("The canonical evaluation failed; no duplicate decision was stored. Please retry or reset.")

trace = st.session_state.get("last_trace")
if trace:
    status = gamification_ui.format_performance_status(trace)
    message = {
        "correct": "Correct PPE selection.",
        "partial": "Partially correct PPE selection.",
        "incorrect": "Incorrect PPE selection.",
    }.get(status["status"], "Decision evaluated.")
    features = trace["observable_response_features"]
    ui_visuals.render_feedback_panel(
        trace["correct"], trace["missing_ppe"], trace["unnecessary_ppe"],
        features["response_quality"], features["independence"],
        {
            competence_id: {
                "before": trace["learner_estimate_before"][competence_id],
                "after": trace["learner_estimate_after"][competence_id],
            }
            for competence_id in trace["affected_competencies"]
        },
        message,
    )
    ui_visuals.render_adaptation_panel(
        trace["competence"], trace["next_difficulty"], trace["next_assistance"],
        trace["selected_rule"], trace["next_scenario"],
    )
    st.info(trace["explanation"])
    if trace.get("persisted_to_file") is False:
        st.warning("Decision completed, but the local JSON Lines trace could not be exported.")

st.subheader("Next Adaptation")
if trace is None:
    st.caption("The canonical adaptation will appear after the decision is submitted.")

st.subheader("Target Competence Progress")
competence_view = {
    competence_id: {
        "display_name": definition.display_name,
        "mastery": st.session_state.competence_scores[competence_id],
        "target_mastery": CANONICAL_CONFIG.target_mastery,
        "gap_remaining": max(0.0, CANONICAL_CONFIG.target_mastery - st.session_state.competence_scores[competence_id]),
    }
    for competence_id, definition in data["competencies"].items()
}
ui_visuals.render_mastery_progress(competence_view, CANONICAL_CONFIG.target_mastery)

if audit_mode:
    st.subheader("Reviewer / Audit Evidence")
    if trace:
        factor_rows = [
            {
                "competence": competence_id,
                "R_hat": trace["risk_hat"][competence_id],
                "G": trace["competence_gap"][competence_id],
                "phi": trace["repetition_factor"][competence_id],
                "U": trace["urgency"][competence_id],
                "Q": trace["priority_q"][competence_id],
            }
            for competence_id, _ in trace["priority_ranking"]
        ]
        st.dataframe(pd.DataFrame(factor_rows), use_container_width=True, hide_index=True)
        audit_columns = st.columns(3)
        # audit_columns[0].write("**Eligible rules**", trace["eligible_rules"])
        # audit_columns[1].write("**Requested action**", trace["requested_action"])
        # audit_columns[2].write("**Applied action**", trace["applied_action"])
        with audit_columns[0]:
            st.markdown("**Eligible rules**")
            if trace["eligible_rules"]:
                for rule in trace["eligible_rules"]:
                    st.code(str(rule))
            else:
                st.caption("No eligible rule recorded.")

        with audit_columns[1]:
            st.markdown("**Requested action**")
            st.json(trace["requested_action"], expanded=True)

        with audit_columns[2]:
            st.markdown("**Applied / bounded action**")
            st.json(trace["applied_action"], expanded=True)
        st.caption(
            f"Engine: {trace['engine_version']} · Parameters: {trace['parameter_version']} · "
            f"Rules: {trace['ruleset_version']} · KB: {trace['knowledge_base_version']} · "
            f"Trace: {trace['trace_id']}"
        )
        if not screenshot_mode:
            with st.expander("Canonical decision trace"):
                st.json(trace)
            st.download_button(
                "Download current trace (JSON)",
                json.dumps(trace, indent=2),
                file_name=f"canonical_trace_{trace['trace_id']}.json",
                mime="application/json",
                key=f"trace_download_{trace['trace_id']}",
            )
    else:
        st.info("Submit a decision to inspect R_hat, G, phi, U, Q, rule precedence, and bounded action.")

if screenshot_mode:
    st.subheader("Explainable Decision")
    if trace:
        st.write(trace["explanation"])
    else:
        st.caption("Submit a decision to display the compact canonical rationale.")
else:
    with st.expander("Why did the framework choose this adaptation?"):
        if trace:
            st.write(trace["explanation"])
            st.json(
                {
                    "R_hat": trace["risk_hat"],
                    "G": trace["competence_gap"],
                    "phi": trace["repetition_factor"],
                    "U": trace["urgency"],
                    "Q": trace["priority_q"],
                    "selected_rule": trace["selected_rule"],
                    "next_scenario": trace["next_scenario"],
                }
            )
        else:
            st.caption("No canonical decision is available yet.")

st.subheader("Display Achievements")
gamification_ui.render_achievement_badges(
    gamification_ui.calculate_display_achievements(st.session_state.decision_traces)
)

controls = st.columns(2)
controls[0].button(
    "Continue to Canonical Next Scenario",
    on_click=_continue_episode,
    disabled=not st.session_state.submission_processed,
)
controls[1].button("Reset Session", on_click=_reset_session)

st.markdown(
    '<footer class="paper-screenshot-footer">Research prototype — synthetic validation</footer>',
    unsafe_allow_html=True,
)
