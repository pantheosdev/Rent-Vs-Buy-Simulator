# Contributing

Thanks for considering a contribution.

## Development setup
1. Create a virtual environment (recommended).
2. Install deps:
   - `pip install -r requirements.txt`
   - `pip install -r requirements-dev.txt` (optional; for visual regression)
3. Run the app:
   - `streamlit run app.py`

## QA gates (required)
Before submitting a PR:
- `python run_all_qa.py`

## Visual regression (optional but recommended)
Playwright snapshots can catch UI regressions:
- Install browsers: `python -m playwright install --with-deps chromium`
- Update baselines: `python tools/visual_regression/vr_playwright.py --update-baseline`
- Compare: `python tools/visual_regression/vr_playwright.py`

## Style
- Keep changes focused and readable.
- Avoid breaking `st.session_state` keys; add backward-compatible fallbacks if needed.
