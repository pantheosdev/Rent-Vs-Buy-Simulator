from __future__ import annotations

import numpy as np
import pandas as pd


def safe_numeric_series(df: pd.DataFrame, col: str, cache: dict[str, pd.Series] | None = None) -> pd.Series:
    if cache is not None and col in cache:
        return cache[col]
    if (df is not None) and (col in df.columns):
        try:
            ser = pd.to_numeric(df[col], errors="coerce").fillna(0.0).astype(float)
        except (TypeError, ValueError):
            ser = pd.Series(np.zeros(len(df), dtype=float), index=df.index, dtype=float)
    else:
        n = len(df) if df is not None else 0
        idx = getattr(df, "index", pd.RangeIndex(n))
        ser = pd.Series(np.zeros(n, dtype=float), index=idx, dtype=float)
    if cache is not None:
        cache[col] = ser
    return ser


def safe_numeric_mean(df: pd.DataFrame, col: str, cache: dict[str, float] | None = None) -> float:
    if cache is not None and col in cache:
        return cache[col]
    if (df is not None) and (col in df.columns):
        try:
            val = float(pd.to_numeric(df[col], errors="coerce").fillna(0.0).mean())
        except (TypeError, ValueError):
            val = 0.0
    else:
        val = 0.0
    if cache is not None:
        cache[col] = val
    return val


def has_finite_signal(series: pd.Series, eps: float = 0.01) -> bool:
    try:
        arr = np.asarray(series, dtype=float)
        return bool(np.isfinite(arr).any()) and (float(np.nanmax(np.abs(arr))) > float(eps))
    except (TypeError, ValueError):
        return False


def normalize_month_like_series(df: pd.DataFrame, col: str, *, min_value: float = 1.0, outlier_mult: float = 2.0, outlier_floor: float = 24.0) -> pd.Series:
    n = len(df)
    fallback = pd.Series(np.arange(1, n + 1), index=df.index, dtype=float)
    if col not in df.columns:
        return fallback
    vals = pd.to_numeric(df[col], errors="coerce")
    vals = vals.where(vals.notna(), fallback).clip(lower=min_value)
    if float(vals.max()) > max(outlier_floor, float(n) * outlier_mult):
        return fallback
    return vals.astype(float)
