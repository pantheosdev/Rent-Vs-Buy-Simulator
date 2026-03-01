# Changelog
## v2.94.0 — Phase D: Missing Financial Features

### New Features

- **Foreign buyer taxes** (`rbv/core/policy_canada.py`): Added `foreign_buyer_tax_rate()` and `foreign_buyer_tax_amount()` helpers modeling BC's Additional Property Transfer Tax (APTT, 20% as of 2018) and Ontario's Non-Resident Speculation Tax (NRST, 25% as of 2023). Full date-aware history from 2016 (BC) / 2017 (ON). UI: "Foreign / non-resident buyer" checkbox in the Taxes & Eligibility section; only shown when province is BC or Ontario. Tax is added to one-time closing costs in the engine.

- **RRSP Home Buyers' Plan (HBP)** (`rbv/core/government_programs.py`): New module modeling the HBP withdrawal (up to $35k pre-2024-04-16, $60k post) applied toward the down payment, plus the 15-year repayment obligation (1/15th per year, 2-year grace period). Engine wires repayment as a monthly buyer cash outflow. UI: opt-in checkbox + withdrawal amount input with inline repayment hint.

- **FHSA (First Home Savings Account)** (`rbv/core/government_programs.py`): Models tax-advantaged pre-purchase accumulation ($8k/yr, $40k lifetime, available since 2023-04-01). Balance (contributions + growth) added to down payment supplement; contribution tax deduction estimated as a credit at purchase. UI: opt-in checkbox + years contributed, annual contribution, return %, and marginal tax rate inputs.

- **IRD mortgage prepayment penalty** (`rbv/core/mortgage.py`): Added `ird_prepayment_penalty()` and `ird_penalty_for_simulation()` implementing the Canadian standard: max(3 months' interest, IRD). IRD = remaining_balance × (contract_rate − comparison_rate) × remaining_term_years. Engine deducts the penalty from buyer equity at the terminal month when `years < mortgage_term`. UI: opt-in checkbox + term length + assumed rate-drop inputs.

### Engine Changes

- `rbv/core/engine.py`: All four Phase D features wired into `run_simulation_core()`. New cfg keys: `is_foreign_buyer`, `hbp_enabled`, `hbp_withdrawal`, `fhsa_enabled`, `fhsa_annual_contribution`, `fhsa_years_contributed`, `fhsa_return_pct`, `fhsa_marginal_tax_rate_pct`, `ird_enabled`, `mortgage_term_months`, `ird_rate_drop_pp`. Phase D metadata attached to `df.attrs` for UI consumption.
- `simulate_single()` and `_run_monte_carlo_vectorized()`: Extended with `hbp_monthly_cost`, `hbp_repayment_start_month`, `hbp_repayment_end_month`, `prepayment_penalty_amount` optional parameters (all default to 0/0).

### Tests

- `tests/test_phase_d.py`: 49 new tests covering all four Phase D modules and engine integration.

### Docs

- `docs/ASSUMPTIONS.md`: Updated to remove HBP, FHSA, foreign buyer taxes, and mortgage prepayment penalties from the "Not Modeled" list.

## v2.93.10

- UI: Surface **negative equity warning** in the results area when the buyer goes underwater during the simulation. Calls `detect_negative_equity(df)` and `format_underwater_warning()` from `rbv/core/equity_monitor.py` after `run_simulation_core()` returns. Displays a styled `⚠️` banner using the new `.rbv-warning-banner` CSS class (amber left-border accent on dark panel) added to `rbv/ui/theme.py`. Warning only appears when `has_negative_equity` is `True`.

## v2.93.9

- UI: Restyled **OSFI B-20 qualifying rate** display to match the premium dark fintech theme. Replaced the out-of-place `st.info()` blue box with a compact, muted hint line (same `.rbv-hint` pattern as the "≈ x% down" annotation) placed directly below the mortgage rate input. Now shows qualifying rate and payment comparison (`$X,XXX/mo at qualifying rate vs $X,XXX/mo contract`). Added a ℹ️ tooltip (using the app's standard `rbv_help_html` system) with the full B-20 rule explanation. Added `"B-20 Qualifying Rate"` entry to `RBV_SIDEBAR_TOOLTIPS`.

## v2.93.8

- UI: Display **OSFI B-20 stress test qualifying rate** in the sidebar next to the mortgage rate input. The qualifying rate updates dynamically as the user adjusts their contract rate and is informational only (does not gate the simulation). Formula: `max(contract_rate + 2%, 5.25%)`.

## v2.93.7

- PR7: Added **New construction** toggle and simplified **net GST/HST** estimate (with manual override field) for cash-to-close planning.
- Added cash-to-close breakdown line item for net GST/HST (new construction) and surfaced estimator note/override status in run summary.
- Added truth-table QA coverage for simplified new-home GST/HST rebate estimator thresholds and caps.
- Sensitivity/override recompute path now refreshes new-construction GST/HST estimate when price changes (unless override is set).
- UI cleanup: removed duplicate **Cash to Close breakdown** dropdown under **BUYING DETAILS** (kept the run-level breakdown below “What changed in this run?”).

## v2.93.6

- Policy: Add **date-aware insured 30-year amortization validation** schedule (pre-2024-08-01, Aug 1 2024 FTB+new-build, Dec 15 2024 FTB-or-new-build).
- Validation: Block insured amortizations above the modeled policy limit and surface rule-specific error messaging tied to the **Tax/Policy Rules As-of Date**.
- QA: Add truth-table coverage for insured 30-year amortization policy stage boundaries and eligibility combinations.

## v2.93.5

- Policy/UI: Add **Down payment source** toggle (Traditional vs Non-traditional) for high-LTV insured mortgages.
- Policy: Model non-traditional down payment premium tier: **4.50%** for **90.01–95% LTV** (else standard CMHC tiers).
- QA: Add reference regression check for the non-traditional premium tier.

## v2.93.4

- UX: Add an itemized **Cash to Close** breakdown (down payment, transfer tax, legal/closing, inspection, other closing costs, PST on CMHC premium where applicable).
- UX: Move **Cash to Close** breakdown below the run-level banners (next to "What changed in this run?") and render as simple key/value rows (no index/headers).
- UX: Surface province transfer-tax notes (e.g., BC FTHB exemption) alongside the breakdown for easier verification.
- UX: If mortgage default insurance applies, surface **CMHC premium (financed)** and clarify that PST (if any) is due at closing.
- UX: Center the low-down-payment leverage warning within its banner for readability.


## v2.93.3

- UX: Add an itemized **Cash to Close** breakdown (down payment, transfer tax, legal/closing, inspection, other closing costs, PST on CMHC premium where applicable).
- UX: Surface province transfer-tax notes (e.g., BC FTHB exemption) alongside the breakdown for easier verification.


## v2.92.10

- Net Worth chart: add optional breakeven (Δ=0) vertical marker + subtle negative-region shading.
- Heatmap: add base-case marker and improve colorbar labeling for clarity.
- Tooltips (mobile): add horizontal auto-flip and overflow hardening to prevent clipping.
- Sidebar: reduce overwhelm by collapsing Economic Scenario by default and clarifying Expert-mode lock wording.

## v2.93.0

- Buying inputs: add an explicit **Province** selector (drives land transfer / welcome tax rules).
- Guardrail: **Toronto MLTT** toggle now only appears for Ontario; it is auto-cleared when switching provinces.
- QA: add cross-province transfer-tax reference anchors (ON/BC/MB/AB) to truth tables.

## v2.92.9

- Engine: when surplus investing is OFF, monthly buy-vs-rent cost differences are tracked as cash (0% return) rather than discarded.
- Engine: tighten parsing exception scopes (TypeError/ValueError) in core numeric coercions.
- App: add cross-session caching for simulation runs to reduce repeated Monte Carlo compute under multi-user load.

## v2.92.8
- UI: Remove accent strip-lines from the 4 Quick Signals KPI cards (neutral informational style).
- UI: One-time shocks row now uses 3 full-width inputs (no spacer gap).

## v2.92.7
- UI: Added **Quick Signals** KPI row (Breakeven year, Price-to-rent, Surplus investing status, Mode).
- UX guardrail: **Invest Monthly Surplus** is locked ON in standard mode; disabling requires Expert mode and shows a prominent warning.
- Consistency: Helper paths (breakeven/bias/heatmap) now default `invest_surplus_input` to **True** to avoid first-load mismatches.

## v2.92.6
- Closing costs: centralize **mortgage default insurance sales tax** rules and make Quebec rate date-aware (**9% through 2026**, 9.975% from 2027).
- Cash-out: add **Principal residence** toggle; if disabled, apply a simplified **home capital gains tax** at horizon sale (net of selling costs).
- Validation: enforce **minimum down payment** rule in UI (tiered Canada rule by as-of date).
- QA: add regression truth-table targets for independent reference numbers (mortgage PMTs, CMHC premiums, Ontario/Toronto LTT, min down).

## v2.92.5
- Guardrails: add engine-level **non-finite (NaN/Inf) detection** for Monte Carlo paths and terminal win% inputs (surfaced via `df.attrs`).
- Mortgage: support **hypothetical negative rates** safely (no silent clamp); in UI, negative rates are blocked unless Expert mode is enabled.
- Cash-out: add explicit **"Assume home sold at horizon"** toggle; when disabled, cash-out view treats home as held and excludes home equity + selling costs.
- UX: suppress Monte Carlo win-probability text when MC is **degenerate (σ=0)** to avoid misleading "stochastic" labeling.
- QA: update truth tables for cash-out semantics when `assume_sale_end=False`.

## v2.92.4
- UX: Add a small **🔒/🔓 Expert mode status** line under the Expert mode toggle so users understand why advanced cash-out sensitivities are hidden.

## v2.92.3
- UX: Add **Expert mode** gate for advanced cash-out sensitivity toggles (hypothetical CG inclusion + registered shelter approximation).
- Reproducibility: Scenario import/export now supports `expert_mode` and auto-enables it when importing advanced toggles.
- Release readiness: Add GitHub Actions workflows for **QA** (ruff + QA) and **Release** (build zip on tag).
- Preflight: Add **Ruff** lint + format checks as a required gate.
- Visual regression tooling: Playwright harness now fails fast with a clear message if Streamlit is missing, and prints Streamlit startup failures.

## v2.92.2
- UI defaults now seed from scenario presets via `rbv.ui.defaults` (single source of truth).
- Added QA truth-table gate to prevent preset/default drift.
- Fixed version string consistency (`VERSION.txt` and `rbv.__version__`).

## v2.92.1
- Hotfix: Align first-load mortgage rate default with Baseline preset (4.75%).

## v2.92.0 (2026-02-20)

- Scenario: Add optional one-time **Special Assessment** shock (buyer-only, unrecoverable) with UI inputs and a monthly output column.
- Output clarity: Add renter-series toggle (Recurring vs Total incl. moving) and a new **Monthly Unrecoverable Cost Over Time** chart.
- Tax modeling: Add opt-in cash-out sensitivity knobs for **CG inclusion policy** (current vs hypothetical tiered) and a conservative **registered shelter** approximation.
- QA: Extend Truth Tables to cover special assessment timing, tiered inclusion math, and shelter behavior.


## v2.93.2 (2026-02-22)

- Tax: Model **BC First-Time Home Buyer (FTHB)** exemption (simplified) as a reduction to base PTT, capped at **$8,000**.
- Policy: Make BC FTHB schedule **date-aware** (pre/post **Apr 1, 2024** thresholds).
- QA: Add BC FTHB boundary truth-table tests (500k, 835k, 850k, 860k; plus legacy 520k/525k).


## v2.93.1 (2026-02-22)

- UX: Make purchase closing costs editable via inputs (legal/closing, inspection, other one-time costs).
- Calc: Closing costs now include the new editable 'Other closing costs' bucket.
- QA: Add truth-table invariant that one-time closing costs reduce buyer net worth dollar-for-dollar when returns are zero.

## v2.93.0 (2026-02-22)

- UX: Add Province selector so transfer tax rules are not implicitly locked to Ontario.
- UX: Toronto MLTT toggle is now Ontario-only and is auto-cleared when switching provinces.
- QA: Add cross-province transfer tax anchors.

## v2.90.4 (2026-02-20)

- UX: Fix clipped custom tooltips by allowing KPI cards to overflow and restoring tooltip scrolling.
- UX: Clarify buyer vs renter monthly figures by renaming KPI to **Avg Monthly Outflow** and explicitly separating **Irrecoverable Costs** from principal paydown.
- UX: Rename/clarify the cost breakdown section as **Irrecoverable Costs (cost of living)** and add a principal-paydown bridge line.
- Perf: Quality-mode defaults tuned for Streamlit Cloud (Main MC 90k, grid 45×45, heatmap sims 25k; bias sims unchanged).

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
