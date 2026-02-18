# Visual regression snapshots (Playwright)

This project is UI-heavy and has historically suffered from **"fixed → regressed"** styling issues.

This folder contains a **lightweight Playwright snapshot script** that:

- launches the Streamlit app locally
- captures screenshots for known regression hotspots
- optionally compares against a baseline set

## Install (one-time)

Create a dev venv, then:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
python -m playwright install --with-deps chromium
```

If you are in a restricted environment where Playwright cannot download browsers,
you can point the script at a **system Chromium**:

```bash
export RBV_CHROMIUM_EXECUTABLE=/usr/bin/chromium
```

## Create / update baselines

```bash
python tools/visual_regression/vr_playwright.py --update-baseline
```

This writes PNGs into `tools/visual_regression/baseline/`.

## Run comparison

```bash
python tools/visual_regression/vr_playwright.py
```

Outputs:

- fresh captures → `tools/visual_regression/output/`
- diffs (if mismatched) → `tools/visual_regression/diffs/`

Exit code is non-zero if any snapshot mismatches (useful for CI).

## Smoke mode (no baselines)

If you just want to ensure the snapshot run works and produce images for review:

```bash
python tools/visual_regression/vr_playwright.py --smoke
```
