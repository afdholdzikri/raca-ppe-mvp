"""Reusable, lightweight Streamlit visuals for the RACA PPE serious game."""
from __future__ import annotations

import html
import base64
import logging
from pathlib import Path
from typing import Any

import streamlit as st

import assets_manager


_CSS_SESSION_KEY = "_raca_game_css_injected"
_CSS_PATH = assets_manager.ASSETS_ROOT / "game_ui.css"
_LOGGER = logging.getLogger(__name__)
_FALLBACK_GAME_CSS = """
.game-header { padding: 1rem; color: #fff; background: #173f55;
  border: 1px solid #2c6078; border-radius: .75rem; }
.game-header-title { margin: 0; font-size: 1.2rem; font-weight: 700; }
.game-subtitle { margin-top: .35rem; color: #d8e9f0; }
.placeholder-notice { padding: .45rem; border: 1px dashed #7c641f; }
"""


def _load_game_css(css_path: Path = _CSS_PATH) -> str:
    """Read project-local game CSS, falling back safely on file errors."""
    try:
        return css_path.read_text(encoding="utf-8")
    except OSError as exc:
        _LOGGER.warning("Unable to read game UI stylesheet %s: %s", css_path, exc)
        return _FALLBACK_GAME_CSS


def _safe_text(value: Any, default: str = "Not available") -> str:
    """Return an HTML-escaped display value."""
    if value is None or str(value).strip() == "":
        return html.escape(default, quote=True)
    return html.escape(str(value).strip(), quote=True)


def _label(value: Any) -> str:
    """Format an identifier as a human-readable label without HTML markup."""
    key = assets_manager.normalize_asset_key("" if value is None else str(value))
    return key.replace("_", " ").title() if key else "Not available"


def _clamp_display_score(value: float | int | None) -> float | None:
    """Clamp a numeric value for display only; no scientific value is changed."""
    if value is None or isinstance(value, bool):
        return None
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    if score != score:  # NaN
        return None
    return min(1.0, max(0.0, score))


def _risk_display_model(risk_score: float | None, risk_category: str | None) -> dict[str, Any]:
    """Build a presentation-only risk model without calculating risk."""
    score = _clamp_display_score(risk_score)
    category = assets_manager.normalize_asset_key(risk_category or "")
    if category not in {"low", "medium", "high", "critical"}:
        category = "unknown"
    return {
        "score": score,
        "percentage": None if score is None else round(score * 100.0, 1),
        "category": category,
    }


def _stable_widget_key(key_prefix: str, ppe_id: str, index: int) -> str:
    """Create a deterministic widget key unique within a PPE card collection."""
    prefix = assets_manager.normalize_asset_key(key_prefix) or "ppe_selection"
    item = assets_manager.normalize_asset_key(ppe_id) or "unknown"
    return f"{prefix}__ppe__{item}__{index}"


def _placeholder_details(path: Path) -> tuple[bool, str, str]:
    """Return placeholder status, category, and asset name for a path."""
    candidate = Path(path)
    is_placeholder = candidate.parent.resolve() == assets_manager.PLACEHOLDERS_DIR.resolve()
    name = candidate.stem
    category = name.removeprefix("missing_").removesuffix("_icon") if is_placeholder else ""
    return is_placeholder, category, name


def _safe_image_path(path: str | Path | None, category: str) -> Path:
    """Return a valid image path, substituting a managed fallback if necessary."""
    candidate = Path(path) if path is not None else Path()
    if path is not None and assets_manager.image_exists(candidate):
        return candidate
    fallback_keys = {
        "character": "unknown_character",
        "background": "unknown_background",
        "ppe": "unknown_ppe",
        "hazard": "unknown_hazard",
        "badge": "unknown_badge",
    }
    return assets_manager.resolve_asset_path(category, fallback_keys[category])


def inject_game_css() -> None:
    """Inject static game styling at most once in the current Streamlit session."""
    if not st.session_state.get(_CSS_SESSION_KEY, False):
        st.markdown(f"<style>{_load_game_css()}</style>", unsafe_allow_html=True)
        st.session_state[_CSS_SESSION_KEY] = True


def render_scenario_header(
    domain: str,
    scenario_title: str,
    scenario_id: str | None,
    difficulty: int | str,
    trainee_profile: str | None,
) -> None:
    """Render a compact, research-oriented scenario header."""
    inject_game_css()
    scenario = _safe_text(scenario_title)
    domain_text = _safe_text(_label(domain))
    scenario_code = _safe_text(scenario_id, "Unassigned")
    difficulty_text = _safe_text(difficulty)
    trainee = _safe_text(trainee_profile, "Anonymous")
    markup = (
        '<section class="game-header">'
        '<div>'
        f'<h2 class="game-header-title">{scenario}</h2>'
        f'<p class="game-subtitle">Domain: {domain_text} · Scenario: {scenario_code}</p>'
        "</div>"
        '<div class="game-subtitle">'
        f'<span class="difficulty-badge">Difficulty: {difficulty_text}</span> '
        f'<span class="status-badge">Trainee: {trainee}</span>'
        "</div></section>"
    )
    st.markdown(markup, unsafe_allow_html=True)


def render_scenario_visual(
    background_path: str | Path | None,
    character_path: str | Path | None,
    caption: str | None = None,
    selected_ppe: list[str] | None = None,
) -> None:
    """Render responsive background and character imagery with safe fallbacks."""
    background = _safe_image_path(background_path, "background")
    character = _safe_image_path(character_path, "character")
    background_column, character_column = st.columns([3, 1])
    with background_column:
        st.image(str(background), caption=caption or None, use_column_width=True)
    with character_column:
        render_dynamic_ppe_worker(character, selected_ppe or [])
    for path in (background, character):
        placeholder, category, name = _placeholder_details(path)
        if placeholder:
            render_placeholder_notice(category, name)


_PPE_OVERLAY_POSITIONS = {
    "helmet": ("25%", "2%", "50%"),
    "safety_helmet": ("25%", "2%", "50%"),
    "goggles": ("34%", "19%", "32%"),
    "safety_goggles": ("34%", "19%", "32%"),
    "laboratory_goggles": ("34%", "19%", "32%"),
    "face_shield": ("29%", "13%", "42%"),
    "respirator": ("37%", "27%", "26%"),
    "dust_respirator": ("37%", "27%", "26%"),
    "hearing_protection": ("25%", "18%", "50%"),
    "vest": ("27%", "38%", "46%"),
    "safety_vest": ("27%", "38%", "46%"),
    "high_visibility_vest": ("27%", "38%", "46%"),
    "laboratory_coat": ("23%", "36%", "54%"),
    "fall_arrest_system": ("28%", "37%", "44%"),
    "gloves": ("4%", "51%", "92%"),
    "work_gloves": ("4%", "51%", "92%"),
    "chemical_gloves": ("4%", "51%", "92%"),
    "shoes": ("22%", "86%", "56%"),
    "safety_shoes": ("22%", "86%", "56%"),
    "safety_footwear": ("22%", "86%", "56%"),
    "closed_safety_footwear": ("22%", "86%", "56%"),
}


def _image_data_uri(path: Path) -> str | None:
    """Encode a validated local image for a self-contained HTML layer."""
    if not assets_manager.image_exists(path):
        return None
    mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(
        path.suffix.lower(), "image/png"
    )
    try:
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    except OSError:
        return None
    return f"data:{mime};base64,{encoded}"


def _ppe_overlay_model(selected_ppe: list[str]) -> list[dict[str, str]]:
    """Return fixed presentation coordinates; no scientific state is read."""
    layers = []
    for ppe_id in selected_ppe:
        key = assets_manager.normalize_asset_key(ppe_id)
        position = _PPE_OVERLAY_POSITIONS.get(key)
        if position is None:
            continue
        icon = assets_manager.get_ppe_icon(ppe_id)
        source = _image_data_uri(icon)
        if source is None:
            continue
        left, top, width = position
        layers.append(
            {"ppe_id": key, "src": source, "left": left, "top": top, "width": width}
        )
    return layers


def render_dynamic_ppe_worker(character_path: str | Path | None, selected_ppe: list[str]) -> None:
    """Render a local character with immediately updated PPE overlays."""
    character = _safe_image_path(character_path, "character")
    source = _image_data_uri(character)
    if source is None:
        st.image(str(character), use_column_width=True)
        return
    layer_markup = "".join(
        '<img class="ppe-overlay" src="{}" alt="{}" style="left:{};top:{};width:{}">'.format(
            layer["src"], _safe_text(_label(layer["ppe_id"])), layer["left"], layer["top"], layer["width"]
        )
        for layer in _ppe_overlay_model(selected_ppe)
    )
    st.markdown(
        '<div class="dynamic-worker-frame" aria-label="Worker with selected PPE">'
        f'<img class="dynamic-worker-base" src="{source}" alt="Training worker">'
        f"{layer_markup}</div>",
        unsafe_allow_html=True,
    )


def render_hazard_badges(hazards: list[dict[str, Any]] | list[str]) -> None:
    """Render hazard icons, names, and supplied severity/risk metadata."""
    if not hazards:
        st.info("No active hazard information is available.")
        return
    columns = st.columns(min(4, len(hazards)))
    for index, hazard in enumerate(hazards):
        record = hazard if isinstance(hazard, dict) else {"id": hazard}
        hazard_id = str(record.get("id") or record.get("hazard_id") or record.get("name") or "unknown")
        name = str(record.get("display_name") or record.get("name") or _label(hazard_id))
        metadata = record.get("severity", record.get("risk", record.get("criticality")))
        icon = assets_manager.get_hazard_icon(hazard_id)
        with columns[index % len(columns)]:
            with st.container(border=True):
                st.image(str(icon), width=52)
                st.markdown(f"**{name}**")
                if metadata is not None:
                    st.caption(f"Severity / risk: {metadata}")
                placeholder, category, asset_name = _placeholder_details(icon)
                if placeholder:
                    render_placeholder_notice(category, asset_name)


def render_risk_panel(
    risk_score: float | None,
    risk_category: str | None,
    urgency: str | None,
    active_hazards: list[Any] | None,
) -> None:
    """Display supplied normalized risk data without recomputing it."""
    model = _risk_display_model(risk_score, risk_category)
    with st.container(border=True):
        st.subheader("Contextual Risk")
        badge_column, detail_column = st.columns([1, 4])
        with badge_column:
            st.image(str(assets_manager.get_risk_badge(model["category"])), width=72)
        with detail_column:
            if model["score"] is None:
                st.write("Risk score: Not available")
                st.progress(0.0, text="Awaiting risk assessment")
            else:
                st.metric("Normalized risk", f'{model["percentage"]:.1f}%')
                st.progress(model["score"], text=f'{model["category"].title()} risk')
        st.caption(f"Urgency: {urgency or 'Not available'} · Active hazards: {len(active_hazards or [])}")


def render_adaptation_panel(
    target_competencies: Any,
    difficulty: Any,
    assistance_mode: Any,
    adaptation_rule: Any,
    next_scenario: Any = None,
) -> None:
    """Render the supplied adaptation decision and its immediate consequences."""
    if isinstance(target_competencies, dict):
        targets = ", ".join(_label(key) for key in target_competencies)
    elif isinstance(target_competencies, (list, tuple, set)):
        targets = ", ".join(_label(item) for item in target_competencies)
    else:
        targets = _label(target_competencies)
    with st.container(border=True):
        st.subheader("Adaptation Decision")
        columns = st.columns(4)
        columns[0].metric("Difficulty", difficulty if difficulty is not None else "—")
        columns[1].metric("Assistance", _label(assistance_mode))
        columns[2].metric("Active rule", _label(adaptation_rule))
        columns[3].metric("Next scenario", next_scenario if next_scenario is not None else "—")
        st.caption(f"Target competencies: {targets}")


def render_ppe_selection_cards(
    ppe_items: list[dict[str, Any]],
    selected_ids: list[str],
    key_prefix: str,
) -> list[str]:
    """Render stable checkbox cards and return the PPE identifiers selected."""
    if not ppe_items:
        st.info("No PPE options are available.")
        return []
    previously_selected = {str(item) for item in selected_ids}
    selected: list[str] = []
    columns = st.columns(min(3, len(ppe_items)))
    for index, item in enumerate(ppe_items):
        ppe_id = str(item.get("id") or item.get("ppe_id") or f"unknown_{index}")
        label = str(item.get("display_name") or item.get("name") or _label(ppe_id))
        description = str(item.get("description") or "No description available.")
        icon = assets_manager.get_ppe_icon(ppe_id)
        with columns[index % len(columns)]:
            with st.container(border=True):
                st.image(str(icon), width=72)
                checked = st.checkbox(
                    label,
                    value=ppe_id in previously_selected,
                    key=_stable_widget_key(key_prefix, ppe_id, index),
                    help=description,
                )
                st.caption(description)
                st.caption("Status: Selected" if checked else "Status: Not selected")
                if checked:
                    selected.append(ppe_id)
                placeholder, category, asset_name = _placeholder_details(icon)
                if placeholder:
                    render_placeholder_notice(category, asset_name)
    return selected


def render_feedback_panel(
    is_correct: bool | None,
    missing_ppe: list[str],
    unnecessary_ppe: list[str],
    response_score: float | None,
    independence_score: float | None,
    competence_change: dict[str, Any] | None,
    message: str | None,
) -> None:
    """Render decision feedback from already-computed assessment values."""
    if is_correct is None:
        st.info(message or "Submit a PPE decision to receive feedback.")
        return
    partial = bool(message and message.strip().lower().startswith("partially correct"))
    feedback = st.success if is_correct else (st.warning if partial else st.error)
    feedback(message or ("Correct PPE selection." if is_correct else "PPE selection needs revision."))
    columns = st.columns(2)
    columns[0].write("**Missing PPE:** " + (", ".join(_label(item) for item in missing_ppe) or "None"))
    columns[1].write("**Unnecessary PPE:** " + (", ".join(_label(item) for item in unnecessary_ppe) or "None"))
    scores = st.columns(2)
    response = _clamp_display_score(response_score)
    independence = _clamp_display_score(independence_score)
    scores[0].metric("Response score", "—" if response is None else f"{response:.2f}")
    scores[1].metric("Independence score", "—" if independence is None else f"{independence:.2f}")
    if competence_change:
        st.caption("Competence change")
        st.json(competence_change)


def render_mastery_progress(competence_state: dict[str, Any], target_mastery: float | None = None) -> None:
    """Render competence mastery values and supplied target information."""
    if not competence_state:
        st.info("No competence data is available.")
        return
    default_target = _clamp_display_score(target_mastery)
    for competence_id, raw in competence_state.items():
        if isinstance(raw, dict):
            name = str(raw.get("display_name") or raw.get("name") or _label(competence_id))
            value = _clamp_display_score(raw.get("mastery", raw.get("value")))
            target = _clamp_display_score(raw.get("target_mastery", default_target))
            prior = _clamp_display_score(raw.get("prior_mastery"))
            gap = _clamp_display_score(raw.get("gap_remaining"))
        else:
            name = _label(competence_id)
            value = _clamp_display_score(raw)
            target = default_target
            prior = None
            gap = None
        with st.container(border=True):
            heading, status_column = st.columns([3, 1])
            heading.write(f"**{name}**")
            if value is None:
                status = "Unavailable"
            elif target is None:
                status = "Recorded"
            else:
                status = "Target achieved" if value >= target else "Developing"
            status_column.caption(status)
            st.progress(value or 0.0, text="No mastery value" if value is None else f"{value * 100:.1f}% mastery")
            details = ["Target: Not specified" if target is None else f"Target mastery: {target * 100:.1f}%"]
            if prior is not None:
                details.append(f"Prior mastery: {prior * 100:.1f}%")
            if gap is not None:
                details.append(f"Gap remaining: {gap * 100:.1f}%")
            st.caption(" · ".join(details))


def render_game_status_bar(
    episode: int,
    max_episodes: int,
    current_score: float | None,
    difficulty: Any,
    assistance_mode: Any,
) -> None:
    """Render compact episode, score, difficulty, and assistance status."""
    score = _clamp_display_score(current_score)
    columns = st.columns(4)
    columns[0].metric("Episode", f"{episode} / {max_episodes}")
    columns[1].metric("Current score", "—" if score is None else f"{score * 100:.1f}%")
    columns[2].metric("Difficulty", difficulty if difficulty is not None else "—")
    columns[3].metric("Assistance", _label(assistance_mode))


def render_placeholder_notice(asset_category: str, asset_name: str) -> None:
    """Show a concise notice that development fallback artwork is displayed."""
    category = _label(asset_category)
    name = _label(asset_name)
    st.caption(f"Development placeholder in use — {category}: {name}.")
