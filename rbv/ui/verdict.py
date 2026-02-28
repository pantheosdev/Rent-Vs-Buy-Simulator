"""Verdict banner module for the Rent‑vs‑Buy simulator.

This module encapsulates the logic used to determine and display the
final verdict of the rent‑vs‑buy comparison (e.g., whether renting or
buying yields a higher net worth). In the original application, this
logic was embedded within ``app.py`` and tightly coupled with
Streamlit widgets and metrics. Separating it into its own module
improves readability and testability.

Functions
---------
render_verdict(cfg, results, st)
    Compute the outcome of the simulation and display a verdict banner.
"""
from __future__ import annotations

from typing import Any, Dict

import streamlit as st


def render_verdict(cfg: Dict[str, Any], results: Dict[str, Any], st_module: Any) -> None:
    """Compute and display the simulation verdict.

    Parameters
    ----------
    cfg : Dict[str, Any]
        The configuration dictionary returned by ``render_sidebar``.
    results : Dict[str, Any]
        A dictionary containing key outputs from the simulation engine.
        It should include the buyer net worth and renter net worth.
    st_module : Any
        The Streamlit module instance used for rendering.

    Notes
    -----
    This implementation provides a simple comparison based on
    ``final_buyer_net_worth`` and ``final_renter_net_worth`` keys in
    ``results``. Replace this logic with the more sophisticated
    verdict determination found in ``app.py``. The banner styling
    relies on CSS classes defined in ``rbv/ui/theme.py`` and is
    maintained automatically via ``inject_global_css``.
    """
    buyer_value = results.get("final_buyer_net_worth", 0)
    renter_value = results.get("final_renter_net_worth", 0)
    if buyer_value > renter_value:
        verdict_text = "Buying wins"
        banner_class = "buyer-win"
    elif renter_value > buyer_value:
        verdict_text = "Renting wins"
        banner_class = "renter-win"
    else:
        verdict_text = "It's a tie"
        banner_class = "tie"

    st_module.markdown(
        f"<div class='verdict-banner {banner_class}'>\n"
        f"  <span class='verdict-text'>{verdict_text}</span>\n"
        f"</div>",
        unsafe_allow_html=True,
    )
