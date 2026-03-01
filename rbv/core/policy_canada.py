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
      - Returns 0 when no insurance is required (<=80% LTV).
      - CMHC insurance is not available for LTV > 95% (minimum 5% down payment required).
        Inputs above 95% LTV are invalid; this function logs a warning and returns 0.0.
        The UI enforces the minimum down payment upstream, so this path should not be
        reachable in normal usage.
      - Some insurers apply a higher premium when the down payment is **non-traditional**
        (e.g., borrowed / unsecured / certain gift structures). We model that case as:
            - LTV 90.01% .. 95.00%: 4.50% (instead of 4.00%)

    Args:
        ltv: Loan-to-value as a fraction (e.g., 0.95 for 95%).
        down_payment_source: Optional label, typically "Traditional" or "Non-traditional".

    Returns:
        Premium rate as a decimal fraction (e.g., 0.04 for 4%).
    """
    import warnings as _warnings

    try:
        x = float(ltv)
        if x != x:  # NaN check (NaN != NaN is always True)
            return 0.0
    except Exception:
        return 0.0

    if x <= 0.80:
        return 0.0

    if x > 0.95:
        _warnings.warn(
            f"cmhc_premium_rate_from_ltv: LTV={x:.4f} exceeds 95% — CMHC insurance is not "
            "available above 95% LTV (less than 5% down payment). Returning 0.0. "
            "Ensure the minimum down payment rule is enforced upstream.",
            stacklevel=2,
        )
        return 0.0

    src = (down_payment_source or "").strip().lower()
    non_traditional = src.startswith("non") or (src in {"borrowed", "gift", "gifted", "other"})

    if x <= 0.85:
        return 0.028
    if x <= 0.90:
        return 0.031
    # LTV 90.01–95.00%: non-traditional down payment attracts the 4.50% tier.
    if non_traditional and (x > 0.90 + 1e-12):
        return 0.045
    return 0.040


def b20_stress_test_qualifying_rate(contract_rate_pct: float, *, floor_pct: float = 5.25) -> float:
    """Compute the OSFI B-20 stress test qualifying rate.

    Per OSFI Guideline B-20, the qualifying rate is the greater of:
    - The contractual mortgage rate + 2 percentage points
    - The stress test floor rate (currently 5.25%)

    Args:
        contract_rate_pct: The actual mortgage contract rate as a percentage (e.g., 4.5 for 4.5%)
        floor_pct: The stress test floor rate as a percentage (default 5.25%)

    Returns:
        The qualifying rate as a percentage (e.g., 6.5 for 6.5%)

    Reference:
        OSFI Guideline B-20, Section 3.5 (Minimum Qualifying Rate)
        https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/residential-mortgage-underwriting-practices-and-procedures
    """
    return max(contract_rate_pct + 2.0, floor_pct)


def b20_monthly_payment_at_qualifying_rate(
    principal: float, contract_rate_pct: float, amortization_months: int = 300,
    *, canadian_compounding: bool = True, floor_pct: float = 5.25
) -> tuple[float, float, float]:
    """Calculate the mortgage payment at the B-20 qualifying rate.

    Returns:
        Tuple of (qualifying_rate_pct, payment_at_qualifying_rate, payment_at_contract_rate)
    """
    from rbv.core.mortgage import _annual_nominal_pct_to_monthly_rate, _pmt

    qual_rate = b20_stress_test_qualifying_rate(contract_rate_pct, floor_pct=floor_pct)

    mr_qual = _annual_nominal_pct_to_monthly_rate(qual_rate, canadian=canadian_compounding)
    mr_contract = _annual_nominal_pct_to_monthly_rate(contract_rate_pct, canadian=canadian_compounding)

    pmt_qual = _pmt(principal, mr_qual, amortization_months)
    pmt_contract = _pmt(principal, mr_contract, amortization_months)

    return qual_rate, pmt_qual, pmt_contract


def foreign_buyer_tax_rate(province: str, asof_date: dt.date | None = None) -> float:
    """Additional property transfer tax rate for foreign/non-resident buyers.

    BC: Additional Property Transfer Tax (APTT)
      - 2016-08-02: introduced at 15%
      - 2018-02-21: raised to 20%

    Ontario: Non-Resident Speculation Tax (NRST)
      - 2017-04-21: introduced at 15%
      - 2022-03-30: raised to 20%
      - 2023-03-29: raised to 25%

    All other provinces: 0% (not modeled).

    Args:
        province: Province name (full name or two-letter code).
        asof_date: The date for which to look up the rate (defaults to today).

    Returns:
        Tax rate as a decimal fraction (e.g., 0.20 for 20%).

    Reference:
        BC: https://www2.gov.bc.ca/gov/content/taxes/property-taxes/property-transfer-tax/additional-property-transfer-tax
        ON: https://www.ontario.ca/page/non-resident-speculation-tax
    """
    d = _coerce_date(asof_date)
    prov_raw = (province or "").strip().lower()
    prov = {
        "bc": "british columbia",
        "on": "ontario",
        "ab": "alberta",
        "sk": "saskatchewan",
        "mb": "manitoba",
        "qc": "quebec",
        "ns": "nova scotia",
        "nb": "new brunswick",
        "pe": "prince edward island",
        "nl": "newfoundland and labrador",
        "nt": "northwest territories",
        "nu": "nunavut",
        "yt": "yukon",
    }.get(prov_raw, prov_raw)

    if prov == "british columbia":
        if d >= dt.date(2018, 2, 21):
            return 0.20
        if d >= dt.date(2016, 8, 2):
            return 0.15
        return 0.0

    if prov == "ontario":
        if d >= dt.date(2023, 3, 29):
            return 0.25
        if d >= dt.date(2022, 3, 30):
            return 0.20
        if d >= dt.date(2017, 4, 21):
            return 0.15
        return 0.0

    return 0.0


def foreign_buyer_tax_amount(price: float, province: str, asof_date: dt.date | None = None) -> float:
    """Compute the foreign buyer additional tax on a purchase.

    Args:
        price: Purchase price in dollars.
        province: Province name (full name or two-letter code).
        asof_date: As-of date for the applicable rate.

    Returns:
        Tax amount in dollars.
    """
    try:
        p = max(0.0, float(price))
    except Exception:
        p = 0.0
    rate = foreign_buyer_tax_rate(province, asof_date)
    return p * rate


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
