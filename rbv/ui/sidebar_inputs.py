"""Sidebar input helpers for the Rent vs Buy simulator.

Phase 4.1 (partial): This module establishes the foundation for extracting
the sidebar construction logic from ``app.py``.  Currently contains:

* :data:`RBV_SIDEBAR_TOOLTIPS` – tooltip text registry for sidebar widgets
* :func:`sidebar_hint` – renders a low-noise hint below a sidebar widget
* :func:`sidebar_pills` – renders a compact row of pill badges in the sidebar

Planned future extraction (Phase 4.2+):
    The full sidebar construction code (currently in the ``with st.sidebar:``
    block in ``app.py``) will be extracted into a ``build_sidebar_inputs``
    function here once dependent helpers (``sidebar_label``, ``rbv_help_html``,
    ``apply_preset``, etc.) are also moved or made importable without circular
    dependencies.

Safety notes (from Phase 4 implementation plan):
* Do NOT change ``st.session_state`` key names used by the sidebar.
* Do NOT change the ``run_simulation_core`` engine API.
* Every extraction step must keep the app fully launchable and UI-identical.
"""

from __future__ import annotations

import html as _html

import streamlit as st

# ---------------------------------------------------------------------------
# Tooltip registry
# ---------------------------------------------------------------------------

RBV_SIDEBAR_TOOLTIPS: dict[str, str] = {
    "Public Mode (simple UI)": "When ON, hides power-user controls and uses safe presets. Turn OFF for Power Mode.",
    "Monte Carlo results": "Choose Stable for reproducible results, or New random run for a fresh random draw each rerun.",
    "Power overrides": "Optional manual overrides for sim counts/grid on top of the balanced defaults.",
    "Province": "Select the province for land transfer / welcome tax rules.",
    "Toronto Property?": "If yes, applies Toronto Municipal Land Transfer Tax (MLTT) in addition to Ontario LTT (rates depend on date).",
    "First-Time Buyer?": "If eligible, applies applicable first-time buyer rebates where modeled.",
    "Purchase Price ($)": "Home purchase price at month 0.",
    "Down Payment ($)": "Cash paid up front. Remainder is financed by the mortgage (unless you set a smaller loan elsewhere).",
    "Transfer Tax Override ($)": "If set > 0, overrides computed land transfer/welcome tax and becomes the ground truth closing tax.",
    "Legal & Closing Costs ($)": "Legal fees and other closing costs (excluding transfer tax).",
    "Home Inspection ($)": "One-time inspection cost at purchase.",
    "Mortgage Rate Mode": "Choose how the mortgage rate behaves (fixed vs resets/renewals).",
    "Mortgage Rate (Fixed %)": "Nominal annual mortgage rate used for the payment calculation.",
    "Canadian mortgage compounding (semi-annual)": "If enabled, converts the nominal rate using Canadian semi-annual compounding before monthly payments.",
    "Amortization Period (Years)": "Total amortization length used to compute the monthly mortgage payment. Note: 30-year amortization has eligibility restrictions in Canada (policy-dependent).",
    "Reset Frequency (Years)": "How often the mortgage rate resets/renews (approximation).",
    "Rate at Reset (%)": "Mortgage rate applied after a reset/renewal occurs.",
    "Rate Change Per Reset (pp)": "Staircase applied at renewals: Renewal 1 = reset rate; Renewal 2 = reset rate + step; Renewal 3 = reset rate + 2\u00d7step; etc.",
    "Stress test: +2% rate shock at Year 5": "Adds a temporary rate shock (e.g., +2%) starting at year 5 for the configured duration.",
    "Add crisis shock event": "Adds a one-time drawdown event for home and/or portfolio at a specified year.",
    "Crisis year": "Year (from start) when the crisis drawdown is applied.",
    "Home price drawdown (%)": "One-time % drop in home value applied at the crisis year.",
    "Stock drawdown (%)": "One-time % drop in the investment portfolio applied at the crisis year.",
    "Monthly Rent ($)": "Starting monthly rent at month 0.",
    "Rent Inflation (%)": "Annual market rent growth rate (subject to rent control cap if enabled).",
    "Utilities ($/mo)": "Renter utilities cost. Set to 0 if you assume utilities are the same as the owner side.",
    "Insurance ($/mo)": "Renter insurance cost per month.",
    "Moving Costs ($)": "One-time moving cost each time the renter moves (if moving is enabled).",
    "Moving Frequency (Years)": "How often the renter moves (used to apply moving costs).",
    "Renter Invests Closing Costs?": "If enabled, renter invests the cash the buyer would have spent on closing costs.",
    "Invest Monthly Surplus?": "If enabled, the side with lower monthly housing costs invests the difference each month.",
    "Allow portfolio drawdown to fund deficits": "If enabled, portfolios can go negative/withdrawn to cover monthly deficits (instead of clipping at zero).",
    "Investment Tax Modeling": "Choose how investment taxes are approximated (pre-tax, annual drag, or deferred capital gains at the end).",
    "Tax on Investment Gains (%)": 'Annual return drag applied to both portfolios when using the \u201cAnnual drag\u201d tax mode.',
    "Effective Capital Gains Tax at End (%)": 'Tax rate applied to unrealized gains when liquidating portfolios at the horizon in \u201cDeferred CG\u201d mode.',
    "Liquidation view at horizon (cash-in-hand)": "Shows a liquidation (after-tax/after-selling) view at the horizon for clarity.",
    "Buyer Investment Return (%)": "Nominal annual return used for the buyer's invested cashflows/portfolio.",
    "Renter Investment Return (%)": "Nominal annual return used for the renter's invested cashflows/portfolio.",
    "Enable Volatility": "Turns on Monte Carlo volatility for home and portfolio returns.",
    "Number of Simulations": "Monte Carlo simulation count. Higher = smoother estimates but slower.",
    "Monte Carlo seed": "Seed for repeatable Monte Carlo runs. Leave blank for a stable derived seed.",
    "Seed": "Leave blank to auto-derive a stable seed from your inputs (recommended for comparing scenarios). In 'New random run' mode, the manual seed is ignored.",
    "Randomize seed each run": "If enabled, uses a new random seed every run (results will vary run-to-run).",
    "Investment Volatility (Std Dev %)": "Annualized volatility (standard deviation) for the portfolio return process in Monte Carlo.",
    "Appreciation Volatility (Std Dev %)": "Annualized volatility (standard deviation) for the home appreciation process in Monte Carlo.",
    "Correlation (\u03c1)": "Correlation between home and portfolio shocks in Monte Carlo. Negative values mean they tend to move opposite.",
    "Home Appreciation (%)": "Baseline nominal annual home appreciation rate (drift).",
    "General Inflation Rate (%)": "CPI/general inflation used to grow many non-housing costs over time.",
    "PV (Discount) Rate (%)": "Discount rate used to compute present value (PV) versions of dollars and deltas.",
    "Property Tax Rate (%)": "Annual property tax rate as % of home value.",
    "Property Tax Growth Model": "Toronto realism: MPAC assessments lag market prices and municipalities smooth year-over-year bill changes. Hybrid is a simple, realistic approximation: market pressure capped by CPI + 0.5%/yr.",
    "Hybrid cap add-on (%/yr)": "Extra room above CPI used only in Hybrid mode. Default 0.5%/yr keeps taxes responsive to market pressure without assuming bills rise 1:1 with home prices.",
    "Maintenance (Repairs/Reno) Rate (%)": "Annual maintenance/repairs budget as % of home value.",
    "Repair Costs Rate (%)": "Additional repair reserve rate as % of home value (separate from maintenance).",
    "Condo Fees ($/mo)": "Monthly condo/HOA fees (0 for freehold).",
    "Condo Fee Inflation Mode": "How condo fees grow over time: CPI + spread, or a custom fixed rate.",
    "Condo Fee Inflation Spread vs CPI (%/yr)": "Adds this many % per year on top of CPI for condo fee inflation (CPI+spread mode).",
    "Condo Fee Inflation (%)": "Custom condo fee inflation rate (only used in custom mode).",
    "Selling Cost (%)": "Selling costs as % of sale price (e.g., realtor commission).",
    'Home Sale Legal/Closing Fee at Exit ($)': 'Legal/closing fee paid on sale (added when \u201cAssume sold at horizon\u201d is enabled).',
    "Assume home sold at horizon (apply selling costs)": "If enabled, applies selling costs and liquidation at the horizon; otherwise treats the home as held.",
    "After-tax household income ($/mo)": "If income constraints are enabled, this caps how much total spending you can cover each month.",
    "Non-housing spending ($/mo)": "If income constraints are enabled, this models other spending outside housing each month.",
    "Income growth (%/yr)": "Annual growth rate for income/spending when income constraints are enabled.",
    "Enable income/budget constraints (experimental)": "If enabled, the model constrains cashflows by after-tax income and non-housing spending (experimental).",
    "Performance profile": "Single balanced profile tuned for responsive Monte Carlo and heatmap runs (80k main sims, 20k heatmap sims, 40k bias sims, 40\u00d740 grid). Use Advanced overrides only when needed.",
    "Economic Scenario": "Preset bundle of assumptions (baseline / high inflation / stagnation) applied to key inputs.",
    "Analysis Duration (Years)": "How many years to simulate (monthly cashflows, investing, and PV discounting).",
    "Apply Rent Control Cap?": "Caps rent growth at the configured maximum (use only if your unit is legally rent-controlled). Effective rent growth = min(Rent Inflation, Cap).",
    "Rent Control Cap (%)": "Maximum annual rent increase allowed under rent control (e.g., provincial guideline).",
    "Main Monte Carlo sims": "Number of simulations for the main Monte Carlo net worth chart. Higher = smoother percentiles / win% but slower (and uses more memory).",
    "Heatmap Monte Carlo sims": "Monte Carlo simulations used per heatmap pass for stochastic metrics (shared batched execution across the grid). Higher = less noisy cells but slower.",
    "Bias Monte Carlo sims": "Monte Carlo simulations used inside the breakeven/bias solver. Higher = more stable breakeven results but slower.",
    "Heatmap grid size (N\u00d7N)": "Resolution of the heatmap grid. Higher N means more detail but compute grows roughly with N\u00b2.",
    "Bias grid size (N\u00d7N)": "Resolution of the bias scan grid (used for breakeven). Higher N improves accuracy but can be slow.",
}


# ---------------------------------------------------------------------------
# Sidebar rendering helpers
# ---------------------------------------------------------------------------


def sidebar_hint(text: str) -> None:
    'Small, low-noise hint text in the sidebar (replaces verbose captions).'
    if isinstance(text, str) and text.strip():
        st.markdown(f'<div class="rbv-hint">{_html.escape(text)}</div>', unsafe_allow_html=True)


def sidebar_pills(items: list[str]) -> None:
    'Render a compact row of pills in the sidebar (for mode summaries, etc.).'
    safe = [_html.escape(str(x)) for x in (items or []) if str(x).strip()]
    if not safe:
        return
    pills = ''.join([f'<div class="rbv-pill">{x}</div>' for x in safe])
    st.markdown(f'<div class="rbv-pill-row">{pills}</div>', unsafe_allow_html=True)
