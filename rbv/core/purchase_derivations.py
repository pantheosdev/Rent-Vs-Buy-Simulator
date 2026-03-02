"""Purchase-time derivations shared by UI, CLI, and the core engine.

The Streamlit UI pre-computes several *derived* purchase fields and includes them
in the engine config dict (``cfg``):

  - ``mort``: initial mortgage principal (base loan + insured premium if applicable)
  - ``pst``: PST/QST on the insured premium (province/date dependent)
  - ``close``: total closing costs (transfer tax + fees + pst on premium)

Historically, the engine assumed these keys were always present. That assumption
is true for the UI, but it is **not** true for headless callers (CLI/tests/other
integrations). This module provides a single, pure helper to derive those fields
when missing so headless runs match UI economics.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass

from .mortgage import _annual_nominal_pct_to_monthly_rate
from .policy_canada import (
    cmhc_premium_rate_from_ltv,
    insured_mortgage_price_cap,
    min_down_payment_canada,
    mortgage_default_insurance_sales_tax_rate,
)
from .taxes import calc_transfer_tax


def _f(x, default: float = 0.0) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return float(default)


def _b(x) -> bool:
    return bool(x)


def _parse_asof_date(x) -> _dt.date:
    """Parse a policy as-of date.

    Accepts:
      - datetime.date
      - datetime.datetime
      - ISO strings (YYYY-MM-DD...)
      - None -> today
    """
    if x is None:
        return _dt.date.today()
    if hasattr(x, "date") and hasattr(x, "year") and hasattr(x, "month") and hasattr(x, "day"):
        # datetime.date or datetime.datetime
        try:
            return x if isinstance(x, _dt.date) and not isinstance(x, _dt.datetime) else x.date()
        except Exception:
            return _dt.date.today()
    try:
        return _dt.date.fromisoformat(str(x)[:10])
    except Exception:
        return _dt.date.today()


def _mortgage_payment(principal: float, mr: float, n_months: int) -> float:
    """Fixed monthly payment.

    Matches the engine's behavior for mr≈0 and negative-rate hypotheticals.
    """
    p = _f(principal, 0.0)
    n = max(1, int(n_months or 1))
    try:
        r = float(mr)
    except Exception:
        r = 0.0
    r = max(r, -0.999999)
    if p <= 0.0:
        return 0.0
    if abs(r) < 1e-12:
        return p / float(n)
    base = 1.0 + r
    if base <= 0.0:
        base = 1e-12
    pow_ = base ** float(n)
    return p * (r * pow_) / (pow_ - 1.0)


@dataclass(frozen=True)
class DerivedPurchase:
    """Derived purchase-time fields."""

    mort: float
    pst: float
    close: float
    monthly_payment: float
    loan: float
    premium: float
    ltv: float
    transfer_tax_total: float


def derive_purchase_fields(cfg: dict, *, strict: bool = False) -> DerivedPurchase:
    """Derive mort/pst/close/monthly_payment from a (possibly incomplete) cfg.

    If ``strict`` is True, raises ValueError for invalid insured-mortgage scenarios
    (e.g., down below the minimum rule, LTV>95%, insured above the price cap).
    """
    price = _f(cfg.get("price", 0.0), 0.0)
    down = _f(cfg.get("down", 0.0), 0.0)
    province = str(cfg.get("province", "Ontario") or "Ontario").strip()
    down_src = str(cfg.get("down_payment_source", "Traditional") or "Traditional")
    asof = _parse_asof_date(cfg.get("asof_date", None))

    # Transfer tax knobs (UI-compatible)
    first_time = _b(cfg.get("first_time", True))
    toronto = _b(cfg.get("toronto", False))
    override_amt = _f(cfg.get("transfer_tax_override", 0.0), 0.0)
    assessed_value = cfg.get("assessed_value", None)
    if assessed_value is not None:
        assessed_value = _f(assessed_value, price)
    ns_deed_transfer_rate = cfg.get("ns_deed_transfer_rate", None)
    if ns_deed_transfer_rate is not None:
        ns_deed_transfer_rate = _f(ns_deed_transfer_rate, 0.0)
        # Back-compat: allow percent-points input like 1.5 for 1.5%
        if ns_deed_transfer_rate > 1.0:
            ns_deed_transfer_rate = ns_deed_transfer_rate / 100.0

    tt = calc_transfer_tax(
        province,
        float(price),
        bool(first_time),
        bool(toronto),
        override_amount=float(override_amt),
        asof_date=asof,
        assessed_value=assessed_value,
        ns_deed_transfer_rate=ns_deed_transfer_rate,
    )
    transfer_tax_total = _f(tt.get("total", 0.0), 0.0)

    # Fees (UI-compatible names)
    lawyer = _f(cfg.get("purchase_legal_fee", cfg.get("lawyer", 1800.0)), 1800.0)
    insp = _f(cfg.get("home_inspection", 500.0), 500.0)
    other = _f(cfg.get("other_closing_costs", 0.0), 0.0)

    # Mortgage
    loan = max(price - down, 0.0)
    ltv = (loan / price) if price > 0 else 0.0
    insured_attempt = (price > 0.0) and (ltv > 0.80 + 1e-12)

    premium = 0.0
    pst = 0.0
    mort = loan

    if insured_attempt:
        min_down = float(min_down_payment_canada(float(price), asof))
        price_cap = float(insured_mortgage_price_cap(asof))

        if down + 1e-9 < min_down:
            msg = (
                f"Minimum down payment is about ${min_down:,.0f} for price ${price:,.0f} "
                f"as of {asof.isoformat()}."
            )
            if strict:
                raise ValueError(msg)
        if price >= price_cap:
            msg = (
                f"Insured mortgages are not available at/above ${price_cap:,.0f} purchase price "
                f"as of {asof.isoformat()}."
            )
            if strict:
                raise ValueError(msg)
        if ltv > 0.95 + 1e-12:
            msg = f"Maximum LTV for insured mortgages is 95% (ltv={ltv:.4f})."
            if strict:
                raise ValueError(msg)

        cmhc_eligible = (down + 1e-9 >= min_down) and (price < price_cap) and (ltv <= 0.95 + 1e-12)
        if cmhc_eligible:
            cmhc_r = float(cmhc_premium_rate_from_ltv(float(ltv), down_src))
            premium = loan * cmhc_r
            pst_rate = float(mortgage_default_insurance_sales_tax_rate(province, asof))
            pst = premium * pst_rate
            mort = loan + premium

    close = transfer_tax_total + lawyer + insp + other + pst

    # Payment uses cfg's amortization months (nm) and nominal annual rate in percent.
    nm = int(max(1, int(cfg.get("nm", 300) or 300)))
    rate_pct = _f(cfg.get("rate", 0.0), 0.0)
    canadian = bool(cfg.get("canadian_compounding", True))
    mr = _annual_nominal_pct_to_monthly_rate(float(rate_pct), bool(canadian))
    pmt = _mortgage_payment(mort, float(mr), nm)

    return DerivedPurchase(
        mort=float(mort),
        pst=float(pst),
        close=float(close),
        monthly_payment=float(pmt),
        loan=float(loan),
        premium=float(premium),
        ltv=float(ltv),
        transfer_tax_total=float(transfer_tax_total),
    )


def enrich_cfg_with_purchase_derivations(cfg: dict, *, strict: bool = False) -> dict:
    """Return a copy of ``cfg`` enriched with missing purchase-time derived fields.

    Behavior:
      - Never mutates the caller's dict.
      - Computes and fills ``mort``/``pst``/``close`` only when missing/zero.
      - Always ensures ``asof_date`` is present (ISO string) for auditability.
    """
    out = dict(cfg or {})

    # Ensure an as-of date exists so policy-dependent fields are reproducible.
    asof = _parse_asof_date(out.get("asof_date", None))
    out["asof_date"] = asof.isoformat()

    need_mort = _f(out.get("mort", 0.0), 0.0) <= 0.0
    need_close = _f(out.get("close", 0.0), 0.0) <= 0.0
    need_pst = _f(out.get("pst", 0.0), 0.0) <= 0.0

    # Only derive if something material is missing.
    if not (need_mort or need_close or need_pst):
        return out

    d = derive_purchase_fields(out, strict=strict)

    if need_mort and d.mort > 0.0:
        out["mort"] = float(d.mort)
    if need_pst and d.pst > 0.0:
        out["pst"] = float(d.pst)
    if need_close and d.close > 0.0:
        out["close"] = float(d.close)

    return out
