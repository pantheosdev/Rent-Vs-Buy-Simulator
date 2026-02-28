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

from typing import Any, Dict


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
    fig.add_trace(go.Scatter(x=time, y=buyer, mode='lines', name='Buyer Net Worth', line=dict(color='#00B8A9')))
    fig.add_trace(go.Scatter(x=time, y=renter, mode='lines', name='Renter Net Worth', line=dict(color='#F6416C')))
    fig.update_layout(
        title="Net Worth Comparison",
        xaxis_title="Time",
        yaxis_title="Net Worth ($)",
        legend_title="Scenario",
        template="plotly_white",
    )
    st_module.plotly_chart(fig, use_container_width=True)


def render_monthly_cost_table(cfg: Dict[str, Any], results: Any, st_module: Any) -> None:
    """Render a table summarising cumulative housing costs for buyer and renter.

    Uses ``rbv.ui.costs_tab.build_costs_core`` to extract cost breakdowns
    from the engine DataFrame (``results['df']``) when available.  Falls back
    to explicit ``buyer_monthly_costs`` / ``renter_monthly_costs`` dicts if
    the DataFrame is absent for backwards compatibility.

    Parameters
    ----------
    cfg : Dict[str, Any]
        Configuration dictionary from sidebar inputs.
    results : Any
        Simulation results dict.  Must contain ``results['df']`` (the
        engine DataFrame) or pre-computed ``buyer_monthly_costs`` /
        ``renter_monthly_costs`` dicts.
    st_module : Any
        The Streamlit module instance used for rendering.
    """
    import pandas as pd

    # ── Primary path: use the engine DataFrame via build_costs_core ──────────
    df_engine = None
    if isinstance(results, dict):
        df_engine = results.get("df")

    if df_engine is not None:
        try:
            from rbv.ui.costs_tab import build_costs_core, build_cost_mix_dataframe

            costs = build_costs_core(df_engine)
            series = costs["series"]
            totals = costs["totals"]

            # Cumulative totals per category
            categories = [
                "Interest",
                "Property Tax",
                "Maintenance",
                "Repairs",
                "Condo Fees",
                "Home Insurance",
                "Utilities",
                "Special Assessment",
            ]
            series_keys = [
                "b_interest",
                "b_tax",
                "b_maint",
                "b_repairs",
                "b_condo",
                "b_ins",
                "b_util",
                "b_special",
            ]
            buyer_vals = [float(series[k].sum()) for k in series_keys]

            renter_categories = ["Rent", "Rent Insurance", "Rent Utilities", "Moving"]
            renter_keys = ["r_rent", "r_ins", "r_util", "r_move"]
            renter_vals = [float(series[k].sum()) for k in renter_keys]

            # Build display table
            buyer_rows = [
                {"Party": "Buyer", "Category": cat, "Cumulative ($)": val}
                for cat, val in zip(categories, buyer_vals)
                if abs(val) > 0.01
            ]
            renter_rows = [
                {"Party": "Renter", "Category": cat, "Cumulative ($)": val}
                for cat, val in zip(renter_categories, renter_vals)
                if abs(val) > 0.01
            ]
            df_display = pd.DataFrame(buyer_rows + renter_rows)
            if not df_display.empty:
                df_display["Cumulative ($)"] = df_display["Cumulative ($)"].map(lambda x: f"${x:,.0f}")
                st_module.subheader("Cumulative Cost Breakdown")
                st_module.dataframe(df_display, use_container_width=True, hide_index=True)

                col1, col2 = st_module.columns(2)
                with col1:
                    st_module.metric(
                        "Total Buyer Costs",
                        f"${totals['buyer_total_actual']:,.0f}",
                    )
                with col2:
                    st_module.metric(
                        "Total Renter Costs",
                        f"${totals['renter_total_actual']:,.0f}",
                    )
            else:
                st_module.info("No cost breakdown data available for this simulation.")
            return
        except Exception as exc:
            st_module.warning(f"Could not build cost breakdown: {exc}")
            return

    # ── Fallback: pre-computed dicts (backwards compatibility) ────────────────
    buyer_costs = None
    renter_costs = None
    if isinstance(results, dict):
        buyer_costs = results.get("buyer_monthly_costs")
        renter_costs = results.get("renter_monthly_costs")
    else:
        buyer_costs = getattr(results, "buyer_monthly_costs", None)
        renter_costs = getattr(results, "renter_monthly_costs", None)

    if not buyer_costs or not renter_costs:
        st_module.info("Cost breakdown requires simulation results to be available.")
        return

    all_keys = sorted(set(buyer_costs.keys()) | set(renter_costs.keys()))
    df = pd.DataFrame(
        {
            "Category": all_keys,
            "Buyer ($/mo)": [buyer_costs.get(k, 0.0) for k in all_keys],
            "Renter ($/mo)": [renter_costs.get(k, 0.0) for k in all_keys],
        }
    )
    st_module.table(df)


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
    This function attempts to display a heatmap using precomputed matrix
    data in the ``results`` object.  The original application computed
    sensitivity matrices for parameters like appreciation and rent
    growth; those arrays should be made available as
    ``results['heatmap_matrix']`` with corresponding axis labels
    ``results['heatmap_x']`` and ``results['heatmap_y']``.
    If these fields are missing, a placeholder message is displayed.
    """
    import numpy as np
    import plotly.express as px

    # Attempt to extract heatmap data from results
    matrix = None
    x_labels = None
    y_labels = None
    if isinstance(results, dict):
        matrix = results.get('heatmap_matrix')
        x_labels = results.get('heatmap_x')
        y_labels = results.get('heatmap_y')
    else:
        matrix = getattr(results, 'heatmap_matrix', None)
        x_labels = getattr(results, 'heatmap_x', None)
        y_labels = getattr(results, 'heatmap_y', None)

    if matrix is None or x_labels is None or y_labels is None:
        st_module.info(
            "Heatmap data not available. To display a heatmap, include "
            "'heatmap_matrix', 'heatmap_x' and 'heatmap_y' in the results."
        )
        return

    # Convert to numpy array for Plotly
    matrix_np = np.array(matrix)
    fig = px.imshow(matrix_np, x=x_labels, y=y_labels, color_continuous_scale='Viridis')
    fig.update_layout(
        title="Sensitivity Heatmap",
        xaxis_title="Parameter X",
        yaxis_title="Parameter Y",
    )
    st_module.plotly_chart(fig, use_container_width=True)
