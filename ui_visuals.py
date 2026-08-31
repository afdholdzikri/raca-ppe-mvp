"""Reusable, lightweight Streamlit visuals for the RACA PPE serious game."""
from __future__ import annotations

import html
import base64
import logging
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

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

# Optional animation enhancement loaded from a CDN inside the isolated
# components.html iframe only. Every scene/worker/gauge animates fully via
# self-contained CSS keyframes first; this script only adds extra polish
# (organic randomised timing) when the reviewer's browser can reach it, and
# is wrapped so a blocked/offline load never breaks the baseline animation.
_GSAP_TAG = (
    '<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js" '
    'referrerpolicy="no-referrer" onerror="window.__racaGsapFailed=true"></script>'
)


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
    """Inject the static game stylesheet for the current page run.

    Streamlit re-executes the whole page script on every rerun (any widget
    interaction, page switch, etc.) and only elements emitted *during that
    run* remain in the rendered DOM — an element skipped this run because it
    was already emitted on some earlier run simply is not there any more.
    The stylesheet is therefore re-emitted on every call rather than only
    once per session; ``_CSS_SESSION_KEY`` is kept (and still set) purely as
    a lightweight backward-compatible marker, not as a skip guard.
    """
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
    domain_icon = {
        "manufacturing": "\U0001F3ED",
        "chemical_laboratory": "\U0001F9EA",
        "construction": "\U0001F3D7️",
    }.get(assets_manager.normalize_asset_key(domain), "\U0001F3AF")
    markup = (
        '<section class="game-header">'
        '<div>'
        f'<h2 class="game-header-title">{domain_icon}&nbsp; {scenario}</h2>'
        f'<p class="game-subtitle">Domain: {domain_text} &middot; Scenario: {scenario_code}</p>'
        "</div>"
        '<div class="game-subtitle">'
        f'<span class="difficulty-badge">⚡ Difficulty: {difficulty_text}</span> '
        f'<span class="status-badge">\U0001F464 Trainee: {trainee}</span>'
        "</div></section>"
    )
    st.markdown(markup, unsafe_allow_html=True)


def render_page_header(icon: str, title: str, subtitle: str | None = None) -> None:
    """Render a generic page hero banner sharing the Serious Game header look.

    Used by the landing page and the Dashboard / Decision Trace / Experiment
    Simulator / Scientific Validation pages so every screen in the app reads
    as one consistent product instead of one styled screen surrounded by
    plain Streamlit defaults. Purely presentational — takes no scientific
    state and changes nothing about how any page computes its results.
    """
    inject_game_css()
    title_text = _safe_text(title)
    markup = f'<section class="raca-page-hero"><h1 class="raca-page-hero-title">{icon} {title_text}</h1>'
    if subtitle:
        markup += f'<p class="raca-page-hero-subtitle">{_safe_text(subtitle)}</p>'
    markup += "</section>"
    st.markdown(markup, unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Domain theming shared by the animated scene and the animated worker
# --------------------------------------------------------------------------

_DOMAIN_THEMES: dict[str, dict[str, str]] = {
    "manufacturing": {
        "label": "MANUFACTURING FLOOR",
        "icon": "\U0001F3ED",
        "accent": "#f59e0b",
        "accent_soft": "#fde3b0",
    },
    "chemical_laboratory": {
        "label": "CHEMICAL LABORATORY",
        "icon": "\U0001F9EA",
        "accent": "#14b8a6",
        "accent_soft": "#bdeee6",
    },
    "construction": {
        "label": "CONSTRUCTION SITE",
        "icon": "\U0001F3D7️",
        "accent": "#f97316",
        "accent_soft": "#ffd9b0",
    },
}


def domain_theme(domain: str | None) -> dict[str, str]:
    """Return the public icon/label/accent theme for a domain (manufacturing fallback)."""
    key = assets_manager.normalize_asset_key(domain or "")
    return _DOMAIN_THEMES.get(key, _DOMAIN_THEMES["manufacturing"])


def _resolve_domain_key(domain: str | None, scene_text: str) -> str:
    """Resolve a domain key from an explicit domain, falling back to keywords."""
    if domain:
        normalized = assets_manager.normalize_asset_key(domain)
        if normalized in _DOMAIN_THEMES:
            return normalized
    lower = (scene_text or "").lower()
    if any(token in lower for token in ("chemical", "laboratory", "lab", "reagent", "solvent", "corrosive")):
        return "chemical_laboratory"
    if any(token in lower for token in ("construction", "ground site", "height", "lifting", "crane", "scaffold")):
        return "construction"
    return "manufacturing"


def _character_state_from_path(path: Path | str | None) -> str:
    """Infer the presentation state (safe/warning/neutral) from an asset stem."""
    stem = Path(path).stem.lower() if path else ""
    if "warning" in stem:
        return "warning"
    if "safe" in stem:
        return "safe"
    return "neutral"


# --------------------------------------------------------------------------
# Scene + worker rendering
# --------------------------------------------------------------------------

def render_scenario_visual(
    background_path: str | Path | None,
    character_path: str | Path | None,
    caption: str | None = None,
    selected_ppe: list[str] | None = None,
    domain: str | None = None,
) -> None:
    """Render an animated 2D workplace scene and an animated PPE worker.

    ``domain`` is an optional, presentation-only hint (e.g. ``"construction"``)
    used to pick the correct animated illustration set. When omitted, the
    domain is inferred from ``caption``/``background_path`` keywords, exactly
    as in earlier releases, so existing call sites keep working unchanged.
    """
    background = _safe_image_path(background_path, "background")
    character = _safe_image_path(character_path, "character")
    scene_text = " ".join(
        part for part in (
            str(caption or ""),
            Path(background_path).stem if background_path is not None else "",
        ) if part
    ).lower()
    domain_key = _resolve_domain_key(domain, scene_text)
    state = _character_state_from_path(character_path)

    background_column, character_column = st.columns([3, 1])
    with background_column:
        components.html(_domain_scene_html(domain_key, caption), height=410, scrolling=False)
    with character_column:
        render_dynamic_ppe_worker(character, selected_ppe or [], domain=domain_key, state=state)
    for path in (background, character):
        placeholder, category, name = _placeholder_details(path)
        if placeholder:
            render_placeholder_notice(category, name)


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


def _normalized_ppe_set(selected_ppe: list[str]) -> set[str]:
    """Normalize PPE identifiers into visual categories only."""
    categories: set[str] = set()
    for raw in selected_ppe:
        key = assets_manager.normalize_asset_key(raw)
        if key in {"helmet", "safety_helmet"}:
            categories.add("helmet")
        elif key in {"goggles", "safety_goggles", "laboratory_goggles"}:
            categories.add("goggles")
        elif key == "face_shield":
            categories.add("face_shield")
        elif key in {"respirator", "dust_respirator"}:
            categories.add("respirator")
        elif key in {"hearing_protection", "earmuff", "earmuffs"}:
            categories.add("hearing")
        elif key in {"vest", "safety_vest", "high_visibility_vest"}:
            categories.add("vest")
        elif key == "laboratory_coat":
            categories.add("coat")
        elif key in {"fall_arrest_system", "body_harness", "harness"}:
            categories.add("harness")
        elif key in {"gloves", "work_gloves", "chemical_gloves"}:
            categories.add("gloves")
        elif key in {"shoes", "safety_shoes", "safety_footwear", "closed_safety_footwear"}:
            categories.add("shoes")
    return categories


_WORKER_UNIFORM_BY_DOMAIN = {
    "manufacturing": {"body": "#2563EB", "sleeve": "#1D4ED8", "boot": "#1F2937"},
    "chemical_laboratory": {"body": "#E2E8F0", "sleeve": "#CBD5E1", "boot": "#334155"},
    "construction": {"body": "#EA580C", "sleeve": "#C2410C", "boot": "#3F2E1E"},
}

_STATE_GLOW = {
    "safe": "#22c55e",
    "warning": "#ef4444",
    "neutral": "#38bdf8",
}


def _animated_worker_svg(selected_ppe: list[str], domain: str = "manufacturing", state: str = "neutral") -> str:
    """Return a self-contained animated SVG worker with attached PPE layers."""
    ppe = _normalized_ppe_set(selected_ppe)
    uniform = _WORKER_UNIFORM_BY_DOMAIN.get(domain, _WORKER_UNIFORM_BY_DOMAIN["manufacturing"])
    body_color = uniform["body"]
    sleeve_color = uniform["sleeve"]
    boot_color = uniform["boot"]

    helmet = """
      <g class="ppe-layer">
        <path d="M77 42 Q100 19 123 42 L122 49 L78 49 Z"
              fill="#FACC15" stroke="#A16207" stroke-width="2"/>
        <rect x="76" y="47" width="48" height="5" rx="2.5" fill="#6B4F15"/>
      </g>
    """ if "helmet" in ppe else ""

    goggles = """
      <g class="ppe-layer">
        <rect x="83" y="55" width="14" height="9" rx="4" fill="#BAE6FD" stroke="#0F172A" stroke-width="2"/>
        <rect x="103" y="55" width="14" height="9" rx="4" fill="#BAE6FD" stroke="#0F172A" stroke-width="2"/>
        <line x1="97" y1="59.5" x2="103" y2="59.5" stroke="#0F172A" stroke-width="2"/>
      </g>
    """ if "goggles" in ppe else ""

    shield = """
      <g class="ppe-layer">
        <path d="M79 49 Q100 42 121 49 L118 78 Q100 88 82 78 Z"
              fill="#DBEAFE" fill-opacity=".36" stroke="#60A5FA" stroke-width="2"/>
      </g>
    """ if "face_shield" in ppe else ""

    respirator = """
      <g class="ppe-layer">
        <path d="M90 67 Q100 61 110 67 L107 77 Q100 82 93 77 Z"
              fill="#F1F5F9" stroke="#475569" stroke-width="2"/>
        <circle cx="89" cy="71" r="4" fill="#94A3B8"/>
        <circle cx="111" cy="71" r="4" fill="#94A3B8"/>
      </g>
    """ if "respirator" in ppe else ""

    hearing = """
      <g class="ppe-layer">
        <path d="M79 58 Q79 39 100 39 Q121 39 121 58"
              fill="none" stroke="#111827" stroke-width="4"/>
        <rect x="74" y="55" width="10" height="21" rx="5" fill="#EF4444"/>
        <rect x="116" y="55" width="10" height="21" rx="5" fill="#EF4444"/>
      </g>
    """ if "hearing" in ppe else ""

    vest = """
      <g class="ppe-layer">
        <path d="M69 89 L86 78 L100 91 L114 78 L131 89 L124 143 L76 143 Z"
              fill="#F97316" stroke="#B45309" stroke-width="2"/>
        <path d="M82 84 L92 97 L85 140 M118 84 L108 97 L115 140"
              stroke="#FEF08A" stroke-width="6" fill="none"/>
        <line x1="77" y1="118" x2="123" y2="118" stroke="#FFF7B3" stroke-width="6"/>
      </g>
    """ if "vest" in ppe else ""

    coat = """
      <g class="ppe-layer">
        <path d="M67 88 L86 78 L100 91 L114 78 L133 88 L129 158 L71 158 Z"
              fill="#F8FAFC" stroke="#94A3B8" stroke-width="2"/>
        <line x1="100" y1="91" x2="100" y2="157" stroke="#CBD5E1" stroke-width="2"/>
        <line x1="81" y1="120" x2="92" y2="120" stroke="#CBD5E1" stroke-width="2"/>
        <line x1="108" y1="120" x2="119" y2="120" stroke="#CBD5E1" stroke-width="2"/>
      </g>
    """ if "coat" in ppe else ""

    harness = """
      <g class="ppe-layer">
        <path d="M80 84 L116 143 M120 84 L84 143"
              stroke="#F59E0B" stroke-width="5" fill="none"/>
        <rect x="82" y="113" width="36" height="6" rx="3" fill="#F59E0B"/>
      </g>
    """ if "harness" in ppe else ""

    gloves = """
      <g class="ppe-layer">
        <circle cx="54" cy="140" r="10" fill="#FACC15" stroke="#A16207" stroke-width="2"/>
        <circle cx="146" cy="140" r="10" fill="#FACC15" stroke="#A16207" stroke-width="2"/>
      </g>
    """ if "gloves" in ppe else ""

    shoes = """
      <g class="ppe-layer">
        <path d="M75 178 H99 V190 H69 Q65 182 75 178Z"
              fill="#7C3F16" stroke="#4B260D" stroke-width="2"/>
        <path d="M101 178 H125 Q135 182 131 190 H101Z"
              fill="#7C3F16" stroke="#4B260D" stroke-width="2"/>
      </g>
    """ if "shoes" in ppe else ""

    glow = _STATE_GLOW.get(state, _STATE_GLOW["neutral"])

    return f"""
    <svg viewBox="0 0 200 205" xmlns="http://www.w3.org/2000/svg"
         role="img" aria-label="Animated PPE training worker">
      <defs>
        <radialGradient id="stateGlow" cx="50%" cy="46%" r="55%">
          <stop offset="0%" stop-color="{glow}" stop-opacity="0.32"/>
          <stop offset="100%" stop-color="{glow}" stop-opacity="0"/>
        </radialGradient>
      </defs>
      <circle cx="100" cy="100" r="98" fill="url(#stateGlow)" class="state-halo"/>
      <ellipse cx="100" cy="195" rx="48" ry="7" fill="#0F172A" fill-opacity=".10"/>
      <g class="worker-idle">
        <g class="worker-leg-left"><rect x="78" y="145" width="20" height="37" rx="8" fill="{sleeve_color}"/>
          <rect x="72" y="178" width="29" height="11" rx="5" fill="{boot_color}"/></g>
        <g class="worker-leg-right"><rect x="102" y="145" width="20" height="37" rx="8" fill="{sleeve_color}"/>
          <rect x="99" y="178" width="29" height="11" rx="5" fill="{boot_color}"/></g>
        <rect x="73" y="88" width="54" height="61" rx="15" fill="{body_color}"/>
        <rect x="52" y="92" width="18" height="55" rx="9" fill="{body_color}" transform="rotate(7 61 92)"/>
        <rect x="130" y="92" width="18" height="55" rx="9" fill="{body_color}" transform="rotate(-7 139 92)"/>
        <circle cx="54" cy="140" r="7" fill="#E8B17D"/>
        <circle cx="146" cy="140" r="7" fill="#E8B17D"/>
        <circle cx="100" cy="64" r="21" fill="#E8B17D" stroke="#7C5232" stroke-width="2"/>
        <path d="M81 57 Q100 42 119 57" fill="#263238"/>
        <g class="worker-blink">
          <ellipse cx="92" cy="63" rx="2.4" ry="2.6" fill="#1f2937"/>
          <ellipse cx="108" cy="63" rx="2.4" ry="2.6" fill="#1f2937"/>
        </g>
        <path d="M90 72 Q100 76 110 72" stroke="#7C5232" stroke-width="2" fill="none" stroke-linecap="round"/>
        {coat}{vest}{harness}{helmet}{hearing}{goggles}{shield}{respirator}{gloves}{shoes}
      </g>
    </svg>
    """


def _hazard_symbol(hazard_id: str) -> str:
    """Return a licensing-safe visual symbol for a hazard badge."""
    key = assets_manager.normalize_asset_key(hazard_id)
    if "fall" in key and "object" in key:
        return "\U0001FAA8"
    if "moving_equipment" in key or "vehicle" in key:
        return "\U0001F69C"
    if "dust" in key:
        return "\U0001F32B️"
    if "debris" in key:
        return "\U0001F4A5"
    if "noise" in key:
        return "\U0001F50A"
    if "height" in key:
        return "\U0001FA9C"
    if "sharp" in key or "glass" in key:
        return "\U0001F52A"
    if "corrosive" in key:
        return "\U0001F9EA"
    if "toxic" in key or "vapour" in key or "vapor" in key:
        return "\U00002623️"
    if "splash" in key:
        return "\U0001F4A7"
    if "flammable" in key or "solvent" in key:
        return "\U0001F525"
    if "ventilation" in key:
        return "\U0001F32C️"
    return "\U000026A0️"


def _ppe_symbol(ppe_id: str) -> str:
    """Return a licensing-safe visual symbol for a PPE card."""
    key = assets_manager.normalize_asset_key(ppe_id)
    if "helmet" in key:
        return "⛑️"
    if "goggle" in key or "eye" in key:
        return "\U0001F97D"
    if "face_shield" in key:
        return "\U0001F6E1️"
    if "respirator" in key:
        return "\U0001F637"
    if "hearing" in key:
        return "\U0001F3A7"
    if "vest" in key or "visibility" in key:
        return "\U0001F9BA"
    if "coat" in key:
        return "\U0001F97C"
    if "harness" in key or "fall_arrest" in key:
        return "\U0001FA79"
    if "glove" in key:
        return "\U0001F9E4"
    if "shoe" in key or "footwear" in key:
        return "\U0001F97E"
    return "\U0001F9F0"


# --------------------------------------------------------------------------
# Shared CSS building blocks for the self-contained scene / worker iframes
# --------------------------------------------------------------------------

_SCENE_BASE_CSS = """
html,body{margin:0;padding:0;background:transparent;font-family:'Segoe UI',Arial,sans-serif;overflow:hidden}
.scene{position:relative;height:398px;overflow:hidden;border:1px solid #cbd5e1;border-radius:20px;
  box-shadow:0 10px 26px -14px rgba(9,30,42,.38);}
.scene-title{position:absolute;top:16px;left:50%;transform:translateX(-50%);z-index:5;
  display:flex;align-items:center;gap:.4rem;padding:.32rem .85rem;border-radius:999px;
  background:rgba(15,23,42,.62);color:#fff;font-weight:700;font-size:13px;letter-spacing:.05em;
  backdrop-filter:blur(2px);}
.scene-caption{position:absolute;left:16px;right:16px;bottom:14px;z-index:5;text-align:center;
  padding:.4rem .7rem;border-radius:.6rem;background:rgba(255,255,255,.86);color:#1f2937;
  font-size:12.5px;font-weight:600;box-shadow:0 2px 8px rgba(15,23,42,.12);}
.hazard-ring{position:absolute;z-index:4;width:66px;height:66px;border-radius:50%;
  border:4px solid rgba(239,68,68,.45);animation:raca-pulse 1.7s ease-out infinite;}
.hazard-flag{position:absolute;z-index:5;transform:translate(-50%,-135%);
  padding:.16rem .5rem;border-radius:.4rem;background:#ef4444;color:#fff;font-size:10.5px;
  font-weight:800;letter-spacing:.03em;white-space:nowrap;box-shadow:0 3px 8px rgba(239,68,68,.4);}
.dust-mote{position:absolute;border-radius:50%;background:rgba(255,255,255,.55);
  animation:raca-float-up linear infinite;}
.beacon{position:absolute;border-radius:50%;filter:blur(.5px);
  animation:raca-beacon-spin 1.1s linear infinite;}
@keyframes raca-pulse{0%{transform:scale(.55);opacity:.95}100%{transform:scale(1.9);opacity:0}}
@keyframes raca-float-up{0%{transform:translateY(0) translateX(0);opacity:0}
  10%{opacity:.8}90%{opacity:.5}100%{transform:translateY(-160px) translateX(14px);opacity:0}}
@keyframes raca-beacon-spin{0%{transform:rotate(0)}100%{transform:rotate(360deg)}}
@keyframes raca-bob{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}
@keyframes raca-drift{0%{transform:translateX(-60px)}100%{transform:translateX(70px)}}
"""


def _scene_shell(
    domain_key: str,
    caption: str | None,
    body: str,
    extra_style: str,
    hazard_label: str,
    hazard_pos: tuple[str, str],
    scale: float = 1.0,
) -> str:
    """Wrap per-domain scene markup in the shared animated iframe document.

    ``scale`` shrinks the whole 398px-tall scene proportionally via a CSS
    transform (used for compact recap previews) while keeping every
    absolutely-positioned element's relative layout intact — changing the
    declared scene height directly would misalign them instead.
    """
    theme = _DOMAIN_THEMES[domain_key]
    label = _safe_text(caption or f"{theme['label'].title()} training context.")
    left, top = hazard_pos
    outer_height = round(398 * scale)
    scene_style = ""
    if abs(scale - 1.0) > 1e-6:
        scene_style = f' style="transform:scale({scale:.4f});transform-origin:top left;width:{100 / scale:.3f}%"'
    return f"""<!doctype html>
<html><head><meta charset='utf-8'><style>{_SCENE_BASE_CSS}{extra_style}
.scene-outer{{height:{outer_height}px;overflow:hidden}}
</style></head>
<body>
<div class="scene-outer"><div class="scene"{scene_style}>
  <div class="scene-title">{theme['icon']} {theme['label']}</div>
  {body}
  <div class="hazard-ring" style="left:{left};top:{top}"></div>
  <div class="hazard-flag" style="left:{left};top:{top}">{html.escape(hazard_label)}</div>
  <div class="scene-caption">{label}</div>
</div></div>
{_GSAP_TAG}
<script>
(function(){{
  function sprinkle(className, count, zoneSel){{
    try {{
      var zone = document.querySelector(zoneSel);
      if(!zone) return;
      for (var i=0;i<count;i++){{
        var el = document.createElement('div');
        el.className = className;
        el.style.left = (8 + Math.random()*84) + '%';
        el.style.animationDelay = (Math.random()*3.2) + 's';
        el.style.animationDuration = (2.4 + Math.random()*2.2) + 's';
        zone.appendChild(el);
      }}
    }} catch(e) {{}}
  }}
  sprinkle('dust-mote raca-mote', 10, '.scene');
  if (window.gsap && !window.__racaGsapFailed) {{
    try {{
      gsap.utils.toArray('.raca-gsap-sway').forEach(function(el, i){{
        gsap.to(el, {{rotation: (i % 2 ? 4 : -4), transformOrigin: 'top center',
          duration: 2.6 + (i % 3) * 0.4, yoyo: true, repeat: -1, ease: 'sine.inOut'}});
      }});
      gsap.utils.toArray('.raca-gsap-spark').forEach(function(el){{
        gsap.to(el, {{opacity: 1, scale: 1.3, duration: 0.18, repeat: -1,
          repeatDelay: 0.6 + Math.random()*0.8, yoyo: true, ease: 'power2.out'}});
      }});
    }} catch(e) {{}}
  }}
}})();
</script>
</body></html>"""


def _domain_scene_html(domain_key: str, caption: str | None, scale: float = 1.0) -> str:
    """Dispatch to the correct richly animated, licensing-safe domain scene."""
    builder = {
        "manufacturing": _scene_manufacturing,
        "chemical_laboratory": _scene_chemical_lab,
        "construction": _scene_construction,
    }.get(domain_key, _scene_manufacturing)
    return builder(caption, scale)


def _scene_manufacturing(caption: str | None, scale: float = 1.0) -> str:
    style = """
    .sky{position:absolute;inset:0 0 42% 0;background:linear-gradient(180deg,#dfe7ee 0%,#c9d6e0 100%)}
    .wall-grid{position:absolute;inset:0 0 42% 0;opacity:.5;
      background-image:repeating-linear-gradient(90deg,rgba(255,255,255,.5) 0 2px,transparent 2px 96px),
        repeating-linear-gradient(0deg,rgba(255,255,255,.35) 0 2px,transparent 2px 60px)}
    .floor{position:absolute;left:0;right:0;bottom:0;height:42%;background:linear-gradient(180deg,#e7ebef 0%,#cfd8de 100%)}
    .floor-line{position:absolute;left:4%;right:4%;bottom:36px;height:4px;background:#94a3b8;border-radius:3px}
    .safety-tape{position:absolute;left:0;right:0;bottom:0;height:10px;
      background-image:repeating-linear-gradient(135deg,#f59e0b 0 16px,#1f2937 16px 32px)}
    .rail{position:absolute;left:4%;right:4%;top:52px;height:6px;background:#64748b;border-radius:3px;box-shadow:0 2px 3px rgba(0,0,0,.15)}
    .trolley{position:absolute;top:52px;width:34px;height:14px;background:#334155;border-radius:3px;
      animation:raca-trolley 8s ease-in-out infinite}
    .hook-cable{position:absolute;top:66px;left:17px;width:2px;background:#1f2937;
      animation:raca-cable 8s ease-in-out infinite}
    .hook-load{position:absolute;top:0;left:-13px;width:28px;height:24px;background:#f59e0b;
      border:2px solid #b45309;border-radius:3px;animation:raca-cable-load 8s ease-in-out infinite}
    @keyframes raca-trolley{0%,100%{left:6%}50%{left:64%}}
    @keyframes raca-cable{0%,100%{height:26px}30%,70%{height:74px}}
    @keyframes raca-cable-load{0%,100%{top:26px}30%,70%{top:74px}}
    .conveyor{position:absolute;left:12%;bottom:96px;width:44%;height:14px;background:#475569;border-radius:8px;
      box-shadow:0 3px 4px rgba(0,0,0,.18)}
    .roller{position:absolute;bottom:-3px;width:12px;height:12px;border-radius:50%;background:#94a3b8;
      border:2px solid #334155;animation:raca-roll .9s linear infinite}
    .cbox{position:absolute;bottom:12px;width:26px;height:22px;background:#c98a3f;border:2px solid #7c4a12;
      border-radius:2px;animation:raca-conveyor-move 4.2s linear infinite}
    @keyframes raca-roll{0%{transform:rotate(0)}100%{transform:rotate(360deg)}}
    @keyframes raca-conveyor-move{0%{left:-8%;opacity:0}8%{opacity:1}92%{opacity:1}100%{left:104%;opacity:0}}
    .forklift{position:absolute;bottom:44px;width:64px;height:34px;animation:raca-forklift 9s ease-in-out infinite}
    .fk-body{position:absolute;bottom:10px;left:10px;width:44px;height:20px;background:#facc15;border:2px solid #92620a;border-radius:4px}
    .fk-cab{position:absolute;bottom:26px;left:16px;width:22px;height:14px;background:#fde68a;border:2px solid #92620a;border-radius:3px 3px 0 0}
    .fk-mast{position:absolute;bottom:6px;left:2px;width:4px;height:34px;background:#334155}
    .fk-fork{position:absolute;bottom:6px;left:0px;width:14px;height:4px;background:#334155}
    .fk-wheel{position:absolute;bottom:0;width:12px;height:12px;border-radius:50%;background:#1f2937;
      border:2px solid #64748b;animation:raca-roll .5s linear infinite}
    @keyframes raca-forklift{0%,100%{left:2%;transform:scaleX(1)}45%{left:58%;transform:scaleX(1)}
      50%{left:58%;transform:scaleX(-1)}95%{left:2%;transform:scaleX(-1)}}
    .grinder{position:absolute;right:9%;bottom:78px;width:30px;height:30px}
    .grinder-wheel{position:absolute;inset:0;border-radius:50%;border:5px solid #475569;border-top-color:#facc15;
      animation:raca-roll .35s linear infinite}
    .spark{position:absolute;width:5px;height:5px;border-radius:50%;background:#fbbf24;opacity:0;
      box-shadow:0 0 6px 1px rgba(251,191,36,.9)}
    .beacon{right:8%;top:16%;width:16px;height:16px;
      background:conic-gradient(from 0deg,#ef4444 0deg 40deg,transparent 40deg 360deg)}
    .beacon-glow{position:absolute;right:calc(8% - 10px);top:calc(16% - 10px);width:36px;height:36px;border-radius:50%;
      background:radial-gradient(circle,rgba(239,68,68,.35),transparent 70%);animation:raca-pulse 1.4s ease-out infinite}
    """
    body = """
    <div class="sky"></div><div class="wall-grid"></div><div class="floor"></div>
    <div class="floor-line"></div><div class="safety-tape"></div>
    <div class="rail"></div>
    <div class="trolley"><div class="hook-cable"><div class="hook-load"></div></div></div>
    <div class="conveyor">
      <div class="roller" style="left:2px"></div><div class="roller" style="left:34%"></div>
      <div class="roller" style="left:64%"></div><div class="roller" style="right:2px"></div>
      <div class="cbox" style="animation-delay:0s"></div>
      <div class="cbox" style="animation-delay:-1.4s"></div>
      <div class="cbox" style="animation-delay:-2.8s"></div>
    </div>
    <div class="forklift">
      <div class="fk-mast"></div><div class="fk-fork"></div><div class="fk-cab"></div><div class="fk-body"></div>
      <div class="fk-wheel" style="left:14px"></div><div class="fk-wheel" style="left:40px"></div>
    </div>
    <div class="grinder"><div class="grinder-wheel"></div>
      <div class="spark raca-gsap-spark" style="left:26px;top:6px;animation:raca-pulse 1.1s ease-out infinite"></div>
      <div class="spark raca-gsap-spark" style="left:4px;top:18px;animation:raca-pulse 1.3s ease-out .3s infinite"></div>
      <div class="spark raca-gsap-spark" style="left:20px;top:24px;animation:raca-pulse 1s ease-out .6s infinite"></div>
    </div>
    <div class="beacon-glow"></div><div class="beacon"></div>
    """
    return _scene_shell("manufacturing", caption, body, style, "Moving equipment", ("60%", "55%"), scale)


def _scene_chemical_lab(caption: str | None, scale: float = 1.0) -> str:
    style = """
    .lab-wall{position:absolute;inset:0 0 38% 0;background:linear-gradient(180deg,#eaf6f5 0%,#d9efec 100%)}
    .tiles{position:absolute;inset:0 0 38% 0;opacity:.5;
      background-image:repeating-linear-gradient(90deg,rgba(255,255,255,.6) 0 2px,transparent 2px 40px),
        repeating-linear-gradient(0deg,rgba(255,255,255,.4) 0 2px,transparent 2px 40px)}
    .bench{position:absolute;left:0;right:0;bottom:0;height:38%;background:linear-gradient(180deg,#e7ece9 0%,#c9d6d2 100%)}
    .bench-edge{position:absolute;left:0;right:0;bottom:calc(38% - 6px);height:6px;background:#64748b}
    .hood{position:absolute;right:6%;bottom:38%;width:120px;height:150px;background:rgba(219,234,254,.35);
      border:2px solid #60a5fa;border-radius:6px 6px 0 0}
    .hood-sash{position:absolute;left:6px;right:6px;top:14px;height:5px;background:#1d4ed8;border-radius:3px}
    .hood-flow{position:absolute;width:3px;height:26px;background:linear-gradient(180deg,rgba(96,165,250,.05),rgba(96,165,250,.5));
      border-radius:2px;animation:raca-hoodflow 2.4s linear infinite}
    @keyframes raca-hoodflow{0%{transform:translateY(20px);opacity:0}30%{opacity:.8}100%{transform:translateY(-90px);opacity:0}}
    .stand{position:absolute;left:14%;bottom:38%;width:4px;height:120px;background:#94a3b8}
    .stand-base{position:absolute;left:calc(14% - 20px);bottom:calc(38% - 4px);width:46px;height:6px;background:#64748b;border-radius:2px}
    .burette{position:absolute;left:calc(14% - 2px);bottom:calc(38% + 60px);width:6px;height:52px;background:rgba(20,184,166,.55);
      border:1px solid #0f766e;border-radius:2px}
    .drop{position:absolute;left:calc(14% + 1px);bottom:calc(38% + 4px);width:4px;height:6px;border-radius:50% 50% 50% 0;
      background:#14b8a6;transform:rotate(45deg);animation:raca-drop 1.8s ease-in infinite}
    @keyframes raca-drop{0%{transform:translateY(0) rotate(45deg);opacity:0}
      10%{opacity:1}90%{transform:translateY(46px) rotate(45deg);opacity:1}100%{transform:translateY(50px) rotate(45deg);opacity:0}}
    .beaker{position:absolute;left:calc(14% - 11px);bottom:38%;width:26px;height:20px;border:2px solid #64748b;
      border-top:none;border-radius:0 0 6px 6px;background:rgba(148,163,184,.25)}
    .flask-wrap{position:absolute;left:38%;bottom:38%;width:70px;height:96px;animation:raca-bob 3.2s ease-in-out infinite}
    .flask-neck{position:absolute;left:29px;bottom:78px;width:12px;height:20px;background:rgba(226,232,240,.55);border:2px solid #94a3b8;border-bottom:none}
    .flask-body{position:absolute;left:6px;bottom:16px;width:58px;height:62px;border-radius:0 0 30px 30px;
      background:rgba(226,232,240,.35);border:2px solid #94a3b8;overflow:hidden}
    .flask-liquid{position:absolute;left:-2px;right:-2px;bottom:-2px;height:60%;
      background:linear-gradient(180deg,#5eead4,#0d9488);animation:raca-liquid 4s ease-in-out infinite}
    @keyframes raca-liquid{0%,100%{height:55%}50%{height:62%}}
    .bubble{position:absolute;width:6px;height:6px;border-radius:50%;background:rgba(255,255,255,.85);
      animation:raca-bubble 2.2s ease-in infinite}
    @keyframes raca-bubble{0%{transform:translateY(0) scale(.4);opacity:0}20%{opacity:.9}
      100%{transform:translateY(-46px) scale(1);opacity:0}}
    .stirrer{position:absolute;left:16px;bottom:38%;width:46px;height:10px;background:#1f2937;border-radius:3px}
    .stir-glow{position:absolute;left:12px;bottom:calc(38% - 4px);width:54px;height:14px;border-radius:50%;
      background:radial-gradient(ellipse,rgba(249,115,22,.5),transparent 70%);animation:raca-pulse 1.6s ease-out infinite}
    .vapor{position:absolute;left:52%;bottom:calc(38% + 88px);width:20px;height:26px;border-radius:50%;
      background:radial-gradient(circle,rgba(255,255,255,.75),rgba(255,255,255,0) 70%);
      animation:raca-vapor 3.4s ease-out infinite}
    @keyframes raca-vapor{0%{transform:translate(0,0) scale(.5);opacity:0}
      15%{opacity:.85}100%{transform:translate(18px,-92px) scale(1.6);opacity:0}}
    .eyewash{position:absolute;left:2%;bottom:calc(38% + 40px);width:20px;height:26px;background:#e2e8f0;
      border:2px solid #64748b;border-radius:4px}
    .eyewash-led{position:absolute;left:2%;bottom:calc(38% + 62px);width:6px;height:6px;border-radius:50%;
      background:#22c55e;animation:raca-led 1.4s ease-in-out infinite}
    @keyframes raca-led{0%,100%{opacity:1;box-shadow:0 0 4px 1px #22c55e}50%{opacity:.35;box-shadow:none}}
    """
    body = """
    <div class="lab-wall"></div><div class="tiles"></div><div class="bench"></div><div class="bench-edge"></div>
    <div class="hood"><div class="hood-sash"></div>
      <div class="hood-flow" style="left:24px;animation-delay:0s"></div>
      <div class="hood-flow" style="left:56px;animation-delay:.8s"></div>
      <div class="hood-flow" style="left:88px;animation-delay:1.6s"></div>
    </div>
    <div class="eyewash"></div><div class="eyewash-led"></div>
    <div class="stand-base"></div><div class="stand"></div><div class="burette"></div>
    <div class="drop"></div><div class="beaker"></div>
    <div class="flask-wrap raca-gsap-sway">
      <div class="flask-neck"></div>
      <div class="flask-body">
        <div class="flask-liquid"></div>
        <div class="bubble" style="left:14px;bottom:8px;animation-delay:0s"></div>
        <div class="bubble" style="left:30px;bottom:4px;animation-delay:.7s"></div>
        <div class="bubble" style="left:42px;bottom:10px;animation-delay:1.3s"></div>
      </div>
    </div>
    <div class="stirrer"></div><div class="stir-glow"></div>
    <div class="vapor" style="animation-delay:0s"></div>
    <div class="vapor" style="animation-delay:1.1s;left:56%"></div>
    <div class="vapor" style="animation-delay:2.2s;left:49%"></div>
    """
    return _scene_shell("chemical_laboratory", caption, body, style, "Chemical exposure", ("47%", "48%"), scale)


def _scene_construction(caption: str | None, scale: float = 1.0) -> str:
    style = """
    .sky{position:absolute;inset:0 0 34% 0;background:linear-gradient(180deg,#dbeeff 0%,#eaf4ff 100%)}
    .cloud{position:absolute;width:70px;height:18px;background:rgba(255,255,255,.85);border-radius:30px}
    .cloud::before,.cloud::after{content:"";position:absolute;background:inherit;border-radius:50%}
    .cloud::before{width:26px;height:26px;left:10px;top:-11px}.cloud::after{width:32px;height:32px;right:8px;top:-15px}
    .c1{left:10%;top:14%;animation:raca-drift 16s linear infinite}
    .c2{left:52%;top:9%;animation:raca-drift 21s linear infinite reverse}
    .ground{position:absolute;left:0;right:0;bottom:0;height:34%;background:linear-gradient(180deg,#e4d2b4 0%,#cdb488 100%)}
    .frame{position:absolute;left:8%;bottom:34%;width:180px;height:180px}
    .beam{position:absolute;background:#94a3b8}
    .caution{position:absolute;left:0;right:0;bottom:8px;height:9px;
      background-image:repeating-linear-gradient(135deg,#f59e0b 0 16px,#1f2937 16px 32px);
      animation:raca-tape-wave 3.4s ease-in-out infinite}
    @keyframes raca-tape-wave{0%,100%{transform:skewY(0)}50%{transform:skewY(.35deg)}}
    .mast{position:absolute;right:22%;bottom:34%;width:8px;height:190px;background:#475569;border-radius:2px}
    .jib{position:absolute;right:calc(22% - 4px);bottom:216px;width:150px;height:6px;background:#334155;border-radius:3px;
      transform-origin:8px 3px;animation:raca-jib 5.6s ease-in-out infinite}
    .counterjib{position:absolute;right:calc(22% + 46px);bottom:216px;width:44px;height:6px;background:#1f2937;border-radius:3px;
      transform-origin:right center;animation:raca-jib 5.6s ease-in-out infinite}
    @keyframes raca-jib{0%,100%{transform:rotate(-7deg)}50%{transform:rotate(7deg)}}
    .cable{position:absolute;right:16.6%;top:222px;width:2px;height:58px;background:#1f2937;
      transform-origin:top center;animation:raca-swing 5.6s ease-in-out infinite}
    .load{position:absolute;top:56px;left:-13px;width:28px;height:22px;background:#f59e0b;border:2px solid #b45309;border-radius:3px}
    @keyframes raca-swing{0%,100%{transform:rotate(-6deg)}50%{transform:rotate(6deg)}}
    .scaffold{position:absolute;left:36%;bottom:34%;width:96px;height:150px;opacity:.85}
    .bar{position:absolute;background:#64748b}
    .dumptruck{position:absolute;bottom:26px;width:60px;height:30px;animation:raca-truck 8.5s linear infinite}
    .dt-body{position:absolute;bottom:8px;left:0;width:44px;height:18px;background:#fb923c;border:2px solid #9a3412;border-radius:3px}
    .dt-cab{position:absolute;bottom:8px;left:44px;width:16px;height:20px;background:#fdba74;border:2px solid #9a3412;border-radius:3px}
    .dt-wheel{position:absolute;bottom:0;width:11px;height:11px;border-radius:50%;background:#1f2937;border:2px solid #64748b;
      animation:raca-roll .5s linear infinite}
    @keyframes raca-truck{0%{left:-10%}100%{left:104%}}
    .drill{position:absolute;left:60%;bottom:40px;width:10px;height:34px;background:#334155;border-radius:2px;
      animation:raca-jitter .12s linear infinite}
    @keyframes raca-jitter{0%,100%{transform:translateX(0)}50%{transform:translateX(1.4px)}}
    .puff{position:absolute;width:14px;height:14px;border-radius:50%;background:rgba(180,142,94,.6);
      animation:raca-puff 1.6s ease-out infinite}
    @keyframes raca-puff{0%{transform:translateY(0) scale(.4);opacity:0}20%{opacity:.75}
      100%{transform:translateY(-38px) scale(1.5);opacity:0}}
    """
    body = """
    <div class="sky"></div><div class="cloud c1"></div><div class="cloud c2"></div><div class="ground"></div>
    <div class="scaffold">
      <div class="bar" style="left:0;top:0;width:4px;height:150px"></div>
      <div class="bar" style="right:0;top:0;width:4px;height:150px"></div>
      <div class="bar" style="left:0;top:20px;width:96px;height:4px"></div>
      <div class="bar" style="left:0;top:75px;width:96px;height:4px"></div>
      <div class="bar" style="left:0;top:130px;width:96px;height:4px"></div>
    </div>
    <div class="mast"></div>
    <div class="jib"><div class="cable"><div class="load"></div></div></div>
    <div class="counterjib"></div>
    <div class="dumptruck">
      <div class="dt-body"></div><div class="dt-cab"></div>
      <div class="dt-wheel" style="left:8px"></div><div class="dt-wheel" style="left:30px"></div>
    </div>
    <div class="drill"></div>
    <div class="puff" style="left:59%;bottom:70px;animation-delay:0s"></div>
    <div class="puff" style="left:62%;bottom:70px;animation-delay:.5s"></div>
    <div class="puff" style="left:57%;bottom:70px;animation-delay:1s"></div>
    <div class="caution"></div>
    """
    return _scene_shell("construction", caption, body, style, "Work at height", ("18%", "40%"), scale)


def render_dynamic_ppe_worker(
    character_path: str | Path | None,
    selected_ppe: list[str],
    domain: str | None = None,
    state: str | None = None,
) -> None:
    """Render an animated SVG worker with selected PPE visibly attached.

    ``domain`` selects the illustrated uniform archetype (manufacturing
    coverall, laboratory coat, or hi-vis construction gear); ``state``
    (``"safe"``/``"warning"``/``"neutral"``) drives a soft presentation-only
    colour halo that echoes the evaluated decision without altering it.
    """
    domain_key = domain if domain in _DOMAIN_THEMES else _resolve_domain_key(domain, "")
    state_key = state if state in _STATE_GLOW else "neutral"
    selected_label = ", ".join(_label(item) for item in selected_ppe) or "No PPE selected"
    worker_html = f"""<!doctype html>
<html><head><meta charset='utf-8'><style>
html,body{{margin:0;padding:0;background:transparent;font-family:Arial,sans-serif;overflow:hidden}}
.card{{height:398px;border-radius:20px;padding:10px 8px 0;
  background:linear-gradient(180deg,#e6f3fa 0 68%,#f8fafc 68%);border:1px solid #cbd5e1;position:relative;
  overflow:hidden;box-shadow:0 10px 26px -14px rgba(9,30,42,.38)}}
.card:before{{content:"";position:absolute;left:-10%;right:-10%;bottom:27%;height:4px;background:#94a3b8;box-shadow:0 17px 0 #cbd5e1}}
.stage{{position:relative;z-index:2;max-width:230px;margin:8px auto 0}}.stage svg{{display:block;width:100%;height:auto}}
.worker-idle{{transform-origin:100px 190px;animation:idle 2.1s ease-in-out infinite}}
.ppe-layer{{animation:attach .26s cubic-bezier(.22,.8,.32,1) both}}
.worker-blink{{animation:blink 4.6s ease-in-out infinite}}
.worker-leg-left{{transform-origin:88px 145px;animation:step 2.1s ease-in-out infinite}}
.worker-leg-right{{transform-origin:112px 145px;animation:step 2.1s ease-in-out infinite reverse}}
.state-halo{{animation:halo-breathe 2.6s ease-in-out infinite}}
.label{{position:absolute;z-index:3;left:8px;right:8px;bottom:12px;text-align:center;font-size:12px;color:#334155;
  background:rgba(255,255,255,.82);padding:5px 7px;border-radius:8px;font-weight:600}}
@keyframes idle{{0%,100%{{transform:translateY(0) rotate(0)}}50%{{transform:translateY(-5px) rotate(.5deg)}}}}
@keyframes step{{0%,100%{{transform:rotate(0)}}50%{{transform:rotate(2.4deg)}}}}
@keyframes blink{{0%,92%,100%{{transform:scaleY(1)}}95%{{transform:scaleY(.12)}}}}
@keyframes halo-breathe{{0%,100%{{opacity:.65}}50%{{opacity:1}}}}
@keyframes attach{{from{{opacity:0;transform:scale(.72) translateY(-6px)}}to{{opacity:1;transform:scale(1) translateY(0)}}}}
</style></head><body>
<div class='card'><div class='stage'>{_animated_worker_svg(selected_ppe, domain_key, state_key)}</div>
<div class='label'><b>Selected PPE:</b> {_safe_text(selected_label)}</div></div>
{_GSAP_TAG}
</body></html>"""
    components.html(worker_html, height=400, scrolling=False)


def render_domain_scene_preview(domain: str, caption: str | None = None, height: int = 260) -> None:
    """Render the same animated domain scene used on the Serious Game page.

    Reused on the Training Dashboard's "Most Recent Scenario" recap so it
    shows a genuine illustrated, moving scene instead of the raw generator-
    stamped placeholder background PNG. ``height`` should stay well below
    the Serious Game page's own 410px so the recap reads as a compact echo
    rather than a second full gameplay scene.
    """
    domain_key = _resolve_domain_key(domain, "")
    doc = _domain_scene_html(domain_key, caption, scale=height / 398)
    components.html(doc, height=height, scrolling=False)


def render_scenario_chip(domain: str, title: str, caption: str | None = None) -> None:
    """Render a compact, non-animated scenario chip (icon + title + caption).

    Used where a full animated scene per row would be wasteful — e.g. once
    per episode in a potentially long Decision Trace list — while still
    replacing the raw placeholder background PNG with a clean presentation.
    """
    domain_key = _resolve_domain_key(domain, "")
    theme = _DOMAIN_THEMES.get(domain_key, _DOMAIN_THEMES["manufacturing"])
    caption_html = f'<div class="raca-scene-chip-caption">{_safe_text(caption)}</div>' if caption else ""
    st.markdown(
        '<div class="raca-scene-chip">'
        f'<div class="raca-scene-chip-icon">{theme["icon"]}</div>'
        '<div>'
        f'<div class="raca-scene-chip-title">{_safe_text(title)}</div>'
        f'{caption_html}'
        "</div></div>",
        unsafe_allow_html=True,
    )


def render_risk_badge_chip(risk_category: str | None) -> None:
    """Render a compact colour-coded risk chip in place of the placeholder badge image."""
    category = assets_manager.normalize_asset_key(str(risk_category or ""))
    class_map = {"low": "risk-low", "medium": "risk-medium", "high": "risk-high", "critical": "risk-critical"}
    symbol_map = {"low": "✅", "medium": "⚠️", "high": "\U0001F7E0", "critical": "\U0001F534"}
    css_class = class_map.get(category, "status-badge")
    symbol = symbol_map.get(category, "ℹ️")
    label = _label(risk_category) if risk_category else "Not available"
    st.markdown(f'<span class="{css_class} raca-risk-chip">{symbol} {label} risk</span>', unsafe_allow_html=True)


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
        severity_key = assets_manager.normalize_asset_key(str(metadata or ""))
        severity_class = {
            "critical": "hazard-sev-critical",
            "high": "hazard-sev-high",
            "medium": "hazard-sev-medium",
            "low": "hazard-sev-low",
        }.get(severity_key, "")
        icon = assets_manager.get_hazard_icon(hazard_id)
        # Every shipped hazard icon asset is currently generator-stamped
        # development artwork, so hazard badges always use a clean, custom
        # vector/emoji symbol rather than that placeholder art. A hazard id
        # that fails to resolve to *any* known icon (parent dir is the
        # shared placeholders/ folder) is flagged separately below.
        unmapped, category, asset_name = _placeholder_details(icon)
        icon_inner = f'<span>{_hazard_symbol(hazard_id)}</span>'
        meta_line = f'<div class="hazard-badge-meta">Severity / risk: {_safe_text(metadata, "Not specified")}</div>' if metadata is not None else ""
        with columns[index % len(columns)]:
            st.markdown(
                f'<div class="hazard-badge {severity_class}">'
                f'<div class="hazard-badge-icon is-symbol">{icon_inner}</div>'
                f'<div class="hazard-badge-name">{_safe_text(name)}</div>'
                f'{meta_line}'
                '</div>',
                unsafe_allow_html=True,
            )
            if unmapped:
                st.caption("Unmapped hazard identifier — built-in fallback symbol shown.")


def _risk_gauge_html(category: str, percentage: float | None) -> str:
    """Small self-contained animated radial risk gauge (decorative only)."""
    colors = {
        "low": "#0e7a4d",
        "medium": "#b8790f",
        "high": "#c2500f",
        "critical": "#b6323f",
        "unknown": "#64748b",
    }
    color = colors.get(category, colors["unknown"])
    target = 0 if percentage is None else max(0.0, min(100.0, percentage))
    circumference = 2 * 3.14159265 * 42
    offset = circumference * (1 - target / 100.0)
    symbol = {"low": "✅", "medium": "⚠️", "high": "\U0001F7E0", "critical": "\U0001F534"}.get(category, "ℹ️")
    display_value = "N/A" if percentage is None else f"{target:.0f}%"
    return f"""<!doctype html>
<html><head><meta charset='utf-8'><style>
html,body{{margin:0;padding:0;background:transparent;overflow:hidden;font-family:Arial,sans-serif}}
.wrap{{display:flex;align-items:center;justify-content:center;height:112px}}
svg{{transform:rotate(-90deg)}}
.track{{fill:none;stroke:#e6edf0;stroke-width:9}}
.fill{{fill:none;stroke:{color};stroke-width:9;stroke-linecap:round;
  stroke-dasharray:{circumference:.2f};stroke-dashoffset:{circumference:.2f};
  animation:raca-gauge-fill 1.1s cubic-bezier(.22,.8,.32,1) forwards .1s}}
@keyframes raca-gauge-fill{{to{{stroke-dashoffset:{offset:.2f}}}}}
.center{{position:absolute;display:flex;flex-direction:column;align-items:center;font-family:Arial,sans-serif}}
.emoji{{font-size:19px;line-height:1}}
.pct{{font-size:15px;font-weight:800;color:#0f2233;margin-top:1px}}
.holder{{position:relative;width:104px;height:104px;display:flex;align-items:center;justify-content:center}}
</style></head><body>
<div class="wrap"><div class="holder">
<svg width="104" height="104" viewBox="0 0 104 104">
  <circle class="track" cx="52" cy="52" r="42"/>
  <circle class="fill" cx="52" cy="52" r="42"/>
</svg>
<div class="center"><div class="emoji">{symbol}</div><div class="pct">{display_value}</div></div>
</div></div>
</body></html>"""


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
            components.html(_risk_gauge_html(model["category"], model["percentage"]), height=116, scrolling=False)
        with detail_column:
            if model["score"] is None:
                st.write("Risk score: Not available")
                st.progress(0.0, text="Awaiting risk assessment")
            else:
                st.metric("Normalized risk", f'{model["percentage"]:.1f}%')
                st.progress(model["score"], text=f'{model["category"].title()} risk')
            category_class = {
                "low": "risk-low", "medium": "risk-medium", "high": "risk-high", "critical": "risk-critical",
            }.get(model["category"])
            if category_class:
                st.markdown(
                    f'<span class="{category_class}">{model["category"].title()} risk category</span>',
                    unsafe_allow_html=True,
                )
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
        widget_key = _stable_widget_key(key_prefix, ppe_id, index)
        # Session state already reflects the widget's latest value before it
        # is (re)declared this run, so the icon frame can react live to the
        # user's most recent click without waiting for a second rerun.
        is_checked_now = bool(st.session_state.get(widget_key, ppe_id in previously_selected))
        with columns[index % len(columns)]:
            with st.container(border=True):
                # Every shipped PPE icon asset is currently generator-stamped
                # development artwork, so PPE cards always use a clean, custom
                # vector/emoji symbol instead. A PPE id that fails to resolve
                # to *any* known icon is flagged separately below.
                unmapped, category, asset_name = _placeholder_details(icon)
                frame_state = " is-selected" if is_checked_now else ""
                st.markdown(
                    f'<div class="ppe-icon-frame is-symbol{frame_state}">{_ppe_symbol(ppe_id)}</div>',
                    unsafe_allow_html=True,
                )
                checked = st.checkbox(
                    label,
                    value=ppe_id in previously_selected,
                    key=widget_key,
                    help=description,
                )
                st.caption(description)
                chip_class = "selected" if checked else "unselected"
                chip_text = "Selected" if checked else "Not selected"
                st.markdown(
                    f'<span class="ppe-status-chip {chip_class}">{chip_text}</span>',
                    unsafe_allow_html=True,
                )
                if checked:
                    selected.append(ppe_id)
                if unmapped:
                    st.caption("Unmapped PPE identifier — built-in fallback symbol shown.")
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
    tiles = [
        ("\U0001F3AF Episode", f"{episode} / {max_episodes}"),
        ("\U0001F4CA Current score", "—" if score is None else f"{score * 100:.1f}%"),
        ("\U0001F39A️ Difficulty", str(difficulty) if difficulty is not None else "—"),
        ("\U0001FA79 Assistance", _label(assistance_mode)),
    ]
    tiles_html = "".join(
        f'<div class="raca-status-tile"><span class="raca-status-label">{label}</span>'
        f'<span class="raca-status-value">{_safe_text(value)}</span></div>'
        for label, value in tiles
    )
    st.markdown(f'<div class="raca-status-bar">{tiles_html}</div>', unsafe_allow_html=True)


def render_placeholder_notice(asset_category: str, asset_name: str) -> None:
    """Show a concise notice that development fallback artwork is displayed."""
    category = _label(asset_category)
    name = _label(asset_name)
    st.caption(f"Development placeholder in use — {category}: {name}.")
