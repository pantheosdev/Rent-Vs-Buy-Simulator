#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from rbv.ui.costs_tab import build_costs_core, build_cost_mix_dataframe


def main(argv=None):
    df = pd.DataFrame(
        {
            "Month": [1, 2, 3, 4],
            "Interest": [100.0, 100.0, 100.0, 100.0],
            "Property Tax": [50.0, 50.0, 50.0, 50.0],
            "Maintenance": [10.0, 10.0, 10.0, 10.0],
            "Repairs": [5.0, 5.0, 5.0, 5.0],
            "Condo Fees": [0.0, 0.0, 0.0, 0.0],
            "Home Insurance": [20.0, 20.0, 20.0, 20.0],
            "Utilities": [30.0, 30.0, 30.0, 30.0],
            "Special Assessment": [0.0, 0.0, 0.0, 0.0],
            "Rent": [200.0, 200.0, 200.0, 200.0],
            "Rent Insurance": [15.0, 15.0, 15.0, 15.0],
            "Rent Utilities": [25.0, 25.0, 25.0, 25.0],
            "Moving": [0.0, 100.0, 0.0, 0.0],
            # Intentionally near-zero cumulative totals to trigger fallback-to-rec logic
            "Buyer Unrecoverable": [0.0, 0.0, 0.0, 0.0],
            "Renter Unrecoverable": [0.0, 0.0, 0.0, 0.0],
        }
    )

    out = build_costs_core(df)
    totals = out["totals"]
    flags = out["flags"]
    series = out["series"]

    assert totals["buyer_total_actual"] > 0.0
    assert totals["renter_total_actual"] > 0.0
    assert flags["has_b_unrec"] is False
    assert flags["has_r_unrec"] is False
    assert len(series["b_step"]) == len(df)

    categories = ["Housing", "Insurance", "Moving"]
    bvals = [500.0, -25.0, 0.0]
    rvals = [450.0, 20.0, 100.0]
    mix = build_cost_mix_dataframe(
        categories, bvals, rvals, totals["buyer_total_actual"], totals["renter_total_actual"]
    )
    assert not mix.empty
    assert "Buyer Mix (%)" in mix.columns
    assert "Renter Net Share (%)" in mix.columns

    # near-zero totals should hide net share columns via NaN
    mix2 = build_cost_mix_dataframe(categories, bvals, rvals, 0.2, 0.1)
    assert np.isnan(float(mix2.iloc[0]["Buyer Net Share (%)"]))
    assert np.isnan(float(mix2.iloc[0]["Renter Net Share (%)"]))

    print("[QA COSTS TAB CORE OK]")


if __name__ == "__main__":
    main()
