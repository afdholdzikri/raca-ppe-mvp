# RACA PPE Development Visual Assets

This directory contains lightweight 2D placeholder artwork for local Streamlit
interface development. The supplied PNGs are deliberately neutral, labelled
`DEVELOPMENT PLACEHOLDER`, and are not intended as final publication artwork.

## Directory purpose

- `characters/`: trainee states for manufacturing, laboratory, and construction.
- `backgrounds/`: scenario and domain context panels.
- `ppe_icons/`: personal protective equipment selection icons.
- `hazard_icons/`: active-hazard indicators.
- `badges/`: risk and mastery level indicators.
- `placeholders/`: category-specific fallbacks for missing assets.

All filenames use lowercase `snake_case`. Application code should resolve asset
paths relative to the project or this directory and fall back to the appropriate
file in `placeholders/` when an expected image is unavailable.

## Recommended dimensions

| Category | Dimensions |
|---|---:|
| Character | 512 × 768 px |
| Background | 1280 × 720 px |
| PPE icon | 256 × 256 px |
| Hazard icon | 256 × 256 px |
| Badge | 256 × 256 px |
| Missing character/background/icon | Matching category dimensions |

Icons and badges should use transparent backgrounds where practical. Character
art may use transparency if it will be layered over scenario backgrounds.
Backgrounds should normally be opaque and retain sufficient contrast for UI text.

## Replacing placeholders

Replace a PNG in place while preserving its filename, purpose, and recommended
dimensions. Verify the replacement at normal and reduced Streamlit display sizes.
Keep important content away from image edges and avoid embedding essential safety
instructions solely inside artwork.

Supported delivery formats are PNG (preferred for runtime assets), SVG where the
application explicitly supports it, and source formats retained outside the
runtime directory when needed. Do not silently change a `.png` file to another
encoded format.

Run the reproducible placeholder generator and verifier with:

```powershell
python assets/generate_placeholders.py
```

## Licensing and attribution

Every replacement must have a documented license or written permission suitable
for research, publication, redistribution, and demonstration. Record the creator,
source URL or internal provenance, license, and required attribution. Do not use
copyrighted commercial game assets, stock artwork, trademarks, or third-party
illustrations without explicit permission.
