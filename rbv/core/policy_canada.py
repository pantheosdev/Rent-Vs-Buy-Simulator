"""Canada-specific policy helpers.

These are *rules-of-thumb* used for simulation defaults; lenders/insurers may apply additional criteria.
We key rules off an as-of date so changes can be audited over time.
"""

from __future__ import annotations

import datetime as dt


# Last reviewed for correctness (YYYY-MM-DD).
# Update this when modifying any thresholds in this module.
POLICY_LAST_REVIEWED = dt.date(2026, 2, 19)


def insured_mortgage_price_cap(asof_date: dt.date) -> float:
    """Return the insured-mortgage purchase price cap for the given as-of date.

    As of 2024-12-15, the federal government increased the cap from $1,000,000 to $1,500,000.
    """
    if asof_date >= dt.date(2024, 12, 15):
        return 1_500_000.0
    return 1_000_000.0


def min_down_payment_canada(price: float, asof_date: dt.date) -> float:
    """Minimum down payment in Canada (simulation default).

    - <= $500k: 5% of price
    - $500k .. insured cap: 5% of first $500k + 10% of remainder
    - >= insured cap: 20% (and mortgage insurance is not available)

    Note: For price >= cap, 20% is a common minimum and aligns with insured-mortgage ineligibility.
    """
    p = max(0.0, float(price))
    if p <= 500_000.0:
        return 0.05 * p

    cap = insured_mortgage_price_cap(asof_date)

    if p < cap:
        return 0.05 * 500_000.0 + 0.10 * (p - 500_000.0)

    return 0.20 * p


def cmhc_premium_rate_from_ltv(ltv: float) -> float:
    """Approximate CMHC premium rate based on loan-to-value (LTV).

    Returns 0 when no insurance is required (<=80% LTV) or when out-of-range.
    """
    x = float(ltv)
    if x <= 0.80:
        return 0.0
    if x <= 0.85:
        return 0.028
    if x <= 0.90:
        return 0.031
    if x <= 0.95:
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
    prov = (province or "").strip().lower()
    if prov == "ontario":
        return 0.08
    if prov == "saskatchewan":
        return 0.06
    if prov == "quebec":
        # Quebec's tax on insurance premiums is 9% through 2026, then aligns to 9.975% starting 2027-01-01.
        if asof_date >= dt.date(2027, 1, 1):
            return 0.09975
        return 0.09
    return 0.0
