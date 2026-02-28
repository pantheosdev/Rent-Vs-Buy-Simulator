#!/usr/bin/env python3
"""Quick smoke checks for the modular RBV app.

Run:
  python smoke_check.py
"""

from __future__ import annotations
import sys
from pathlib import Path

# Ensure repo root is on sys.path regardless of where this script is invoked from.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import os
import compileall


def die(msg: str, code: int = 1) -> None:
    print(f"\n[SMOKE CHECK FAILED] {msg}\n")
    raise SystemExit(code)


def main() -> None:
    # Use repo root (two levels above rbv/qa/) so paths resolve consistently.
    root = str(Path(__file__).resolve().parents[2])

    app_py = os.path.join(root, "app.py")
    pkg_dir = os.path.join(root, "rbv")

    if not os.path.exists(app_py):
        die("app.py not found (run from the modular folder root).")

    ok_app = compileall.compile_file(app_py, quiet=1)
    ok_pkg = compileall.compile_dir(pkg_dir, quiet=1)
    if not ok_app:
        die("app.py failed to compile.")
    if not ok_pkg:
        die("rbv/ package failed to compile.")

    try:
        from rbv.core.engine import run_simulation_core
    except Exception as e:
        die(f"Import failure: {e}")

    # Note: app config uses *decimals* (e.g., 0.02 for 2%) for rates/vols.
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

    try:
        df_det, close_cash_det, m_pmt_det, win_pct_det = run_simulation_core(
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
    except Exception as e:
        die(f"Deterministic sim failed: {e}")

    if df_det is None or len(df_det) < 1:
        die("Deterministic sim returned empty result.")

    try:
        df_mc, close_cash_mc, m_pmt_mc, win_pct_mc = run_simulation_core(
            cfg,
            buyer_ret_pct=7.0,
            renter_ret_pct=7.0,
            apprec_pct=3.0,
            invest_diff=0.0,
            rent_closing=False,
            mkt_corr=0.25,
            mc_seed=123,
            force_use_volatility=True,
            num_sims_override=20,
        )
    except Exception as e:
        die(f"MC sim failed: {e}")

    if df_mc is None or len(df_mc) < 5:
        die("MC sim returned too few rows.")

    try:
        win = (df_mc["Buyer Liquidation NW"] > df_mc["Renter Liquidation NW"]).mean() * 100.0
    except Exception:
        win = (df_mc["Buyer Net Worth"] > df_mc["Renter Net Worth"]).mean() * 100.0

    print("\n[SMOKE CHECK OK]")
    print(f"Deterministic rows: {len(df_det)}")
    print(f"MC rows: {len(df_mc)}")
    print(f"MC Win% sanity: {win:.1f}%\n")


if __name__ == "__main__":
    main()
