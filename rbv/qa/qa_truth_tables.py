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


def _run_det(
    cfg: dict,
    *,
    buyer_ret_pct: float,
    renter_ret_pct: float,
    apprec_pct: float,
    invest_diff: bool,
    mc_seed: int = 123,
    overrides: dict | None = None,
):
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


def _run_mc(
    cfg: dict,
    *,
    buyer_ret_pct: float,
    renter_ret_pct: float,
    apprec_pct: float,
    invest_diff: bool,
    mc_seed: int,
    num_sims: int,
):
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
    df, close_cash, mort_pmt, _ = _run_det(
        cfg, buyer_ret_pct=0.0, renter_ret_pct=0.0, apprec_pct=0.0, invest_diff=False
    )
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
    _, close_cash, mort_pmt, _ = _run_det(
        cfg, buyer_ret_pct=0.0, renter_ret_pct=0.0, apprec_pct=0.0, invest_diff=False, overrides=overrides
    )

    _assert_close("TT-T1 close_cash (eligible)", close_cash, 102_959.89712, atol=1e-6)
    _assert_close("TT-T1 mort_pmt (eligible)", mort_pmt, 5595.034512233429, atol=1e-9)

    # Case B (ineligible): 5% down is BELOW the legal minimum at this price (no insurance should be applied).
    overrides_bad = {"price": price, "down_pct": 0.05, "province": "Ontario", "asof_date": asof}
    _, close_cash2, mort_pmt2, _ = _run_det(
        cfg, buyer_ret_pct=0.0, renter_ret_pct=0.0, apprec_pct=0.0, invest_diff=False, overrides=overrides_bad
    )

    _assert_close("TT-T2 close_cash (ineligible)", close_cash2, 74_999.95, atol=1e-6)
    _assert_close("TT-T2 mort_pmt (ineligible)", mort_pmt2, 5525.24183260429, atol=1e-9)


def _tt_liquidation_cg_tax_end_only() -> None:
    # Buyer owns a mortgage-free home; buyer invests the rent-vs-buy difference (1000/mo).
    # CG tax applies ONLY to gains at liquidation.
    cfg = _base_cfg()
    cfg.update(
        {
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
        }
    )

    df, _, _, _ = _run_det(cfg, buyer_ret_pct=12.0, renter_ret_pct=0.0, apprec_pct=0.0, invest_diff=True)
    last = df.iloc[-1]
    _assert_close("TT-L1 buyer_liq", float(last["Buyer Liquidation NW"]), 12_574.87343126489, atol=1e-6)
    _assert_close("TT-L1 renter_liq", float(last["Renter Liquidation NW"]), 100_000.0, atol=1e-9)


def _tt_annual_drag_disables_extra_liquidation_cg() -> None:
    cfg = _base_cfg()
    cfg.update(
        {
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
        }
    )

    df, _, _, _ = _run_det(cfg, buyer_ret_pct=12.0, renter_ret_pct=0.0, apprec_pct=0.0, invest_diff=True)
    last = df.iloc[-1]
    _assert_close("TT-L2 buyer_liq", float(last["Buyer Liquidation NW"]), 12_758.95931785213, atol=1e-6)
    _assert_close("TT-L2 renter_liq", float(last["Renter Liquidation NW"]), 100_000.0, atol=1e-9)


def _tt_special_assessment_applied_once() -> None:
    cfg = _base_cfg()
    cfg.update(
        {
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
        }
    )

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
    cfg.update(
        {
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
        }
    )

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


def _tt_city_preset_framework_toronto_mltt_and_summary() -> None:
    from rbv.ui.defaults import (
        CITY_PRESET_CUSTOM,
        apply_city_preset_values,
        build_city_preset_change_summary,
        city_preset_filter_region_options,
        city_preset_filter_type_options,
        city_preset_filtered_options,
        city_preset_metadata,
        city_preset_options,
        city_preset_preview_summary_lines,
        city_preset_values,
    )

    opts = city_preset_options()
    assert isinstance(opts, list) and opts and opts[0] == CITY_PRESET_CUSTOM
    toronto_name = next((x for x in opts if str(x).startswith("Toronto (ON)")), None)
    assert toronto_name is not None

    # PR13 filtering / metadata helpers
    assert "All regions" in city_preset_filter_region_options()
    assert "All homes" in city_preset_filter_type_options()
    tor_only = city_preset_filtered_options(region="Toronto only")
    assert tor_only and tor_only[0] == CITY_PRESET_CUSTOM
    assert all((x == CITY_PRESET_CUSTOM) or str(x).startswith("Toronto (ON)") for x in tor_only)
    condo_only = city_preset_filtered_options(home_type="Condo")
    assert any("Condo" in str(x) for x in condo_only[1:])
    assert all((x == CITY_PRESET_CUSTOM) or ("Detached" not in str(x)) for x in condo_only)
    vanc_only = city_preset_filtered_options(query="vanc")
    assert any(str(x).startswith("Vancouver (BC)") for x in vanc_only)
    meta = city_preset_metadata(toronto_name)
    assert str(meta.get("province_code")) == "ON"
    assert bool(meta.get("is_toronto")) is True
    preview_lines = city_preset_preview_summary_lines(toronto_name, max_items=4)
    assert isinstance(preview_lines, list) and preview_lines and any("Region:" in str(x) for x in preview_lines)

    st0 = {
        "city_preset": CITY_PRESET_CUSTOM,
        "province": "British Columbia",
        "toronto": False,
        "price": 700000.0,
        "down": 140000.0,
        "rent": 2600.0,
        "p_tax_rate_pct": 0.5,
        "condo": 0.0,
        "o_util": 180.0,
        "r_util": 120.0,
    }
    changes = apply_city_preset_values(st0, toronto_name)
    assert str(st0.get("city_preset")) == str(toronto_name)
    assert str(st0.get("province")) == "Ontario"
    assert bool(st0.get("toronto")) is True
    assert float(st0.get("price")) > 0.0 and float(st0.get("rent")) > 0.0
    assert any(str(r.get("key")) == "toronto" for r in changes)

    summary = build_city_preset_change_summary(changes, max_items=12)
    assert isinstance(summary, list) and summary
    assert any(("Toronto property" in str(x)) or ("MLTT" in str(x)) for x in summary)

    # Custom should not overwrite values (only normalize marker).
    before_price = float(st0.get("price"))
    no_changes = apply_city_preset_values(st0, CITY_PRESET_CUSTOM)
    assert no_changes == []
    assert str(st0.get("city_preset")) == CITY_PRESET_CUSTOM
    _assert_close("TT-CITY custom no overwrite", float(st0.get("price")), before_price, atol=0.0)

    # Non-Toronto preset should clear MLTT and force toronto flag off.
    van_name = next((x for x in opts if str(x).startswith("Vancouver (BC)")), None)
    assert van_name is not None
    st1 = {"province": "Ontario", "toronto": True}
    apply_city_preset_values(st1, van_name)
    assert str(st1.get("province")) == "British Columbia"
    assert bool(st1.get("toronto")) is False
    assert isinstance(city_preset_values(van_name), dict)


def _tt_rent_control_cadence_every3() -> None:
    cfg = _base_cfg()
    cfg.update(
        {
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
        }
    )

    df, _, _, _ = _run_det(cfg, buyer_ret_pct=0.0, renter_ret_pct=0.0, apprec_pct=0.0, invest_diff=False)
    if df is None or len(df) < 37:
        _die("TT-RC1: expected >= 37 months")

    rent_m36 = float(df.iloc[35]["Rent"])
    rent_m37 = float(df.iloc[36]["Rent"])
    _assert_close("TT-RC1 rent m36", rent_m36, 1000.0, atol=1e-12)
    _assert_close("TT-RC1 rent m37", rent_m37, 1000.0 * (1.02**3), atol=1e-6)


def _tt_moving_frequency_default_is_5_years() -> None:
    """When moving_freq is omitted, engine should fall back to 5-year cadence."""
    cfg_missing = _base_cfg()
    cfg_missing.update({"years": 6, "rent": 2_000.0, "moving_cost": 2_500.0})
    cfg_missing.pop("moving_freq", None)

    df_missing, _, _, _ = _run_det(
        cfg_missing, buyer_ret_pct=0.0, renter_ret_pct=0.0, apprec_pct=0.0, invest_diff=False
    )
    if df_missing is None or len(df_missing) < 72:
        _die("TT-MOVE-DEF: engine returned empty/short df for missing moving_freq")

    moving_missing = float(df_missing["Moving"].sum())
    _assert_close("TT-MOVE-DEF one move over 6 years", moving_missing, 2_500.0, atol=1e-9)

    cfg_explicit = _base_cfg()
    cfg_explicit.update({"years": 6, "rent": 2_000.0, "moving_cost": 2_500.0, "moving_freq": 5.0})

    df_explicit, _, _, _ = _run_det(
        cfg_explicit, buyer_ret_pct=0.0, renter_ret_pct=0.0, apprec_pct=0.0, invest_diff=False
    )
    if df_explicit is None or len(df_explicit) < 72:
        _die("TT-MOVE-DEF: engine returned empty/short df for explicit moving_freq")

    moving_explicit = float(df_explicit["Moving"].sum())
    _assert_close("TT-MOVE-DEF parity with explicit 5y", moving_missing, moving_explicit, atol=1e-9)


def _tt_mc_seed_reproducible() -> None:
    cfg = _base_cfg()
    cfg.update(
        {
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
        }
    )

    df1, close1, pmt1, win1 = _run_mc(
        cfg, buyer_ret_pct=7.0, renter_ret_pct=7.0, apprec_pct=3.0, invest_diff=False, mc_seed=424242, num_sims=200
    )
    df2, close2, pmt2, win2 = _run_mc(
        cfg, buyer_ret_pct=7.0, renter_ret_pct=7.0, apprec_pct=3.0, invest_diff=False, mc_seed=424242, num_sims=200
    )

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
    import datetime as _dt

    from rbv.core.mortgage import _annual_nominal_pct_to_monthly_rate
    from rbv.core.policy_canada import cmhc_premium_rate_from_ltv, min_down_payment_canada
    from rbv.core.taxes import calc_transfer_tax

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

    prem_5_non = loan_5 * cmhc_premium_rate_from_ltv(ltv_5, "Non-traditional")
    _assert_close("TT-REF CMHC prem 5% down (non-traditional)", prem_5_non, 25_650.0, atol=1.0)

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
        float(
            calc_transfer_tax("British Columbia", 500_000.0, first_time_buyer=False, toronto_property=False)["total"]
        ),
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

    # Non-positive prices should never generate negative transfer tax.
    _assert_close(
        "TT-TAX ON negative",
        float(calc_transfer_tax("Ontario", -100_000.0, first_time_buyer=False, toronto_property=False)["total"]),
        0.0,
        atol=1e-9,
    )

    _assert_close(
        "TT-TAX BC negative",
        float(
            calc_transfer_tax("British Columbia", -100_000.0, first_time_buyer=False, toronto_property=False)["total"]
        ),
        0.0,
        atol=1e-9,
    )

    # Alberta example: $400k => base 50 + 5*ceil(400k/5000)=50+5*80=450 (transfer-of-land)

    # NB: tax base is max(purchase price, assessed value) (1% simplified).
    _assert_close(
        "TT-TAX NB assessed>price",
        float(
            calc_transfer_tax(
                "New Brunswick", 300_000.0, first_time_buyer=False, toronto_property=False, assessed_value=350_000.0
            )["total"]
        ),
        3500.0,
        atol=1e-6,
    )
    _assert_close(
        "TT-TAX NB assessed<price",
        float(
            calc_transfer_tax(
                "New Brunswick", 300_000.0, first_time_buyer=False, toronto_property=False, assessed_value=250_000.0
            )["total"]
        ),
        3000.0,
        atol=1e-6,
    )

    # PEI: simplified schedule uses max(purchase price, assessed value).
    # 1% on (min(base,1M)-30k) + 2% above 1M
    _assert_close(
        "TT-TAX PEI assessed>price",
        float(
            calc_transfer_tax(
                "Prince Edward Island",
                200_000.0,
                first_time_buyer=False,
                toronto_property=False,
                assessed_value=250_000.0,
            )["total"]
        ),
        2200.0,
        atol=1e-6,
    )
    _assert_close(
        "TT-TAX PEI assessed<price",
        float(
            calc_transfer_tax(
                "Prince Edward Island",
                200_000.0,
                first_time_buyer=False,
                toronto_property=False,
                assessed_value=150_000.0,
            )["total"]
        ),
        1700.0,
        atol=1e-6,
    )

    # Nova Scotia: municipal rate varies; ensure custom rate is applied.
    _assert_close(
        "TT-TAX NS custom rate 2.0%",
        float(
            calc_transfer_tax(
                "Nova Scotia", 500_000.0, first_time_buyer=False, toronto_property=False, ns_deed_transfer_rate=0.02
            )["total"]
        ),
        10_000.0,
        atol=1e-6,
    )

    _assert_close(
        "TT-TAX AB 400k",
        float(calc_transfer_tax("Alberta", 400_000.0, first_time_buyer=False, toronto_property=False)["total"]),
        450.0,
        atol=1e-6,
    )

    # Input normalization: province labels with different casing should map to same rule.
    _assert_close(
        "TT-TAX NL canonical-case parity",
        float(
            calc_transfer_tax("newfoundland and labrador", 400_000.0, first_time_buyer=False, toronto_property=False)[
                "total"
            ]
        ),
        float(
            calc_transfer_tax("Newfoundland and Labrador", 400_000.0, first_time_buyer=False, toronto_property=False)[
                "total"
            ]
        ),
        atol=1e-9,
    )


def _tt_bc_fthb_exemption_date_aware() -> None:
    """BC FTHB exemption should be date-aware and bounded by the $8,000 max benefit."""
    import datetime as _dt

    from rbv.core.taxes import calc_transfer_tax

    # Post Apr 1, 2024 schedule (current)
    asof = _dt.date(2026, 2, 20)

    # <=500k: fully exempt (PTT <= 8k)
    _assert_close(
        "TT-BC-FTHB 400k post2024",
        float(
            calc_transfer_tax(
                "British Columbia", 400_000.0, first_time_buyer=True, toronto_property=False, asof_date=asof
            )["total"]
        ),
        0.0,
        atol=1e-9,
    )

    # 500k: base PTT 8k; max exemption 8k => 0
    _assert_close(
        "TT-BC-FTHB 500k post2024",
        float(
            calc_transfer_tax(
                "British Columbia", 500_000.0, first_time_buyer=True, toronto_property=False, asof_date=asof
            )["total"]
        ),
        0.0,
        atol=1e-9,
    )

    # 600k: base PTT 10k; exemption 8k => 2k
    _assert_close(
        "TT-BC-FTHB 600k post2024",
        float(
            calc_transfer_tax(
                "British Columbia", 600_000.0, first_time_buyer=True, toronto_property=False, asof_date=asof
            )["total"]
        ),
        2000.0,
        atol=1e-6,
    )

    # 835k: full benefit (8k) still applies
    _assert_close(
        "TT-BC-FTHB 835k post2024",
        float(
            calc_transfer_tax(
                "British Columbia", 835_000.0, first_time_buyer=True, toronto_property=False, asof_date=asof
            )["total"]
        ),
        6700.0,
        atol=1e-6,
    )

    # 850k: partial phaseout => exemption 3.2k; base 15k => 11.8k
    _assert_close(
        "TT-BC-FTHB 850k post2024",
        float(
            calc_transfer_tax(
                "British Columbia", 850_000.0, first_time_buyer=True, toronto_property=False, asof_date=asof
            )["total"]
        ),
        11800.0,
        atol=1e-6,
    )

    # 860k+: no exemption
    _assert_close(
        "TT-BC-FTHB 860k post2024",
        float(
            calc_transfer_tax(
                "British Columbia", 860_000.0, first_time_buyer=True, toronto_property=False, asof_date=asof
            )["total"]
        ),
        15200.0,
        atol=1e-6,
    )

    # Pre Apr 1, 2024 legacy schedule: phaseout 500k -> 525k
    asof_old = _dt.date(2024, 3, 1)
    _assert_close(
        "TT-BC-FTHB 520k pre2024",
        float(
            calc_transfer_tax(
                "British Columbia", 520_000.0, first_time_buyer=True, toronto_property=False, asof_date=asof_old
            )["total"]
        ),
        6800.0,
        atol=1e-6,
    )
    _assert_close(
        "TT-BC-FTHB 525k pre2024",
        float(
            calc_transfer_tax(
                "British Columbia", 525_000.0, first_time_buyer=True, toronto_property=False, asof_date=asof_old
            )["total"]
        ),
        8500.0,
        atol=1e-6,
    )


def _tt_purchase_closing_costs_reduce_buyer_nw() -> None:
    """Truth table: one-time closing costs must reduce buyer net worth dollar-for-dollar when returns are zero."""
    cfg = _base_cfg()
    cfg.update(
        {
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
        }
    )

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


def _tt_insured_30yr_amortization_policy_schedule() -> None:
    import datetime as dt

    from rbv.core.policy_canada import insured_30yr_amortization_policy_stage, insured_max_amortization_years

    # Stage transitions
    assert insured_30yr_amortization_policy_stage(dt.date(2024, 7, 31)) == "pre_2024_08_01"
    assert insured_30yr_amortization_policy_stage(dt.date(2024, 8, 1)) == "ftb_and_new_build"
    assert insured_30yr_amortization_policy_stage(dt.date(2024, 12, 14)) == "ftb_and_new_build"
    assert insured_30yr_amortization_policy_stage(dt.date(2024, 12, 15)) == "ftb_or_new_build"

    # Before Aug 1, 2024: no modeled insured 30-year exception
    assert insured_max_amortization_years(dt.date(2024, 7, 31), first_time_buyer=False, new_construction=False) == 25
    assert insured_max_amortization_years(dt.date(2024, 7, 31), first_time_buyer=True, new_construction=True) == 25

    # Aug 1, 2024 .. Dec 14, 2024: must be BOTH first-time buyer and new build
    d_mid = dt.date(2024, 10, 1)
    assert insured_max_amortization_years(d_mid, first_time_buyer=False, new_construction=False) == 25
    assert insured_max_amortization_years(d_mid, first_time_buyer=True, new_construction=False) == 25
    assert insured_max_amortization_years(d_mid, first_time_buyer=False, new_construction=True) == 25
    assert insured_max_amortization_years(d_mid, first_time_buyer=True, new_construction=True) == 30

    # Dec 15, 2024+: first-time buyer OR new build qualifies
    d_new = dt.date(2024, 12, 15)
    assert insured_max_amortization_years(d_new, first_time_buyer=False, new_construction=False) == 25
    assert insured_max_amortization_years(d_new, first_time_buyer=True, new_construction=False) == 30
    assert insured_max_amortization_years(d_new, first_time_buyer=False, new_construction=True) == 30
    assert insured_max_amortization_years(d_new, first_time_buyer=True, new_construction=True) == 30


def _tt_policy_and_snapshot_input_guardrails() -> None:
    """Input guardrails for policy/tax/snapshot helpers (regression set)."""
    import datetime as dt

    from rbv.core.mortgage import _annual_nominal_pct_to_monthly_rate, _monthly_rate_to_annual_nominal_pct
    from rbv.core.policy_canada import (
        cmhc_premium_rate_from_ltv,
        insured_30yr_amortization_policy_stage,
        insured_mortgage_price_cap,
        mortgage_default_insurance_sales_tax_rate,
    )
    from rbv.core.scenario_snapshots import (
        ScenarioConfig,
        ScenarioSnapshot,
        parse_scenario_payload,
        scenario_state_diff_rows,
    )
    from rbv.core.taxes import calc_transfer_tax

    # 1-2) Date coercion should not crash and should behave like "today".
    cap_none = insured_mortgage_price_cap(None)
    cap_today = insured_mortgage_price_cap(dt.date.today())
    _assert_close("TT-GUARD cap-none-equals-today", cap_none, cap_today, atol=0.0)

    stage_none = insured_30yr_amortization_policy_stage(None)
    stage_today = insured_30yr_amortization_policy_stage(dt.date.today())
    if stage_none != stage_today:
        _die(f"TT-GUARD stage-none mismatch: {stage_none} vs {stage_today}")

    # 3-4) CMHC helper should be safe for non-numeric LTV and continue valid edge behavior.
    _assert_close("TT-GUARD cmhc-nonnumeric", cmhc_premium_rate_from_ltv("abc"), 0.0, atol=0.0)
    _assert_close("TT-GUARD cmhc-95", cmhc_premium_rate_from_ltv(0.95), 0.04, atol=1e-12)

    # 5-8) Province aliases for mortgage insurance sales tax.
    _assert_close(
        "TT-GUARD pst-on", mortgage_default_insurance_sales_tax_rate("ON", dt.date(2026, 1, 1)), 0.08, atol=0.0
    )
    _assert_close(
        "TT-GUARD pst-sk", mortgage_default_insurance_sales_tax_rate("sk", dt.date(2026, 1, 1)), 0.06, atol=0.0
    )
    _assert_close(
        "TT-GUARD pst-qc", mortgage_default_insurance_sales_tax_rate("QC", dt.date(2026, 1, 1)), 0.09, atol=0.0
    )
    _assert_close(
        "TT-GUARD pst-qc-2027", mortgage_default_insurance_sales_tax_rate("pq", dt.date(2027, 1, 1)), 0.09975, atol=0.0
    )

    # 9-16) Tax province + boolean parsing regressions.
    _assert_close(
        "TT-GUARD tax-on-alias",
        float(calc_transfer_tax("ON", 500_000.0, first_time_buyer=False, toronto_property=False)["total"]),
        6475.0,
        atol=1e-6,
    )
    _assert_close(
        "TT-GUARD tax-bc-alias",
        float(calc_transfer_tax("BC", 500_000.0, first_time_buyer=False, toronto_property=False)["total"]),
        8000.0,
        atol=1e-6,
    )
    _assert_close(
        "TT-GUARD tax-nl-alias",
        float(calc_transfer_tax("NL", 400_000.0, first_time_buyer=False, toronto_property=False)["total"]),
        float(
            calc_transfer_tax("Newfoundland and Labrador", 400_000.0, first_time_buyer=False, toronto_property=False)[
                "total"
            ]
        ),
        atol=1e-9,
    )
    _assert_close(
        "TT-GUARD tax-pei-alias",
        float(calc_transfer_tax("PEI", 200_000.0, first_time_buyer=False, toronto_property=False)["total"]),
        1700.0,
        atol=1e-6,
    )

    # String booleans should not accidentally trigger rebates/toronto MLTT.
    _assert_close(
        "TT-GUARD bool-false-fthb",
        float(calc_transfer_tax("Ontario", 500_000.0, first_time_buyer="False", toronto_property=False)["total"]),
        6475.0,
        atol=1e-6,
    )
    _assert_close(
        "TT-GUARD bool-false-toronto",
        float(calc_transfer_tax("Ontario", 500_000.0, first_time_buyer=False, toronto_property="False")["total"]),
        6475.0,
        atol=1e-6,
    )
    _assert_close(
        "TT-GUARD bool-true-fthb",
        float(calc_transfer_tax("Ontario", 500_000.0, first_time_buyer="true", toronto_property=False)["total"]),
        2475.0,
        atol=1e-6,
    )
    _assert_close(
        "TT-GUARD bool-true-toronto",
        float(calc_transfer_tax("Ontario", 500_000.0, first_time_buyer=False, toronto_property="yes")["total"]),
        12950.0,
        atol=1e-6,
    )

    # 17-18) Snapshot helpers should tolerate non-dict state and preserve schema from payload state form.
    cfg = ScenarioConfig.from_state([("price", 1)])
    if cfg.state != {}:
        _die(f"TT-GUARD scenario-config non-dict state should clear; got {cfg.state}")

    cfg2 = ScenarioConfig.from_payload({"schema": "custom.schema", "state": {"price": 123}})
    if cfg2.schema != "custom.schema":
        _die(f"TT-GUARD scenario-config schema not preserved: {cfg2.schema}")

    # 19) ScenarioSnapshot should coerce config payload dicts.
    snap = ScenarioSnapshot(config={"state": {"price": 9}}, slot="X")
    if not isinstance(snap.config, ScenarioConfig):
        _die("TT-GUARD scenario-snapshot config not coerced")

    # 20) state diff helper should gracefully handle non-dict canonicalization outputs.
    rows = scenario_state_diff_rows("abc", [1, 2, 3])
    if rows != []:
        _die(f"TT-GUARD scenario-state-diff non-dict expected [], got {rows}")

    # 21-22) Mortgage helpers should sanitize NaN/inf, not propagate NaN/inf.
    _assert_close("TT-GUARD mort-nan", _annual_nominal_pct_to_monthly_rate(float('nan'), canadian=False), 0.0, atol=0.0)
    _assert_close("TT-GUARD mort-inf", _monthly_rate_to_annual_nominal_pct(float('inf'), canadian=False), 0.0, atol=0.0)

    # 23) parse payload should tolerate non-dict metadata.
    state_rt, meta = parse_scenario_payload({"state": {"x": 1}, "meta": "bad"})
    if int(state_rt.get("x", 0)) != 1 or not isinstance(meta, dict):
        _die("TT-GUARD parse_scenario_payload malformed-meta handling failed")


def _tt_discount_rate_unit_guard() -> None:
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


def _tt_scenario_snapshot_hash_stable_roundtrip() -> None:
    from rbv.core.scenario_snapshots import (
        SCENARIO_CONFIG_SCHEMA,
        SCENARIO_SNAPSHOT_SCHEMA,
        build_scenario_config,
        build_scenario_snapshot,
        parse_scenario_payload,
    )

    state_a = {
        "price": 800000.0,
        "down": 160000.00000000003,
        "province": "Ontario",
        "years": 25,
        "use_volatility": False,
    }
    # Same semantic values, different key order / floating noise.
    state_b = {
        "use_volatility": False,
        "years": 25.0,
        "province": "Ontario",
        "down": 160000.0,
        "price": 800000,
    }

    cfg_a = build_scenario_config(state_a)
    cfg_b = build_scenario_config(state_b)
    assert cfg_a.deterministic_hash() == cfg_b.deterministic_hash()

    snap = build_scenario_snapshot(state_a, slot="A", label="Scenario A", version="qa")
    payload = snap.to_dict()
    assert str(payload.get("schema")) == SCENARIO_SNAPSHOT_SCHEMA
    assert (
        isinstance(payload.get("config"), dict)
        and str((payload.get("config") or {}).get("schema")) == SCENARIO_CONFIG_SCHEMA
    )
    state_rt, meta = parse_scenario_payload(payload)
    assert state_rt.get("province") == "Ontario"
    assert int(state_rt.get("years")) == 25
    assert float(state_rt.get("down")) == 160000.0
    assert str(meta.get("slot")) == "A"
    assert str(meta.get("scenario_hash")) == cfg_a.deterministic_hash()


def _tt_scenario_snapshot_filters_allowed_keys() -> None:
    from rbv.core.scenario_snapshots import build_scenario_snapshot

    state = {"price": 700000, "province": "Quebec", "_tmp": "ignore-me"}
    snap = build_scenario_snapshot(state, slot="B", allowed_keys=["price", "province"])
    payload = snap.to_dict()
    st = payload.get("state") or {}
    assert "price" in st and "province" in st
    assert "_tmp" not in st
    assert str(payload.get("slot")) == "B"
    assert bool(payload.get("scenario_hash"))


def _tt_scenario_compare_delta_engine_zero_when_equal() -> None:
    from rbv.core.scenario_snapshots import compare_metric_rows, scenario_state_diff_rows

    metrics_a = {
        "advantage_final": 125000.0,
        "pv_advantage_final": 82000.0,
        "close_cash": 45550.0,
        "monthly_payment": 3199.25,
        "win_pct": 61.25,
    }
    metrics_b = {
        "advantage_final": 125000.0 + 1e-12,
        "pv_advantage_final": 82000.0,
        "close_cash": 45550.0,
        "monthly_payment": 3199.25 + 1e-12,
        "win_pct": 61.25,
    }

    rows = compare_metric_rows(metrics_a, metrics_b, atol=1e-9)
    by_metric = {str(r.get("metric")): r for r in rows}
    assert float(by_metric["Final Net Advantage"]["delta"]) == 0.0
    assert float(by_metric["Monthly Payment"]["delta"]) == 0.0
    assert float(by_metric["Win %"]["delta"]) == 0.0

    state_a = {"price": 900000.0, "rate": 5.1, "province": "Ontario"}
    state_b = {"province": "Ontario", "rate": 5.1 + 1e-12, "price": 900000}
    assert scenario_state_diff_rows(state_a, state_b, atol=1e-9) == []

    # Material change should still be reported.
    state_c = {"province": "Ontario", "rate": 5.6, "price": 900000}
    diffs = scenario_state_diff_rows(state_a, state_c, atol=1e-9)
    assert any(str(r.get("key")) == "rate" for r in diffs)


def _tt_compare_export_helpers_schema_and_csv() -> None:
    from rbv.core.scenario_snapshots import (
        build_compare_export_payload,
        compare_metric_rows_to_csv_text,
        scenario_state_diff_rows_to_csv_text,
    )

    payload_a = {
        "schema": "rbv.scenario_snapshot.v1",
        "slot": "A",
        "state": {"price": 800000, "province": "Ontario"},
    }
    payload_b = {
        "schema": "rbv.scenario_snapshot.v1",
        "slot": "B",
        "state": {"price": 820000, "province": "Ontario"},
    }
    metric_rows = [
        {"metric": "Final Net Advantage", "a": 100000.0, "b": 120000.0, "delta": 20000.0, "pct_delta": 20.0},
        {"metric": "Win %", "a": 55.0, "b": 61.0, "delta": 6.0, "pct_delta": 10.9090909},
    ]
    diff_rows = [
        {"key": "price", "a": 800000, "b": 820000},
        {"key": "notes", "a": {"x": 1}, "b": [1, 2]},
    ]

    exp = build_compare_export_payload(
        payload_a=payload_a,
        payload_b=payload_b,
        metric_rows=metric_rows,
        state_diff_rows=diff_rows,
        meta={"source": "qa"},
    )
    assert str(exp.get("schema")) == "rbv.compare_export.v1"
    assert isinstance(exp.get("snapshots"), dict) and "A" in exp["snapshots"] and "B" in exp["snapshots"]
    assert isinstance(exp.get("metrics"), list) and len(exp["metrics"]) == 2
    assert isinstance(exp.get("state_diffs"), list) and len(exp["state_diffs"]) == 2

    csv_metrics = compare_metric_rows_to_csv_text(metric_rows)
    assert csv_metrics.startswith("metric,a,b,delta,pct_delta\n")
    assert "Final Net Advantage" in csv_metrics and "Win %" in csv_metrics

    csv_diffs = scenario_state_diff_rows_to_csv_text(diff_rows)
    assert csv_diffs.startswith("key,a,b\n")
    assert "price,800000,820000" in csv_diffs
    # Nested values should serialize deterministically as JSON strings.
    assert '{""x"":1}' in csv_diffs


def main(argv: list[str] | None = None) -> None:
    # Mortgage invariants
    _tt_mortgage_rate_and_payment()
    _tt_reference_numbers_regression()
    _tt_purchase_closing_costs_reduce_buyer_nw()
    _tt_transfer_tax_examples_multi_province()
    _tt_bc_fthb_exemption_date_aware()
    _tt_insured_30yr_amortization_policy_schedule()
    _tt_amortization_interest_equity()
    _tt_zero_rate_sanity()

    # Taxes / liquidation invariants
    _tt_cmhc_pst_recompute()
    _tt_liquidation_cg_tax_end_only()
    _tt_annual_drag_disables_extra_liquidation_cg()
    _tt_special_assessment_applied_once()
    _tt_cg_inclusion_tier_and_shelter()
    _tt_discount_rate_unit_guard()
    _tt_ui_defaults_match_presets()
    _tt_city_preset_framework_toronto_mltt_and_summary()
    _tt_scenario_snapshot_hash_stable_roundtrip()
    _tt_scenario_snapshot_filters_allowed_keys()
    _tt_scenario_compare_delta_engine_zero_when_equal()
    _tt_compare_export_helpers_schema_and_csv()
    _tt_policy_and_snapshot_input_guardrails()

    # Rent control cadence
    _tt_rent_control_cadence_every3()
    _tt_moving_frequency_default_is_5_years()

    # MC determinism
    _tt_mc_seed_reproducible()

    print("\n[TRUTH TABLES OK]\n")


if __name__ == "__main__":
    main()
