# Auto-extracted from v167_public_baseline_hotfix4.py


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
    except Exception:
        mr_f = 0.0

    if canadian:
        # (1 + r/2)^(2/12) - 1 = mr  => (1 + r/2) = (1+mr)^6  => r = 2((1+mr)^6 - 1)
        mr_eff = max(mr_f, -0.999999)
        base = 1.0 + mr_eff
        if base <= 0.0:
            base = 1e-12
        return 100.0 * (2.0 * ((base ** 6.0) - 1.0))

    return 100.0 * (mr_f * 12.0)


# Mortgage Payment
