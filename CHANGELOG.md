# Changelog


## Unreleased
- TBD

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
