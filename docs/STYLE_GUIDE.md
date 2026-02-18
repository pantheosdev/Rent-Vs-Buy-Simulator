# UI style guide

## Theme rules (do not regress)
- Buyer accent: **Azure Blue**
- Renter accent: **Warm Yellow**
- Rounded cards/banners/tables everywhere
- Avoid Streamlit native `help=` popovers; use the custom tooltip system

## Inputs
- Use the unified input styling (single container + internal dividers)
- Steppers are low-contrast by default and brighten on hover/focus
- Focus ring should apply to the whole control (no "ears" / radius mismatch)

## Tooltips
- Tooltips must render on top of expanders and near the viewport edge they should auto-flip (up/down)

## Tables
- Delta coloring should be text-only (no background fills)
