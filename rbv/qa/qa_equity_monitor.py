#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from rbv.core.equity_monitor import detect_negative_equity, format_underwater_warning


def main(argv: list[str] | None = None):
    # --- Case 1: all positive equity ---
    df_pos = pd.DataFrame({
        "Month": [1, 2, 3, 4],
        "Buyer Home Equity": [10000.0, 15000.0, 20000.0, 25000.0],
    })
    r = detect_negative_equity(df_pos)
    assert r["has_negative_equity"] is False
    assert r["first_underwater_month"] is None
    assert r["months_underwater"] == 0
    assert r["max_negative_equity"] == 0.0
    assert r["underwater_at_horizon"] is False
    assert r["pct_months_underwater"] == 0.0

    # --- Case 2: equity goes negative mid-simulation ---
    df_mid = pd.DataFrame({
        "Month": [1, 2, 3, 4, 5, 6],
        "Buyer Home Equity": [5000.0, 3000.0, -2000.0, -8000.0, -5000.0, 1000.0],
    })
    r = detect_negative_equity(df_mid)
    assert r["has_negative_equity"] is True
    assert r["first_underwater_month"] == 3
    assert r["months_underwater"] == 3
    assert r["max_negative_equity"] == -8000.0
    assert r["underwater_at_horizon"] is False
    assert abs(r["pct_months_underwater"] - 3 / 6) < 1e-9

    # --- Case 3: equity is negative throughout ---
    df_all_neg = pd.DataFrame({
        "Month": [1, 2, 3],
        "Buyer Home Equity": [-1000.0, -2000.0, -3000.0],
    })
    r = detect_negative_equity(df_all_neg)
    assert r["has_negative_equity"] is True
    assert r["first_underwater_month"] == 1
    assert r["months_underwater"] == 3
    assert r["max_negative_equity"] == -3000.0
    assert r["underwater_at_horizon"] is True
    assert r["pct_months_underwater"] == 1.0

    # --- Case 4: DataFrame missing equity column ---
    df_no_col = pd.DataFrame({
        "Month": [1, 2, 3],
        "Something Else": [100.0, 200.0, 300.0],
    })
    r = detect_negative_equity(df_no_col)
    assert r["has_negative_equity"] is False
    assert r["first_underwater_month"] is None

    # --- Case 5: empty DataFrame ---
    df_empty = pd.DataFrame()
    r = detect_negative_equity(df_empty)
    assert r["has_negative_equity"] is False

    # --- Case 6: None input ---
    r = detect_negative_equity(None)
    assert r["has_negative_equity"] is False

    # --- Case 7: format_underwater_warning returns None when not underwater ---
    r_pos = detect_negative_equity(df_pos)
    assert format_underwater_warning(r_pos) is None

    # --- Case 8: format_underwater_warning returns proper message when underwater ---
    r_neg = detect_negative_equity(df_all_neg)
    msg = format_underwater_warning(r_neg)
    assert msg is not None
    assert "⚠️" in msg
    assert "3 month(s)" in msg
    assert "month 1" in msg
    assert "$3,000" in msg
    assert "STILL underwater" in msg
    assert "ASSUMPTIONS.md" in msg

    print("[QA EQUITY MONITOR OK]")


if __name__ == "__main__":
    main()
