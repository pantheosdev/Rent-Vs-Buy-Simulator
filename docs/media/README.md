# Screenshots & Media

This directory contains screenshots and demo media for the README.

## Required files

| File | Description | Recommended size |
|---|---|---|
| `main.png` | Main interface with inputs and results | 1200×800 |
| `mc.png` | Monte Carlo net worth chart with bands | 1200×600 |
| `heatmap.png` | Sensitivity heatmap visualization | 1200×600 |
| `sidebar.png` | Sidebar settings panel | 400×800 |

## How to capture

Option A — Playwright (automated):
```bash
python tools/visual_regression/vr_playwright.py --smoke
```
Then copy the relevant PNGs from `tools/visual_regression/output/` to this directory.

Option B — Manual:
1. Run `streamlit run app.py`
2. Navigate to the relevant views
3. Use browser DevTools or screenshot tool
4. Save as PNG files with the names above
