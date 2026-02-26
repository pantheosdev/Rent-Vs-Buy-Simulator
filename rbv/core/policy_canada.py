"""Canada-specific policy helpers.

These are *rules-of-thumb* used for simulation defaults; lenders/insurers may apply additional criteria.
We key rules off an as-of date so changes can be audited over time.
"""

from __future__ import annotations

import datetime as dt


# Last reviewed for correctness (YYYY-MM-DD).
# Update this when modifying any thresholds in this module.
POLICY_LAST_REVIEWED = dt.date(2026, 2, 23)


def _coerce_date(asof_date: dt.date | None) -> dt.date:
    """Return a safe date for policy lookups.

    Public helpers in this module are called by UI/session state code where values may
    be missing or stringly typed. Falling back to today's date avoids hard crashes.
    """
    if isinstance(asof_date, dt.date):
        return asof_date
    return dt.date.today()


def insured_mortgage_price_cap(asof_date: dt.date) -> float:
    """Return the insured-mortgage purchase price cap for the given as-of date.

    As of 2024-12-15, the federal government increased the cap from $1,000,000 to $1,500,000.
    """
    d = _coerce_date(asof_date)
    if d >= dt.date(2024, 12, 15):
        return 1_500_000.0
    return 1_000_000.0


def min_down_payment_canada(price: float, asof_date: dt.date) -> float:
    """Minimum down payment in Canada (simulation default).

    - <= $500k: 5% of price
    - $500k .. insured cap: 5% of first $500k + 10% of remainder
    - >= insured cap: 20% (and mortgage insurance is not available)

    Note: For price >= cap, 20% is a common minimum and aligns with insured-mortgage ineligibility.
    """
    try:
        p = max(0.0, float(price))
    except Exception:
        p = 0.0
    if p <= 500_000.0:
        return 0.05 * p

    cap = insured_mortgage_price_cap(asof_date)

    if p < cap:
        return 0.05 * 500_000.0 + 0.10 * (p - 500_000.0)

    return 0.20 * p


def insured_30yr_amortization_policy_stage(asof_date: dt.date) -> str:
    """Return the insured 30-year amortization eligibility regime for an as-of date.

    Stages modeled (date-aware):
      - pre_2024_08_01: insured mortgages are generally capped at 25-year amortization
      - ftb_and_new_build: 30-year insured amortization allowed only for first-time buyers
        purchasing newly built homes (effective 2024-08-01)
      - ftb_or_new_build: 30-year insured amortization expanded to all first-time buyers
        OR all buyers of newly built homes (effective 2024-12-15)

    These stages align with 2024 federal mortgage-rule changes and are intentionally
    represented as a policy schedule rather than a single cutoff so future amendments
    can be added cleanly.
    """
    d = _coerce_date(asof_date)
    if d >= dt.date(2024, 12, 15):
        return "ftb_or_new_build"
    if d >= dt.date(2024, 8, 1):
        return "ftb_and_new_build"
    return "pre_2024_08_01"


def insured_max_amortization_years(
    asof_date: dt.date,
    *,
    first_time_buyer: bool = False,
    new_construction: bool = False,
) -> int:
    """Return the maximum insured amortization (years) under the modeled schedule.

    This helper only models the *30-year* eligibility schedule for insured (high-ratio)
    mortgages; it does not assess other lender/insurer underwriting criteria.
    """
    stage = insured_30yr_amortization_policy_stage(asof_date)
    ftb = bool(first_time_buyer)
    newb = bool(new_construction)

    if stage == "ftb_or_new_build":
        return 30 if (ftb or newb) else 25
    if stage == "ftb_and_new_build":
        return 30 if (ftb and newb) else 25
    return 25


def insured_amortization_rule_label(asof_date: dt.date) -> str:
    """Human-readable summary of the insured 30-year amortization rule on a date."""
    stage = insured_30yr_amortization_policy_stage(asof_date)
    if stage == "ftb_or_new_build":
        return "30-year insured amortization allowed for first-time buyers OR new builds"
    if stage == "ftb_and_new_build":
        return "30-year insured amortization allowed only for first-time buyers purchasing new builds"
    return "25-year max insured amortization (no 30-year exception modeled yet)"


def cmhc_premium_rate_from_ltv(ltv: float, down_payment_source: str | None = None) -> float:
    """Approximate CMHC premium rate based on loan-to-value (LTV).

    Premiums are modeled as a simple percent of the base loan amount (pre-premium).

    Notes:
      - Returns 0 when no insurance is required (<=80% LTV) or when out-of-range.
      - Some insurers apply a higher premium when the down payment is **non-traditional**
        (e.g., borrowed / unsecured / certain gift structures). We model that case as:
            - LTV 90.01% .. 95.00%: 4.50% (instead of 4.00%)

    Args:
        ltv: Loan-to-value as a fraction (e.g., 0.95 for 95%).
        down_payment_source: Optional label, typically "Traditional" or "Non-traditional".

    Returns:
        Premium rate as a decimal fraction (e.g., 0.04 for 4%).
    """
    try:
        x = float(ltv)
    except Exception:
        return 0.0

    if x <= 0.80:
        return 0.0

    src = (down_payment_source or "").strip().lower()
    non_traditional = src.startswith("non") or (src in {"borrowed", "gift", "gifted", "other"})

    if x <= 0.85:
        return 0.028
    if x <= 0.90:
        return 0.031
    if x <= 0.95:
        # Non-traditional down payment: model the 4.50% tier for 90.01–95% LTV.
        if non_traditional and (x > 0.90 + 1e-12):
            return 0.045
        return 0.040

    return 0.0


def mortgage_default_insurance_sales_tax_rate(province: str, asof_date: dt.date) -> float:
    """Provincial sales tax on mortgage default insurance premiums (cash due at closing).

    CMHC notes that some provinces apply provincial sales tax to the mortgage loan insurance premium,
    and that this tax can't be added to the loan amount.

    As of 2026-02-20:
      - Ontario: 8% RST on many insurance premiums
      - Saskatchewan: 6% PST
      - Quebec: 9% tax on insurance premiums (scheduled to rise to 9.975% on premiums paid after 2026-12-31)

    Returns the applicable tax rate as a decimal (e.g., 0.08 for 8%).
    """
    prov_raw = (province or "").strip().lower()
    prov = {
        "on": "ontario",
        "sk": "saskatchewan",
        "qc": "quebec",
        "pq": "quebec",
    }.get(prov_raw, prov_raw)
    d = _coerce_date(asof_date)
    if prov == "ontario":
        return 0.08
    if prov == "saskatchewan":
        return 0.06
    if prov == "quebec":
        # Quebec's tax on insurance premiums is 9% through 2026, then aligns to 9.975% starting 2027-01-01.
        if d >= dt.date(2027, 1, 1):
            return 0.09975
        return 0.09
    return 0.0
