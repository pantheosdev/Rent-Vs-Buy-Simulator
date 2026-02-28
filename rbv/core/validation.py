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
