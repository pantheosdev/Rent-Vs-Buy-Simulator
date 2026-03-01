"""Canadian government homebuyer programs.

Models the RRSP Home Buyers' Plan (HBP) and First Home Savings Account (FHSA)
for use in the Rent vs Buy simulation engine.

These are simulation-level approximations, not a complete tax engine. The goal
is to capture the *order-of-magnitude* financial impact on the buy vs rent
comparison. Users should consult a tax professional for their specific situation.
"""

from __future__ import annotations

import datetime as dt
import math

# ---------------------------------------------------------------------------
# RRSP Home Buyers' Plan (HBP)
# ---------------------------------------------------------------------------

#: HBP maximum withdrawal limit schedule.
#:   - Prior to 2024-04-16: $35,000 per person
#:   - 2024-04-16 onward:   $60,000 per person (2024 Federal Budget)
_HBP_LIMIT_SCHEDULE = [
    (dt.date(2024, 4, 16), 60_000.0),
    (dt.date(1992, 1, 1), 35_000.0),  # original introduction
]

#: Repayment window (years). 15-year schedule mandated by CRA.
HBP_REPAYMENT_YEARS = 15

#: Repayment grace period (years before first required repayment). The HBP
#: withdrawal year and the following year do not require a repayment; the
#: first required repayment is in the *second* year after the withdrawal year.
HBP_GRACE_YEARS = 2


def hbp_max_withdrawal(asof_date: dt.date | None = None) -> float:
    """Return the HBP maximum withdrawal per person for the given date.

    Args:
        asof_date: Date of the RRSP withdrawal. Defaults to today.

    Returns:
        Maximum HBP withdrawal in dollars.
    """
    if asof_date is None:
        asof_date = dt.date.today()
    for cutoff, limit in _HBP_LIMIT_SCHEDULE:
        if asof_date >= cutoff:
            return limit
    return 35_000.0


def hbp_annual_repayment(withdrawal: float) -> float:
    """Required annual HBP repayment (1/15th of the withdrawal amount).

    If the full annual amount is not repaid in a given year, the shortfall
    is added to the taxpayer's income for that year. This simulation models
    the *full repayment* scenario (no income inclusion penalty).

    Args:
        withdrawal: Actual HBP amount withdrawn (≤ hbp_max_withdrawal).

    Returns:
        Annual repayment amount in dollars.
    """
    try:
        w = max(0.0, float(withdrawal))
    except Exception:
        w = 0.0
    return w / float(HBP_REPAYMENT_YEARS)


def hbp_monthly_repayment(withdrawal: float) -> float:
    """Monthly equivalent of the HBP annual repayment obligation.

    The CRA requires an annual repayment, but for cash-flow simulation we
    spread this evenly across 12 months.

    Args:
        withdrawal: Actual HBP amount withdrawn.

    Returns:
        Monthly repayment amount in dollars.
    """
    return hbp_annual_repayment(withdrawal) / 12.0


def hbp_repayment_monthly_schedule(
    withdrawal: float,
    sim_months: int,
    *,
    grace_years: int = HBP_GRACE_YEARS,
) -> list[float]:
    """Build a month-by-month repayment schedule for the simulation.

    Repayment begins after `grace_years` years (months 0..grace*12-1 are 0).
    Repayments continue for `HBP_REPAYMENT_YEARS` years after the grace period.
    Months after the repayment window are 0.

    Args:
        withdrawal: Actual HBP amount withdrawn.
        sim_months: Number of simulation months (len of the returned list).
        grace_years: Grace period in years before repayment begins.

    Returns:
        List of monthly repayment amounts (length == sim_months).
    """
    try:
        w = max(0.0, float(withdrawal))
    except Exception:
        w = 0.0
    try:
        n = max(1, int(sim_months))
    except Exception:
        n = 1

    monthly = hbp_monthly_repayment(w)
    grace_months = max(0, int(grace_years)) * 12
    repay_end = grace_months + HBP_REPAYMENT_YEARS * 12

    return [
        monthly if (grace_months <= m < repay_end) else 0.0
        for m in range(n)
    ]


# ---------------------------------------------------------------------------
# First Home Savings Account (FHSA)
# ---------------------------------------------------------------------------

#: Annual contribution limit per CRA.
FHSA_ANNUAL_LIMIT = 8_000.0

#: Lifetime contribution limit per CRA.
FHSA_LIFETIME_LIMIT = 40_000.0

#: FHSA introduction date (April 1, 2023).
FHSA_START_DATE = dt.date(2023, 4, 1)


def fhsa_balance(
    annual_contribution: float,
    years_contributed: int,
    annual_return_pct: float,
    *,
    asof_date: dt.date | None = None,
) -> tuple[float, float]:
    """Estimate the FHSA balance and cumulative contributions after a saving period.

    The FHSA allows first-time home buyers to contribute up to $8,000/year
    (lifetime cap $40,000). Contributions are tax-deductible and growth is
    tax-free. Qualifying withdrawals for home purchase are also tax-free.

    This function models a simple compound-growth scenario where the same
    annual amount is contributed each year and grows at a constant rate.

    Args:
        annual_contribution: Annual contribution amount (clamped to $8,000/year).
        years_contributed: Number of years of contributions before home purchase.
        annual_return_pct: Annual return on FHSA investments (percent, e.g., 5.0).
        asof_date: As-of date; FHSA not available before 2023-04-01.

    Returns:
        (balance, cumulative_contributions) tuple in dollars.
        Returns (0.0, 0.0) if FHSA is not yet available on the given date.
    """
    d = asof_date if isinstance(asof_date, dt.date) else dt.date.today()
    if d < FHSA_START_DATE:
        return 0.0, 0.0

    try:
        contrib = max(0.0, min(float(annual_contribution), FHSA_ANNUAL_LIMIT))
    except Exception:
        contrib = 0.0
    try:
        yrs = max(0, int(years_contributed))
    except Exception:
        yrs = 0
    try:
        r = float(annual_return_pct) / 100.0
    except Exception:
        r = 0.0

    # Respect lifetime limit: effective years capped where cumulative contributions hit $40k
    max_years = math.floor(FHSA_LIFETIME_LIMIT / contrib) if contrib > 0 else 0
    effective_years = min(yrs, max_years)

    cumulative = contrib * effective_years
    cumulative = min(cumulative, FHSA_LIFETIME_LIMIT)

    # Future value of an annuity-due (contributions at start of each year)
    if effective_years == 0:
        balance = 0.0
    elif abs(r) < 1e-12:
        balance = cumulative
    else:
        # FV of annuity-immediate: contrib * ((1+r)^n - 1) / r * (1+r)
        balance = contrib * ((1.0 + r) ** effective_years - 1.0) / r * (1.0 + r)
        # Cap balance proportionally if we hit the lifetime limit mid-stream
        balance = min(balance, cumulative * (1.0 + r) ** effective_years)

    return float(balance), float(cumulative)


def fhsa_tax_savings(
    cumulative_contributions: float,
    marginal_tax_rate_pct: float,
) -> float:
    """Estimate the total income-tax savings from FHSA contributions.

    FHSA contributions are deducted from taxable income (similar to RRSP).
    This is a first-order estimate: actual savings depend on the tax year
    the deduction is claimed and marginal bracket thresholds.

    Args:
        cumulative_contributions: Total FHSA contributions made.
        marginal_tax_rate_pct: Combined federal + provincial marginal tax rate
            (percent, e.g., 40.0 for 40%).

    Returns:
        Estimated tax savings in dollars.
    """
    try:
        c = max(0.0, float(cumulative_contributions))
    except Exception:
        c = 0.0
    try:
        t = max(0.0, min(float(marginal_tax_rate_pct), 100.0)) / 100.0
    except Exception:
        t = 0.0
    return c * t
