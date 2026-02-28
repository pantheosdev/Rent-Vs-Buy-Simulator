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
    """Render a net worth comparison chart for buyer vs renter.

    This implementation extracts time-series net worth data from the provided
    ``results`` object and plots it as a line chart using Plotly.  It is
    designed to mirror the behaviour of the original monolithic ``app.py``
    chart but in a modular function that can be unit tested.

    Parameters
    ----------
    cfg : Dict[str, Any]
        Configuration dictionary produced by ``render_sidebar``.  It may contain
        options that affect chart styling (e.g., colours) in future
        iterations.
    results : Any
        Simulation results from the core engine.  The object should expose
        ``results['time']`` for the horizontal axis and two series
        ``results['buyer_networth']`` and ``results['renter_networth']`` for
        the buyer and renter cumulative net worth.  If these keys are not
        present, the function will attempt to fall back to reasonable
        alternatives or emit an informative message.
    st_module : Any
        The Streamlit module instance used for rendering.  Passing it
        explicitly allows this function to be called from outside the main
        ``app.py`` while still using Streamlit primitives.

    Notes
    -----
    The plotting code uses Plotly directly to avoid coupling to Streamlit
    specifics beyond the final ``st_module.plotly_chart`` call.  You may need
    to adjust the field names if the engine results change.  If the
    simulation results object is missing expected fields, this function
    displays a warning rather than raising an exception.
    """
    import plotly.graph_objects as go
    # Validate input structure
    time = None
    buyer = None
    renter = None
    if isinstance(results, dict):
        time = results.get('time') or results.get('Year') or results.get('year')
        buyer = results.get('buyer_networth') or results.get('Buyer Net Worth')
        renter = results.get('renter_networth') or results.get('Renter Net Worth')
    else:
        # Attempt to handle pandas-like objects (e.g., DataFrame)
        try:
            time = results['time'] if 'time' in results else results['Year']
            buyer = results['buyer_networth'] if 'buyer_networth' in results else results['Buyer Net Worth']
            renter = results['renter_networth'] if 'renter_networth' in results else results['Renter Net Worth']
        except Exception:
            pass
    # Check that all series are available
    if time is None or buyer is None or renter is None:
        st_module.warning(
            "Unable to render net worth chart: simulation results missing required fields "
            "('time', 'buyer_networth', 'renter_networth')."
        )
        return
    # Build Plotly figure
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=time, y=buyer, mode='lines', name='Buyer Net Worth',
                             line=dict(color='#00B8A9')))
    fig.add_trace(go.Scatter(x=time, y=renter, mode='lines', name='Renter Net Worth',
                             line=dict(color='#F6416C')))
    fig.update_layout(
        title="Net Worth Comparison",
        xaxis_title="Time",
        yaxis_title="Net Worth ($)",
        legend_title="Scenario",
        template="plotly_white",
    )
    st_module.plotly_chart(fig, use_container_width=True)


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
    implementing Phase 2 fully, port the existing cost table logic
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
