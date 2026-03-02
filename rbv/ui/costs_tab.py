from __future__ import annotations

import numpy as np
import pandas as pd

from rbv.ui.costs_utils import has_finite_signal, safe_numeric_series


def build_costs_core(df: pd.DataFrame) -> dict:
    cache: dict[str, pd.Series] = {}

    def s(col: str) -> pd.Series:
        return safe_numeric_series(df, col, cache)

    b_unrec = s("Buyer Unrecoverable")
    r_unrec = s("Renter Unrecoverable")
    b_interest = s("Interest")
    b_tax = s("Property Tax")
    b_maint = s("Maintenance")
    b_repairs = s("Repairs")
    b_condo = s("Condo Fees")
    b_ins = s("Home Insurance")
    b_util = s("Utilities")
    b_special = s("Special Assessment")
    r_rent = s("Rent")
    r_ins = s("Rent Insurance")
    r_util = s("Rent Utilities")
    r_move = s("Moving")

    buyer_total_actual = float(df.iloc[-1]["Buyer Unrecoverable"]) if "Buyer Unrecoverable" in df.columns else float("nan")
    renter_total_actual = float(df.iloc[-1]["Renter Unrecoverable"]) if "Renter Unrecoverable" in df.columns else float("nan")

    buyer_rec_total = float((b_interest + b_tax + b_maint + b_repairs + b_condo + b_ins + b_util + b_special).sum())
    renter_rec_total = float((r_rent + r_ins + r_util + r_move).sum())

    if (not np.isfinite(buyer_total_actual)) or ((abs(buyer_total_actual) <= 0.01) and (buyer_rec_total > 0.01)):
        buyer_total_actual = buyer_rec_total
    if (not np.isfinite(renter_total_actual)) or ((abs(renter_total_actual) <= 0.01) and (renter_rec_total > 0.01)):
        renter_total_actual = renter_rec_total

    has_b_unrec = ("Buyer Unrecoverable" in df.columns) and has_finite_signal(b_unrec, eps=0.01)
    has_r_unrec = ("Renter Unrecoverable" in df.columns) and has_finite_signal(r_unrec, eps=0.01)

    b_step = b_unrec.diff().fillna(b_unrec)
    r_step = r_unrec.diff().fillna(r_unrec)

    return {
        "series": {
            "b_unrec": b_unrec,
            "r_unrec": r_unrec,
            "b_interest": b_interest,
            "b_tax": b_tax,
            "b_maint": b_maint,
            "b_repairs": b_repairs,
            "b_condo": b_condo,
            "b_ins": b_ins,
            "b_util": b_util,
            "b_special": b_special,
            "r_rent": r_rent,
            "r_ins": r_ins,
            "r_util": r_util,
            "r_move": r_move,
            "b_step": b_step,
            "r_step": r_step,
        },
        "totals": {
            "buyer_total_actual": buyer_total_actual,
            "renter_total_actual": renter_total_actual,
            "buyer_rec_total": buyer_rec_total,
            "renter_rec_total": renter_rec_total,
        },
        "flags": {
            "has_b_unrec": has_b_unrec,
            "has_r_unrec": has_r_unrec,
        },
        "cache": cache,
    }


def build_cost_mix_dataframe(categories: list[str], buyer_vals: list[float], renter_vals: list[float], buyer_total_actual: float, renter_total_actual: float) -> pd.DataFrame:
    rows: list[dict] = []
    buyer_share_base = abs(float(buyer_total_actual))
    renter_share_base = abs(float(renter_total_actual))
    buyer_net_ok = buyer_share_base >= 1.0
    renter_net_ok = renter_share_base >= 1.0
    buyer_mix_base = max(1e-9, float(sum(abs(v) for v in buyer_vals)))
    renter_mix_base = max(1e-9, float(sum(abs(v) for v in renter_vals)))

    for cat, b, r in zip(categories, buyer_vals, renter_vals):
        if (abs(b) > 0.01) or (abs(r) > 0.01):
            rows.append({
                "Category": cat,
                "Buyer ($)": b,
                "Buyer Net Share (%)": ((b / buyer_share_base * 100.0) if buyer_net_ok else np.nan),
                "Buyer Mix (%)": (abs(b) / buyer_mix_base * 100.0),
                "Renter ($)": r,
                "Renter Net Share (%)": ((r / renter_share_base * 100.0) if renter_net_ok else np.nan),
                "Renter Mix (%)": (abs(r) / renter_mix_base * 100.0),
            })

    return pd.DataFrame(rows).set_index("Category") if rows else pd.DataFrame()
