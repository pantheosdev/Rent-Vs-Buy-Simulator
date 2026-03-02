"""Tests verifying that run_simulation_core clamps/validates invalid inputs."""

from __future__ import annotations

import warnings

import pytest

from rbv.core.engine import run_simulation_core

_BASE_CFG = {
    "years": 5,
    "province": "ON",
    "price": 800_000.0,
    "rent": 3_200.0,
    "down": 160_000.0,
    "rate": 5.0,
    "nm": 300,
    "sell_cost": 0.05,
    "p_tax_rate": 0.007,
    "maint_rate": 0.01,
    "repair_rate": 0.002,
    "h_ins": 90.0,
    "r_ins": 25.0,
    "general_inf": 0.02,
    "rent_inf": 0.02,
    "discount_rate": 0.0,
    "canadian_compounding": True,
    "use_volatility": False,
    "ret_std": 0.15,
    "apprec_std": 0.10,
    "prop_tax_growth_model": "Hybrid (recommended for Toronto)",
    "prop_tax_hybrid_addon_pct": 0.5,
    "investment_tax_mode": "Pre-tax (no investment taxes)",
    "assume_sale_end": True,
    "show_liquidation_view": True,
}

_BASE_KWARGS = dict(
    buyer_ret_pct=7.0,
    renter_ret_pct=7.0,
    apprec_pct=3.0,
    invest_diff=0.0,
    rent_closing=False,
    mkt_corr=0.25,
    force_deterministic=True,
    mc_seed=123,
    force_use_volatility=False,
    num_sims_override=1,
)


def _run(cfg_overrides=None, **kwargs):
    cfg = {**_BASE_CFG, **(cfg_overrides or {})}
    kw = {**_BASE_KWARGS, **kwargs}
    return run_simulation_core(cfg, **kw)


def test_negative_home_price_clamped():
    """A negative home price should be clamped to 0 with a warning."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        df, _close, _pmt, _win = _run({"price": -50_000.0, "down": 0.0})
    assert df is not None
    messages = [str(w.message) for w in caught]
    assert any("Home price" in m for m in messages), f"Expected 'Home price' warning, got: {messages}"


def test_zero_years_clamped_to_one():
    """years=0 should be clamped to 1 with a warning, and the simulation completes."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        df, _close, _pmt, _win = _run({"years": 0})
    assert df is not None
    assert len(df) >= 1


def test_excessive_buyer_ret_clamped():
    """buyer_ret_pct > 50 should be clamped to 50."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        df, _close, _pmt, _win = _run(buyer_ret_pct=999.0)
    assert df is not None
    messages = [str(w.message) for w in caught]
    assert any("Buyer investment return" in m for m in messages), (
        f"Expected 'Buyer investment return' warning, got: {messages}"
    )


def test_excessive_mortgage_rate_clamped():
    """A mortgage rate above 25% should be clamped and produce a warning."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        df, _close, _pmt, _win = _run({"rate": 500.0})
    assert df is not None
    messages = [str(w.message) for w in caught]
    assert any("Mortgage rate" in m for m in messages), (
        f"Expected 'Mortgage rate' warning, got: {messages}"
    )


def test_negative_rent_clamped():
    """A negative monthly rent should be clamped to 0 with a warning."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        df, _close, _pmt, _win = _run({"rent": -100.0})
    assert df is not None
    messages = [str(w.message) for w in caught]
    assert any("Monthly rent" in m for m in messages), f"Expected 'Monthly rent' warning, got: {messages}"


def test_valid_inputs_no_warnings():
    """Normal valid inputs should produce no validation warnings."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        df, _close, _pmt, _win = _run()
    assert df is not None
    # Filter to only warnings from the validation module
    val_warnings = [w for w in caught if "validation" in (w.filename or "").lower() or "Clamping" in str(w.message)]
    assert len(val_warnings) == 0, f"Unexpected validation warnings: {[str(w.message) for w in val_warnings]}"
