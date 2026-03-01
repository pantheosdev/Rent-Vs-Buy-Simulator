#!/usr/bin/env python3
"""Automated sensitivity / dependency test suite for the modular Rent-vs-Buy simulator.

Goal:
- Perturb each important input +/-X (or +/- absolute delta)
- Assert that *at least one* relevant output changes (and optionally monotonic direction)
- Flag "dead inputs" (wired to UI but not affecting the engine/results)

Run:
  python qa_sensitivity.py

Notes:
- This is a *wiring + regression* test, not a full economic proof.
- We keep tests deterministic by default. A small MC sub-suite checks MC knobs.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root is on sys.path regardless of where this script is invoked from.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import copy
import datetime
import math
import sys

MONEY_EPS = 1.0          # $1 threshold for "changed"
SMALL_EPS = 1e-6         # fallback for unitless values
MC_EPS = 1.0             # $1 threshold for MC mean metrics
DEFAULT_REL_X = 0.05     # 5% perturb for large money inputs


def _finite(x) -> bool:
    try:
        return math.isfinite(float(x))
    except Exception:
        return False


def _changed(a, b, eps: float) -> bool:
    if a is None or b is None:
        return False
    try:
        a = float(a); b = float(b)
    except Exception:
        return False
    if (not _finite(a)) or (not _finite(b)):
        return False
    return abs(b - a) > eps


def _extract_metrics(df, close_cash, m_pmt, win_pct) -> dict:
    """Return a compact set of horizon metrics for sensitivity comparisons."""
    last = df.iloc[-1]
    out = {
        "Buyer Net Worth": float(last.get("Buyer Net Worth", float("nan"))),
        "Renter Net Worth": float(last.get("Renter Net Worth", float("nan"))),
        "PV Delta": float(last.get("PV Delta", float("nan"))),
        "Buyer Unrecoverable": float(last.get("Buyer Unrecoverable", float("nan"))),
        "Renter Unrecoverable": float(last.get("Renter Unrecoverable", float("nan"))),
        "Buyer Home Equity": float(last.get("Buyer Home Equity", float("nan"))),
        "Rent": float(last.get("Rent", float("nan"))),
        "Buy Payment": float(last.get("Buy Payment", float("nan"))),
        "Moving": float(last.get("Moving", float("nan"))),
        "Buyer Liquidation NW": float(last.get("Buyer Liquidation NW", float("nan"))) if "Buyer Liquidation NW" in df.columns else float("nan"),
        "Renter Liquidation NW": float(last.get("Renter Liquidation NW", float("nan"))) if "Renter Liquidation NW" in df.columns else float("nan"),
        "Buyer PV NW": float(last.get("Buyer PV NW", float("nan"))),
        "Renter PV NW": float(last.get("Renter PV NW", float("nan"))),
    }
    # MC mean columns (if present)
    if "PV Delta Mean" in df.columns:
        out["PV Delta Mean"] = float(last.get("PV Delta Mean", float("nan")))
        out["Buyer PV NW Mean"] = float(last.get("Buyer PV NW Mean", float("nan")))
        out["Renter PV NW Mean"] = float(last.get("Renter PV NW Mean", float("nan")))
    out["close_cash"] = float(close_cash) if close_cash is not None else float("nan")
    out["m_pmt"] = float(m_pmt) if m_pmt is not None else float("nan")
    out["win_pct"] = float(win_pct) if win_pct is not None else float("nan")
    return out


def _build_baseline_cfg(*, price: float, down: float, rent: float, province: str, toronto: bool, first_time: bool, years: int) -> dict:
    """Build a baseline cfg similar to app.py (computes mort/close/pst)."""
    from rbv.core.taxes import calc_transfer_tax

    lawyer = 1800.0
    insp = 500.0

    loan = max(0.0, price - down)
    ltv = (loan / price) if price > 0 else 0.0
    insured = (ltv > 0.80 + 1e-12)

    # Transfer tax
    asof = datetime.date.today()
    tt = calc_transfer_tax(province, float(price), first_time_buyer=bool(first_time), toronto_property=bool(toronto), override_amount=0.0, asof_date=asof)
    total_ltt = float(tt.get("total", 0.0) or 0.0)

    # CMHC premium approximation (matches app.py logic)
    cmhc_r = 0.04 if ltv > 0.90 else (0.031 if ltv > 0.85 else (0.028 if ltv > 0.80 else 0.0))
    prem = loan * (cmhc_r if insured else 0.0)

    # PST/QST on CMHC premium (province-dependent)
    _prov = str(province or "").strip().lower()
    _pst_rate = 0.0
    if _prov == "ontario":
        _pst_rate = 0.08
    elif _prov == "saskatchewan":
        _pst_rate = 0.06
    elif _prov == "quebec":
        _pst_rate = 0.09975
    pst = prem * _pst_rate

    mort = loan + prem
    close = total_ltt + lawyer + insp + pst

    cfg = {
        "years": int(years),
        "province": province,
        "toronto_property": bool(toronto),
        "first_time_buyer": bool(first_time),

        "price": float(price),
        "down": float(down),
        "rent": float(rent),

        "rate": 5.0,             # percent
        "nm": 25 * 12,           # months amortization

        "sell_cost": 0.05,
        "p_tax_rate": 0.007,
        "maint_rate": 0.010,
        "repair_rate": 0.002,

        # Monthly recurring owner/renter costs
        "condo": 350.0,
        "condo_inf": 0.02,
        "h_ins": 90.0,
        "o_util": 120.0,
        "r_ins": 25.0,
        "r_util": 80.0,

        "general_inf": 0.02,
        "rent_inf": 0.02,
        "discount_rate": 0.00,

        "moving_cost": 2500.0,
        "moving_freq": 5.0,

        # Rent control defaults (off unless enabled in a prereq)
        "rent_control_enabled": False,
        "rent_control_cap": 0.02,
        "rent_control_frequency_years": 1,
        "rent_control_frequency": 1,

        # Rate modes (off unless enabled)
        "rate_mode": "Fixed",
        "rate_reset_years_eff": 5,
        "rate_reset_to_eff": 6.0,
        "rate_reset_step_pp_eff": 0.25,
        "rate_shock_enabled_eff": False,
        "rate_shock_start_year_eff": 3,
        "rate_shock_duration_years_eff": 2,
        "rate_shock_pp_eff": 2.0,

        "canadian_compounding": True,

        # Property tax growth model (Phase-1/2 work)
        "prop_tax_growth_model": "Hybrid (recommended for Toronto)",
        "prop_tax_hybrid_addon_pct": 0.5,

        # Investment taxes
        "investment_tax_mode": "Pre-tax (no investment taxes)",
        "tax_r": 20.0,  # percent (only used in Annual return drag)

        # Cash-out / liquidation view
        "assume_sale_end": True,
        "show_liquidation_view": True,
        "cg_tax_end": 0.0,
        "home_sale_legal_fee": 0.0,

        # Mortgage + closing costs computed above
        "mort": float(mort),
        "close": float(close),
        "pst": float(pst),

        # Volatility defaults (MC suite uses these)
        "use_volatility": False,
        "num_sims": 200,
        "ret_std": 0.15,
        "apprec_std": 0.10,
        "vectorized_mc": True,
    }
    return cfg


def _run_det(cfg: dict, *, buyer_ret_pct: float = 7.0, renter_ret_pct: float = 7.0, apprec_pct: float = 3.0,
             invest_diff: float = 1.0, rent_closing: bool = False, mkt_corr: float = 0.25, mc_seed: int = 123):
    from rbv.core.engine import run_simulation_core
    df, close_cash, m_pmt, win_pct = run_simulation_core(
        cfg,
        buyer_ret_pct=buyer_ret_pct,
        renter_ret_pct=renter_ret_pct,
        apprec_pct=apprec_pct,
        invest_diff=invest_diff,
        rent_closing=rent_closing,
        mkt_corr=mkt_corr,
        force_deterministic=True,
        mc_seed=mc_seed,
        force_use_volatility=False,
        num_sims_override=1,
    )
    return _extract_metrics(df, close_cash, m_pmt, win_pct)


def _run_mc(cfg: dict, *, buyer_ret_pct: float = 7.0, renter_ret_pct: float = 7.0, apprec_pct: float = 3.0,
            invest_diff: float = 1.0, rent_closing: bool = False, mkt_corr: float = 0.25, mc_seed: int = 123, num_sims: int = 200):
    from rbv.core.engine import run_simulation_core
    cfg2 = copy.deepcopy(cfg)
    cfg2["use_volatility"] = True
    cfg2["num_sims"] = int(num_sims)
    df, close_cash, m_pmt, win_pct = run_simulation_core(
        cfg2,
        buyer_ret_pct=buyer_ret_pct,
        renter_ret_pct=renter_ret_pct,
        apprec_pct=apprec_pct,
        invest_diff=invest_diff,
        rent_closing=rent_closing,
        mkt_corr=mkt_corr,
        force_deterministic=False,
        mc_seed=mc_seed,
        force_use_volatility=True,
        num_sims_override=int(num_sims),
    )
    return _extract_metrics(df, close_cash, m_pmt, win_pct)


def main() -> None:
    # Build deterministic baseline
    cfg0 = _build_baseline_cfg(price=800_000.0, down=160_000.0, rent=3_200.0, province="Ontario",
                              toronto=True, first_time=False, years=10)

    base_det = _run_det(cfg0)
    # Deterministic runs may not produce win_pct; only enforce finiteness on core metrics.
    _core_keys = [
        "Buyer Net Worth", "Renter Net Worth", "PV Delta",
        "Buyer Unrecoverable", "Renter Unrecoverable",
        "Buyer Home Equity", "Buyer PV NW", "Renter PV NW",
        "close_cash", "m_pmt",
    ]
    for k in _core_keys:
        v = base_det.get(k)
        if not _finite(v):
            print(f"[FAIL] Baseline produced non-finite metric: {k}={v}")
            raise SystemExit(2)

    # ----------------------------
    # Deterministic sensitivity specs
    # ----------------------------
    # Each spec:
    # - name: label
    # - kind: "cfg" or "arg"
    # - key: cfg key OR arg name
    # - delta_rel OR delta_abs
    # - prereq: optional function(cfg)->cfg (for conditional features)
    # - expect: list of metric keys that must change (any one is enough)
    # - mono: optional {"metric": "...", "dir": +1/-1} direction check when increasing
    specs = [
        dict(name="price", kind="cfg", key="price", delta_rel=DEFAULT_REL_X, expect=["Buyer Net Worth", "Buyer Home Equity", "close_cash"], rebuild=True),
        dict(name="rent", kind="cfg", key="rent", delta_rel=DEFAULT_REL_X, expect=["Renter Net Worth", "PV Delta", "Renter Unrecoverable"], mono={"metric":"Renter Net Worth", "dir": -1}),
        dict(name="down", kind="cfg", key="down", delta_rel=DEFAULT_REL_X, expect=["Buyer Net Worth", "Buyer Home Equity", "close_cash"], rebuild=True),
        dict(name="rate (pp)", kind="cfg", key="rate", delta_abs=0.50, expect=["Buyer Net Worth", "Buy Payment"], mono={"metric":"Buyer Net Worth", "dir": -1}),
        dict(name="sell_cost", kind="cfg", key="sell_cost", delta_abs=0.01, expect=["Buyer Net Worth", "Buyer Liquidation NW"]),
        dict(name="p_tax_rate", kind="cfg", key="p_tax_rate", delta_abs=0.001, expect=["Buyer Net Worth", "Buyer Unrecoverable"]),
        dict(name="maint_rate", kind="cfg", key="maint_rate", delta_abs=0.002, expect=["Buyer Net Worth", "Buyer Unrecoverable"]),
        dict(name="repair_rate", kind="cfg", key="repair_rate", delta_abs=0.001, expect=["Buyer Net Worth", "Buyer Unrecoverable"]),
        dict(name="condo", kind="cfg", key="condo", delta_rel=0.10, expect=["Buyer Net Worth", "Buyer Unrecoverable"]),
        dict(name="h_ins", kind="cfg", key="h_ins", delta_rel=0.20, expect=["Buyer Net Worth", "Buyer Unrecoverable"]),
        dict(name="o_util", kind="cfg", key="o_util", delta_rel=0.20, expect=["Buyer Net Worth", "Buyer Unrecoverable"]),
        dict(name="r_ins", kind="cfg", key="r_ins", delta_rel=0.20, expect=["Renter Net Worth", "Renter Unrecoverable"]),
        dict(name="r_util", kind="cfg", key="r_util", delta_rel=0.20, expect=["Renter Net Worth", "Renter Unrecoverable"]),
        dict(name="general_inf", kind="cfg", key="general_inf", delta_abs=0.005, expect=["Buyer Unrecoverable", "Renter Unrecoverable"]),
        dict(name="rent_inf", kind="cfg", key="rent_inf", delta_abs=0.005, expect=["Renter Net Worth", "Rent"]),
        dict(name="discount_rate", kind="cfg", key="discount_rate", delta_abs=0.01, expect=["Buyer PV NW", "PV Delta"]),

        dict(name="buyer_ret_pct", kind="arg", key="buyer_ret_pct", delta_abs=1.0, expect=["Buyer Net Worth"], mono={"metric":"Buyer Net Worth", "dir": +1}, prereq=lambda c: {**copy.deepcopy(c), "rent": 4500.0}),
        dict(name="renter_ret_pct", kind="arg", key="renter_ret_pct", delta_abs=1.0, expect=["Renter Net Worth"], mono={"metric":"Renter Net Worth", "dir": +1}),
        dict(name="apprec_pct", kind="arg", key="apprec_pct", delta_abs=1.0, expect=["Buyer Net Worth"], mono={"metric":"Buyer Net Worth", "dir": +1}),
        dict(name="invest_diff (toggle)", kind="arg", key="invest_diff", delta_abs=1.0, expect=["Buyer Net Worth", "Renter Net Worth", "PV Delta"]),
    ]

    # Conditional: annual drag must respond to tax_r
    def _prereq_annual_drag(cfg: dict) -> dict:
        c = copy.deepcopy(cfg)
        c["investment_tax_mode"] = "Annual return drag"
        c["tax_r"] = 20.0
        return c

    specs.append(dict(name="tax_r (annual drag)", kind="cfg", key="tax_r", delta_abs=5.0,
                      prereq=_prereq_annual_drag, expect=["Buyer Net Worth", "Renter Net Worth"]))

    # Conditional: rent control cap/frequency must affect rent path when enabled
    def _prereq_rent_control(cfg: dict) -> dict:
        c = copy.deepcopy(cfg)
        c["rent_control_enabled"] = True
        c["rent_control_cap"] = 0.02
        c["rent_control_frequency_years"] = 1
        c["rent_control_frequency"] = 1
        return c

    specs.append(dict(name="rent_control_cap", kind="cfg", key="rent_control_cap", delta_abs=0.01,
                      prereq=_prereq_rent_control, expect=["Rent", "Renter Net Worth", "PV Delta"]))

    specs.append(dict(name="rent_control_frequency_years", kind="cfg", key="rent_control_frequency_years", delta_abs=2,
                      prereq=_prereq_rent_control, expect=["Renter Unrecoverable", "Rent Payment"]))

    # Moving frequency is discrete; change enough to alter the number of move events
    specs.append(dict(name="moving_freq", kind="cfg", key="moving_freq", delta_abs=2.0,
                      expect=["Moving", "Buyer Unrecoverable", "Renter Unrecoverable"]))

    # ----------------------------
    # Execute deterministic sensitivity
    # ----------------------------
    failures = []
    print("\n=== Deterministic sensitivity suite ===")
    for s in specs:
        cfg_use = cfg0
        if "prereq" in s and s["prereq"]:
            cfg_use = s["prereq"](cfg0)

        # baseline for this spec (if prereq changes cfg)
        base = _run_det(cfg_use)

        # build overrides
        cfg_p = copy.deepcopy(cfg_use)
        args_base = dict(buyer_ret_pct=7.0, renter_ret_pct=7.0, apprec_pct=3.0, invest_diff=1.0)
        args_p = copy.deepcopy(args_base)
        args_m = copy.deepcopy(args_base)

        if s["kind"] == "cfg":
            k = s["key"]
            v0 = float(cfg_use.get(k, 0.0) or 0.0)
            if "delta_rel" in s:
                dv = abs(v0) * float(s["delta_rel"])
                if dv == 0.0:
                    dv = float(s.get("delta_abs", 1.0))  # fallback
            else:
                dv = float(s.get("delta_abs", 0.0))
                if dv == 0.0:
                    dv = max(1.0, abs(v0) * DEFAULT_REL_X)

            # Some primary inputs (price/down) have downstream derived values (mort/close/pst).
            # When `rebuild=True`, re-run the baseline builder so derived values stay coherent.
            if s.get("rebuild"):
                price0 = float(cfg_use.get("price", 0.0) or 0.0)
                down0 = float(cfg_use.get("down", 0.0) or 0.0)
                rent0 = float(cfg_use.get("rent", 0.0) or 0.0)
                province0 = str(cfg_use.get("province", "Ontario"))
                tor0 = bool(cfg_use.get("toronto_property", False))
                ftb0 = bool(cfg_use.get("first_time_buyer", False))
                years0 = int(cfg_use.get("years", 10))

                if k == "price":
                    cfg_p = _build_baseline_cfg(price=max(0.0, price0 + dv), down=down0, rent=rent0, province=province0, toronto=tor0, first_time=ftb0, years=years0)
                    cfg_m = _build_baseline_cfg(price=max(0.0, price0 - dv), down=down0, rent=rent0, province=province0, toronto=tor0, first_time=ftb0, years=years0)
                elif k == "down":
                    cfg_p = _build_baseline_cfg(price=price0, down=max(0.0, down0 + dv), rent=rent0, province=province0, toronto=tor0, first_time=ftb0, years=years0)
                    cfg_m = _build_baseline_cfg(price=price0, down=max(0.0, down0 - dv), rent=rent0, province=province0, toronto=tor0, first_time=ftb0, years=years0)
                else:
                    cfg_p[k] = v0 + dv
                    cfg_m = copy.deepcopy(cfg_use)
                    cfg_m[k] = max(0.0, v0 - dv) if k not in ("discount_rate", "general_inf", "rent_inf", "rent_control_cap") else (v0 - dv)
            else:
                cfg_p[k] = v0 + dv
                cfg_m = copy.deepcopy(cfg_use)
                cfg_m[k] = max(0.0, v0 - dv) if k not in ("discount_rate", "general_inf", "rent_inf", "rent_control_cap") else (v0 - dv)
        else:
            k = s["key"]
            v0 = float(args_base.get(k, 0.0) or 0.0)
            dv = float(s.get("delta_abs", 1.0))

            if k == "invest_diff":
                # treat as boolean toggle: base=True, plus=True, minus=False
                args_p[k] = 1.0
                args_m[k] = 0.0
            else:
                args_p[k] = v0 + dv
                args_m[k] = v0 - dv

            cfg_m = cfg_use

        # run perturbed
        plus = _run_det(cfg_p if s["kind"]=="cfg" else cfg_use, **args_p)
        minus = _run_det(cfg_m if s["kind"]=="cfg" else cfg_use, **args_m)

        # check expected outputs
        expect = s.get("expect", [])
        ok = False
        for met in expect:
            eps = MONEY_EPS if ("Net Worth" in met or "PV" in met or "Unrecoverable" in met or met in ("Rent","Buy Payment","close_cash")) else SMALL_EPS
            if _changed(base.get(met), plus.get(met), eps) or _changed(base.get(met), minus.get(met), eps):
                ok = True
                break

        # monotonic check on plus direction (optional)
        mono_ok = True
        mono = s.get("mono")
        if mono:
            met = mono["metric"]
            direction = mono["dir"]
            a = base.get(met); b = plus.get(met)
            if _finite(a) and _finite(b):
                if direction > 0 and not (b > a + MONEY_EPS):
                    mono_ok = False
                if direction < 0 and not (b < a - MONEY_EPS):
                    mono_ok = False
            else:
                mono_ok = False

        if ok and mono_ok:
            print(f"[PASS] {s['name']}")
        else:
            why = []
            if not ok:
                why.append("no expected metric changed")
            if not mono_ok:
                why.append("monotonic expectation failed")
            failures.append((s["name"], "; ".join(why)))
            print(f"[FAIL] {s['name']}: {'; '.join(why)}")

    # ----------------------------
    # Monte Carlo knob sub-suite (small, non-flaky)
    # ----------------------------
    print("\n=== Monte Carlo knob sub-suite ===")
    mc_fail = []

    mc_base = _run_mc(cfg0, mc_seed=123, num_sims=200)
    if "PV Delta Mean" not in mc_base:
        mc_fail.append(("MC baseline", "missing mean columns"))
    else:
        # ret_std should change mean distribution (at least slightly)
        cfg_std = copy.deepcopy(cfg0); cfg_std["ret_std"] = 0.25
        mc_std = _run_mc(cfg_std, mc_seed=123, num_sims=200)
        if not _changed(mc_base.get("PV Delta Mean"), mc_std.get("PV Delta Mean"), MC_EPS):
            mc_fail.append(("ret_std", "PV Delta Mean did not change"))

        # apprec_std
        cfg_astd = copy.deepcopy(cfg0); cfg_astd["apprec_std"] = 0.25
        mc_astd = _run_mc(cfg_astd, mc_seed=123, num_sims=200)
        if not _changed(mc_base.get("PV Delta Mean"), mc_astd.get("PV Delta Mean"), MC_EPS):
            mc_fail.append(("apprec_std", "PV Delta Mean did not change"))

        # seed change should change mean *or* win_pct (allow either)
        mc_seed2 = _run_mc(cfg0, mc_seed=456, num_sims=200)
        if (not _changed(mc_base.get("PV Delta Mean"), mc_seed2.get("PV Delta Mean"), MC_EPS)) and (not _changed(mc_base.get("win_pct"), mc_seed2.get("win_pct"), 0.01)):
            mc_fail.append(("mc_seed", "neither mean nor win_pct changed"))

    for name, msg in mc_fail:
        print(f"[FAIL] {name}: {msg}")
    for name, msg in failures:
        pass

    if failures or mc_fail:
        print("\n=== SENSITIVITY SUITE FAILED ===")
        if failures:
            print("\nDeterministic failures:")
            for n, msg in failures:
                print(f" - {n}: {msg}")
        if mc_fail:
            print("\nMonte Carlo failures:")
            for n, msg in mc_fail:
                print(f" - {n}: {msg}")
        raise SystemExit(1)

    print("\n[SENSITIVITY SUITE PASS] All tested inputs influenced expected outputs.\n")


if __name__ == "__main__":
    main()
