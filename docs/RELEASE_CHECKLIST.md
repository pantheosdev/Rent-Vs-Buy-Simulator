# Release checklist (RBV)

This checklist is intended for maintainers preparing a public GitHub release.

## Preflight (required)
1. Create/activate a clean virtualenv.
2. Install runtime deps:
   - `pip install -r requirements.txt`
3. Run the app once:
   - `streamlit run app.py`
4. Run QA gates:
   - `python run_all_qa.py`
5. Run the preflight script:
   - `python scripts/preflight.py`

## Visual regression (recommended)
Visual snapshots prevent UI regressions.

1. Install dev deps:
   - `pip install -r requirements-dev.txt`
   - `python -m playwright install --with-deps chromium`
2. Generate/update baseline images:
   - `python tools/visual_regression/vr_playwright.py --update-baseline`
3. Commit baseline images:
   - `git add tools/visual_regression/baseline/*.png`
   - `git commit -m "Update visual baselines"`
4. Verify compare passes:
   - `python tools/visual_regression/vr_playwright.py`

## Repo sanity (required)
- Confirm no secrets are present in the repo history.
- Confirm no absolute local paths remain (preflight checks common patterns).
- Confirm large binaries are not committed.

## Tag + release (required)
1. Update `VERSION.txt` (and `rbv.__version__`) if needed.
2. Update `CHANGELOG.md` with release notes.
3. Create an annotated tag:
   - `git tag -a v1.0.0 -m "v1.0.0"`
4. Push tag:
   - `git push origin v1.0.0`

A GitHub Actions workflow (`.github/workflows/release.yml`) will build and attach a release zip when a tag `v*` is pushed.
