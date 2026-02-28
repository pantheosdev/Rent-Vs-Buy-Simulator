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
    """Run the rent‑vs‑buy simulation.

    This is a placeholder function that should call into the core
    simulation engine (e.g., ``rbv.core.engine.run_simulation``) and
    return a dictionary of results. For now, it returns dummy values.

    Parameters
    ----------
    cfg : dict
        Configuration dictionary produced by ``render_sidebar``.

    Returns
    -------
    dict
        A dictionary with at least ``final_buyer_net_worth`` and
        ``final_renter_net_worth`` entries.
    """
    # TODO: import and call the real simulation engine here.
    # For demonstration purposes, we return zero net worth for both.
    return {
        "final_buyer_net_worth": 0.0,
        "final_renter_net_worth": 0.0,
        # Additional fields (e.g., time series) would appear here.
    }


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