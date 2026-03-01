"""Validation helpers for the Rent‑vs‑Buy simulator.

This module provides simple heuristics to detect configuration values
that are outside of the legal or modeled ranges used by the core
simulation engine.  It is intended to support UI layers in issuing
friendly, actionable warnings to the user before running a
simulation.  None of the functions here raise exceptions; they
accumulate warning messages and return them as a list of strings.

Implemented checks:

* **Uninsurable LTV (>95%)** – High‑ratio mortgages in Canada are
  subject to mortgage insurance.  Loans with a loan‑to‑value above
  95 percent are not insurable.  When this condition is detected the
  helper returns a warning explaining that mortgage insurance is
  unavailable.

* **Minimum down payment** – Federal rules mandate a minimum down
  payment that depends on the purchase price and the insured mortgage
  cap.  When the down payment supplied by the user is below this
  threshold the helper warns and includes the required minimum.

* **Insured amortization limit** – Under 2024 policy changes the
  maximum insured amortization extends beyond 25 years only for
  specific buyer profiles (first‑time buyers and/or purchasers of
  newly built homes).  When the requested amortization (derived from
  ``nm`` in the config) exceeds the allowed number of years for the
  given profile a warning is emitted.  Uninsured (conventional)
  mortgages may still support longer terms, but this helper focuses
  on insured loan rules.

These checks do not enforce policy; they merely surface potential
issues so that the UI can prompt the user for correction or
confirmation.  Future extensions may add additional validations as
policies evolve (e.g. foreign buyer taxes, RRSP HBP limits).
"""

from __future__ import annotations

import datetime as _dt
import warnings as _warnings
from typing import Iterable, List, Sequence

from .policy_canada import (
    insured_mortgage_price_cap,
    min_down_payment_canada,
    insured_max_amortization_years,
)


def _coerce_date(value) -> _dt.date:
    """Coerce a user‑supplied date or None into a ``datetime.date``.

    Accepts ``datetime.date``, ISO date strings, or ``None`` and
    defaults to ``datetime.date.today()`` if parsing fails.  This
    wrapper mirrors the private ``policy_canada._coerce_date`` helper
    without importing it directly.
    """
    if isinstance(value, _dt.date):
        return value
    if value:
        try:
            # Allow passing a full ISO timestamp; slice to YYYY‑MM‑DD.
            s = str(value).strip()[:10]
            return _dt.date.fromisoformat(s)
        except Exception:
            pass
    return _dt.date.today()


def get_validation_warnings(cfg: dict) -> List[str]:
    """Return a list of human‑readable warnings for a simulation config.

    The config dictionary should contain at least the keys used by the
    simulation engine: ``price``, ``down``, ``nm`` (number of
    amortization months), and optionally ``province``, ``asof_date``,
    ``first_time_buyer`` and ``new_construction``.  Additional keys
    are ignored.

    Args:
        cfg: A dictionary of simulation parameters.  This helper does
            not mutate the input.

    Returns:
        A list of warning strings.  The list is empty when no issues
        are detected.
    """
    warnings: List[str] = []

    # Extract and normalize basic inputs.
    try:
        price = max(0.0, float(cfg.get("price", 0.0)))
    except Exception:
        price = 0.0
    try:
        down = max(0.0, float(cfg.get("down", 0.0)))
    except Exception:
        down = 0.0
    # Loan computation (pre‑insurance premium).  Negative loans clamp to zero.
    loan = max(0.0, price - down)
    ltv = (loan / price) if price > 0.0 else 0.0

    # Determine as‑of date (policy schedule anchor).
    asof_raw = cfg.get("asof_date", None)
    asof_date = _coerce_date(asof_raw)

    # Check for uninsurable LTV (>95%).  Only warn when price is below the
    # insured mortgage cap; above the cap, insurance is unavailable anyway.
    cap = insured_mortgage_price_cap(asof_date)
    if price < cap and ltv > 0.95:
        warnings.append(
            "Loan‑to‑value (LTV) exceeds 95% — mortgage insurance is unavailable for such high‑ratio loans in Canada."
        )

    # Check minimum down payment.  When the supplied down payment is below
    # the legal minimum, advise the user.  We add a small epsilon to avoid
    # floating‑point false positives.
    min_down = min_down_payment_canada(price, asof_date)
    if down + 1e-9 < min_down:
        warnings.append(
            f"Down payment of ${down:,.2f} is below the legal minimum of ${min_down:,.2f} for a ${price:,.0f} home."
        )

    # Determine requested amortization.  The engine uses ``nm`` for the
    # number of mortgage payments; by convention ``nm`` divided by 12
    # gives the amortization horizon in years.  If ``nm`` is missing or
    # invalid we treat the amortization as unknown and skip this check.
    amort_years: float | None = None
    nm_raw = cfg.get("nm")
    if nm_raw is not None:
        try:
            nm_int = int(float(nm_raw))
            if nm_int > 0:
                amort_years = nm_int / 12.0
        except Exception:
            amort_years = None

    # Flags controlling 30‑year insured eligibility.  The config may
    # store these under various names (e.g. ``first_time_buyer``,
    # ``first_time_buyer_enabled``); we coerce any truthy value.
    ftb = bool(cfg.get("first_time_buyer") or cfg.get("first_time_buyer_enabled"))
    newb = bool(cfg.get("new_construction") or cfg.get("new_build"))

    if (amort_years is not None) and (price > 0.0):
        max_insured = insured_max_amortization_years(asof_date, first_time_buyer=ftb, new_construction=newb)
        # If the loan requires insurance (LTV > 80%) and the requested
        # amortization exceeds the insured limit, issue a warning.  For
        # conventional mortgages the lender may allow longer amortizations;
        # we only warn for insured cases to avoid false positives.
        if ltv > 0.80 and amort_years > max_insured:
            warnings.append(
                f"Requested amortization of {amort_years:.1f} years exceeds the maximum insured amortization of {max_insured} years for your buyer profile."
            )

    return warnings


# ---------------------------------------------------------------------------
# Rate / value clamping helpers
# ---------------------------------------------------------------------------

def clamp_rate(value: float, name: str, *, min_val: float = -10.0, max_val: float = 50.0) -> float:
    """Clamp a percentage rate to a reasonable range, warning if adjusted."""
    if value > max_val:
        _warnings.warn(f"{name}={value:.1f}% exceeds maximum {max_val:.1f}%. Clamping to {max_val:.1f}%.")
        return max_val
    if value < min_val:
        _warnings.warn(f"{name}={value:.1f}% is below minimum {min_val:.1f}%. Clamping to {min_val:.1f}%.")
        return min_val
    return value


def clamp_positive(value: float, name: str, *, max_val: float | None = None) -> float:
    """Ensure a value is non-negative, with optional upper bound."""
    if value < 0:
        _warnings.warn(f"{name}={value} is negative. Clamping to 0.")
        return 0.0
    if max_val is not None and value > max_val:
        _warnings.warn(f"{name}={value} exceeds maximum {max_val}. Clamping to {max_val}.")
        return max_val
    return value


def validate_simulation_params(
    *,
    rate_pct: float,
    buyer_ret_pct: float,
    renter_ret_pct: float,
    apprec_pct: float,
    general_inf: float,
    rent_inf: float,
    years: int,
    price: float,
    rent: float,
    down: float,
) -> dict:
    """Validate and return clamped simulation parameters.

    Returns a dict with the validated values. Issues warnings for any adjustments.
    Does NOT raise exceptions.
    """
    return {
        "rate_pct": clamp_rate(rate_pct, "Mortgage rate", min_val=0.0, max_val=25.0),
        "buyer_ret_pct": clamp_rate(buyer_ret_pct, "Buyer investment return", min_val=-20.0, max_val=50.0),
        "renter_ret_pct": clamp_rate(renter_ret_pct, "Renter investment return", min_val=-20.0, max_val=50.0),
        "apprec_pct": clamp_rate(apprec_pct, "Home appreciation", min_val=-20.0, max_val=30.0),
        "general_inf": clamp_rate(general_inf * 100, "General inflation", min_val=-5.0, max_val=20.0) / 100,
        "rent_inf": clamp_rate(rent_inf * 100, "Rent inflation", min_val=-5.0, max_val=25.0) / 100,
        "years": max(1, min(years, 50)),
        "price": clamp_positive(price, "Home price", max_val=50_000_000.0),
        "rent": clamp_positive(rent, "Monthly rent", max_val=100_000.0),
        "down": clamp_positive(down, "Down payment", max_val=50_000_000.0),
    }
