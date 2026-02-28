"""Sidebar input module for the Rent‑vs‑Buy simulator.

This module encapsulates all logic related to rendering the sidebar
controls in the Streamlit user interface. By isolating the sidebar
inputs here, we avoid cluttering the main application file and
facilitate independent testing and reuse of input widgets.

The original ``app.py`` contained a large ``with st.sidebar`` block
responsible for constructing dozens of number inputs, checkboxes,
select boxes and help tooltips. That logic should be migrated into
functions defined in this module. Each function should return a
configuration dictionary or update the Streamlit session state as
appropriate.

Example usage in ``app.py``::

    import streamlit as st
    from rbv.ui.sidebar_inputs import render_sidebar

    def main():
        # Draw the sidebar and capture user selections
        cfg = render_sidebar(st)
        # Use ``cfg`` to run simulations and render charts

Functions
---------
render_sidebar(st)
    Render the sidebar widgets and return a configuration dictionary.
"""
from __future__ import annotations

from typing import Any, Dict

import streamlit as st


def render_sidebar(st_module: Any) -> Dict[str, Any]:
    """Render the sidebar widgets and return a configuration dictionary.

    This function encapsulates the Streamlit widgets that allow a user to
    customise the rent‑vs‑buy analysis. It replaces the monolithic sidebar
    construction from the original ``app.py`` with a concise and focused
    implementation. Only a subset of the original inputs are exposed for
    demonstration purposes. Additional fields (e.g., taxes, rent control,
    amortisation schedule) should be added here as part of incremental
    refactoring.

    Parameters
    ----------
    st_module : Any
        The Streamlit module instance to use for rendering widgets. In most
        cases this will be the ``streamlit`` module imported in ``app.py``.

    Returns
    -------
    Dict[str, Any]
        A dictionary of user‑selected configuration values. These values
        should match the expected keys for the core simulation engine.
    """
    sidebar = st_module.sidebar
    sidebar.title("Rent vs Buy Simulator")

    # Basic property inputs
    price = sidebar.number_input(
        "Home purchase price ($)", min_value=50000.0, max_value=5_000_000.0,
        value=750_000.0, step=5_000.0, format="%.0f"
    )
    down_payment_pct = sidebar.number_input(
        "Down payment (%)", min_value=0.0, max_value=100.0,
        value=10.0, step=0.5, format="%.1f"
    )
    interest_rate = sidebar.number_input(
        "Mortgage interest rate (annual %)", min_value=0.0, max_value=20.0,
        value=5.0, step=0.1, format="%.2f"
    )

    # Basic rental/investment inputs
    rent_amount = sidebar.number_input(
        "Monthly rent ($)", min_value=0.0, max_value=20_000.0,
        value=3_000.0, step=50.0, format="%.0f"
    )
    investment_return_pct = sidebar.number_input(
        "Expected annual investment return (%)", min_value=-10.0, max_value=20.0,
        value=5.0, step=0.5, format="%.1f"
    )

    # Build configuration dictionary. Keys mirror those expected by the
    # engine's ``_build_cfg`` in the original implementation. Additional
    # parameters can be added as new inputs are ported.
    cfg: Dict[str, Any] = {
        "price": float(price),
        "down_payment_pct": float(down_payment_pct) / 100.0,  # convert to fraction
        "interest_rate_annual_pct": float(interest_rate),
        "rent": float(rent_amount),
        "investment_return_pct": float(investment_return_pct),
    }

    return cfg
