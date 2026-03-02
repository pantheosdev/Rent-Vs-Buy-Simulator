"""Canadian mortgage compounding utilities."""


def _annual_nominal_pct_to_monthly_rate(rate_pct: float, canadian: bool) -> float:
    """Convert an annual nominal rate in percent to an effective monthly rate (decimal).

    - Standard (US-style): nominal compounded monthly -> r/12
    - Canada: nominal compounded semi-annually -> (1 + r/2)^(2/12) - 1

    Guardrails:
    - Supports negative rates (hypothetical) but clamps monthly rate to > -100% to keep (1+mr) > 0.
    - For Canadian compounding, clamps the fractional-power base to a tiny positive value if needed.
    """
    try:
        r = float(rate_pct) / 100.0
        if r != r or r in (float("inf"), float("-inf")):
            r = 0.0
    except Exception:
        r = 0.0

    if canadian:
        base = 1.0 + (r / 2.0)
        if base <= 0.0:
            base = 1e-12
        mr = (base ** (2.0 / 12.0)) - 1.0
        return max(float(mr), -0.999999)

    mr = r / 12.0
    return max(float(mr), -0.999999)


def _monthly_rate_to_annual_nominal_pct(mr: float, canadian: bool) -> float:
    """Inverse of _annual_nominal_pct_to_monthly_rate: monthly effective rate -> annual nominal percent."""
    try:
        mr_f = float(mr)
        if mr_f != mr_f or mr_f in (float("inf"), float("-inf")):
            mr_f = 0.0
    except Exception:
        mr_f = 0.0

    if canadian:
        # (1 + r/2)^(2/12) - 1 = mr  => (1 + r/2) = (1+mr)^6  => r = 2((1+mr)^6 - 1)
        mr_eff = max(mr_f, -0.999999)
        base = 1.0 + mr_eff
        if base <= 0.0:
            base = 1e-12
        return float(100.0 * (2.0 * ((base**6.0) - 1.0)))

    return 100.0 * (mr_f * 12.0)


# Mortgage Payment


def _pmt(principal: float, mr: float, n: int) -> float:
    """Fixed monthly payment for a loan.

    Args:
        principal: Loan principal.
        mr: Effective monthly rate (decimal).
        n: Number of months.

    Returns:
        Monthly payment amount.
    """
    principal = float(principal)
    mr = float(mr)
    n = int(max(1, n))
    if principal <= 0:
        return 0.0
    if mr <= 0:
        return principal / float(n)
    return principal * (mr * (1.0 + mr) ** n) / ((1.0 + mr) ** n - 1.0)


# ---------------------------------------------------------------------------
# IRD Mortgage Prepayment Penalty
# ---------------------------------------------------------------------------

def ird_prepayment_penalty(
    remaining_balance: float,
    contract_rate_pct: float,
    comparison_rate_pct: float,
    remaining_term_months: int,
    *,
    canadian_compounding: bool = True,
) -> float:
    """Compute the Interest Rate Differential (IRD) prepayment penalty.

    When a borrower breaks a fixed-rate mortgage before the term ends, most
    Canadian lenders charge the *greater of*:
      - 3 months' interest on the outstanding balance at the contract rate, OR
      - The Interest Rate Differential (IRD): the present value of the interest
        cost difference between the contract rate and the lender's current
        comparison (re-offer) rate for the remaining term.

    IRD formula used here (simplified, lender-posted rate model):
        IRD = remaining_balance × (contract_rate - comparison_rate) × remaining_term_years

    This is a simplified IRD that omits lender-specific discounting adjustments.
    Actual penalties vary by lender; some use discounted rates and NPV-based IRD.
    For most simulations this approximation is sufficiently accurate.

    Args:
        remaining_balance: Outstanding principal at the time of breaking the mortgage.
        contract_rate_pct: Original (contract) annual mortgage rate as a percent (e.g., 4.5).
        comparison_rate_pct: Current lender rate for the remaining term, as a percent.
            Typically the posted rate minus the original discount. If the comparison
            rate exceeds the contract rate, the IRD is 0 (only the 3-month rule applies).
        remaining_term_months: Months left in the mortgage *term* (not amortization).
        canadian_compounding: If True, uses semi-annual compounding (Canadian Bank Act).

    Returns:
        Prepayment penalty in dollars (always ≥ 0).

    Reference:
        FCAC Mortgage Prepayment Penalties Guide:
        https://www.canada.ca/en/financial-consumer-agency/services/mortgages/mortgage-prepayment.html
    """
    try:
        bal = max(0.0, float(remaining_balance))
    except Exception:
        bal = 0.0
    try:
        c_rate = float(contract_rate_pct) / 100.0
    except Exception:
        c_rate = 0.0
    try:
        cmp_rate = float(comparison_rate_pct) / 100.0
    except Exception:
        cmp_rate = 0.0
    try:
        rem_months = max(0, int(remaining_term_months))
    except Exception:
        rem_months = 0

    if bal <= 0.0 or rem_months <= 0:
        return 0.0

    # 3-month interest penalty (always applicable baseline)
    mr_contract = _annual_nominal_pct_to_monthly_rate(float(contract_rate_pct), canadian_compounding)
    three_month_interest = bal * float(mr_contract) * 3.0

    # IRD penalty
    rate_diff = c_rate - cmp_rate
    if rate_diff <= 0.0:
        # When comparison rate >= contract rate, IRD is zero; only 3-month rule applies.
        return max(0.0, three_month_interest)

    remaining_term_years = rem_months / 12.0
    ird = bal * rate_diff * remaining_term_years

    return max(0.0, max(three_month_interest, ird))


def ird_penalty_for_simulation(
    original_principal: float,
    contract_rate_pct: float,
    monthly_payment: float,
    months_elapsed: int,
    term_months: int,
    *,
    comparison_rate_pct: float | None = None,
    rate_drop_pp: float = 1.5,
    canadian_compounding: bool = True,
) -> float:
    """Compute the IRD prepayment penalty for use in the simulation engine.

    This helper estimates:
    1. The remaining mortgage balance at `months_elapsed` using amortization math.
    2. The remaining term months.
    3. The IRD penalty.

    The comparison rate defaults to (contract_rate - rate_drop_pp), which approximates
    the scenario where rates have fallen since origination. This is the case where
    an IRD penalty typically arises (lender loses the rate spread if re-lending).

    Args:
        original_principal: Mortgage principal at origination (post-CMHC if applicable).
        contract_rate_pct: Original contract rate (percent, e.g., 4.5).
        monthly_payment: Monthly mortgage payment at origination.
        months_elapsed: Number of months elapsed since mortgage origination.
        term_months: Total mortgage term in months (e.g., 60 for a 5-year term).
        comparison_rate_pct: Lender's current comparison rate (percent). If None,
            estimated as (contract_rate_pct - rate_drop_pp).
        rate_drop_pp: Assumed rate drop in percentage points (used only when
            comparison_rate_pct is None). Default 1.5 pp.
        canadian_compounding: Semi-annual compounding if True.

    Returns:
        Prepayment penalty in dollars (0 if no term break — i.e., months_elapsed >= term_months).
    """
    try:
        bal = max(0.0, float(original_principal))
    except Exception:
        bal = 0.0
    try:
        n_elapsed = max(0, int(months_elapsed))
    except Exception:
        n_elapsed = 0
    try:
        n_term = max(0, int(term_months))
    except Exception:
        n_term = 0

    # No penalty if the term has already ended.
    if n_elapsed >= n_term or bal <= 0.0:
        return 0.0

    remaining_term_months = n_term - n_elapsed

    # Estimate remaining balance via standard amortization
    mr = _annual_nominal_pct_to_monthly_rate(float(contract_rate_pct), canadian_compounding)
    pmt = float(monthly_payment)
    remaining_balance = bal
    for _ in range(n_elapsed):
        interest = remaining_balance * mr
        principal_paid = pmt - interest
        remaining_balance = max(0.0, remaining_balance - principal_paid)

    if comparison_rate_pct is None:
        try:
            comparison_rate_pct = max(0.0, float(contract_rate_pct) - float(rate_drop_pp))
        except Exception:
            comparison_rate_pct = 0.0

    return ird_prepayment_penalty(
        remaining_balance,
        contract_rate_pct,
        comparison_rate_pct,
        remaining_term_months,
        canadian_compounding=canadian_compounding,
    )
