"""Generate and verify neutral development-only PNG assets."""
from __future__ import annotations

from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
ASSETS = {
    "characters": (
        (512, 768),
        [
            "manufacturing_worker_neutral", "manufacturing_worker_safe",
            "manufacturing_worker_warning", "chemical_laboratory_worker_neutral",
            "chemical_laboratory_worker_safe", "chemical_laboratory_worker_warning",
            "construction_worker_neutral", "construction_worker_safe",
            "construction_worker_warning",
        ],
    ),
    "backgrounds": (
        (1280, 720),
        [
            "manufacturing_default", "machinery_inspection", "material_handling",
            "welding_area", "dusty_manufacturing_zone", "chemical_laboratory_default",
            "corrosive_liquid_transfer", "volatile_solvent_mixing",
            "contaminated_glassware", "chemical_splash_response",
            "low_ventilation_lab", "construction_default", "ground_site_inspection",
            "material_cutting", "moving_equipment_zone", "drilling_zone",
            "work_at_height", "high_noise_operation",
        ],
    ),
    "ppe_icons": (
        (256, 256),
        [
            "helmet", "safety_goggles", "face_shield", "respirator", "dust_mask",
            "chemical_gloves", "work_gloves", "safety_vest", "laboratory_coat",
            "safety_footwear", "hearing_protection", "fall_arrest_system",
        ],
    ),
    "hazard_icons": (
        (256, 256),
        [
            "falling_object", "moving_equipment", "airborne_dust", "flying_debris",
            "excessive_noise", "work_at_height", "sharp_material", "corrosive_liquid",
            "toxic_vapour", "chemical_splash", "broken_glass", "flammable_solvent",
            "inadequate_ventilation",
        ],
    ),
    "badges": (
        (256, 256),
        [
            "risk_low", "risk_medium", "risk_high", "risk_critical",
            "mastery_beginner", "mastery_developing", "mastery_proficient",
            "mastery_advanced",
        ],
    ),
}
PLACEHOLDERS = {
    "missing_character": (512, 768),
    "missing_background": (1280, 720),
    "missing_ppe_icon": (256, 256),
    "missing_hazard_icon": (256, 256),
}


def _font(size: int):
    candidates = (
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
    )
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def _centered_lines(draw, text, box, font, fill, spacing=8):
    x0, y0, x1, y1 = box
    width = max(8, int((x1 - x0) / max(8, font.size * 0.58)))
    lines = wrap(text.replace("_", " ").upper(), width=width) or [text]
    bounds = [draw.textbbox((0, 0), line, font=font) for line in lines]
    heights = [bound[3] - bound[1] for bound in bounds]
    total = sum(heights) + spacing * (len(lines) - 1)
    y = y0 + (y1 - y0 - total) / 2
    for line, bound, height in zip(lines, bounds, heights):
        line_width = bound[2] - bound[0]
        draw.text((x0 + (x1 - x0 - line_width) / 2, y), line, font=font, fill=fill)
        y += height + spacing


def _draw_asset(category: str, name: str, size: tuple[int, int], path: Path):
    width, height = size
    transparent = category in {"ppe_icons", "hazard_icons", "badges"}
    image = Image.new("RGBA", size, (0, 0, 0, 0) if transparent else (231, 235, 238, 255))
    draw = ImageDraw.Draw(image)
    margin = max(12, min(width, height) // 14)
    palette = {
        "characters": ((77, 94, 108, 255), (244, 246, 247, 255)),
        "backgrounds": ((91, 108, 117, 255), (245, 247, 248, 255)),
        "ppe_icons": ((61, 90, 128, 230), (244, 247, 250, 255)),
        "hazard_icons": ((125, 91, 55, 230), (250, 247, 241, 255)),
        "badges": ((75, 100, 84, 230), (246, 249, 246, 255)),
        "placeholders": ((100, 100, 100, 255), (245, 245, 245, 255)),
    }
    border, panel = palette[category]
    draw.rounded_rectangle(
        (margin, margin, width - margin, height - margin),
        radius=max(12, margin), fill=panel, outline=border, width=max(3, margin // 5),
    )
    if category == "characters":
        cx = width // 2
        draw.ellipse((cx - 72, 105, cx + 72, 249), fill=(173, 181, 186, 255), outline=border, width=5)
        draw.rounded_rectangle((cx - 125, 265, cx + 125, 610), radius=60,
                               fill=(194, 201, 205, 255), outline=border, width=5)
        label_box = (35, 615, width - 35, height - 55)
    elif category == "backgrounds":
        draw.line((margin * 2, height * 0.66, width - margin * 2, height * 0.66), fill=border, width=7)
        for offset in range(4):
            x = width * (0.18 + offset * 0.2)
            draw.rectangle((x - 55, height * 0.38, x + 55, height * 0.66), outline=border, width=5)
        label_box = (width * 0.18, height * 0.12, width * 0.82, height * 0.34)
    else:
        cx, cy = width // 2, int(height * 0.38)
        draw.ellipse((cx - 55, cy - 55, cx + 55, cy + 55), fill=(210, 216, 219, 255), outline=border, width=5)
        draw.line((cx - 28, cy, cx + 28, cy), fill=border, width=8)
        draw.line((cx, cy - 28, cx, cy + 28), fill=border, width=8)
        label_box = (20, height * 0.62, width - 20, height - 36)
    _centered_lines(draw, name, label_box, _font(max(16, min(width, height) // 15)), border)
    banner_height = max(22, height // 24)
    draw.rectangle((0, height - banner_height, width, height), fill=(54, 61, 65, 235))
    banner_font = _font(max(10, banner_height // 2))
    _centered_lines(draw, "DEVELOPMENT PLACEHOLDER", (4, height - banner_height, width - 4, height), banner_font, (255, 255, 255, 255), 0)
    image.save(path, "PNG", optimize=True)


def generate():
    for category, (size, names) in ASSETS.items():
        directory = ROOT / category
        directory.mkdir(parents=True, exist_ok=True)
        for name in names:
            _draw_asset(category, name, size, directory / f"{name}.png")
    directory = ROOT / "placeholders"
    directory.mkdir(parents=True, exist_ok=True)
    for name, size in PLACEHOLDERS.items():
        _draw_asset("placeholders", name, size, directory / f"{name}.png")


def verify():
    expected = {
        ROOT / category / f"{name}.png": size
        for category, (size, names) in ASSETS.items()
        for name in names
    }
    expected.update({ROOT / "placeholders" / f"{name}.png": size for name, size in PLACEHOLDERS.items()})
    errors = []
    for path, expected_size in expected.items():
        if not path.exists():
            errors.append(f"missing: {path.relative_to(ROOT)}")
            continue
        if path.stat().st_size == 0:
            errors.append(f"zero bytes: {path.relative_to(ROOT)}")
            continue
        try:
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                if image.size != expected_size:
                    errors.append(f"wrong size: {path.relative_to(ROOT)} {image.size}")
        except Exception as exc:
            errors.append(f"invalid PNG: {path.relative_to(ROOT)} ({exc})")
    directories = set(ASSETS) | {"placeholders"}
    for directory in directories:
        if not (ROOT / directory).is_dir():
            errors.append(f"missing directory: {directory}")
    return expected, errors


if __name__ == "__main__":
    generate()
    files, failures = verify()
    print(f"Verified {len(files)} relative PNG assets under {ROOT.name}/")
    if failures:
        for failure in failures:
            print(f"ERROR: {failure}")
        raise SystemExit(1)
    print("All required directories and PNG files are valid and non-empty.")
