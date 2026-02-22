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

        # Optional modeling layers (must be opt-in)
        "special_assessment_amount": 0.0,
        "special_assessment_month": 0,
        "cg_inclusion_policy": "current",
        "cg_inclusion_threshold": 250000.0,
        "reg_shelter_enabled": False,
        "reg_initial_room": 0.0,
        "reg_annual_room": 0.0,
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
    _assert_close("TT-L1 buyer_liq", float(last["Buyer Liquidation NW"]), 12_574.87343126489, atol=1e-6)
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
    _assert_close("TT-L2 buyer_liq", float(last["Buyer Liquidation NW"]), 12_758.95931785213, atol=1e-6)
    _assert_close("TT-L2 renter_liq", float(last["Renter Liquidation NW"]), 100_000.0, atol=1e-9)


def _tt_special_assessment_applied_once() -> None:
    cfg = _base_cfg()
    cfg.update({
        "years": 2,
        "price": 100_000.0,
        "down": 100_000.0,
        "mort": 0.0,
        "rate": 0.0,
        "rent": 0.0,
        "show_liquidation_view": False,
        "assume_sale_end": False,
        "special_assessment_amount": 10_000.0,
        "special_assessment_month": 7,
    })

    df, _, _, _ = _run_det(cfg, buyer_ret_pct=0.0, renter_ret_pct=0.0, apprec_pct=0.0, invest_diff=False)
    if df is None or len(df) < 24:
        _die("TT-SA1: engine returned empty/short df")
    if "Special Assessment" not in df.columns:
        _die("TT-SA1: missing 'Special Assessment' column")

    sa_sum = float(df["Special Assessment"].sum())
    _assert_close("TT-SA1 assessment sum", sa_sum, 10_000.0, atol=1e-9)
    sa_m7 = float(df.iloc[6]["Special Assessment"])  # month 7
    _assert_close("TT-SA1 assessment month 7", sa_m7, 10_000.0, atol=1e-9)
    b_unrec_end = float(df.iloc[-1]["Buyer Unrecoverable"])
    _assert_close("TT-SA1 buyer unrec end", b_unrec_end, 10_000.0, atol=1e-9)


def _tt_cg_inclusion_tier_and_shelter() -> None:
    # Construct a deterministic case with large portfolio gains so the tier triggers.
    cfg = _base_cfg()
    cfg.update({
        "years": 1,
        "price": 100_000.0,
        "down": 100_000.0,
        "mort": 0.0,
        "rate": 0.0,
        "rent": 100_000.0,  # forces buyer to invest 100k/mo when invest_diff=True
        "r_ins": 0.0,
        "r_util": 0.0,
        "moving_cost": 0.0,
        "moving_freq": 1000.0,
        "show_liquidation_view": True,
        "assume_sale_end": False,
        "investment_tax_mode": "Pre-tax (no investment taxes)",
        "cg_tax_end": 25.0,
        "cg_inclusion_threshold": 250_000.0,
        "reg_shelter_enabled": False,
    })

    basis = 12.0 * 100_000.0
    home_eq = 100_000.0
    eff = 0.25

    # Current policy: flat effective rate
    cfg["cg_inclusion_policy"] = "current"
    df1, _, _, _ = _run_det(cfg, buyer_ret_pct=200.0, renter_ret_pct=0.0, apprec_pct=0.0, invest_diff=True)
    last1 = df1.iloc[-1]
    b_nw1 = float(last1["Buyer Net Worth"])
    b_liq1 = float(last1["Buyer Liquidation NW"])
    port1 = b_nw1 - home_eq
    gain1 = max(0.0, port1 - basis)
    tax1 = eff * gain1
    _assert_close("TT-L3 current buyer_liq", b_liq1, (b_nw1 - home_eq) - tax1, atol=1e-6)

    # Tiered policy: above-threshold gains taxed at 4/3 of effective rate
    cfg["cg_inclusion_policy"] = "proposed_2_3_over_250k"
    df2, _, _, _ = _run_det(cfg, buyer_ret_pct=200.0, renter_ret_pct=0.0, apprec_pct=0.0, invest_diff=True)
    last2 = df2.iloc[-1]
    b_nw2 = float(last2["Buyer Net Worth"])
    b_liq2 = float(last2["Buyer Liquidation NW"])
    port2 = b_nw2 - home_eq
    gain2 = max(0.0, port2 - basis)
    thr = 250_000.0
    tax2 = eff * min(gain2, thr) + (eff * (4.0 / 3.0)) * max(0.0, gain2 - thr)
    _assert_close("TT-L3 tiered buyer_liq", b_liq2, (b_nw2 - home_eq) - tax2, atol=1e-6)

    # Full shelter: cap basis at >= total basis => taxable gain should be 0
    cfg["reg_shelter_enabled"] = True
    cfg["reg_initial_room"] = basis
    cfg["reg_annual_room"] = 0.0
    df3, _, _, _ = _run_det(cfg, buyer_ret_pct=200.0, renter_ret_pct=0.0, apprec_pct=0.0, invest_diff=True)
    last3 = df3.iloc[-1]
    b_nw3 = float(last3["Buyer Net Worth"])
    b_liq3 = float(last3["Buyer Liquidation NW"])
    _assert_close("TT-L3 sheltered buyer_liq", b_liq3, (b_nw3 - home_eq), atol=1e-6)



def _tt_ui_defaults_match_presets() -> None:
    """UI first-load defaults must match the selected scenario preset (single source of truth).

    This prevents drift where:
      - the preset says one thing (e.g., rate=4.75)
      - but initial session_state seeding uses a stale value (e.g., 5.25)
    """
    from rbv.ui.defaults import PRESETS, build_session_defaults

    for scen, preset in PRESETS.items():
        d = build_session_defaults(scen)
        if str(d.get("scenario_select")) != str(scen):
            _die(f"ui_defaults: scenario_select mismatch for {scen} (got={d.get('scenario_select')})")
        for k, v in preset.items():
            if k not in d:
                _die(f"ui_defaults: missing key '{k}' for scenario {scen}")
            _assert_close(f"ui_defaults[{scen}].{k}", float(d[k]), float(v), atol=1e-12, rtol=0.0)

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



def _tt_reference_numbers_regression() -> None:
    """Regression targets from independent calculations (audit report)."""
    from rbv.core.mortgage import _annual_nominal_pct_to_monthly_rate
    from rbv.core.policy_canada import cmhc_premium_rate_from_ltv, min_down_payment_canada
    from rbv.core.taxes import calc_transfer_tax
    import datetime as _dt

    asof = _dt.date(2026, 2, 20)

    # Mortgage payments (Canadian semi-annual nominal compounding)
    mr = _annual_nominal_pct_to_monthly_rate(5.0, canadian=True)
    pmt_25 = _pmt(500_000.0, mr, 25 * 12)
    pmt_30 = _pmt(500_000.0, mr, 30 * 12)
    _assert_close("TT-REF mort pmt 25y", pmt_25, 2908.0249251850773, atol=0.02)
    _assert_close("TT-REF mort pmt 30y", pmt_30, 2668.4533940437777, atol=0.02)

    # CMHC premium amounts (premium is % of base loan amount)
    price = 600_000.0
    down_5 = 30_000.0
    loan_5 = price - down_5
    ltv_5 = loan_5 / price
    prem_5 = loan_5 * cmhc_premium_rate_from_ltv(ltv_5)
    _assert_close("TT-REF CMHC prem 5% down", prem_5, 22_800.0, atol=1.0)

    down_10 = 60_000.0
    loan_10 = price - down_10
    ltv_10 = loan_10 / price
    prem_10 = loan_10 * cmhc_premium_rate_from_ltv(ltv_10)
    _assert_close("TT-REF CMHC prem 10% down", prem_10, 16_740.0, atol=1.0)

    # Min down payment (tiered)
    md = min_down_payment_canada(800_000.0, asof)
    _assert_close("TT-REF min down 800k", md, 55_000.0, atol=1e-9)

    # Ontario land transfer tax
    tt_on = calc_transfer_tax("Ontario", 800_000.0, first_time_buyer=False, toronto_property=False, asof_date=asof)
    _assert_close("TT-REF ON LTT 800k", float(tt_on["total"]), 12_475.0, atol=1.0)

    tt_on_ftb = calc_transfer_tax("Ontario", 800_000.0, first_time_buyer=True, toronto_property=False, asof_date=asof)
    _assert_close("TT-REF ON LTT 800k FTB", float(tt_on_ftb["total"]), 8_475.0, atol=1.0)

    tt_to = calc_transfer_tax("Ontario", 800_000.0, first_time_buyer=False, toronto_property=True, asof_date=asof)
    _assert_close("TT-REF Toronto total LTT 800k", float(tt_to["total"]), 24_950.0, atol=1.0)


def _tt_transfer_tax_examples_multi_province() -> None:
    """Cross-province sanity anchors for transfer-tax / registration-fee schedules.

    These are intentionally simple, hand-checkable examples that should remain stable
    unless tax rule implementations change.
    """
    from rbv.core.taxes import calc_transfer_tax

    # Ontario example: $500k, first-time buyer (rebate up to $4k), non-Toronto.
    # LTT = 6475 - 4000 = 2475
    _assert_close(
        "TT-TAX ON 500k FTHB",
        float(calc_transfer_tax("Ontario", 500_000.0, first_time_buyer=True, toronto_property=False)["total"]),
        2475.0,
        atol=1e-6,
    )

    # BC example: $500k => 200k*1% + 300k*2% = 8000
    _assert_close(
        "TT-TAX BC 500k",
        float(calc_transfer_tax("British Columbia", 500_000.0, first_time_buyer=False, toronto_property=False)["total"]),
        8000.0,
        atol=1e-6,
    )

    # MB example: $250k => 0 on 30k; 60k*0.5%=300; 60k*1%=600; 50k*1.5%=750; 50k*2%=1000 => 2650
    _assert_close(
        "TT-TAX MB 250k",
        float(calc_transfer_tax("Manitoba", 250_000.0, first_time_buyer=False, toronto_property=False)["total"]),
        2650.0,
        atol=1e-6,
    )

    # Alberta example: $400k => base 50 + 5*ceil(400k/5000)=50+5*80=450 (transfer-of-land)
    _assert_close(
        "TT-TAX AB 400k",
        float(calc_transfer_tax("Alberta", 400_000.0, first_time_buyer=False, toronto_property=False)["total"]),
        450.0,
        atol=1e-6,
    )


def _tt_bc_fthb_exemption_date_aware() -> None:
    """BC FTHB exemption should be date-aware and bounded by the $8,000 max benefit."""
    from rbv.core.taxes import calc_transfer_tax
    import datetime as _dt

    # Post Apr 1, 2024 schedule (current)
    asof = _dt.date(2026, 2, 20)

    # <=500k: fully exempt (PTT <= 8k)
    _assert_close(
        "TT-BC-FTHB 400k post2024",
        float(calc_transfer_tax("British Columbia", 400_000.0, first_time_buyer=True, toronto_property=False, asof_date=asof)["total"]),
        0.0,
        atol=1e-9,
    )

    # 500k: base PTT 8k; max exemption 8k => 0
    _assert_close(
        "TT-BC-FTHB 500k post2024",
        float(calc_transfer_tax("British Columbia", 500_000.0, first_time_buyer=True, toronto_property=False, asof_date=asof)["total"]),
        0.0,
        atol=1e-9,
    )

    # 600k: base PTT 10k; exemption 8k => 2k
    _assert_close(
        "TT-BC-FTHB 600k post2024",
        float(calc_transfer_tax("British Columbia", 600_000.0, first_time_buyer=True, toronto_property=False, asof_date=asof)["total"]),
        2000.0,
        atol=1e-6,
    )

    # 835k: full benefit (8k) still applies
    _assert_close(
        "TT-BC-FTHB 835k post2024",
        float(calc_transfer_tax("British Columbia", 835_000.0, first_time_buyer=True, toronto_property=False, asof_date=asof)["total"]),
        6700.0,
        atol=1e-6,
    )

    # 850k: partial phaseout => exemption 3.2k; base 15k => 11.8k
    _assert_close(
        "TT-BC-FTHB 850k post2024",
        float(calc_transfer_tax("British Columbia", 850_000.0, first_time_buyer=True, toronto_property=False, asof_date=asof)["total"]),
        11800.0,
        atol=1e-6,
    )

    # 860k+: no exemption
    _assert_close(
        "TT-BC-FTHB 860k post2024",
        float(calc_transfer_tax("British Columbia", 860_000.0, first_time_buyer=True, toronto_property=False, asof_date=asof)["total"]),
        15200.0,
        atol=1e-6,
    )

    # Pre Apr 1, 2024 legacy schedule: phaseout 500k -> 525k
    asof_old = _dt.date(2024, 3, 1)
    _assert_close(
        "TT-BC-FTHB 520k pre2024",
        float(calc_transfer_tax("British Columbia", 520_000.0, first_time_buyer=True, toronto_property=False, asof_date=asof_old)["total"]),
        6800.0,
        atol=1e-6,
    )
    _assert_close(
        "TT-BC-FTHB 525k pre2024",
        float(calc_transfer_tax("British Columbia", 525_000.0, first_time_buyer=True, toronto_property=False, asof_date=asof_old)["total"]),
        8500.0,
        atol=1e-6,
    )



def _tt_purchase_closing_costs_reduce_buyer_nw() -> None:
    """Truth table: one-time closing costs must reduce buyer net worth dollar-for-dollar when returns are zero."""
    cfg = _base_cfg()
    cfg.update({
        "years": 1,
        "rent": 0.0,
        "general_inf": 0.0,
        "rent_inf": 0.0,
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
        "assume_sale_end": False,
        "show_liquidation_view": False,
    })

    cfg0 = dict(cfg)
    cfg0["close"] = 0.0
    df0, _, _, _ = _run_det(cfg0, buyer_ret_pct=0.0, renter_ret_pct=0.0, apprec_pct=0.0, invest_diff=False)

    cfg1 = dict(cfg)
    cfg1["close"] = 10_000.0
    df1, _, _, _ = _run_det(cfg1, buyer_ret_pct=0.0, renter_ret_pct=0.0, apprec_pct=0.0, invest_diff=False)

    bnw0 = float(df0.iloc[-1]["Buyer Net Worth"])
    bnw1 = float(df1.iloc[-1]["Buyer Net Worth"])
    _assert_close("TT-CLOSE buyer NW delta", bnw0 - bnw1, 10_000.0, atol=1e-6)

    bu0 = float(df0.iloc[-1]["Buyer Unrecoverable"])
    bu1 = float(df1.iloc[-1]["Buyer Unrecoverable"])
    _assert_close("TT-CLOSE buyer unrecoverable delta", bu1 - bu0, 10_000.0, atol=1e-6)

def main(argv: list[str] | None = None) -> None:
    # Mortgage invariants
    _tt_mortgage_rate_and_payment()
    _tt_reference_numbers_regression()
    _tt_purchase_closing_costs_reduce_buyer_nw()
    _tt_transfer_tax_examples_multi_province()
    _tt_bc_fthb_exemption_date_aware()
    _tt_amortization_interest_equity()
    _tt_zero_rate_sanity()

    # Taxes / liquidation invariants
    _tt_cmhc_pst_recompute()
    _tt_liquidation_cg_tax_end_only()
    _tt_annual_drag_disables_extra_liquidation_cg()
    _tt_special_assessment_applied_once()
    _tt_cg_inclusion_tier_and_shelter()
    _tt_ui_defaults_match_presets()

    # Rent control cadence
    _tt_rent_control_cadence_every3()

    # MC determinism
    _tt_mc_seed_reproducible()

    print("\n[TRUTH TABLES OK]\n")


if __name__ == "__main__":
    main()
def _tt_discount_rate_unit_guard():
    """Guard: discount_rate passed as percent-points should not zero-out PV outputs."""
    cfg = _base_cfg()
    cfg["discount_rate"] = 3.0  # percent points (UI-style); engine should normalize to 0.03
    df, _, _, _ = _run_det(cfg, buyer_ret_pct=0.0, renter_ret_pct=0.0, apprec_pct=0.0, invest_diff=False)
    # PV should be finite and non-trivial; also engine should mark normalization.
    assert bool(getattr(df, "attrs", {}).get("discount_rate_autonormalized", False)) is True
    bpv = float(df.iloc[-1].get("Buyer PV NW", 0.0))
    rpv = float(df.iloc[-1].get("Renter PV NW", 0.0))
    assert math.isfinite(bpv) and math.isfinite(rpv)
    assert (bpv > 1_000.0) and (rpv > 1_000.0)



