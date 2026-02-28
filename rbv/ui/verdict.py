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
    # Determine final net worth values for buyer and renter.
    # We attempt multiple keys for robustness.
    # Use explicit `is None` check so that legitimate 0.0 values are honoured.
    _raw_buyer = results.get("final_buyer_net_worth")
    _raw_renter = results.get("final_renter_net_worth")
    buyer_value = float(_raw_buyer) if _raw_buyer is not None else None
    renter_value = float(_raw_renter) if _raw_renter is not None else None

    # Fall back to the last entry in net worth series when scalar is absent.
    if buyer_value is None or renter_value is None:
        buyer_series = results.get("buyer_networth") or results.get("Buyer Net Worth")
        renter_series = results.get("renter_networth") or results.get("Renter Net Worth")
        try:
            if buyer_value is None and buyer_series is not None:
                buyer_value = float(buyer_series[-1])
            if renter_value is None and renter_series is not None:
                renter_value = float(renter_series[-1])
        except Exception:
            pass

    # Default to 0.0 if still missing
    if buyer_value is None:
        buyer_value = 0.0
    if renter_value is None:
        renter_value = 0.0

    # Compare final values and build verdict message
    diff = buyer_value - renter_value
    if diff > 0:
        verdict_text = f"Buying leads by ${diff:,.0f}"
        banner_class = "buyer-win"
    elif diff < 0:
        verdict_text = f"Renting leads by ${abs(diff):,.0f}"
        banner_class = "renter-win"
    else:
        verdict_text = "Buying and renting end up equal"
        banner_class = "tie"

    # Render the verdict banner using pre-defined CSS classes.
    st_module.markdown(
        f"<div class='verdict-banner {banner_class}'>\n  <span class='verdict-text'>{verdict_text}</span>\n</div>",
        unsafe_allow_html=True,
    )
