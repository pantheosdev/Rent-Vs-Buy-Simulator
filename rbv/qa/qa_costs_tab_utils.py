#!/usr/bin/env python3
from __future__ import annotations

import numpy as np
import pandas as pd

import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from rbv.ui.costs_utils import safe_numeric_series, safe_numeric_mean, has_finite_signal, normalize_month_like_series


def main(argv=None):
    df = pd.DataFrame(
        {
            "Month": [1, 2, "bad", 4],
            "A": [1, "2", None, "x"],
            "B": [0.0, 0.0, 0.0, 0.0],
        }
    )

    scache: dict[str, pd.Series] = {}
    mcache: dict[str, float] = {}

    a = safe_numeric_series(df, "A", scache)
    assert np.allclose(a.to_numpy(), np.array([1.0, 2.0, 0.0, 0.0]))
    # cache hit path
    a2 = safe_numeric_series(df, "A", scache)
    assert a2 is a

    missing = safe_numeric_series(df, "Missing", scache)
    assert len(missing) == len(df)
    assert float(missing.sum()) == 0.0

    m = safe_numeric_mean(df, "A", mcache)
    assert abs(m - 0.75) < 1e-9
    m2 = safe_numeric_mean(df, "A", mcache)
    assert m2 == m

    assert has_finite_signal(pd.Series([0.0, 0.0, 0.02]), eps=0.01)
    assert not has_finite_signal(pd.Series([0.0, 0.0, 0.001]), eps=0.01)

    # malformed month with outlier should fallback to sequential 1..n
    df2 = pd.DataFrame({"Month": [1, 2, 999999, 4]})
    norm = normalize_month_like_series(df2, "Month")
    assert np.allclose(norm.to_numpy(), np.array([1.0, 2.0, 3.0, 4.0]))

    print("[QA COSTS UTILS OK]")


if __name__ == "__main__":
    main()
