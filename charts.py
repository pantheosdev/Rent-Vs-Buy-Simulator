"""Chart rendering module for the Rent‑vs‑Buy simulator.

This module encapsulates the logic for rendering charts and tables in
the Streamlit user interface. The original ``app.py`` contained a
combination of functions and inline code to produce net worth plots,
monthly cost breakdowns, sensitivity heatmaps and other visualisations.

Separating the charting logic into this module improves readability
and makes it possible to unit test individual chart functions. Each
function should accept pre‑computed simulation results and relevant
configuration parameters, and it should use ``streamlit`` or
``plotly`` to display the output.

Functions
---------
render_net_worth_chart(cfg, results, st)
    Render the net worth comparison chart for buyer vs renter.

render_monthly_cost_table(cfg, results, st)
    Render a table summarising ongoing housing costs.

render_heatmap(cfg, results, st)
    Render a sensitivity heatmap (e.g., appreciation vs rent growth).
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import streamlit as st


def render_net_worth_chart(cfg: Dict[str, Any], results: Any, st_module: Any) -> None:
    """Render the net worth comparison chart.

    Parameters
    ----------
    cfg : Dict[str, Any]
        Configuration dictionary produced by ``render_sidebar``.
    results : Any
        Simulation results (likely a pandas DataFrame or similar) from
        the core engine.
    st_module : Any
        The Streamlit module instance used for rendering.

    Notes
    -----
    This function is a placeholder. The existing chart generation
    logic in ``app.py`` (using Plotly or Altair) should be moved here.
    """
    st_module.write("Net worth chart placeholder. Implement using Plotly.")


def render_monthly_cost_table(cfg: Dict[str, Any], results: Any, st_module: Any) -> None:
    """Render a table summarising ongoing housing costs for buyer and renter.

    Parameters
    ----------
    cfg : Dict[str, Any]
        Configuration dictionary from sidebar inputs.
    results : Any
        Simulation results containing cost breakdowns.
    st_module : Any
        The Streamlit module instance used for rendering.

    Notes
    -----
    This function currently shows a placeholder message. When
    implementing Phase 2 fully, port the existing cost table logic
    from ``app.py`` to this function.
    """
    st_module.write("Monthly cost table placeholder. Implement actual table here.")


def render_heatmap(cfg: Dict[str, Any], results: Any, st_module: Any) -> None:
    """Render a sensitivity heatmap for the simulation.

    Parameters
    ----------
    cfg : Dict[str, Any]
        Configuration dictionary from sidebar inputs.
    results : Any
        Simulation results used to compute heatmap values.
    st_module : Any
        The Streamlit module instance used for rendering.

    Notes
    -----
    This function is currently a placeholder. The heatmap computation
    and visualisation logic from ``app.py`` should be migrated here.
    """
    st_module.write("Heatmap placeholder. Implement heatmap rendering.")
