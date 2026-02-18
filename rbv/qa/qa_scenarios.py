#!/usr/bin/env python3
"""Lightweight QA harness for the modular Rent-vs-Buy simulator.

Goal: catch regressions early (crashes, NaNs, missing columns) across the major
feature toggles (rent control, volatility/MC, mortgage shocks, moving, budgets, etc.).

Run:
  python qa_scenarios.py

This is NOT a proof of correctness; it is a guardrail for "public ready" stability.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root is on sys.path regardless of where this script is invoked from.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import math


def _finite(x) -> bool:
    try:
        return math.isfinite(float(x))
    except Exception:
        return False


def main() -> None:
    from rbv.core.engine import run_simulation_core
    from rbv.core.taxes import calc_transfer_tax

    # Exercise the Toronto municipal LTT path (historical brackets + 3M+ bracket).
    tax = calc_transfer_tax("Ontario", 3_500_000.0, first_time_buyer=False, toronto_property=True)
    if not _finite(tax.get("total", float("nan"))):
        raise RuntimeError(f"Toronto LTT calculation returned non-finite: {tax}")

    base_cfg = {
        "years": 10,
        "province": "Ontario",
        "price": 800_000.0,
        "rent": 3_200.0,
        "down": 160_000.0,
        "rate": 5.0,
        "nm": 300,
        "sell_cost": 0.05,
        "p_tax_rate": 0.007,
        "maint_rate": 0.01,
        "repair_rate": 0.002,
        "condo": 0.0,
        "h_ins": 90.0,
        "o_util": 200.0,
        "r_ins": 25.0,
        "r_util": 150.0,
        "moving_cost": 750.0,
        "moving_freq": 5.0,
        "mort": 640_000.0,
        "close": 25_000.0,
        "pst": 0.0,
        "discount_rate": 0.0,
        "tax_r": 0.0,
        "canadian_compounding": True,
        "general_inf": 0.02,
        "rent_inf": 0.025,
        "use_volatility": False,
        "num_sims": 0,
        "ret_std": 0.15,
        "apprec_std": 0.10,
        "prop_tax_growth_model": "Hybrid (recommended for Toronto)",
        "prop_tax_hybrid_addon_pct": 0.5,
        "investment_tax_mode": "Pre-tax (no investment taxes)",
        "assume_sale_end": True,
        "show_liquidation_view": True,
        "cg_tax_end": 0.0,
        "home_sale_legal_fee": 0.0,
        "rate_mode": "Fixed",
        "rate_reset_years_eff": None,
        "rate_reset_to_eff": None,
        "rate_reset_step_pp_eff": 0.0,
        "rate_shock_enabled_eff": False,
        "rate_shock_start_year_eff": 5,
        "rate_shock_duration_years_eff": 5,
        "rate_shock_pp_eff": 0.0,
        "rent_control_enabled": False,
        "rent_control_cap": None,
        "rent_control_frequency_years": 1,
        "condo_inf": 0.02,
    }

    scenarios = [
        ("Deterministic baseline", {"use_volatility": False}),
        ("MC small", {"use_volatility": True, "num_sims": 50}),
        ("MC medium", {"use_volatility": True, "num_sims": 300}),
        ("Rent control annual", {"rent_control_enabled": True, "rent_control_cap": 0.02, "rent_control_frequency_years": 1}),
        ("Rent control every 3y", {"rent_control_enabled": True, "rent_control_cap": 0.02, "rent_control_frequency_years": 3}),
        ("Never move", {"moving_freq": 9999.0}),
        ("Move often", {"moving_freq": 2.0, "moving_cost": 2500.0}),
        ("Rate reset", {"rate_mode": "Reset every N years", "rate_reset_years_eff": 5, "rate_reset_to_eff": 6.0, "rate_reset_step_pp_eff": 0.25}),
        ("Rate shock", {"rate_shock_enabled_eff": True, "rate_shock_start_year_eff": 3, "rate_shock_duration_years_eff": 2, "rate_shock_pp_eff": 2.0}),
        ("Negative appreciation", {}),
        ("High inflation", {"general_inf": 0.05, "rent_inf": 0.05}),
        ("High price (uninsured)", {"price": 1_400_000.0, "down": 350_000.0, "mort": 1_050_000.0, "close": 60_000.0}),
        ("Budget enabled", {}),
    ]

    required_cols = {
        "Buyer Net Worth",
        "Renter Net Worth",
        "Buyer Unrecoverable",
        "Renter Unrecoverable",
        "Rent Payment",
        "Buy Payment",
    }

    print("[QA] Running scenarios...")

    for name, overrides in scenarios:
        cfg = dict(base_cfg)
        cfg.update(overrides)

        # per-scenario param toggles
        force_det = not bool(cfg.get("use_volatility"))
        ns = int(cfg.get("num_sims") or 0)

        # Negative appreciation case via parameters, not cfg
        apprec = -1.0 if name == "Negative appreciation" else 3.0

        budget_enabled = (name == "Budget enabled")

        df, close_cash, m_pmt, win_pct = run_simulation_core(
            cfg,
            buyer_ret_pct=7.0,
            renter_ret_pct=7.0,
            apprec_pct=apprec,
            invest_diff=0.0,
            rent_closing=False,
            mkt_corr=0.25,
            force_deterministic=force_det,
            mc_seed=123,
            force_use_volatility=bool(cfg.get("use_volatility")),
            num_sims_override=(ns if ns > 0 else 1),
            budget_enabled=budget_enabled,
            monthly_income=10_000.0,
            monthly_nonhousing=4_000.0,
            income_growth_pct=2.0,
            budget_allow_withdraw=True,
        )

        if df is None or len(df) < 5:
            raise RuntimeError(f"Scenario '{name}' produced empty/short output")

        missing = required_cols.difference(df.columns)
        if missing:
            raise RuntimeError(f"Scenario '{name}' missing columns: {sorted(missing)}")

        # Last row key metrics should be finite.
        last = df.iloc[-1]
        for col in ["Buyer Net Worth", "Renter Net Worth", "Buyer Unrecoverable", "Renter Unrecoverable"]:
            if not _finite(last[col]):
                raise RuntimeError(f"Scenario '{name}' produced non-finite {col} at horizon: {last[col]}")

        if not _finite(close_cash) or close_cash < 0:
            raise RuntimeError(f"Scenario '{name}' produced invalid close_cash: {close_cash}")

        if not _finite(m_pmt) or m_pmt < 0:
            raise RuntimeError(f"Scenario '{name}' produced invalid mortgage payment: {m_pmt}")

        # Win% may be None when disabled/deterministic; if present, must be within [0, 100]
        if win_pct is not None:
            if (not _finite(win_pct)) or (win_pct < -1e-6) or (win_pct > 100.0 + 1e-6):
                raise RuntimeError(f"Scenario '{name}' produced invalid win_pct: {win_pct}")

        print(f"  OK: {name} (rows={len(df)}, close_cash={close_cash:,.0f}, m_pmt={m_pmt:,.2f}, win_pct={win_pct})")

    print("\n[QA OK] All scenarios completed without exceptions.")


if __name__ == "__main__":
    main()
