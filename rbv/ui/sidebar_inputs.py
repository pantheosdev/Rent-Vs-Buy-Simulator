"""Sidebar input module for the Rent-vs-Buy simulator.

This module encapsulates all logic related to rendering the sidebar
controls in the Streamlit user interface.

Functions
---------
render_sidebar(st_module)
    Render the sidebar widgets and return a configuration dictionary
    compatible with ``rbv.core.engine.run_simulation_core``.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict


def _compute_mort_close_pst(
    price: float,
    down: float,
    province: str,
    first_time: bool,
    toronto: bool,
    purchase_legal_fee: float,
    home_inspection: float,
    other_closing: float,
) -> tuple:
    """Compute mortgage principal, closing costs, and PST on CMHC premium."""
    from rbv.core.taxes import calc_transfer_tax
    from rbv.core.policy_canada import (
        cmhc_premium_rate_from_ltv,
        insured_mortgage_price_cap,
        mortgage_default_insurance_sales_tax_rate,
    )

    loan = max(0.0, price - down)
    ltv = (loan / price) if price > 0 else 0.0

    # Land transfer tax
    asof = datetime.date.today()
    tt = calc_transfer_tax(
        province,
        float(price),
        first_time_buyer=bool(first_time),
        toronto_property=bool(toronto),
        asof_date=asof,
    )
    total_ltt = float(tt.get("total", 0.0) or 0.0)

    # CMHC premium
    prem = 0.0
    pst = 0.0
    if ltv > 0.80:
        price_cap = insured_mortgage_price_cap(asof)
        if price < float(price_cap):
            cmhc_r = cmhc_premium_rate_from_ltv(ltv)
            prem = loan * cmhc_r
            pst_rate = mortgage_default_insurance_sales_tax_rate(province, asof)
            pst = prem * pst_rate

    mort = loan + prem
    close = total_ltt + purchase_legal_fee + home_inspection + other_closing + pst

    return float(mort), float(close), float(pst)


def render_sidebar(st_module: Any) -> Dict[str, Any]:
    """Render the sidebar widgets and return a configuration dictionary.

    Returns a complete dictionary matching the keys expected by
    ``rbv.core.engine.run_simulation_core``, including all mortgage,
    tax, amortization, rent-control, and budget fields.

    Parameters
    ----------
    st_module : Any
        The Streamlit module instance (normally ``streamlit``).

    Returns
    -------
    Dict[str, Any]
        Full configuration dictionary for the simulation engine, plus
        extra keys ``buyer_ret``, ``renter_ret``, ``apprec``,
        ``invest_diff``, ``rent_closing``, and ``mkt_corr`` that
        ``app.py`` passes as positional arguments to ``run_simulation_core``.
    """
    sb = st_module.sidebar
    sb.title("Rent vs Buy Simulator")

    # ── Property & mortgage ──────────────────────────────────────────────────
    sb.header("Property & Mortgage")
    province = sb.selectbox(
        "Province",
        options=[
            "Ontario",
            "British Columbia",
            "Alberta",
            "Quebec",
            "Nova Scotia",
            "New Brunswick",
            "Manitoba",
            "Saskatchewan",
            "Prince Edward Island",
            "Newfoundland and Labrador",
        ],
        index=0,
    )
    toronto = False
    if province == "Ontario":
        toronto = sb.checkbox("Toronto property (MLTT applies)", value=False)
    first_time = sb.checkbox("First-time buyer", value=True)

    price = float(
        sb.number_input(
            "Home purchase price ($)",
            min_value=50_000.0,
            max_value=5_000_000.0,
            value=800_000.0,
            step=5_000.0,
            format="%.0f",
        )
    )
    down_pct = float(
        sb.number_input(
            "Down payment (%)",
            min_value=0.0,
            max_value=100.0,
            value=20.0,
            step=0.5,
            format="%.1f",
        )
    )
    down = price * down_pct / 100.0
    sb.caption(f"Down payment: ${down:,.0f}")

    rate = float(
        sb.number_input(
            "Mortgage interest rate (annual %)",
            min_value=0.0,
            max_value=20.0,
            value=5.0,
            step=0.05,
            format="%.2f",
        )
    )
    amort_years = int(
        sb.number_input(
            "Amortization (years)",
            min_value=1,
            max_value=30,
            value=25,
            step=1,
        )
    )
    nm = amort_years * 12

    sell_cost_pct = float(
        sb.number_input(
            "Selling cost (%)",
            min_value=0.0,
            max_value=15.0,
            value=5.0,
            step=0.1,
            format="%.1f",
        )
    )

    # ── Closing cost sub-inputs ──────────────────────────────────────────────
    sb.subheader("Closing Cost Inputs")
    purchase_legal_fee = float(
        sb.number_input(
            "Legal fees ($)",
            min_value=0.0,
            max_value=10_000.0,
            value=1_800.0,
            step=100.0,
            format="%.0f",
        )
    )
    home_inspection = float(
        sb.number_input(
            "Home inspection ($)",
            min_value=0.0,
            max_value=5_000.0,
            value=500.0,
            step=50.0,
            format="%.0f",
        )
    )
    other_closing = float(
        sb.number_input(
            "Other closing costs ($)",
            min_value=0.0,
            max_value=50_000.0,
            value=0.0,
            step=250.0,
            format="%.0f",
        )
    )

    # Compute mort/close/pst from the inputs above
    mort, close, pst = _compute_mort_close_pst(
        price,
        down,
        province,
        first_time,
        toronto,
        purchase_legal_fee,
        home_inspection,
        other_closing,
    )
    sb.caption(f"Mortgage principal (incl. CMHC): ${mort:,.0f}")
    sb.caption(f"Estimated closing costs: ${close:,.0f}")

    # ── Ongoing owner costs ──────────────────────────────────────────────────
    sb.header("Ongoing Costs (Owner)")
    p_tax_rate_pct = float(
        sb.number_input(
            "Property tax rate (% of value/yr)",
            min_value=0.0,
            max_value=5.0,
            value=1.0,
            step=0.05,
            format="%.2f",
        )
    )
    maint_rate_pct = float(
        sb.number_input(
            "Maintenance (% of value/yr)",
            min_value=0.0,
            max_value=5.0,
            value=1.0,
            step=0.1,
            format="%.1f",
        )
    )
    repair_rate_pct = float(
        sb.number_input(
            "Repairs (% of value/yr)",
            min_value=0.0,
            max_value=5.0,
            value=0.5,
            step=0.1,
            format="%.1f",
        )
    )
    condo = float(
        sb.number_input(
            "Condo/strata fees ($/mo)",
            min_value=0.0,
            max_value=5_000.0,
            value=0.0,
            step=25.0,
            format="%.0f",
        )
    )
    h_ins = float(
        sb.number_input(
            "Home insurance ($/mo)",
            min_value=0.0,
            max_value=500.0,
            value=90.0,
            step=5.0,
            format="%.0f",
        )
    )
    o_util = float(
        sb.number_input(
            "Owner utilities ($/mo)",
            min_value=0.0,
            max_value=2_000.0,
            value=200.0,
            step=10.0,
            format="%.0f",
        )
    )
    home_sale_legal_fee = float(
        sb.number_input(
            "Home sale legal fee ($)",
            min_value=0.0,
            max_value=10_000.0,
            value=2_000.0,
            step=100.0,
            format="%.0f",
        )
    )

    # ── Rental costs ─────────────────────────────────────────────────────────
    sb.header("Rental")
    rent = float(
        sb.number_input(
            "Monthly rent ($)",
            min_value=0.0,
            max_value=20_000.0,
            value=3_000.0,
            step=50.0,
            format="%.0f",
        )
    )
    r_ins = float(
        sb.number_input(
            "Renter's insurance ($/mo)",
            min_value=0.0,
            max_value=200.0,
            value=25.0,
            step=5.0,
            format="%.0f",
        )
    )
    r_util = float(
        sb.number_input(
            "Renter utilities ($/mo)",
            min_value=0.0,
            max_value=2_000.0,
            value=150.0,
            step=10.0,
            format="%.0f",
        )
    )
    moving_cost = float(
        sb.number_input(
            "Moving cost per move ($)",
            min_value=0.0,
            max_value=20_000.0,
            value=2_500.0,
            step=250.0,
            format="%.0f",
        )
    )
    moving_freq = float(
        sb.number_input(
            "Moving frequency (years between moves)",
            min_value=1.0,
            max_value=50.0,
            value=5.0,
            step=1.0,
            format="%.0f",
        )
    )

    # ── Rent control ─────────────────────────────────────────────────────────
    sb.header("Rent Control")
    rent_control_enabled = sb.checkbox("Enable rent control", value=False)
    rent_control_cap = None
    rent_control_frequency_years = 1
    if rent_control_enabled:
        rent_control_cap_pct = float(
            sb.number_input(
                "Annual rent increase cap (%)",
                min_value=0.0,
                max_value=20.0,
                value=2.5,
                step=0.1,
                format="%.1f",
            )
        )
        rent_control_cap = rent_control_cap_pct / 100.0
        rent_control_frequency_years = int(
            sb.number_input(
                "Rent control review cadence (years)",
                min_value=1,
                max_value=10,
                value=1,
                step=1,
            )
        )

    # ── Economic assumptions ─────────────────────────────────────────────────
    sb.header("Economic Assumptions")
    years = int(
        sb.number_input(
            "Simulation horizon (years)",
            min_value=1,
            max_value=50,
            value=25,
            step=1,
        )
    )
    apprec = float(
        sb.number_input(
            "Home appreciation (annual %)",
            min_value=-10.0,
            max_value=20.0,
            value=3.5,
            step=0.25,
            format="%.2f",
        )
    )
    buyer_ret = float(
        sb.number_input(
            "Buyer portfolio return (annual %)",
            min_value=-10.0,
            max_value=30.0,
            value=7.0,
            step=0.5,
            format="%.1f",
        )
    )
    renter_ret = float(
        sb.number_input(
            "Renter portfolio return (annual %)",
            min_value=-10.0,
            max_value=30.0,
            value=7.0,
            step=0.5,
            format="%.1f",
        )
    )
    general_inf_pct = float(
        sb.number_input(
            "General inflation (annual %)",
            min_value=0.0,
            max_value=20.0,
            value=2.0,
            step=0.25,
            format="%.2f",
        )
    )
    rent_inf_pct = float(
        sb.number_input(
            "Rent inflation (annual %)",
            min_value=0.0,
            max_value=20.0,
            value=2.5,
            step=0.25,
            format="%.2f",
        )
    )
    condo_inf_pct = float(
        sb.number_input(
            "Condo fee inflation (annual %)",
            min_value=0.0,
            max_value=20.0,
            value=3.5,
            step=0.25,
            format="%.2f",
        )
    )

    # ── Investment & tax ─────────────────────────────────────────────────────
    sb.header("Investment & Tax")
    invest_diff = float(
        sb.number_input(
            "Investment return spread (buyer vs renter, %)",
            min_value=-5.0,
            max_value=5.0,
            value=0.0,
            step=0.1,
            format="%.1f",
        )
    )
    rent_closing = sb.checkbox(
        "Renter also invests closing costs",
        value=False,
        help="If checked, the renter is assumed to invest the equivalent of the buyer's closing costs.",
    )
    mkt_corr = float(
        sb.number_input(
            "Market correlation (housing vs equities)",
            min_value=-1.0,
            max_value=1.0,
            value=0.25,
            step=0.05,
            format="%.2f",
        )
    )
    investment_tax_mode = sb.selectbox(
        "Investment tax mode",
        options=["Pre-tax (no investment taxes)", "Annual return drag"],
        index=0,
    )
    tax_r = 0.0
    if investment_tax_mode == "Annual return drag":
        tax_r = float(
            sb.number_input(
                "Tax rate on returns (%)",
                min_value=0.0,
                max_value=60.0,
                value=20.0,
                step=1.0,
                format="%.1f",
            )
        )
    cg_tax_end = float(
        sb.number_input(
            "Capital gains tax at horizon (%)",
            min_value=0.0,
            max_value=60.0,
            value=22.5,
            step=0.5,
            format="%.1f",
        )
    )

    # ── Mortgage rate scenarios ───────────────────────────────────────────────
    sb.header("Mortgage Rate Scenarios")
    rate_mode = sb.selectbox(
        "Rate mode",
        options=["Fixed", "Reset every N years", "Variable"],
        index=0,
    )
    rate_reset_years_eff = None
    rate_reset_to_eff = None
    rate_reset_step_pp_eff = 0.0
    rate_shock_enabled_eff = False
    rate_shock_start_year_eff = 5
    rate_shock_duration_years_eff = 5
    rate_shock_pp_eff = 0.0
    if rate_mode == "Reset every N years":
        rate_reset_years_eff = int(
            sb.number_input(
                "Reset every N years",
                min_value=1,
                max_value=30,
                value=5,
                step=1,
            )
        )
        rate_reset_to_eff = float(
            sb.number_input(
                "Reset to rate (%)",
                min_value=0.0,
                max_value=20.0,
                value=6.0,
                step=0.25,
                format="%.2f",
            )
        )
        rate_reset_step_pp_eff = float(
            sb.number_input(
                "Rate step per reset (pp)",
                min_value=0.0,
                max_value=5.0,
                value=0.0,
                step=0.05,
                format="%.2f",
            )
        )
    rate_shock_enabled_eff = sb.checkbox("Enable rate shock", value=False)
    if rate_shock_enabled_eff:
        rate_shock_start_year_eff = int(
            sb.number_input(
                "Shock start year",
                min_value=1,
                max_value=49,
                value=5,
                step=1,
            )
        )
        rate_shock_duration_years_eff = int(
            sb.number_input(
                "Shock duration (years)",
                min_value=1,
                max_value=30,
                value=5,
                step=1,
            )
        )
        rate_shock_pp_eff = float(
            sb.number_input(
                "Shock size (pp)",
                min_value=-10.0,
                max_value=10.0,
                value=2.0,
                step=0.25,
                format="%.2f",
            )
        )

    # ── Monte Carlo ───────────────────────────────────────────────────────────
    sb.header("Monte Carlo")
    use_volatility = sb.checkbox("Enable Monte Carlo simulation", value=False)
    num_sims = 0
    ret_std = 0.15
    apprec_std = 0.10
    if use_volatility:
        num_sims = int(
            sb.number_input(
                "Number of simulations",
                min_value=10,
                max_value=5000,
                value=200,
                step=50,
            )
        )
        ret_std = (
            float(
                sb.number_input(
                    "Portfolio return std dev (%)",
                    min_value=0.0,
                    max_value=60.0,
                    value=15.0,
                    step=1.0,
                    format="%.1f",
                )
            )
            / 100.0
        )
        apprec_std = (
            float(
                sb.number_input(
                    "Appreciation std dev (%)",
                    min_value=0.0,
                    max_value=40.0,
                    value=10.0,
                    step=1.0,
                    format="%.1f",
                )
            )
            / 100.0
        )

    # ── Budget mode ───────────────────────────────────────────────────────────
    sb.header("Budget Mode")
    budget_enabled = sb.checkbox(
        "Enable budget mode",
        value=False,
        help="Model surplus/deficit relative to a monthly income budget.",
    )
    monthly_income = 0.0
    monthly_nonhousing = 0.0
    income_growth_pct = 0.0
    budget_allow_withdraw = True
    if budget_enabled:
        monthly_income = float(
            sb.number_input(
                "Monthly gross income ($)",
                min_value=0.0,
                max_value=100_000.0,
                value=10_000.0,
                step=500.0,
                format="%.0f",
            )
        )
        monthly_nonhousing = float(
            sb.number_input(
                "Monthly non-housing expenses ($)",
                min_value=0.0,
                max_value=50_000.0,
                value=4_000.0,
                step=250.0,
                format="%.0f",
            )
        )
        income_growth_pct = float(
            sb.number_input(
                "Annual income growth (%)",
                min_value=0.0,
                max_value=20.0,
                value=2.0,
                step=0.25,
                format="%.2f",
            )
        )
        budget_allow_withdraw = sb.checkbox(
            "Allow portfolio withdrawals to cover shortfall",
            value=True,
        )

    # ── Advanced / display options ────────────────────────────────────────────
    sb.header("Display Options")
    assume_sale_end = sb.checkbox("Assume sale at horizon", value=True)
    show_liquidation_view = sb.checkbox("Show liquidation net worth", value=True)
    discount_rate_pct = float(
        sb.number_input(
            "Discount rate for PV (%)",
            min_value=0.0,
            max_value=15.0,
            value=0.0,
            step=0.25,
            format="%.2f",
        )
    )
    canadian_compounding = sb.checkbox(
        "Canadian semi-annual mortgage compounding",
        value=True,
    )
    prop_tax_growth_model = sb.selectbox(
        "Property tax growth model",
        options=[
            "Hybrid (recommended for Toronto)",
            "CPI only",
            "Assessment-linked",
        ],
        index=0,
    )
    prop_tax_hybrid_addon_pct = 0.5
    if prop_tax_growth_model == "Hybrid (recommended for Toronto)":
        prop_tax_hybrid_addon_pct = float(
            sb.number_input(
                "Hybrid model addon (%/yr)",
                min_value=0.0,
                max_value=5.0,
                value=0.5,
                step=0.1,
                format="%.1f",
            )
        )

    # ── Build complete config dict ────────────────────────────────────────────
    cfg: Dict[str, Any] = {
        # Horizon & location
        "years": int(years),
        "province": str(province),
        "toronto_property": bool(toronto),
        "first_time_buyer": bool(first_time),
        # Property & mortgage
        "price": float(price),
        "down": float(down),
        "rate": float(rate),
        "nm": int(nm),
        "mort": float(mort),
        "close": float(close),
        "pst": float(pst),
        "sell_cost": float(sell_cost_pct) / 100.0,
        # Ongoing owner costs (rates as decimals)
        "p_tax_rate": float(p_tax_rate_pct) / 100.0,
        "maint_rate": float(maint_rate_pct) / 100.0,
        "repair_rate": float(repair_rate_pct) / 100.0,
        "condo": float(condo),
        "condo_inf": float(condo_inf_pct) / 100.0,
        "h_ins": float(h_ins),
        "o_util": float(o_util),
        "home_sale_legal_fee": float(home_sale_legal_fee),
        # Rental
        "rent": float(rent),
        "r_ins": float(r_ins),
        "r_util": float(r_util),
        "moving_cost": float(moving_cost),
        "moving_freq": float(moving_freq),
        # Rent control
        "rent_control_enabled": bool(rent_control_enabled),
        "rent_control_cap": rent_control_cap,
        "rent_control_frequency_years": int(rent_control_frequency_years),
        # Economic
        "general_inf": float(general_inf_pct) / 100.0,
        "rent_inf": float(rent_inf_pct) / 100.0,
        "discount_rate": float(discount_rate_pct) / 100.0,
        "canadian_compounding": bool(canadian_compounding),
        "prop_tax_growth_model": str(prop_tax_growth_model),
        "prop_tax_hybrid_addon_pct": float(prop_tax_hybrid_addon_pct),
        # Investment & tax
        "investment_tax_mode": str(investment_tax_mode),
        "tax_r": float(tax_r),
        "cg_tax_end": float(cg_tax_end),
        # Mortgage rate scenarios
        "rate_mode": str(rate_mode),
        "rate_reset_years_eff": rate_reset_years_eff,
        "rate_reset_to_eff": rate_reset_to_eff,
        "rate_reset_step_pp_eff": float(rate_reset_step_pp_eff),
        "rate_shock_enabled_eff": bool(rate_shock_enabled_eff),
        "rate_shock_start_year_eff": int(rate_shock_start_year_eff),
        "rate_shock_duration_years_eff": int(rate_shock_duration_years_eff),
        "rate_shock_pp_eff": float(rate_shock_pp_eff),
        # Monte Carlo
        "use_volatility": bool(use_volatility),
        "num_sims": int(num_sims),
        "ret_std": float(ret_std),
        "apprec_std": float(apprec_std),
        # Budget mode
        "budget_enabled": bool(budget_enabled),
        "monthly_income": float(monthly_income),
        "monthly_nonhousing": float(monthly_nonhousing),
        "income_growth_pct": float(income_growth_pct),
        "budget_allow_withdraw": bool(budget_allow_withdraw),
        # Display
        "assume_sale_end": bool(assume_sale_end),
        "show_liquidation_view": bool(show_liquidation_view),
        # Extra keys used as positional args in run_simulation_core
        "buyer_ret": float(buyer_ret),
        "renter_ret": float(renter_ret),
        "apprec": float(apprec),
        "invest_diff": float(invest_diff),
        "rent_closing": bool(rent_closing),
        "mkt_corr": float(mkt_corr),
    }

    return cfg
