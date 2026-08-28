"""Integration tests for backward-compatible dashboard and trace visuals."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from streamlit.testing.v1 import AppTest

from core.trace_manager import REQUIRED_TRACE_FIELDS


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "pages" / "2_Training_Dashboard.py"
TRACE_PAGE = ROOT / "pages" / "3_Decision_Trace.py"


def _legacy_trace():
    trace = {key: "value" for key in REQUIRED_TRACE_FIELDS}
    trace.update(
        session_id="legacy-session",
        timestamp_utc="2026-01-01T00:00:00+00:00",
        episode=1,
        scenario_id="S5",
        zone="Chemical Mixing Area",
        task="Mixing chemicals",
        hazards=["chemical_vapour"],
        selected_ppe=["goggles"],
        required_ppe=["goggles", "respirator"],
        missing_ppe=["respirator"],
        unnecessary_ppe=[],
        correct=False,
        probability=4,
        severity=5,
        exposure=5,
        context_modifier=1.0,
        normalized_risk=0.8,
        competence_before=0.4,
        observation_score=0.4,
        competence_after=0.4,
        repeated_errors=1,
        competence_gap=0.6,
        training_priority=0.48,
        active_rule="high_risk_low_competence",
        adaptation="priority_remediation",
        current_difficulty=2,
        next_difficulty=1,
        assistance="full_visual_guidance",
        feedback="immediate_corrective",
        repeat_required=True,
        adaptation_latency_ms=1.2,
        explanation="Legacy trace explanation.",
    )
    return trace


def _run_with_legacy_trace(page: Path):
    trace = _legacy_trace()
    before = deepcopy(trace)
    app = AppTest.from_file(str(page), default_timeout=20)
    app.session_state["decision_traces"] = [trace]
    app.run()
    return app, before


def test_dashboard_reads_old_trace_and_preserves_downloads():
    app, original = _run_with_legacy_trace(DASHBOARD)
    assert not app.exception
    assert app.session_state["decision_traces"] == [original]
    assert [button.label for button in app.get("download_button")] == [
        "Download session CSV",
        "Download session JSON",
        "Download traces JSONL",
    ]
    assert any("older traces" in warning.value for warning in app.warning)


def test_decision_trace_reads_old_trace_and_preserves_downloads():
    app, original = _run_with_legacy_trace(TRACE_PAGE)
    assert not app.exception
    assert app.session_state["decision_traces"] == [original]
    assert [button.label for button in app.get("download_button")] == [
        "Download filtered CSV",
        "Download filtered JSON",
    ]
    assert any("Episode 1" in expander.label for expander in app.expander)


def test_visual_pages_do_not_persist_or_version_historical_traces():
    for page in (DASHBOARD, TRACE_PAGE):
        source = page.read_text(encoding="utf-8")
        assert "append_trace" not in source
        assert "write_text" not in source
        assert "open(" not in source

