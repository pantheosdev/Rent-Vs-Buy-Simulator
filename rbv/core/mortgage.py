# Auto-extracted from v167_public_baseline_hotfix4.py



def _annual_nominal_pct_to_monthly_rate(rate_pct: float, canadian: bool) -> float:
    """Convert an annual nominal rate in percent to an effective monthly rate (decimal).
    - Standard (US-style): nominal compounded monthly -> r/12
    - Canada: nominal compounded semi-annually -> (1 + r/2)^(2/12) - 1
    """
    try:
        r = float(rate_pct) / 100.0
    except Exception:
        r = 0.0
    if canadian:
        return (1.0 + r / 2.0) ** (2.0 / 12.0) - 1.0
    return r / 12.0

def _monthly_rate_to_annual_nominal_pct(mr: float, canadian: bool) -> float:
    """Inverse of _annual_nominal_pct_to_monthly_rate: effective monthly rate (decimal) -> annual nominal percent."""
    try:
        mr = float(mr)
    except Exception:
        mr = 0.0
    if canadian:
        # (1 + r/2)^(2/12) - 1 = mr  => (1 + r/2) = (1+mr)^6  => r = 2((1+mr)^6 - 1)
        return 100.0 * (2.0 * ((1.0 + mr) ** 6.0 - 1.0))
    return 100.0 * (mr * 12.0)

# Mortgage Payment

