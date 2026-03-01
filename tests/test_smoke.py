"""Pytest wrappers for the RBV core smoke checks."""

from __future__ import annotations

from rbv.core.engine import run_simulation_core


def test_smoke_import() -> None:
    """Engine import succeeds."""
    assert run_simulation_core is not None


def test_smoke_deterministic() -> None:
    """Deterministic simulation returns a non-empty result."""

    cfg = {
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
        "use_volatility": True,
        "ret_std": 0.15,
        "apprec_std": 0.10,
        "prop_tax_growth_model": "Hybrid (recommended for Toronto)",
        "prop_tax_hybrid_addon_pct": 0.5,
        "investment_tax_mode": "Pre-tax (no investment taxes)",
        "assume_sale_end": True,
        "show_liquidation_view": True,
    }

    df, _close_cash, _m_pmt, _win_pct = run_simulation_core(
        cfg,
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

    assert df is not None
    assert len(df) >= 1
