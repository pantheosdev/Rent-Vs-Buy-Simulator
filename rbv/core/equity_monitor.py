"""Equity monitoring utilities for detecting underwater conditions.

These helpers analyze simulation output DataFrames to detect months where
the buyer has negative equity (owes more than the home is worth). This is
important context for users — the simulator assumes the buyer keeps paying
even when underwater, which may not reflect real behavior.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def detect_negative_equity(df: pd.DataFrame) -> dict[str, Any]:
    """Analyze a simulation DataFrame for negative equity conditions.

    Looks for months where Buyer Home Equity < 0 (underwater).

    Args:
        df: Simulation output DataFrame from run_simulation_core.

    Returns:
        Dict with keys:
        - has_negative_equity: bool — True if buyer is ever underwater
        - first_underwater_month: int | None — first month with negative equity
        - max_negative_equity: float — deepest underwater amount (negative number)
        - months_underwater: int — total months with negative equity
        - underwater_at_horizon: bool — whether still underwater at end of sim
        - pct_months_underwater: float — fraction of months spent underwater
    """
    result = {
        "has_negative_equity": False,
        "first_underwater_month": None,
        "max_negative_equity": 0.0,
        "months_underwater": 0,
        "underwater_at_horizon": False,
        "pct_months_underwater": 0.0,
    }

    if df is None or df.empty:
        return result

    equity_col = None
    for col_name in ["Buyer Home Equity", "Home Equity", "Equity"]:
        if col_name in df.columns:
            equity_col = col_name
            break

    if equity_col is None:
        return result

    equity = pd.to_numeric(df[equity_col], errors="coerce")
    underwater_mask = equity < 0

    if not underwater_mask.any():
        return result

    result["has_negative_equity"] = True
    months_underwater = int(underwater_mask.sum())
    result["months_underwater"] = months_underwater
    result["pct_months_underwater"] = months_underwater / len(df)
    result["max_negative_equity"] = float(equity[underwater_mask].min())
    result["underwater_at_horizon"] = bool(underwater_mask.iloc[-1])

    first_idx = underwater_mask.idxmax()
    if "Month" in df.columns:
        result["first_underwater_month"] = int(df.loc[first_idx, "Month"])
    else:
        result["first_underwater_month"] = int(first_idx) + 1

    return result


def format_underwater_warning(analysis: dict[str, Any]) -> str | None:
    """Generate a user-friendly warning message for negative equity.

    Returns None if buyer is never underwater.
    """
    if not analysis.get("has_negative_equity"):
        return None

    months = analysis["months_underwater"]
    max_neg = abs(analysis["max_negative_equity"])
    first_month = analysis["first_underwater_month"]
    at_horizon = analysis["underwater_at_horizon"]

    msg = (
        f"⚠️ The buyer is underwater (negative equity) for {months} month(s). "
        f"First occurring at month {first_month}, with a maximum deficit of ${max_neg:,.0f}."
    )
    if at_horizon:
        msg += " The buyer is STILL underwater at the end of the simulation horizon."

    msg += (
        "\n\nNote: This simulator assumes the buyer continues making payments even when "
        "underwater. In reality, some buyers may default or sell at a loss. "
        "See docs/ASSUMPTIONS.md for known simplifications."
    )

    return msg
