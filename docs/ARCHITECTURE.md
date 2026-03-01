# Architecture

This repo is a Streamlit application with a modular core.

## High-level layout
- `app.py`
  - UI orchestration and layout
  - widget wrapper usage (custom tooltip system)
  - the main glue layer between UI and `rbv/` core

- `rbv/core/`
  - financial engine, amortization + cashflow accounting
  - deterministic + Monte Carlo evaluation
  - volatility-aware breakeven solvers

- `rbv/ui/`
  - theme and CSS overrides
  - reusable styling primitives for the dark fintech look

- `rbv/qa/` + `run_all_qa.py`
  - automated integrity gates (smoke/scenarios/sensitivity/golden)

- `tools/visual_regression/`
  - Playwright-based snapshot harness
  - targets the UI areas most prone to regressions (focus states, tooltips, banners, tabs/tables)

## Versioning

Version policy (numbering scheme, CHANGELOG format, and bump rules) is documented in [`docs/CHANGELOG_POLICY.md`](CHANGELOG_POLICY.md).

## Key invariants
- Do not break stable `st.session_state` keys; if you must evolve them, add backward-compatible fallbacks.
- Volatility (Fast/Quality) may change Monte Carlo controls (sims/grid/caching) but must not change the meaning of financial assumptions.
- Prefer the custom tooltip system over Streamlit native help popovers.
