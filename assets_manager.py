"""Safe, Streamlit-independent resolution of RACA PPE visual assets."""
from __future__ import annotations

import json
import logging
import re
from collections import Counter
from pathlib import Path
from typing import Final


LOGGER = logging.getLogger(__name__)

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parent
ASSETS_ROOT: Final[Path] = PROJECT_ROOT / "assets"
CHARACTERS_DIR: Final[Path] = ASSETS_ROOT / "characters"
BACKGROUNDS_DIR: Final[Path] = ASSETS_ROOT / "backgrounds"
PPE_ICONS_DIR: Final[Path] = ASSETS_ROOT / "ppe_icons"
HAZARD_ICONS_DIR: Final[Path] = ASSETS_ROOT / "hazard_icons"
BADGES_DIR: Final[Path] = ASSETS_ROOT / "badges"
PLACEHOLDERS_DIR: Final[Path] = ASSETS_ROOT / "placeholders"

ALLOWED_EXTENSIONS: Final[frozenset[str]] = frozenset({".png", ".jpg", ".jpeg", ".webp"})

CATEGORY_DIRECTORIES: Final[dict[str, Path]] = {
    "character": CHARACTERS_DIR,
    "background": BACKGROUNDS_DIR,
    "ppe": PPE_ICONS_DIR,
    "hazard": HAZARD_ICONS_DIR,
    "badge": BADGES_DIR,
}

CATEGORY_FALLBACKS: Final[dict[str, tuple[Path, str]]] = {
    "character": (PLACEHOLDERS_DIR, "missing_character"),
    "background": (PLACEHOLDERS_DIR, "missing_background"),
    "ppe": (PLACEHOLDERS_DIR, "missing_ppe_icon"),
    "hazard": (PLACEHOLDERS_DIR, "missing_hazard_icon"),
    # No separate missing-badge artwork exists in the approved catalog.
    "badge": (BADGES_DIR, "risk_medium"),
}

PPE_ICON_ALIASES: Final[dict[str, str]] = {
    "helmet": "helmet",
    "safety_helmet": "helmet",
    "goggles": "safety_goggles",
    "safety_goggles": "safety_goggles",
    "laboratory_goggles": "safety_goggles",
    "face_shield": "face_shield",
    "respirator": "respirator",
    "dust_respirator": "dust_mask",
    "dust_mask": "dust_mask",
    "gloves": "work_gloves",
    "work_gloves": "work_gloves",
    "chemical_gloves": "chemical_gloves",
    "vest": "safety_vest",
    "safety_vest": "safety_vest",
    "high_visibility_vest": "safety_vest",
    "lab_coat": "laboratory_coat",
    "laboratory_coat": "laboratory_coat",
    "shoes": "safety_footwear",
    "boots": "safety_footwear",
    "safety_shoes": "safety_footwear",
    "safety_footwear": "safety_footwear",
    "closed_safety_footwear": "safety_footwear",
    "hearing_protection": "hearing_protection",
    "fall_arrest_system": "fall_arrest_system",
}

HAZARD_ICON_ALIASES: Final[dict[str, str]] = {
    "falling_object": "falling_object",
    "moving_equipment": "moving_equipment",
    "moving_vehicle": "moving_equipment",
    "airborne_dust": "airborne_dust",
    "flying_debris": "flying_debris",
    "flying_fragment": "flying_debris",
    "excessive_noise": "excessive_noise",
    "work_at_height": "work_at_height",
    "sharp_material": "sharp_material",
    "sharp_surface": "sharp_material",
    "corrosive_liquid": "corrosive_liquid",
    "toxic_vapour": "toxic_vapour",
    "toxic_vapor": "toxic_vapour",
    "chemical_vapour": "toxic_vapour",
    "chemical_vapor": "toxic_vapour",
    "chemical_splash": "chemical_splash",
    "liquid_chemical_splash": "chemical_splash",
    "broken_glass": "broken_glass",
    "flammable_solvent": "flammable_solvent",
    "inadequate_ventilation": "inadequate_ventilation",
}


def normalize_asset_key(value: str) -> str:
    """Return a lowercase snake-case key containing only safe characters."""
    normalized = str(value).strip().lower().replace("-", " ")
    normalized = re.sub(r"\s+", "_", normalized)
    normalized = re.sub(r"[^a-z0-9_]", "", normalized)
    return re.sub(r"_+", "_", normalized).strip("_")


def _reject_unsafe_key(value: str) -> None:
    """Reject values that attempt to address paths rather than asset keys."""
    raw = str(value).strip()
    if not raw or Path(raw).is_absolute() or ".." in raw or "/" in raw or "\\" in raw or ":" in raw:
        raise ValueError(f"Unsafe asset key: {value!r}")


def _candidate(directory: Path, key: str) -> Path | None:
    """Return the first existing supported image for a normalized key."""
    supplied_suffix = Path(key).suffix.lower()
    if supplied_suffix:
        if supplied_suffix not in ALLOWED_EXTENSIONS:
            return None
        candidates = (directory / key,)
    else:
        candidates = tuple(directory / f"{key}{suffix}" for suffix in (".png", ".jpg", ".jpeg", ".webp"))
    for path in candidates:
        try:
            path.resolve().relative_to(directory.resolve())
        except ValueError as exc:
            raise ValueError(f"Asset path escapes category directory: {key!r}") from exc
        if image_exists(path):
            return path
    return None


def resolve_asset_path(category: str, asset_key: str, fallback_key: str | None = None) -> Path:
    """Resolve an image key, returning the category fallback when it is missing."""
    category_key = normalize_asset_key(category)
    if category_key not in CATEGORY_DIRECTORIES:
        raise ValueError(f"Invalid asset category: {category!r}")
    _reject_unsafe_key(asset_key)
    key = normalize_asset_key(asset_key)
    path = _candidate(CATEGORY_DIRECTORIES[category_key], key)
    if path is not None:
        return path

    if fallback_key is not None:
        _reject_unsafe_key(fallback_key)
        fallback = _candidate(CATEGORY_DIRECTORIES[category_key], normalize_asset_key(fallback_key))
        if fallback is not None:
            LOGGER.warning("Missing %s asset %r; using %s", category_key, asset_key, fallback.name)
            return fallback

    fallback_dir, default_key = CATEGORY_FALLBACKS[category_key]
    fallback = _candidate(fallback_dir, default_key)
    if fallback is None:
        # The catalog verifier will report this installation defect. Returning the
        # expected path still lets callers display a controlled UI-level warning.
        fallback = fallback_dir / f"{default_key}.png"
    LOGGER.warning("Missing %s asset %r; using %s", category_key, asset_key, fallback.name)
    return fallback


def get_domain_character(domain: str, state: str = "neutral") -> Path:
    """Resolve a domain character and state, or the character placeholder."""
    from scenario_visual_map import DOMAIN_VISUAL_CONFIG

    domain_key = normalize_asset_key(domain)
    state_key = normalize_asset_key(state)
    if state_key not in {"neutral", "safe", "warning"}:
        state_key = "neutral"
    config = DOMAIN_VISUAL_CONFIG.get(domain_key)
    if config is None:
        return resolve_asset_path("character", "unknown_character")
    return resolve_asset_path("character", str(config[f"{state_key}_character"]))


def get_scenario_background(
    domain: str,
    scenario_id: str | None = None,
    scenario_name: str | None = None,
) -> Path:
    """Resolve a scenario background, then domain default, then placeholder."""
    from scenario_visual_map import get_scenario_visual_config

    config = get_scenario_visual_config(domain, scenario_id, scenario_name)
    return PROJECT_ROOT / str(config["background"])


def get_ppe_icon(ppe_id: str) -> Path:
    """Resolve a PPE identifier or alias to its icon."""
    key = normalize_asset_key(ppe_id)
    return resolve_asset_path("ppe", PPE_ICON_ALIASES.get(key, "unknown_ppe"))


def get_hazard_icon(hazard_id: str) -> Path:
    """Resolve a hazard identifier or alias to its icon."""
    key = normalize_asset_key(hazard_id)
    return resolve_asset_path("hazard", HAZARD_ICON_ALIASES.get(key, "unknown_hazard"))


def get_risk_badge(risk_category: str) -> Path:
    """Resolve a low, medium, high, or critical risk badge."""
    key = normalize_asset_key(risk_category)
    if key not in {"low", "medium", "high", "critical"}:
        key = "medium"
    return resolve_asset_path("badge", f"risk_{key}", fallback_key="risk_medium")


def image_exists(path: Path) -> bool:
    """Return whether a path is a non-empty image with a valid file signature."""
    candidate = Path(path)
    try:
        return (
            candidate.suffix.lower() in ALLOWED_EXTENSIONS
            and candidate.is_file()
            and candidate.stat().st_size > 0
            and _header_is_valid(candidate)
        )
    except OSError:
        return False


def _relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def _header_is_valid(path: Path) -> bool:
    """Validate common image signatures without adding a runtime dependency."""
    try:
        with path.open("rb") as image_file:
            header = image_file.read(12)
    except OSError:
        return False
    suffix = path.suffix.lower()
    if suffix == ".png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")
    if suffix in {".jpg", ".jpeg"}:
        return header.startswith(b"\xff\xd8\xff")
    return header.startswith(b"RIFF") and header[8:12] == b"WEBP"


def build_asset_manifest() -> dict[str, object]:
    """Build a deterministic, JSON-serializable catalog of installed assets."""
    assets: list[dict[str, object]] = []
    directories = {
        **CATEGORY_DIRECTORIES,
        "placeholder": PLACEHOLDERS_DIR,
    }
    for category, directory in directories.items():
        if not directory.is_dir():
            continue
        for path in sorted(directory.iterdir(), key=lambda item: item.name.lower()):
            if not path.is_file() or path.suffix.lower() not in ALLOWED_EXTENSIONS:
                continue
            assets.append(
                {
                    "category": category,
                    "key": normalize_asset_key(path.stem),
                    "filename": path.name,
                    "path": _relative(path),
                    "extension": path.suffix.lower(),
                    "size_bytes": path.stat().st_size,
                    "valid": image_exists(path),
                }
            )
    manifest: dict[str, object] = {"assets_root": "assets", "assets": assets}
    # Assert the public contract during development without changing the return.
    json.dumps(manifest)
    return manifest


def validate_asset_catalog() -> dict[str, object]:
    """Report catalog validity, missing mapped assets, and key collisions."""
    manifest = build_asset_manifest()
    assets = manifest["assets"]
    assert isinstance(assets, list)
    invalid = [item["path"] for item in assets if not item["valid"]]

    expected: set[Path] = {
        PLACEHOLDERS_DIR / "missing_character.png",
        PLACEHOLDERS_DIR / "missing_background.png",
        PLACEHOLDERS_DIR / "missing_ppe_icon.png",
        PLACEHOLDERS_DIR / "missing_hazard_icon.png",
    }
    from scenario_visual_map import DOMAIN_VISUAL_CONFIG, SCENARIO_VISUAL_CONFIG

    expected.update(
        CHARACTERS_DIR / f"{config[f'{state}_character']}.png"
        for config in DOMAIN_VISUAL_CONFIG.values()
        for state in ("neutral", "safe", "warning")
    )
    expected.update(BACKGROUNDS_DIR / f"{config['default_background']}.png" for config in DOMAIN_VISUAL_CONFIG.values())
    expected.update(
        BACKGROUNDS_DIR / f"{scene['background_key']}.png"
        for scenarios in SCENARIO_VISUAL_CONFIG.values()
        for scene in scenarios.values()
    )
    expected.update(PPE_ICONS_DIR / f"{stem}.png" for stem in PPE_ICON_ALIASES.values())
    expected.update(HAZARD_ICONS_DIR / f"{stem}.png" for stem in HAZARD_ICON_ALIASES.values())
    expected.update(BADGES_DIR / f"risk_{level}.png" for level in ("low", "medium", "high", "critical"))
    missing = sorted(_relative(path) for path in expected if not image_exists(path))

    pairs = [(str(item["category"]), str(item["key"])) for item in assets]
    counts = Counter(pairs)
    duplicates = [f"{category}:{key}" for (category, key), count in sorted(counts.items()) if count > 1]
    valid_count = sum(bool(item["valid"]) for item in assets)
    return {
        "total_assets": len(assets),
        "valid_assets": valid_count,
        "missing_assets": missing,
        "invalid_assets": invalid,
        "duplicate_normalized_keys": duplicates,
        "status": "ok" if not missing and not invalid and not duplicates else "error",
    }
