"""Helpers for detecting negative-equity (underwater) conditions.

These functions analyze simulation output DataFrames to identify months
where the buyer's home equity is negative (i.e., the mortgage balance
exceeds the home value). They are designed to be called AFTER simulation,
not during.
"""
from __future__ import annotations

from typing import Any

import pandas as pd


def detect_negative_equity(df: pd.DataFrame) -> dict[str, Any]:
    """Analyze a simulation DataFrame for negative equity periods.

    Looks for the 'Buyer Home Equity' column. If equity goes negative
    at any point during the simulation, returns details about the underwater period.

    Args:
        df: The simulation output DataFrame from run_simulation_core()

    Returns:
        Dict with keys:
        - ever_underwater: bool — True if equity was negative at any point
        - underwater_months: int — number of months with negative equity
        - worst_equity: float — the lowest equity value observed
        - worst_month: int — the month when equity was lowest
        - recovered: bool — True if equity was positive by the end
        - final_equity: float — equity at the last month
    """
    result = {
        "ever_underwater": False,
        "underwater_months": 0,
        "worst_equity": 0.0,
        "worst_month": 0,
        "recovered": True,
        "final_equity": 0.0,
    }

    if "Buyer Home Equity" not in df.columns:
        return result

    equity = pd.to_numeric(df["Buyer Home Equity"], errors="coerce").fillna(0.0)

    underwater_mask = equity < 0
    result["ever_underwater"] = bool(underwater_mask.any())
    result["underwater_months"] = int(underwater_mask.sum())
    result["worst_equity"] = float(equity.min())
    result["worst_month"] = int(equity.idxmin()) + 1 if (len(equity) > 0 and bool(underwater_mask.any())) else 0
    result["final_equity"] = float(equity.iloc[-1]) if len(equity) > 0 else 0.0
    result["recovered"] = not bool(underwater_mask.iloc[-1]) if len(equity) > 0 else True

    return result


def format_underwater_warning(analysis: dict[str, Any]) -> str | None:
    """Format a user-friendly warning message if the buyer goes underwater.

    Returns None if the buyer never goes underwater.
    """
    if not analysis.get("ever_underwater", False):
        return None

    months = analysis["underwater_months"]
    worst = analysis["worst_equity"]
    worst_month = analysis["worst_month"]
    recovered = analysis["recovered"]

    msg = (
        f"⚠️ The buyer goes underwater (negative equity) for {months} month(s). "
        f"Worst point: ${worst:,.0f} at month {worst_month}."
    )

    if recovered:
        msg += " Equity recovers to positive by the end of the simulation."
    else:
        final = analysis["final_equity"]
        msg += f" Buyer remains underwater at end of simulation (equity: ${final:,.0f})."

    return msg
