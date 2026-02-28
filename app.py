"""Entry point for the Rent‑vs‑Buy Streamlit application.

This orchestrator module imports the various UI components defined in
``rbv/ui`` and coordinates the flow of data between user inputs, the
core simulation engine, and the visualisations. The goal of this file
is to remain as thin as possible: it should handle high‑level page
layout and rely on helper functions defined elsewhere for the bulk of
the work.

Phase 2 of the technical audit refactors the original monolithic
``app.py`` into a series of submodules. As such, this file no longer
contains all UI definitions, but instead delegates to modules under
``rbv/ui``. Additional core utilities such as validation warnings
remain in ``rbv/core``.
"""

from __future__ import annotations

import streamlit as st

from rbv.core.engine import run_simulation_core
from rbv.core.validation import get_validation_warnings  # type: ignore
from rbv.ui.sidebar_inputs import render_sidebar
from rbv.ui.charts import (
    render_net_worth_chart,
    render_monthly_cost_table,
    render_heatmap,
)
from rbv.ui.verdict import render_verdict
from rbv.ui.bias_dashboard import render_bias_dashboard
from rbv.ui.scenarios import render_scenario_ui


def run_simulation(cfg: dict) -> dict:
    """Run the rent-vs-buy simulation via the core engine.

    Parameters
    ----------
    cfg : dict
        Configuration dictionary produced by ``render_sidebar``.  Must
        include all keys expected by ``run_simulation_core`` as well as
        the extra keys ``buyer_ret``, ``renter_ret``, ``apprec``,
        ``invest_diff``, ``rent_closing``, and ``mkt_corr`` which are
        passed as positional/keyword arguments to the engine.

    Returns
    -------
    dict
        Results dictionary containing the raw DataFrame (``df``),
        derived time-series lists, final net-worth scalars, and other
        engine outputs.
    """
    try:
        df, close_cash, m_pmt, win_pct = run_simulation_core(
            cfg,
            buyer_ret_pct=float(cfg.get("buyer_ret", 7.0)),
            renter_ret_pct=float(cfg.get("renter_ret", 7.0)),
            apprec_pct=float(cfg.get("apprec", 3.5)),
            invest_diff=float(cfg.get("invest_diff", 0.0)),
            rent_closing=bool(cfg.get("rent_closing", False)),
            mkt_corr=float(cfg.get("mkt_corr", 0.25)),
            force_deterministic=not bool(cfg.get("use_volatility", False)),
            num_sims_override=max(1, int(cfg.get("num_sims", 1) or 1)),
            budget_enabled=bool(cfg.get("budget_enabled", False)),
            monthly_income=float(cfg.get("monthly_income", 0.0)),
            monthly_nonhousing=float(cfg.get("monthly_nonhousing", 0.0)),
            income_growth_pct=float(cfg.get("income_growth_pct", 0.0)),
            budget_allow_withdraw=bool(cfg.get("budget_allow_withdraw", True)),
        )
    except Exception as e:
        return {
            "error": str(e),
            "final_buyer_net_worth": 0.0,
            "final_renter_net_worth": 0.0,
        }

    # Normalise to a plain dict for the UI components
    time_col = "Year" if "Year" in df.columns else "Month"
    results: dict = {
        "df": df,
        "close_cash": close_cash,
        "m_pmt": m_pmt,
        "win_pct": win_pct,
        # Time-series lists used by charts
        "time": df[time_col].tolist(),
        "buyer_networth": df["Buyer Net Worth"].tolist(),
        "renter_networth": df["Renter Net Worth"].tolist(),
        # Final scalars used by verdict and other summary widgets
        "final_buyer_net_worth": float(df.iloc[-1]["Buyer Net Worth"]),
        "final_renter_net_worth": float(df.iloc[-1]["Renter Net Worth"]),
    }
    # Include liquidation series when present
    if "Buyer Liquidation NW" in df.columns:
        results["buyer_liquidation_networth"] = df["Buyer Liquidation NW"].tolist()
        results["final_buyer_liquidation_nw"] = float(df.iloc[-1]["Buyer Liquidation NW"])
    if "Renter Liquidation NW" in df.columns:
        results["renter_liquidation_networth"] = df["Renter Liquidation NW"].tolist()
        results["final_renter_liquidation_nw"] = float(df.iloc[-1]["Renter Liquidation NW"])
    return results


def main() -> None:
    """Main entry point for the Streamlit app."""
    st.set_page_config(
        page_title="Rent vs Buy Simulator",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Render the sidebar and obtain user inputs
    cfg = render_sidebar(st)

    # Show validation warnings, if any
    warnings = get_validation_warnings(cfg)
    for warning in warnings:
        st.warning(warning)

    # Run the simulation
    results = run_simulation(cfg)

    # Surface engine errors gracefully
    if "error" in results:
        st.error(f"Simulation error: {results['error']}")
        return

    # Display verdict banner
    render_verdict(cfg, results, st)

    # Render charts and tables in separate tabs
    tab1, tab2, tab3 = st.tabs(["Net Worth", "Costs", "Sensitivity"])
    with tab1:
        render_net_worth_chart(cfg, results, st)
    with tab2:
        render_monthly_cost_table(cfg, results, st)
    with tab3:
        render_heatmap(cfg, results, st)
        render_bias_dashboard(cfg, results, st)

    # Scenario save/load UI
    render_scenario_ui(st, cfg, results)


if __name__ == "__main__":
    main()
