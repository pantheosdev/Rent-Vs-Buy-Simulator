#!/usr/bin/env python3
"""QA tests for rbv.core.equity_checks — negative equity detection helpers."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pandas as pd

from rbv.core.equity_checks import detect_negative_equity, format_underwater_warning


def _make_df(equity_values: list) -> pd.DataFrame:
    return pd.DataFrame({"Buyer Home Equity": equity_values})


def main() -> None:
    print("[QA EQUITY CHECKS] Running tests...")

    # 1. All-positive equity → ever_underwater=False
    df = _make_df([100_000, 110_000, 120_000, 130_000])
    result = detect_negative_equity(df)
    assert result["ever_underwater"] is False, "Expected ever_underwater=False for all-positive equity"
    assert result["underwater_months"] == 0
    assert result["recovered"] is True
    print("  OK: all-positive equity")

    # 2. Equity dips negative then recovers → ever_underwater=True, recovered=True
    df = _make_df([50_000, -10_000, -5_000, 20_000])
    result = detect_negative_equity(df)
    assert result["ever_underwater"] is True, "Expected ever_underwater=True"
    assert result["underwater_months"] == 2
    assert result["recovered"] is True, "Expected recovered=True (ends positive)"
    assert result["worst_equity"] == -10_000
    assert result["worst_month"] == 2  # 1-indexed
    print("  OK: dips negative then recovers")

    # 3. Equity is negative at the end → recovered=False
    df = _make_df([50_000, 10_000, -5_000, -20_000])
    result = detect_negative_equity(df)
    assert result["ever_underwater"] is True
    assert result["recovered"] is False, "Expected recovered=False (ends negative)"
    assert result["final_equity"] == -20_000
    print("  OK: remains underwater at end")

    # 4. Missing equity column → graceful fallback
    df_no_col = pd.DataFrame({"Buyer Net Worth": [100_000, 200_000]})
    result = detect_negative_equity(df_no_col)
    assert result["ever_underwater"] is False
    assert result["underwater_months"] == 0
    assert result["worst_equity"] == 0.0
    assert result["worst_month"] == 0
    assert result["recovered"] is True
    assert result["final_equity"] == 0.0
    print("  OK: missing equity column → graceful fallback")

    # 5. format_underwater_warning returns None for positive equity
    positive_analysis = detect_negative_equity(_make_df([100_000, 200_000]))
    warning = format_underwater_warning(positive_analysis)
    assert warning is None, "Expected None for positive equity scenario"
    print("  OK: format_underwater_warning returns None for positive equity")

    # 6. format_underwater_warning returns non-empty string for underwater scenario
    underwater_analysis = detect_negative_equity(_make_df([50_000, -10_000, -5_000, 20_000]))
    warning = format_underwater_warning(underwater_analysis)
    assert warning is not None and len(warning) > 0, "Expected non-empty warning string"
    assert "underwater" in warning.lower() or "⚠️" in warning
    print("  OK: format_underwater_warning returns non-empty string for underwater scenario")

    # 7. format_underwater_warning mentions recovery when equity recovers
    recovered_analysis = detect_negative_equity(_make_df([50_000, -10_000, 20_000]))
    warning = format_underwater_warning(recovered_analysis)
    assert warning is not None
    assert "recovers" in warning.lower()
    print("  OK: format_underwater_warning mentions recovery")

    # 8. format_underwater_warning mentions remaining underwater when not recovered
    still_under_analysis = detect_negative_equity(_make_df([50_000, -10_000, -20_000]))
    warning = format_underwater_warning(still_under_analysis)
    assert warning is not None
    assert "remains underwater" in warning.lower()
    print("  OK: format_underwater_warning mentions remaining underwater")

    print("\n[QA EQUITY CHECKS OK] All tests passed.")


if __name__ == "__main__":
    main()
