# Changelog

## v2.90.3

- Fix: PV discount rate unit conversion in config builder; prevent PV underflow to $0.
- Harden: engine normalizes discount_rate when passed as percent-points.

## v2.90 (2026-02-19)

- UX: Added above-the-fold disclaimer banner (educational use only; not financial advice).
- UX: Clarified mortgage renewal staircase behavior and amortization eligibility caveat via tooltips.
- UX: Added explicit note that buyer net worth includes one-time closing costs (can start negative).
- UX: Budget mode now explicitly warns that “Invest Monthly Surplus” is ignored; config passes effective `invest_diff=False` when budget is enabled.
- Policy hygiene: Added policy freshness markers + scheduled GitHub Action (`policy-freshness.yml`) to prompt annual review.
- Meta: Aligned `VERSION.txt` and `rbv.__version__` to the release version.

## v2.89 (2026-02-18)

- CI: update GitHub Actions to v6 majors (checkout/setup-python/upload-artifact).
- CI: make Visual Regression (PR) skip Dependabot PRs and remove brittle system Chromium install.


## Unreleased
- TBD

## v2.88
- Premium dark fintech action-button styling (muted glassy gradients, light text, focus rings)
- Add .gitattributes to stabilize line endings across OS
- README scaffolding for screenshots/GIF (docs/media/)

## v2.87
- Fix (CI): Resolved Ruff lint failure (undefined `_mc_cap`) by adding a horizon-aware MC sims cap used for warnings only.
- CI/VR: Hardened Playwright visual regression script so smoke runs don't fail on minor UI variations (fallback screenshots + non-fatal missing elements).
- CI: Updated Ruff config to the non-deprecated `[tool.ruff.lint]` format.

## v2.86
- QA: Added **Truth Tables** suite (`rbv/qa/qa_truth_tables.py`) with explicit numeric invariants for mortgage math, CMHC/PST recompute, liquidation CG logic, rent-control cadence, and MC determinism.
- QA runner: `run_all_qa.py` now includes the `truth_tables` suite.
- Release tooling: `scripts/build_release_zip.py` now excludes `dist/`, nested `__pycache__`, `.pyc`, and common cache dirs to avoid zip-in-zip and accidental artifact inclusion.

## v2.85
- UX: Action buttons (Compute/Download/etc.) are more visually prominent.
- UX: Enable Volatility is now a latching toggle button (Enable ↔ Disable), with clear green/red state.
- Fix: Main-page input widgets no longer duplicate when switching to Quality mode.

## v2.84
- Fix: Sidebar labels/tooltips no longer duplicate after reruns (idempotent widget wrapper).
- Fix: Removed generic “Adjust this setting.” tooltips; added helpful tooltips for advanced Monte Carlo overrides.
- UX: Keep Monte Carlo progress overlay visible through finalization (prevents “silent” extra loading after bar completes).
- Perf: Cap Fast/Quality presets to avoid slow non-vectorized fallback on long horizons; warn when manual overrides exceed the cap.

## v2.83
- Release polish for public GitHub launch: preflight checks, release automation, lint, dependabot, and docs.

## v2.82
- Public repo hardening: README + license + contributor docs + CI QA + visual regression smoke workflow.
