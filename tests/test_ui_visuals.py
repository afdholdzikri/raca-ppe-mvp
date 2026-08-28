"""Pure-helper tests for reusable Streamlit visual components."""
from __future__ import annotations

from pathlib import Path

import pytest

import assets_manager
import ui_visuals


def test_safe_text_escapes_untrusted_html():
    escaped = ui_visuals._safe_text('<script>alert("x")</script>')
    assert "<script>" not in escaped
    assert "&lt;script&gt;" in escaped
    assert "&quot;x&quot;" in escaped


def test_safe_text_handles_missing_values():
    assert ui_visuals._safe_text(None) == "Not available"
    assert ui_visuals._safe_text("  ", "Unknown") == "Unknown"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(-0.25, 0.0), (0.4, 0.4), (2.0, 1.0), (None, None), ("bad", None), (float("nan"), None)],
)
def test_display_score_clamping_only(raw, expected):
    assert ui_visuals._clamp_display_score(raw) == expected


def test_risk_display_formats_percentage_without_recomputation():
    model = ui_visuals._risk_display_model(0.6544, "HIGH")
    assert model == {"score": 0.6544, "percentage": 65.4, "category": "high"}


def test_risk_display_handles_missing_and_invalid_values():
    assert ui_visuals._risk_display_model(None, None) == {
        "score": None,
        "percentage": None,
        "category": "unknown",
    }
    assert ui_visuals._risk_display_model(4.2, "unexpected")["score"] == 1.0


def test_widget_keys_are_stable_unique_and_safe():
    first = ui_visuals._stable_widget_key("Episode 2", "Safety Helmet", 0)
    assert first == ui_visuals._stable_widget_key("Episode 2", "Safety Helmet", 0)
    assert first != ui_visuals._stable_widget_key("Episode 2", "Safety Helmet", 1)
    assert first == "episode_2__ppe__safety_helmet__0"


def test_safe_image_path_substitutes_category_placeholder(tmp_path):
    result = ui_visuals._safe_image_path(tmp_path / "missing.png", "hazard")
    assert result == assets_manager.PLACEHOLDERS_DIR / "missing_hazard_icon.png"


def test_placeholder_details():
    result = ui_visuals._placeholder_details(assets_manager.PLACEHOLDERS_DIR / "missing_ppe_icon.png")
    assert result == (True, "ppe", "missing_ppe_icon")


def test_module_does_not_import_scientific_engines():
    source = Path(ui_visuals.__file__).read_text(encoding="utf-8")
    assert "core.risk_engine" not in source
    assert "core.learner_model" not in source
    assert "core.adaptation_engine" not in source


def test_game_css_file_is_readable_and_project_relative():
    css_path = ui_visuals._CSS_PATH
    assert css_path == assets_manager.ASSETS_ROOT / "game_ui.css"
    assert css_path.is_file()
    assert ui_visuals._load_game_css() == css_path.read_text(encoding="utf-8")
    assert "C:\\Users\\" not in css_path.read_text(encoding="utf-8")


def test_game_css_contains_required_scoped_classes():
    css = ui_visuals._load_game_css()
    required = {
        ".game-header", ".game-header-title", ".game-subtitle", ".scenario-card",
        ".scenario-image-frame", ".character-frame", ".risk-panel", ".risk-low",
        ".risk-medium", ".risk-high", ".risk-critical", ".hazard-badge", ".ppe-card",
        ".ppe-card-selected", ".feedback-card", ".feedback-correct", ".feedback-warning",
        ".feedback-incorrect", ".adaptation-card", ".competence-card", ".status-badge",
        ".difficulty-badge", ".assistance-badge", ".placeholder-notice", ".metric-tile",
    }
    assert all(selector in css for selector in required)


def test_game_css_has_no_remote_imports_or_urls():
    css = ui_visuals._load_game_css().lower()
    assert "@import" not in css
    assert "http://" not in css
    assert "https://" not in css
    assert "url(" not in css


def test_missing_css_uses_embedded_fallback(tmp_path, caplog):
    missing = tmp_path / "missing.css"
    with caplog.at_level("WARNING"):
        css = ui_visuals._load_game_css(missing)
    assert css == ui_visuals._FALLBACK_GAME_CSS
    assert "Unable to read game UI stylesheet" in caplog.text


def test_feedback_renderer_defines_distinct_partial_warning_state():
    source = Path(ui_visuals.__file__).read_text(encoding="utf-8")
    assert "partially correct" in source.lower()
    assert "st.warning if partial" in source
