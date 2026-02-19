#!/usr/bin/env python3
"""Truth-table QA: small, exact, model-level invariants.

These tests are intentionally numeric and explicit. They exist to prove that:
- Rate conversions and mortgage amortization are correct.
- Liquidation/capital-gains logic behaves exactly as intended.
- Rent-control cadence is stepwise (frequency-aware).
- Monte Carlo is reproducible when a seed is supplied.

Run:
  python -m rbv.qa.qa_truth_tables
"""

from __future__ import annotations

import math
import sys
from pathlib import Path


# Ensure repo root is on sys.path regardless of where this script is invoked from.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _die(msg: str, code: int = 1) -> None:
    print(f"\n[TRUTH TABLES FAILED] {msg}\n")
    raise SystemExit(code)


def _assert_close(name: str, got: float, exp: float, *, atol: float = 1e-9, rtol: float = 0.0) -> None:
    try:
        g = float(got)
        e = float(exp)
    except Exception:
        _die(f"{name}: non-numeric (got={got}, exp={exp})")
    if not (math.isfinite(g) and math.isfinite(e)):
        _die(f"{name}: non-finite (got={g}, exp={e})")
    if abs(g - e) > (atol + rtol * abs(e)):
        _die(f"{name}: got {g:.12g} expected {e:.12g} (atol={atol}, rtol={rtol})")


def _canadian_monthly_rate(rate_pct: float) -> float:
    r = float(rate_pct) / 100.0
    return (1.0 + r / 2.0) ** (2.0 / 12.0) - 1.0


def _pmt(principal: float, mr: float, n: int) -> float:
    principal = float(principal)
    mr = float(mr)
    n = int(max(1, n))
    if principal <= 0:
        return 0.0
    if mr <= 0:
        return principal / float(n)
    return principal * (mr * (1.0 + mr) ** n) / ((1.0 + mr) ** n - 1.0)


def _amort_equity(price: float, principal: float, mr: float, n: int, months: int) -> tuple[float, float, float]:
    """Return (interest_m1, equity_m1, equity_mN). Deposits/other costs excluded."""
    price = float(price)
    bal = float(principal)
    mr = float(mr)
    n = int(max(1, n))
    pmt = _pmt(bal, mr, n)

    inte1 = bal * mr
    princ1 = min(max(0.0, pmt - inte1), bal)
    bal1 = bal - princ1
    eq1 = price - bal1

    bal = float(principal)
    for _ in range(int(months)):
        inte = bal * mr
        princ = min(max(0.0, pmt - inte), bal)
        bal -= princ
    eqN = price - bal
    return float(inte1), float(eq1), float(eqN)


def _base_cfg() -> dict:
    return {
        "years": 1,
        "province": "Ontario",
        "price": 800_000.0,
        "rent": 0.0,
        "down": 160_000.0,
        "rate": 5.0,
        "nm": 300,
        "mort": 640_000.0,
        "close": 0.0,
        "pst": 0.0,
        "sell_cost": 0.0,
        "p_tax_rate": 0.0,
        "maint_rate": 0.0,
        "repair_rate": 0.0,
        "condo": 0.0,
        "h_ins": 0.0,
        "o_util": 0.0,
        "r_ins": 0.0,
        "r_util": 0.0,
        "moving_cost": 0.0,
        "moving_freq": 1000.0,
        "general_inf": 0.0,
        "rent_inf": 0.0,
        "canadian_compounding": True,
        "use_volatility": False,
        "num_sims": 0,
        "ret_std": 0.15,
        "apprec_std": 0.10,
        "vectorized_mc": True,
        "prop_tax_growth_model": "Hybrid (recommended for Toronto)",
        "prop_tax_hybrid_addon_pct": 0.5,
        "investment_tax_mode": "Pre-tax (no investment taxes)",
        "tax_r": 0.0,
        "assume_sale_end": False,
        "show_liquidation_view": False,
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
        "condo_inf": 0.0,
    }


def _run_det(cfg: dict, *, buyer_ret_pct: float, renter_ret_pct: float, apprec_pct: float, invest_diff: bool, mc_seed: int = 123, overrides: dict | None = None):
    from rbv.core.engine import run_simulation_core

    return run_simulation_core(
        cfg,
        buyer_ret_pct=buyer_ret_pct,
        renter_ret_pct=renter_ret_pct,
        apprec_pct=apprec_pct,
        invest_diff=bool(invest_diff),
        rent_closing=False,
        mkt_corr=0.0,
        force_deterministic=True,
        mc_seed=mc_seed,
        force_use_volatility=False,
        num_sims_override=1,
        param_overrides=overrides,
    )


def _run_mc(cfg: dict, *, buyer_ret_pct: float, renter_ret_pct: float, apprec_pct: float, invest_diff: bool, mc_seed: int, num_sims: int):
    from rbv.core.engine import run_simulation_core

    return run_simulation_core(
        cfg,
        buyer_ret_pct=buyer_ret_pct,
        renter_ret_pct=renter_ret_pct,
        apprec_pct=apprec_pct,
        invest_diff=bool(invest_diff),
        rent_closing=False,
        mkt_corr=0.25,
        mc_seed=mc_seed,
        force_use_volatility=True,
        num_sims_override=int(num_sims),
    )


def _tt_mortgage_rate_and_payment() -> None:
    from rbv.core.mortgage import _annual_nominal_pct_to_monthly_rate

    mr_exp = 0.0041239154651442345
    pmt_exp = 3722.2719042368994

    mr_got = _annual_nominal_pct_to_monthly_rate(5.0, canadian=True)
    _assert_close("TT-M1 monthly rate", mr_got, mr_exp, atol=1e-15)

    pmt_got = _pmt(640_000.0, mr_got, 300)
    _assert_close("TT-M1 payment", pmt_got, pmt_exp, atol=1e-9)

    # Engine payment agrees
    cfg = _base_cfg()
    df, close_cash, mort_pmt, _ = _run_det(cfg, buyer_ret_pct=0.0, renter_ret_pct=0.0, apprec_pct=0.0, invest_diff=False)
    _assert_close("TT-M1 engine mort_pmt", mort_pmt, pmt_exp, atol=1e-9)


def _tt_amortization_interest_equity() -> None:
    # Expected values from independent amortization math (Canadian semi-annual compounding)
    mr = _canadian_monthly_rate(5.0)
    inte1_exp, eq1_exp, eq12_exp = _amort_equity(800_000.0, 640_000.0, mr, 300, 12)

    cfg = _base_cfg()
    cfg["years"] = 1
    df, _, _, _ = _run_det(cfg, buyer_ret_pct=0.0, renter_ret_pct=0.0, apprec_pct=0.0, invest_diff=False)
    if df is None or len(df) < 12:
        _die("TT-M2: engine returned empty/short df")

    m1 = df.iloc[0]
    m12 = df.iloc[11]
    _assert_close("TT-M2 interest m1", float(m1["Interest"]), float(inte1_exp), atol=1e-9)
    _assert_close("TT-M2 equity m1", float(m1["Buyer Home Equity"]), float(eq1_exp), atol=1e-6)
    _assert_close("TT-M2 equity m12", float(m12["Buyer Home Equity"]), float(eq12_exp), atol=1e-6)


def _tt_zero_rate_sanity() -> None:
    cfg = _base_cfg()
    cfg.update({"price": 120_000.0, "down": 0.0, "mort": 120_000.0, "rate": 0.0, "nm": 120, "years": 1})
    df, _, mort_pmt, _ = _run_det(cfg, buyer_ret_pct=0.0, renter_ret_pct=0.0, apprec_pct=0.0, invest_diff=False)
    _assert_close("TT-M3 payment", mort_pmt, 1000.0, atol=1e-12)
    if df is None or len(df) < 12:
        _die("TT-M3: engine returned empty/short df")
    eq12 = float(df.iloc[11]["Buyer Home Equity"])
    _assert_close("TT-M3 equity after 12", eq12, 12_000.0, atol=1e-6)


def _tt_cmhc_pst_recompute() -> None:
    # Truth table: CMHC/PST recompute when price/down are overridden (used by sensitivity tools).
    # We lock an as-of date so policy thresholds remain deterministic.
    cfg = _base_cfg()
    cfg.update({"close": 25_000.0, "pst": 0.0, "asof_date": "2026-02-19"})

    price = 999_999.0
    asof = "2026-02-19"

    # Case A (eligible): minimum down payment for this price (5% of first $500k + 10% of remainder),
    # insured (LTV>80%) => CMHC 4% + Ontario PST on premium (8%).
    min_down = 0.05 * 500_000.0 + 0.10 * (price - 500_000.0)
    down_pct = min_down / price
    overrides = {"price": price, "down_pct": down_pct, "province": "Ontario", "asof_date": asof}
    _, close_cash, mort_pmt, _ = _run_det(cfg, buyer_ret_pct=0.0, renter_ret_pct=0.0, apprec_pct=0.0, invest_diff=False, overrides=overrides)

    _assert_close("TT-T1 close_cash (eligible)", close_cash, 102_959.89712, atol=1e-6)
    _assert_close("TT-T1 mort_pmt (eligible)", mort_pmt, 5595.034512233429, atol=1e-9)

    # Case B (ineligible): 5% down is BELOW the legal minimum at this price (no insurance should be applied).
    overrides_bad = {"price": price, "down_pct": 0.05, "province": "Ontario", "asof_date": asof}
    _, close_cash2, mort_pmt2, _ = _run_det(cfg, buyer_ret_pct=0.0, renter_ret_pct=0.0, apprec_pct=0.0, invest_diff=False, overrides=overrides_bad)

    _assert_close("TT-T2 close_cash (ineligible)", close_cash2, 74_999.95, atol=1e-6)
    _assert_close("TT-T2 mort_pmt (ineligible)", mort_pmt2, 5525.24183260429, atol=1e-9)


def _tt_liquidation_cg_tax_end_only() -> None:
    # Buyer owns a mortgage-free home; buyer invests the rent-vs-buy difference (1000/mo).
    # CG tax applies ONLY to gains at liquidation.
    cfg = _base_cfg()
    cfg.update({
        "years": 1,
        "price": 100_000.0,
        "down": 100_000.0,
        "mort": 0.0,
        "rate": 0.0,
        "rent": 1_000.0,
        "show_liquidation_view": True,
        "cg_tax_end": 25.0,
        "assume_sale_end": False,
        "investment_tax_mode": "Pre-tax (no investment taxes)",
        "tax_r": 0.0,
    })

    df, _, _, _ = _run_det(cfg, buyer_ret_pct=12.0, renter_ret_pct=0.0, apprec_pct=0.0, invest_diff=True)
    last = df.iloc[-1]
    _assert_close("TT-L1 buyer_liq", float(last["Buyer Liquidation NW"]), 112_574.87343126489, atol=1e-6)
    _assert_close("TT-L1 renter_liq", float(last["Renter Liquidation NW"]), 100_000.0, atol=1e-9)


def _tt_annual_drag_disables_extra_liquidation_cg() -> None:
    cfg = _base_cfg()
    cfg.update({
        "years": 1,
        "price": 100_000.0,
        "down": 100_000.0,
        "mort": 0.0,
        "rate": 0.0,
        "rent": 1_000.0,
        "show_liquidation_view": True,
        "cg_tax_end": 25.0,
        "assume_sale_end": False,
        "investment_tax_mode": "Annual return drag",
        "tax_r": 1.0,
    })

    df, _, _, _ = _run_det(cfg, buyer_ret_pct=12.0, renter_ret_pct=0.0, apprec_pct=0.0, invest_diff=True)
    last = df.iloc[-1]
    _assert_close("TT-L2 buyer_liq", float(last["Buyer Liquidation NW"]), 112_758.95931785213, atol=1e-6)
    _assert_close("TT-L2 renter_liq", float(last["Renter Liquidation NW"]), 100_000.0, atol=1e-9)


def _tt_rent_control_cadence_every3() -> None:
    cfg = _base_cfg()
    cfg.update({
        "years": 4,
        "price": 0.0,
        "down": 0.0,
        "mort": 0.0,
        "rate": 0.0,
        "rent": 1_000.0,
        "rent_inf": 0.03,
        "rent_control_enabled": True,
        "rent_control_cap": 0.02,
        "rent_control_frequency_years": 3,
    })

    df, _, _, _ = _run_det(cfg, buyer_ret_pct=0.0, renter_ret_pct=0.0, apprec_pct=0.0, invest_diff=False)
    if df is None or len(df) < 37:
        _die("TT-RC1: expected >= 37 months")

    rent_m36 = float(df.iloc[35]["Rent"])
    rent_m37 = float(df.iloc[36]["Rent"])
    _assert_close("TT-RC1 rent m36", rent_m36, 1000.0, atol=1e-12)
    _assert_close("TT-RC1 rent m37", rent_m37, 1000.0 * (1.02 ** 3), atol=1e-6)


def _tt_mc_seed_reproducible() -> None:
    cfg = _base_cfg()
    cfg.update({
        "years": 3,
        "price": 800_000.0,
        "down": 160_000.0,
        "mort": 640_000.0,
        "rate": 5.0,
        "rent": 3_200.0,
        "use_volatility": True,
        "num_sims": 200,
        "ret_std": 0.15,
        "apprec_std": 0.10,
        "vectorized_mc": True,
        "assume_sale_end": True,
        "show_liquidation_view": True,
        "cg_tax_end": 0.0,
    })

    df1, close1, pmt1, win1 = _run_mc(cfg, buyer_ret_pct=7.0, renter_ret_pct=7.0, apprec_pct=3.0, invest_diff=False, mc_seed=424242, num_sims=200)
    df2, close2, pmt2, win2 = _run_mc(cfg, buyer_ret_pct=7.0, renter_ret_pct=7.0, apprec_pct=3.0, invest_diff=False, mc_seed=424242, num_sims=200)

    _assert_close("TT-MC1 close_cash", close1, close2, atol=0.0)
    _assert_close("TT-MC1 mort_pmt", pmt1, pmt2, atol=0.0)
    if (win1 is not None) and (win2 is not None):
        _assert_close("TT-MC1 win_pct", float(win1), float(win2), atol=0.0)

    last1 = df1.iloc[-1]
    last2 = df2.iloc[-1]
    for col in [
        "Buyer Net Worth",
        "Renter Net Worth",
        "Buyer Unrecoverable",
        "Renter Unrecoverable",
        "Buyer Liquidation NW",
        "Renter Liquidation NW",
    ]:
        _assert_close(f"TT-MC1 last[{col}]", float(last1[col]), float(last2[col]), atol=0.0)


def main(argv: list[str] | None = None) -> None:
    # Mortgage invariants
    _tt_mortgage_rate_and_payment()
    _tt_amortization_interest_equity()
    _tt_zero_rate_sanity()

    # Taxes / liquidation invariants
    _tt_cmhc_pst_recompute()
    _tt_liquidation_cg_tax_end_only()
    _tt_annual_drag_disables_extra_liquidation_cg()

    # Rent control cadence
    _tt_rent_control_cadence_every3()

    # MC determinism
    _tt_mc_seed_reproducible()

    print("\n[TRUTH TABLES OK]\n")


if __name__ == "__main__":
    main()
