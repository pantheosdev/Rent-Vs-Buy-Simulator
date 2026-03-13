from __future__ import annotations

import numpy as np

from rbv.core.engine import run_heatmap_mc_batch, run_simulation_core
from rbv.core.purchase_derivations import enrich_cfg_with_purchase_derivations


def _base_cfg(**overrides):
    cfg = {
        "years": 5,
        "province": "Ontario",
        "toronto": True,
        "first_time": False,
        "asof_date": "2026-01-15",
        "price": 800_000.0,
        "rent": 3_100.0,
        "down": 160_000.0,
        "rate": 4.8,
        "nm": 300,
        "sell_cost": 0.05,
        "p_tax_rate": 0.0065,
        "maint_rate": 0.01,
        "repair_rate": 0.002,
        "condo": 650.0,
        "condo_inf": 0.02,
        "h_ins": 95.0,
        "o_util": 120.0,
        "r_ins": 30.0,
        "r_util": 70.0,
        "general_inf": 0.02,
        "rent_inf": 0.025,
        "discount_rate": 0.0,
        "canadian_compounding": True,
        "ret_std": 0.0,
        "apprec_std": 0.0,
        "prop_tax_growth_model": "Hybrid (recommended for Toronto)",
        "prop_tax_hybrid_addon_pct": 0.5,
        "investment_tax_mode": "Pre-tax (no investment taxes)",
        "assume_sale_end": True,
        "show_liquidation_view": True,
        "moving_cost": 0.0,
        "moving_freq": 7.0,
        "purchase_legal_fee": 1800.0,
        "home_inspection": 500.0,
        "other_closing_costs": 0.0,
    }
    cfg.update(overrides)
    return cfg


def _terminal_delta_from_main(
    cfg: dict,
    *,
    invest_diff: bool,
    apprec_pct: float = 3.0,
    rent_inf_pct: float = 2.5,
    buyer_ret_pct: float = 6.0,
    renter_ret_pct: float = 6.0,
    num_sims_override: int = 64,
    **kwargs,
) -> float:
    df, _close, _pmt, _win = run_simulation_core(
        cfg,
        buyer_ret_pct=buyer_ret_pct,
        renter_ret_pct=renter_ret_pct,
        apprec_pct=apprec_pct,
        invest_diff=invest_diff,
        rent_closing=False,
        mkt_corr=0.25,
        force_deterministic=False,
        mc_seed=123,
        rate_override_pct=None,
        rent_inf_override_pct=rent_inf_pct,
        force_use_volatility=True,
        num_sims_override=num_sims_override,
        **kwargs,
    )
    if "Buyer NW Mean" in df.columns and "Renter NW Mean" in df.columns:
        return float(df.iloc[-1]["Buyer NW Mean"] - df.iloc[-1]["Renter NW Mean"])
    return float(df.iloc[-1]["Buyer Net Worth"] - df.iloc[-1]["Renter Net Worth"])


def test_heatmap_matches_main_engine_when_invest_diff_false() -> None:
    cfg = _base_cfg(ret_std=0.0, apprec_std=0.0)

    _win_z, delta_z, _pv_z = run_heatmap_mc_batch(
        cfg,
        buyer_ret_pct=6.0,
        renter_ret_pct=6.0,
        app_vals_pct=np.array([3.0]),
        rent_vals_pct=np.array([2.5]),
        invest_diff=False,
        rent_closing=False,
        mkt_corr=0.25,
        num_sims=32,
        mc_seed=123,
    )

    expected = _terminal_delta_from_main(cfg, invest_diff=False, apprec_pct=3.0, rent_inf_pct=2.5, num_sims_override=32)
    np.testing.assert_allclose(delta_z[0, 0], expected, rtol=0.0, atol=5.0)


def test_heatmap_crisis_keeps_cash_unshocked_when_invest_diff_false() -> None:
    cfg = _base_cfg(ret_std=0.0, apprec_std=0.0)

    _win_z, delta_z, _pv_z = run_heatmap_mc_batch(
        cfg,
        buyer_ret_pct=6.0,
        renter_ret_pct=6.0,
        app_vals_pct=np.array([3.0]),
        rent_vals_pct=np.array([2.5]),
        invest_diff=False,
        rent_closing=False,
        mkt_corr=0.25,
        num_sims=32,
        mc_seed=123,
        crisis_enabled=True,
        crisis_year=2,
        crisis_stock_dd=0.30,
        crisis_house_dd=0.10,
        crisis_duration_months=1,
    )

    expected = _terminal_delta_from_main(
        cfg,
        invest_diff=False,
        apprec_pct=3.0,
        rent_inf_pct=2.5,
        num_sims_override=32,
        crisis_enabled=True,
        crisis_year=2,
        crisis_stock_dd=0.30,
        crisis_house_dd=0.10,
        crisis_duration_months=1,
    )
    np.testing.assert_allclose(delta_z[0, 0], expected, rtol=0.0, atol=5.0)


def test_heatmap_autoderives_purchase_fields_when_missing() -> None:
    cfg_missing = _base_cfg()
    cfg_missing.pop("mort", None)
    cfg_missing.pop("close", None)
    cfg_missing.pop("pst", None)
    cfg_enriched = enrich_cfg_with_purchase_derivations(cfg_missing, strict=False)

    _w1, delta_missing, _p1 = run_heatmap_mc_batch(
        cfg_missing,
        buyer_ret_pct=6.0,
        renter_ret_pct=6.0,
        app_vals_pct=np.array([3.0]),
        rent_vals_pct=np.array([2.5]),
        invest_diff=False,
        rent_closing=False,
        mkt_corr=0.25,
        num_sims=16,
        mc_seed=123,
    )
    _w2, delta_enriched, _p2 = run_heatmap_mc_batch(
        cfg_enriched,
        buyer_ret_pct=6.0,
        renter_ret_pct=6.0,
        app_vals_pct=np.array([3.0]),
        rent_vals_pct=np.array([2.5]),
        invest_diff=False,
        rent_closing=False,
        mkt_corr=0.25,
        num_sims=16,
        mc_seed=123,
    )

    np.testing.assert_allclose(delta_missing, delta_enriched, rtol=0.0, atol=1e-4)


def test_heatmap_volatility_normalization_matches_decimal_inputs() -> None:
    cfg_percent_like = _base_cfg(ret_std=1.5, apprec_std=1.5)
    cfg_decimal = _base_cfg(ret_std=0.015, apprec_std=0.015)

    win_pct_a, delta_a, pv_a = run_heatmap_mc_batch(
        cfg_percent_like,
        buyer_ret_pct=6.0,
        renter_ret_pct=6.0,
        app_vals_pct=np.array([3.0]),
        rent_vals_pct=np.array([2.5]),
        invest_diff=True,
        rent_closing=False,
        mkt_corr=0.25,
        num_sims=64,
        mc_seed=123,
    )
    win_pct_b, delta_b, pv_b = run_heatmap_mc_batch(
        cfg_decimal,
        buyer_ret_pct=6.0,
        renter_ret_pct=6.0,
        app_vals_pct=np.array([3.0]),
        rent_vals_pct=np.array([2.5]),
        invest_diff=True,
        rent_closing=False,
        mkt_corr=0.25,
        num_sims=64,
        mc_seed=123,
    )

    np.testing.assert_allclose(win_pct_a, win_pct_b, rtol=0.0, atol=1e-10)
    np.testing.assert_allclose(delta_a, delta_b, rtol=0.0, atol=1e-4)
    np.testing.assert_allclose(pv_a, pv_b, rtol=0.0, atol=1e-4)
