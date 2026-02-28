#!/usr/bin/env python3
"""Golden regression snapshots for the modular Rent-vs-Buy simulator.

Purpose
- Catch unintended model/output drift via a small set of canonical scenarios.
- These are not unit tests for every formula; they are end-to-end sanity anchors.

Run
  python qa_golden.py
  python -m rbv.qa.qa_golden

Notes
- Metrics are asserted at the terminal row (horizon) within tolerances.
- If you intentionally change core math/assumptions, re-baseline by running:
      python -m rbv.qa.qa_golden --print-baseline
  and then copy the printed dict into _EXPECTED.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Any, Dict, Tuple


# Ensure repo root is on sys.path regardless of where this script is invoked from.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# === Golden expected terminal metrics (v2_91 baseline) ===
# NOTE: If you intentionally change core math/assumptions, regenerate via:
#   python -m rbv.qa.qa_golden --print-baseline
_EXPECTED: Dict[str, Dict[str, float]] = {'deterministic_baseline': {'Buyer Net Worth': 524081.12166366115,
                            'Buyer Unrecoverable': 571222.6776092583,
                            'Renter Net Worth': 520750.6104907838,
                            'Renter Unrecoverable': 454164.3024731583,
                            'close_cash': 185000.0,
                            'mort_pmt': 3722.2719042368994},
 'insured_price_1100k_ltv90': {'Buyer Net Worth': 623707.5461864672,
                               'Buyer Unrecoverable': 825416.4806196475,
                               'Renter Net Worth': 753728.3563562596,
                               'Renter Unrecoverable': 454164.3024731583,
                               'close_cash': 137455.2,
                               'mort_pmt': 5936.383921774313},
 'insured_price_999k_ltv95': {'Buyer Net Worth': 550656.6092416401,
                              'Buyer Unrecoverable': 763547.4923318863,
                              'Renter Net Worth': 564481.2831795219,
                              'Renter Unrecoverable': 454164.3024731583,
                              'close_cash': 74999.95000000001,
                              'mort_pmt': 5525.24183260429},
 'ltv80_no_cmhc': {'Buyer Net Worth': 592716.2618716216,
                   'Buyer Unrecoverable': 634693.8777744222,
                   'Renter Net Worth': 637808.3400752838,
                   'Renter Unrecoverable': 454164.3024731583,
                   'close_cash': 205000.0,
                   'mort_pmt': 4187.555892266511},
 'mc_fixed_seed_200': {'Buyer Net Worth': 466342.125,
                       'Buyer Unrecoverable': 559911.25,
                       'Renter Net Worth': 487680.75,
                       'Renter Unrecoverable': 454164.3024731583,
                       'close_cash': 185000.0,
                       'mort_pmt': 3722.2719042368994,
                       'win_pct': 41.5},
 'non_toronto_ltt': {'Buyer Net Worth': 987549.2642624272,
                     'Buyer Unrecoverable': 921537.7585061152,
                     'Renter Net Worth': 1311942.7642649426,
                     'Renter Unrecoverable': 454164.3024731583,
                     '_qa_tax_delta': 0.0,
                     '_qa_tax_total': 24475.0,
                     'close_cash': 375000.0,
                     'mort_pmt': 6106.852342888663},
 'rent_control_every3': {'Buyer Net Worth': 524081.12166366115,
                         'Buyer Unrecoverable': 571222.6776092583,
                         'Renter Net Worth': 537883.84344208,
                         'Renter Unrecoverable': 437031.06952186255,
                         'close_cash': 185000.0,
                         'mort_pmt': 3722.2719042368994},
 'rent_control_off': {'Buyer Net Worth': 524081.12166366115,
                      'Buyer Unrecoverable': 571222.6776092583,
                      'Renter Net Worth': 520750.6104907838,
                      'Renter Unrecoverable': 454164.3024731583,
                      'close_cash': 185000.0,
                      'mort_pmt': 3722.2719042368994},
 'rent_control_on': {'Buyer Net Worth': 524081.12166366115,
                     'Buyer Unrecoverable': 571222.6776092583,
                     'Renter Net Worth': 530491.183986456,
                     'Renter Unrecoverable': 444423.7289774868,
                     'close_cash': 185000.0,
                     'mort_pmt': 3722.2719042368994},
 'toronto_ltt': {'Buyer Net Worth': 963074.2642624272,
                 'Buyer Unrecoverable': 946012.7585061152,
                 'Renter Net Worth': 1311942.7642649426,
                 'Renter Unrecoverable': 454164.3024731583,
                 '_qa_tax_delta': 24475.0,
                 '_qa_tax_total': 48950.0,
                 'close_cash': 399475.0,
                 'mort_pmt': 6106.852342888663},
 'uninsured_price_1mplus_ltv95': {'Buyer Net Worth': 519575.1944543496,
                                  'Buyer Unrecoverable': 783152.634462653,
                                  'Renter Net Worth': 591004.4574053759,
                                  'Renter Unrecoverable': 454164.3024731583,
                                  'close_cash': 78040.05304,
                                  'mort_pmt': 5746.262998422964}}


def _finite(x) -> bool:
    try:
        return math.isfinite(float(x))
    except Exception:
        return False


def _hex_to_rgb(h: str) -> Tuple[int, int, int]:
    h = (h or "").lstrip("#")
    if len(h) != 6:
        return (0, 0, 0)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _cmhc_premium_rate(price: float, down: float) -> float:
    """Mirror engine CMHC logic using policy_canada for the insured-mortgage price cap.

    Updated 2025-01 to reflect the Dec 2024 cap increase from $1,000,000 to $1,500,000.
    """
    from rbv.core.policy_canada import insured_mortgage_price_cap, cmhc_premium_rate_from_ltv
    import datetime as _dt
    loan = max(float(price) - float(down), 0.0)
    ltv = (loan / float(price)) if float(price) > 0 else 0.0
    price_cap = insured_mortgage_price_cap(_dt.date.today())
    if float(price) < price_cap and ltv > 0.8:
        return cmhc_premium_rate_from_ltv(ltv)
    return 0.0


def _pst_rate_for_prov(prov: str) -> float:
    p = (prov or "").strip().lower()
    if p == "ontario":
        return 0.08
    if p == "saskatchewan":
        return 0.06
    if p == "quebec":
        return 0.09975
    return 0.0


def _build_base_cfg() -> Dict[str, Any]:
    # Mirrors qa_scenarios baseline, with canonical province name (used by tax + CMHC PST logic).
    return {
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
        "close": 25_000.0,  # base close (non-Toronto), PST on CMHC is added when applicable
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


def _apply_price_down(cfg: Dict[str, Any], *, price: float, down: float, base_close: float = 25_000.0) -> Dict[str, Any]:
    prov = str(cfg.get("province", "Ontario") or "Ontario")
    cmhc_r = _cmhc_premium_rate(price, down)
    loan = max(float(price) - float(down), 0.0)
    prem = loan * float(cmhc_r)
    pst = prem * _pst_rate_for_prov(prov)

    out = dict(cfg)
    out["price"] = float(price)
    out["down"] = float(down)
    out["pst"] = float(pst)
    out["mort"] = float(loan + prem)
    out["close"] = float(base_close + pst)
    return out


def _apply_toronto_close_delta(cfg: Dict[str, Any], *, toronto_property: bool, first_time_buyer: bool = False, base_close: float = 25_000.0) -> Dict[str, Any]:
    from rbv.core.taxes import calc_transfer_tax

    price = float(cfg.get("price", 0.0))
    prov = str(cfg.get("province", "Ontario") or "Ontario")

    t_tor = calc_transfer_tax(prov, price, first_time_buyer=first_time_buyer, toronto_property=bool(toronto_property))
    t_non = calc_transfer_tax(prov, price, first_time_buyer=first_time_buyer, toronto_property=False)
    delta = float(t_tor.get("total", 0.0)) - float(t_non.get("total", 0.0))

    out = dict(cfg)
    out["close"] = float(base_close + delta + float(out.get("pst", 0.0)))
    # QA-only diagnostic fields (not used by engine)
    out["_qa_tax_total"] = float(t_tor.get("total", 0.0))
    out["_qa_tax_delta"] = float(delta)
    return out


def _run(cfg: Dict[str, Any], *, force_det: bool, force_use_vol: bool, num_sims: int, mc_seed: int = 123) -> Dict[str, float]:
    from rbv.core.engine import run_simulation_core

    df, close_cash, m_pmt, win_pct = run_simulation_core(
        cfg,
        buyer_ret_pct=7.0,
        renter_ret_pct=7.0,
        apprec_pct=3.0,
        invest_diff=0.0,
        rent_closing=False,
        mkt_corr=0.25,
        force_deterministic=force_det,
        mc_seed=mc_seed,
        force_use_volatility=force_use_vol,
        num_sims_override=max(1, int(num_sims)),
        budget_enabled=False,
        monthly_income=10_000.0,
        monthly_nonhousing=4_000.0,
        income_growth_pct=2.0,
        budget_allow_withdraw=True,
    )

    if df is None or len(df) < 5:
        raise RuntimeError("Simulation returned empty/short dataframe")

    last = df.iloc[-1]
    out = {
        "Buyer Net Worth": float(last["Buyer Net Worth"]),
        "Renter Net Worth": float(last["Renter Net Worth"]),
        "Buyer Unrecoverable": float(last["Buyer Unrecoverable"]),
        "Renter Unrecoverable": float(last["Renter Unrecoverable"]),
        "close_cash": float(close_cash),
        "mort_pmt": float(m_pmt),
    }
    if win_pct is not None:
        out["win_pct"] = float(win_pct)

    # propagate QA diagnostic fields if present
    if "_qa_tax_delta" in cfg:
        out["_qa_tax_delta"] = float(cfg.get("_qa_tax_delta") or 0.0)
    if "_qa_tax_total" in cfg:
        out["_qa_tax_total"] = float(cfg.get("_qa_tax_total") or 0.0)

    return out


def _assert_close(actual: float, expected: float, *, tol_pct: float, tol_abs: float, label: str) -> None:
    if not _finite(actual) or not _finite(expected):
        raise AssertionError(f"Non-finite in {label}: actual={actual}, expected={expected}")
    abs_err = abs(float(actual) - float(expected))
    rel_err = abs_err / max(1.0, abs(float(expected)))
    if abs_err > tol_abs and rel_err > tol_pct:
        raise AssertionError(
            f"{label} outside tolerance: actual={actual:,.6f} expected={expected:,.6f} "  # small bilingual hint; safe
            f"abs_err={abs_err:,.6f} rel_err={rel_err*100:.3f}% (tol_abs={tol_abs}, tol_pct={tol_pct*100:.2f}%)"
        )


def _run_and_check(name: str, cfg: Dict[str, Any], run_kw: Dict[str, Any], *, tol_profile: str) -> None:
    expected = _EXPECTED.get(name)
    if not expected:
        raise RuntimeError(f"Missing expected baseline for scenario: {name}")

    actual = _run(cfg, **run_kw)

    # Tolerance profiles: keep public-grade stability while allowing tiny float drift.
    if tol_profile == "det":
        tol_net_pct = 0.010   # 1.0%
        tol_pay_pct = 0.005   # 0.5%
        tol_abs = 250.0
    elif tol_profile == "mc":
        tol_net_pct = 0.015   # 1.5%
        tol_pay_pct = 0.0075  # 0.75%
        tol_abs = 600.0
    else:
        tol_net_pct = 0.010
        tol_pay_pct = 0.005
        tol_abs = 250.0

    # Validate all expected keys
    for k, exp_v in expected.items():
        act_v = actual.get(k, None)
        if act_v is None:
            raise AssertionError(f"Scenario '{name}' missing metric '{k}' in actual output")

        if k in ("mort_pmt", "close_cash", "win_pct", "_qa_tax_delta", "_qa_tax_total"):
            _assert_close(float(act_v), float(exp_v), tol_pct=tol_pay_pct, tol_abs=tol_abs, label=f"{name} :: {k}")
        else:
            _assert_close(float(act_v), float(exp_v), tol_pct=tol_net_pct, tol_abs=tol_abs, label=f"{name} :: {k}")


def _build_cases() -> Dict[str, Tuple[Dict[str, Any], Dict[str, Any], str]]:
    base = _build_base_cfg()

    cases: Dict[str, Tuple[Dict[str, Any], Dict[str, Any], str]] = {}

    # 1) Volatility OFF (deterministic)
    cfg_det = dict(base)
    cfg_det["use_volatility"] = False
    cfg_det["num_sims"] = 0
    cases["deterministic_baseline"] = (cfg_det, {"force_det": True, "force_use_vol": False, "num_sims": 1}, "det")

    # 2) Fixed-seed MC (smoke for MC plumbing + stability)
    cfg_mc = dict(base)
    cfg_mc["use_volatility"] = True
    cfg_mc["num_sims"] = 200
    cases["mc_fixed_seed_200"] = (cfg_mc, {"force_det": False, "force_use_vol": True, "num_sims": 200}, "mc")

    # 3-4) Rent control OFF/ON
    cases["rent_control_off"] = (cfg_det, {"force_det": True, "force_use_vol": False, "num_sims": 1}, "det")

    cfg_rc = dict(base)
    cfg_rc["rent_control_enabled"] = True
    cfg_rc["rent_control_cap"] = 0.02
    cfg_rc["rent_control_frequency_years"] = 1
    cases["rent_control_on"] = (cfg_rc, {"force_det": True, "force_use_vol": False, "num_sims": 1}, "det")

    cfg_rc3 = dict(base)
    cfg_rc3["rent_control_enabled"] = True
    cfg_rc3["rent_control_cap"] = 0.02
    cfg_rc3["rent_control_frequency_years"] = 3
    cases["rent_control_every3"] = (cfg_rc3, {"force_det": True, "force_use_vol": False, "num_sims": 1}, "det")

    # 5-6) Insured vs uninsured boundary (< $1,500,000 enables CMHC since Dec-2024)
    cfg_ins = _apply_price_down(base, price=999_999.0, down=0.05 * 999_999.0, base_close=25_000.0)
    cases["insured_price_999k_ltv95"] = (cfg_ins, {"force_det": True, "force_use_vol": False, "num_sims": 1}, "det")

    cfg_unins = _apply_price_down(base, price=1_000_001.0, down=0.05 * 1_000_001.0, base_close=25_000.0)
    cases["uninsured_price_1mplus_ltv95"] = (cfg_unins, {"force_det": True, "force_use_vol": False, "num_sims": 1}, "det")

    # NEW: $1.1M insured scenario (should apply CMHC since Dec-2024 cap = $1.5M)
    # NOTE: Use the same base config object for consistency (avoid NameError: cfg_base).
    cfg_ins_1m1 = _apply_price_down(dict(base), price=1_100_000.0, down=110_000.0, base_close=25_000.0)
    cases["insured_price_1100k_ltv90"] = (cfg_ins_1m1, {"force_det": True, "force_use_vol": False, "num_sims": 1}, "det")

    # 7) LTV 80% exact (no CMHC)
    cfg_ltv80 = _apply_price_down(base, price=900_000.0, down=0.20 * 900_000.0, base_close=25_000.0)
    cases["ltv80_no_cmhc"] = (cfg_ltv80, {"force_det": True, "force_use_vol": False, "num_sims": 1}, "det")

    # 8-9) Toronto vs non-Toronto LTT (close cost delta wired through cfg.close)
    cfg_t0 = _apply_price_down(base, price=1_400_000.0, down=0.25 * 1_400_000.0, base_close=25_000.0)

    cfg_t = _apply_toronto_close_delta(cfg_t0, toronto_property=True, first_time_buyer=False, base_close=25_000.0)
    cases["toronto_ltt"] = (cfg_t, {"force_det": True, "force_use_vol": False, "num_sims": 1}, "det")

    cfg_nt = _apply_toronto_close_delta(cfg_t0, toronto_property=False, first_time_buyer=False, base_close=25_000.0)
    cases["non_toronto_ltt"] = (cfg_nt, {"force_det": True, "force_use_vol": False, "num_sims": 1}, "det")

    return cases


def _compute_baseline() -> Dict[str, Dict[str, float]]:
    cases = _build_cases()
    out: Dict[str, Dict[str, float]] = {}
    for name, (cfg, run_kw, _tol_profile) in cases.items():
        out[name] = _run(cfg, **run_kw)
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--print-baseline", action="store_true", help="Print a freshly computed baseline dict and exit.")
    args = ap.parse_args(argv)

    if args.print_baseline:
        import pprint
        pprint.pprint(_compute_baseline(), width=120, sort_dicts=True)
        return

    cases = _build_cases()

    print("[QA GOLDEN] Running golden snapshot scenarios...")

    for name, (cfg, run_kw, tol_profile) in cases.items():
        _run_and_check(name, cfg, run_kw, tol_profile=tol_profile)
        print(f"  OK: {name}")

    print("\n[QA GOLDEN OK] All golden scenarios within tolerance.")


if __name__ == "__main__":
    main()
