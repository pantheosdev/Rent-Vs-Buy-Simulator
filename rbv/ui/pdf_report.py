"""PDF report generation for the RBV Simulator."""

from __future__ import annotations

import datetime
import html
import io
import math
from base64 import b64encode
from typing import Any, Iterable

import numpy as np
import pandas as pd

from rbv.ui.theme import BUY_COLOR, RENT_COLOR

_PDF_CSS = """
@page { size: A4; margin: 12mm 11mm 13mm 11mm; }
* { box-sizing: border-box; }
body {
  font-family: "DejaVu Sans", "Segoe UI", Arial, sans-serif;
  font-size: 9pt;
  color: #172236;
  margin: 0;
  background: #ffffff;
  orphans: 3;
  widows: 3;
}
.report-header {
  border: 1px solid #d8e0ef;
  border-top: 4px solid __BUY_COLOR__;
  border-radius: 10px;
  padding: 10px 12px 8px 12px;
  background: #ffffff;
  margin-bottom: 10px;
}
.report-title { font-size: 20pt; font-weight: 700; color: #0f1728; margin: 0 0 3px 0; }
.report-subtitle { font-size: 10pt; color: #53627d; margin: 0; }
.report-date { font-size: 8pt; color: #8694ab; text-align: right; margin-top: -22px; }
.disclaimer {
  font-size: 7.4pt;
  color: #6e7d94;
  margin: 0 0 10px 0;
  padding-left: 8px;
  border-left: 2px solid #dfe6f1;
}
.verdict-box {
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 10px;
  font-size: 10pt;
  font-weight: 600;
}
.verdict-buy { background: #ebf8ef; border-left: 4px solid #1f8a43; color: #1d5f33; }
.verdict-rent { background: #fff5ea; border-left: 4px solid #d08718; color: #7e4d10; }
.verdict-neutral { background: #eef5ff; border-left: 4px solid #2c6db3; color: #173f77; }
.section { margin: 0 0 10px 0; }
.section.page-break {
  break-before: page;
  page-break-before: always;
  margin-top: 0;
}
h2 {
  margin: 0 0 5px 0;
  padding-bottom: 3px;
  border-bottom: 2px solid #e2e8f4;
  font-size: 11pt;
  font-weight: 700;
  color: #0f1728;
  page-break-after: avoid;
}
.small-note {
  margin: 0 0 6px 0;
  color: #64748b;
  font-size: 7.4pt;
}
.note-inline {
  color: #64748b;
  font-size: 7.6pt;
  margin-top: 4px;
}
.layout-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 6px 6px;
  margin: 0 0 6px 0;
}
.layout-table td {
  padding: 0;
  border: none;
  background: transparent;
  vertical-align: top;
}
.cols-2 td { width: 50%; }
.cols-3 td { width: 33.333%; }
.cols-4 td { width: 25%; }
.card {
  border: 1px solid #d8e0ef;
  border-radius: 8px;
  background: #ffffff;
  padding: 8px 9px;
  break-inside: avoid;
  page-break-inside: avoid;
}
.card.soft { background: #f8fbff; }
.card.compact { padding: 7px 8px; }
.card-title {
  font-size: 8.2pt;
  font-weight: 700;
  color: #0f1728;
  margin: 0 0 4px 0;
}
.card-subtitle {
  font-size: 7.2pt;
  color: #64748b;
  margin: 0 0 6px 0;
}
.metric-label {
  font-size: 7pt;
  color: #5f6f86;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 2px;
}
.metric-value { font-size: 11.5pt; font-weight: 700; color: #0f1728; }
.metric-value.buy { color: __BUY_COLOR__; }
.metric-value.rent { color: __RENT_COLOR__; }
.metric-value.neutral { color: #1d4f91; }
.metric-foot {
  margin-top: 3px;
  font-size: 7.4pt;
  color: #64748b;
}
.list-note {
  margin: 0;
  padding-left: 15px;
  color: #31425b;
  font-size: 7.8pt;
}
.list-note li { margin-bottom: 2px; }
.kv-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 7.8pt;
  margin: 0;
}
.kv-table td {
  border: none;
  border-bottom: 1px solid #edf2f8;
  padding: 3px 0;
  vertical-align: top;
}
.kv-table tr:last-child td { border-bottom: none; }
.kv-key { color: #53627d; width: 62%; padding-right: 8px; }
.kv-val { color: #16243a; font-weight: 600; text-align: right; }
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 8pt;
  margin: 2px 0 0 0;
  break-inside: avoid;
  page-break-inside: avoid;
}
.data-table th {
  background: #eef3fb;
  color: #203047;
  text-align: left;
  padding: 5px 6px;
  border-bottom: 1px solid #dce6f3;
  font-weight: 700;
}
.data-table th.buy { background: __BUY_COLOR__; color: #072330; }
.data-table th.rent { background: __RENT_COLOR__; color: #2a153d; }
.data-table td {
  padding: 4px 6px;
  border-bottom: 1px solid #edf2f8;
  vertical-align: top;
}
.data-table tr:nth-child(even) td { background: #f9fbfe; }
.data-table tr:last-child td { border-bottom: none; }
.chart-img {
  width: 100%;
  max-height: 215px;
  display: block;
}
.milestone-year {
  font-size: 8.6pt;
  font-weight: 700;
  color: #0f1728;
  margin-bottom: 6px;
}
.milestone-gap {
  font-size: 11pt;
  font-weight: 700;
  margin-bottom: 2px;
}
.milestone-dir {
  font-size: 7.4pt;
  color: #64748b;
  margin-bottom: 6px;
}
.read-strip {
  border: 1px solid #dce6f3;
  border-radius: 8px;
  background: #fbfdff;
  padding: 7px 9px;
  margin-bottom: 10px;
}
.read-strip ul {
  margin: 0;
  padding-left: 15px;
  font-size: 7.7pt;
  color: #31425b;
}
.read-strip li { margin-bottom: 2px; }
.appendix-card .kv-key { width: 58%; }
.footer {
  margin-top: 8px;
  font-size: 7pt;
  color: #93a0b6;
  text-align: center;
}
""".replace("__BUY_COLOR__", BUY_COLOR).replace("__RENT_COLOR__", RENT_COLOR)


# ---------- numeric helpers ----------

def _is_finite_number(val: Any) -> bool:
    try:
        return math.isfinite(float(val))
    except (TypeError, ValueError):
        return False


def _clean_number(val: Any) -> float | None:
    try:
        num = float(val)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(num):
        return None
    if abs(num) < 5e-7:
        return 0.0
    return num


def _fmt_currency(val: Any, decimals: int = 0) -> str:
    num = _clean_number(val)
    if num is None:
        return "—"
    if decimals > 0:
        return f"${num:,.{decimals}f}"
    return f"${num:,.0f}"


def _fmt_currency_abs(val: Any, decimals: int = 0) -> str:
    num = _clean_number(val)
    if num is None:
        return "—"
    return _fmt_currency(abs(num), decimals=decimals)


def _fmt_pct(val: Any, decimals: int = 1) -> str:
    num = _clean_number(val)
    if num is None:
        return "—"
    return f"{num:.{decimals}f}%"


def _fmt_input_pct(val: Any, decimals: int = 2) -> str:
    num = _clean_number(val)
    if num is None:
        return "—"
    if abs(num) < 1.0:
        num *= 100.0
    return f"{num:.{decimals}f}%"


def _fmt_money_short(val: Any) -> str:
    num = _clean_number(val)
    if num is None:
        return "—"
    a = abs(num)
    sign = "-" if num < 0 else ""
    if a >= 1_000_000:
        return f"{sign}${a / 1_000_000:.2f}M"
    if a >= 10_000:
        return f"{sign}${a / 1_000:.0f}K"
    return f"{sign}${a:,.0f}"


def _safe_last(df: pd.DataFrame, candidates: list[str], default: float = 0.0) -> float:
    for col in candidates:
        if col in df.columns:
            series = pd.to_numeric(df[col], errors="coerce").dropna()
            if not series.empty:
                return float(series.iloc[-1])
    return default


def _pick_series(df: pd.DataFrame, candidates: list[str]) -> pd.Series:
    for col in candidates:
        if col in df.columns:
            return pd.to_numeric(df[col], errors="coerce")
    return pd.Series(np.nan, index=df.index, dtype="float64")


def _time_axis_years(df: pd.DataFrame) -> pd.Series:
    if "Year" in df.columns:
        return pd.to_numeric(df["Year"], errors="coerce")
    if "Month" in df.columns:
        return pd.to_numeric(df["Month"], errors="coerce") / 12.0
    return pd.Series(np.arange(1, len(df) + 1), index=df.index, dtype="float64")


def _series_has_signal(series: pd.Series, *, tol: float = 1.0) -> bool:
    arr = pd.to_numeric(series, errors="coerce").to_numpy(dtype="float64", na_value=np.nan)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return False
    return bool(np.nanmax(np.abs(arr)) > tol)


def _dominant_label(items: list[tuple[str, float]]) -> str:
    valid = [(label, val) for label, val in items if _clean_number(val) not in (None, 0.0)]
    if not valid:
        return "—"
    return max(valid, key=lambda x: float(x[1]))[0]


def _milestone_years(horizon: int, target: int = 12) -> list[int]:
    horizon = max(1, int(horizon))
    target = max(1, int(target))
    if horizon <= target:
        return list(range(1, horizon + 1))
    years = {1, horizon}
    anchors = [2, 3, 5, 7, 10, 12, 15, 18, 20, 25, 30]
    for y in anchors:
        if 1 < y < horizon:
            years.add(y)
    if len(years) < target:
        raw = np.linspace(1, horizon, num=target)
        for y in raw:
            years.add(int(round(float(y))))
    years = {min(horizon, max(1, int(y))) for y in years}
    ordered = sorted(years)
    if len(ordered) > target:
        raw = np.linspace(1, horizon, num=target)
        chosen: list[int] = []
        for y in raw:
            nearest = min(ordered, key=lambda cand: (abs(cand - y), cand))
            if nearest not in chosen:
                chosen.append(nearest)
        for y in ordered:
            if len(chosen) >= target:
                break
            if y not in chosen:
                chosen.append(y)
        ordered = sorted(chosen)
    return ordered


def _first_year_gap_nonnegative(gap_series: pd.Series, years_series: pd.Series) -> str:
    try:
        for idx, val in gap_series.items():
            num = _clean_number(val)
            if num is None:
                continue
            if num >= 0:
                year_val = _clean_number(years_series.loc[idx])
                if year_val is None:
                    break
                return f"Year {int(round(year_val))}"
    except Exception:
        pass
    return "Not reached"


def _after_tax_breakeven_text(liq_delta: float | None, years: int) -> str:
    num = _clean_number(liq_delta)
    if num is None:
        return "Unavailable"
    if num < 0:
        return f"Not reached in {years} years"
    if num == 0:
        return "At parity by horizon"
    return "Reached by horizon"


def _home_equity_outlook(equity_series: pd.Series, years_series: pd.Series) -> list[tuple[str, str]]:
    clean = pd.to_numeric(equity_series, errors="coerce")
    finite = clean[np.isfinite(clean)]
    if finite.empty:
        return [("Home equity at horizon", "—"), ("Peak home equity", "—"), ("First positive-equity year", "Not observed")]
    first_positive = "Not observed"
    try:
        for idx, val in clean.items():
            if _clean_number(val) is not None and float(val) > 0:
                y = _clean_number(years_series.loc[idx])
                if y is not None:
                    first_positive = f"Year {int(round(y))}"
                break
    except Exception:
        pass
    return [
        ("Home equity at horizon", _fmt_currency(finite.iloc[-1])),
        ("Peak home equity", _fmt_currency(np.nanmax(finite.to_numpy(dtype="float64")))),
        ("First positive-equity year", first_positive),
    ]


# ---------- chart helpers ----------

def _try_get_plt() -> Any | None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        return plt
    except Exception:
        return None


def _style_axes(ax: Any) -> None:
    ax.set_facecolor("white")
    ax.grid(axis="y", color="#d9e3f0", linewidth=0.8, alpha=0.9)
    ax.grid(axis="x", color="#eef3f9", linewidth=0.5, alpha=0.7)
    ax.tick_params(labelsize=7.5, colors="#41516b")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color("#d7e0ee")
    ax.spines["bottom"].set_color("#d7e0ee")
    ax.set_xlabel("Years", fontsize=7.5, color="#53627d")


def _apply_money_axis(ax: Any, series_list: Iterable[pd.Series]) -> None:
    try:
        from matplotlib.ticker import FuncFormatter
    except Exception:
        return
    max_abs = 0.0
    for series in series_list:
        arr = pd.to_numeric(series, errors="coerce").to_numpy(dtype="float64", na_value=np.nan)
        arr = arr[np.isfinite(arr)]
        if arr.size:
            max_abs = max(max_abs, float(np.nanmax(np.abs(arr))))
    if max_abs >= 1_000_000:
        scale, suffix, decimals = 1_000_000.0, "M", 1
    elif max_abs >= 10_000:
        scale, suffix, decimals = 1_000.0, "K", 0
    else:
        scale, suffix, decimals = 1.0, "", 0

    def _fmt(x: float, _pos: Any = None) -> str:
        sign = "-" if x < 0 else ""
        val = abs(float(x)) / scale
        return f"{sign}${val:.{decimals}f}{suffix}" if suffix else f"{sign}${val:.0f}"

    ax.ticklabel_format(style="plain", axis="y", useOffset=False)
    ax.yaxis.set_major_formatter(FuncFormatter(_fmt))
    ax.yaxis.get_offset_text().set_visible(False)


def _fig_to_uri(fig: Any, plt_mod: Any) -> str:
    try:
        buf_svg = io.BytesIO()
        fig.savefig(buf_svg, format="svg", bbox_inches="tight", pad_inches=0.02, facecolor="white")
        return f"data:image/svg+xml;base64,{b64encode(buf_svg.getvalue()).decode('utf-8')}"
    except Exception:
        buf_png = io.BytesIO()
        fig.savefig(buf_png, format="png", dpi=220, bbox_inches="tight", pad_inches=0.03, facecolor="white")
        return f"data:image/png;base64,{b64encode(buf_png.getvalue()).decode('utf-8')}"
    finally:
        plt_mod.close(fig)


def _line_chart(df: pd.DataFrame, s1: pd.Series, s2: pd.Series, l1: str, l2: str) -> str:
    plt = _try_get_plt()
    if plt is None:
        return ""
    try:
        x = _time_axis_years(df)
        fig, ax = plt.subplots(figsize=(5.1, 2.35), facecolor="white")
        ax.plot(x, s1, color=BUY_COLOR, linewidth=2.0, label=l1)
        ax.plot(x, s2, color=RENT_COLOR, linewidth=2.0, label=l2)
        _style_axes(ax)
        _apply_money_axis(ax, [s1, s2])
        ax.legend(loc="upper left", fontsize=7, frameon=False, ncol=2)
        return _fig_to_uri(fig, plt)
    except Exception:
        return ""


def _single_line_chart(df: pd.DataFrame, s1: pd.Series, l1: str, *, color: str = BUY_COLOR) -> str:
    plt = _try_get_plt()
    if plt is None:
        return ""
    try:
        x = _time_axis_years(df)
        fig, ax = plt.subplots(figsize=(5.1, 2.35), facecolor="white")
        ax.plot(x, s1, color=color, linewidth=2.0, label=l1)
        ax.axhline(0.0, color="#94a3b8", linewidth=0.9, linestyle="--", alpha=0.8)
        _style_axes(ax)
        _apply_money_axis(ax, [s1])
        ax.legend(loc="upper left", fontsize=7, frameon=False)
        return _fig_to_uri(fig, plt)
    except Exception:
        return ""


def _band_chart(df: pd.DataFrame, med: pd.Series, low: pd.Series, high: pd.Series, label: str, color: str) -> str:
    plt = _try_get_plt()
    if plt is None:
        return ""
    try:
        x = _time_axis_years(df)
        low_arr = pd.to_numeric(low, errors="coerce").to_numpy(dtype="float64", na_value=np.nan)
        high_arr = pd.to_numeric(high, errors="coerce").to_numpy(dtype="float64", na_value=np.nan)
        med_arr = pd.to_numeric(med, errors="coerce").to_numpy(dtype="float64", na_value=np.nan)
        fig, ax = plt.subplots(figsize=(5.1, 2.35), facecolor="white")
        ax.fill_between(x, low_arr, high_arr, color=color, alpha=0.18, linewidth=0.0, label=f"{label} 5–95%")
        ax.plot(x, med_arr, color=color, linewidth=2.0, label=f"{label} median")
        _style_axes(ax)
        _apply_money_axis(ax, [med, low, high])
        ax.legend(loc="upper left", fontsize=7, frameon=False)
        return _fig_to_uri(fig, plt)
    except Exception:
        return ""


# ---------- HTML helpers ----------

def _render_section(title: str, body_html: str, *, page_break: bool = False) -> str:
    cls = "section page-break" if page_break else "section"
    return f"<div class='{cls}'><h2>{html.escape(title)}</h2>{body_html}</div>"


def _metric_card(label: str, value: str, *, tone: str = "neutral", foot: str | None = None) -> str:
    foot_html = f"<div class='metric-foot'>{html.escape(foot)}</div>" if foot else ""
    return (
        "<div class='card compact'>"
        f"<div class='metric-label'>{html.escape(label)}</div>"
        f"<div class='metric-value {html.escape(tone)}'>{html.escape(value)}</div>"
        f"{foot_html}"
        "</div>"
    )


def _kv_card(title: str, rows: list[tuple[str, str]], *, soft: bool = False, extra_note: str | None = None, appendix: bool = False) -> str:
    cls = "card soft appendix-card" if soft and appendix else "card appendix-card" if appendix else "card soft" if soft else "card"
    rows_html = "".join(
        f"<tr><td class='kv-key'>{html.escape(str(k))}</td><td class='kv-val'>{html.escape(str(v))}</td></tr>"
        for k, v in rows
    )
    note_html = f"<div class='note-inline'>{html.escape(extra_note)}</div>" if extra_note else ""
    return f"<div class='{cls}'><div class='card-title'>{html.escape(title)}</div><table class='kv-table'>{rows_html}</table>{note_html}</div>"


def _list_card(title: str, items: list[str], *, soft: bool = True) -> str:
    cls = "card soft" if soft else "card"
    lis = "".join(f"<li>{html.escape(item)}</li>" for item in items)
    return f"<div class='{cls}'><div class='card-title'>{html.escape(title)}</div><ul class='list-note'>{lis}</ul></div>"


def _layout_table(cells: list[str], cols: int) -> str:
    if cols not in (2, 3, 4):
        cols = 2
    rows: list[str] = []
    for i in range(0, len(cells), cols):
        row_cells = cells[i:i + cols]
        if len(row_cells) < cols:
            row_cells = row_cells + ["&nbsp;"] * (cols - len(row_cells))
        rows.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in row_cells) + "</tr>")
    return f"<table class='layout-table cols-{cols}'>{''.join(rows)}</table>"


def _data_table(headers: list[tuple[str, str]], rows: list[list[str]]) -> str:
    head_html = "".join(f"<th class='{html.escape(cls)}'>{html.escape(label)}</th>" for label, cls in headers)
    body_parts: list[str] = []
    for row in rows:
        body_parts.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>")
    return f"<table class='data-table'><thead><tr>{head_html}</tr></thead><tbody>{''.join(body_parts)}</tbody></table>"


def _img_card(title: str, subtitle: str, data_uri: str) -> str:
    if not data_uri:
        return _kv_card(title, [("Status", "Chart unavailable in this runtime")], soft=True)
    return (
        "<div class='card'>"
        f"<div class='card-title'>{html.escape(title)}</div>"
        f"<div class='card-subtitle'>{html.escape(subtitle)}</div>"
        f"<img class='chart-img' src='{data_uri}' alt='{html.escape(title)}' />"
        "</div>"
    )


def _milestone_card(year: int, buyer_nw: float, renter_nw: float, equity: float, buyer_costs: float, renter_costs: float) -> str:
    adv = buyer_nw - renter_nw
    tone = "buy" if adv > 0 else "rent" if adv < 0 else "neutral"
    direction = "Buying ahead" if adv > 0 else "Renting ahead" if adv < 0 else "Near tie"
    rows = [
        ("Buyer NW", _fmt_currency(buyer_nw)),
        ("Renter NW", _fmt_currency(renter_nw)),
        ("Home equity", _fmt_currency(equity)),
        ("Buyer costs", _fmt_currency(buyer_costs)),
        ("Renter costs", _fmt_currency(renter_costs)),
    ]
    rows_html = "".join(
        f"<tr><td class='kv-key'>{html.escape(k)}</td><td class='kv-val'>{html.escape(v)}</td></tr>"
        for k, v in rows
    )
    return (
        "<div class='card compact'>"
        f"<div class='milestone-year'>Year {year}</div>"
        f"<div class='milestone-gap metric-value {tone}'>{html.escape(_fmt_currency_abs(adv))}</div>"
        f"<div class='milestone-dir'>{html.escape(direction)}</div>"
        f"<table class='kv-table'>{rows_html}</table>"
        "</div>"
    )


def _compact_input_rows(cfg: dict[str, Any]) -> list[tuple[str, str]]:
    fields = [
        (("price",), "Home price", "money"),
        (("down",), "Down payment", "money"),
        (("rate",), "Mortgage rate", "pct"),
        (("amort",), "Amortization", "years"),
        (("rent",), "Monthly rent", "money"),
        (("years",), "Horizon", "years"),
        (("province",), "Province", "text"),
        (("sell_cost_pct", "selling_cost_pct", "sell_cost"), "Selling costs", "pct"),
        (("p_tax_rate_pct", "property_tax_rate_annual", "p_tax_rate"), "Property tax", "pct"),
        (("maint_rate_pct", "maintenance_rate_annual", "maint_rate"), "Maintenance", "pct"),
        (("repair_rate_pct", "repair_rate_annual", "repair_rate"), "Repairs", "pct"),
        (("condo", "condo_fees", "condo_fee_monthly"), "Condo fees", "money"),
        (("h_ins", "home_ins", "home_insurance_monthly"), "Home insurance", "money"),
        (("r_ins", "renter_ins", "rent_insurance_monthly"), "Renter insurance", "money"),
        (("rent_inf", "rent_inflation_rate_annual"), "Rent inflation", "pct"),
        (("general_inf", "general_inflation_rate_annual"), "General inflation", "pct"),
        (("moving_cost",), "Moving cost / move", "money"),
        (("moving_freq",), "Moving frequency", "years"),
        (("o_util", "owner_utilities_monthly"), "Owner utilities", "money"),
        (("r_util", "renter_utilities_monthly"), "Renter utilities", "money"),
    ]
    rows: list[tuple[str, str]] = []
    for keys, label, kind in fields:
        key = next((k for k in keys if k in cfg and cfg.get(k) is not None), None)
        if key is None:
            continue
        val = cfg.get(key)
        try:
            if kind == "money":
                if abs(float(val)) < 1e-6:
                    continue
                disp = _fmt_currency(float(val))
            elif kind == "pct":
                disp = _fmt_input_pct(float(val))
            elif kind == "years":
                yrs = int(float(val))
                disp = f"{yrs} years"
            else:
                disp = html.escape(str(val))
        except Exception:
            disp = html.escape(str(val)) if kind == "text" else "—"
        rows.append((label, disp))
    return rows


def _cost_breakdown_rows(df: pd.DataFrame, buyer_total: float, renter_total: float) -> tuple[list[tuple[str, float]], list[tuple[str, float]]]:
    buyer_components = [
        ("Mortgage interest", float(pd.to_numeric(df.get("Interest", pd.Series(dtype=float)), errors="coerce").fillna(0.0).sum())),
        ("Property tax", float(pd.to_numeric(df.get("Property Tax", pd.Series(dtype=float)), errors="coerce").fillna(0.0).sum())),
        ("Maintenance", float(pd.to_numeric(df.get("Maintenance", pd.Series(dtype=float)), errors="coerce").fillna(0.0).sum())),
        ("Repairs", float(pd.to_numeric(df.get("Repairs", pd.Series(dtype=float)), errors="coerce").fillna(0.0).sum())),
        ("Special assessments", float(pd.to_numeric(df.get("Special Assessment", pd.Series(dtype=float)), errors="coerce").fillna(0.0).sum())),
        ("Condo fees", float(pd.to_numeric(df.get("Condo Fees", pd.Series(dtype=float)), errors="coerce").fillna(0.0).sum())),
        ("Home insurance", float(pd.to_numeric(df.get("Home Insurance", pd.Series(dtype=float)), errors="coerce").fillna(0.0).sum())),
        ("Owner utilities", float(pd.to_numeric(df.get("Utilities", pd.Series(dtype=float)), errors="coerce").fillna(0.0).sum())),
        ("Moving", float(pd.to_numeric(df.get("Moving", pd.Series(dtype=float)), errors="coerce").fillna(0.0).sum())),
    ]
    renter_components = [
        ("Rent", float(pd.to_numeric(df.get("Rent", pd.Series(dtype=float)), errors="coerce").fillna(0.0).sum())),
        ("Rent insurance", float(pd.to_numeric(df.get("Rent Insurance", pd.Series(dtype=float)), errors="coerce").fillna(0.0).sum())),
        ("Rent utilities", float(pd.to_numeric(df.get("Rent Utilities", pd.Series(dtype=float)), errors="coerce").fillna(0.0).sum())),
        ("Moving", float(pd.to_numeric(df.get("Moving", pd.Series(dtype=float)), errors="coerce").fillna(0.0).sum())),
    ]
    buyer_components = [(k, v) for k, v in buyer_components if v > 0.5]
    renter_components = [(k, v) for k, v in renter_components if v > 0.5]
    buyer_known = sum(v for _, v in buyer_components)
    renter_known = sum(v for _, v in renter_components)
    buyer_implied = max(0.0, float(buyer_total) - buyer_known)
    renter_implied = max(0.0, float(renter_total) - renter_known)
    if buyer_implied > 1.0:
        buyer_components.append(("Closing & selling (implied)", buyer_implied))
    if renter_implied > 1.0:
        renter_components.append(("Other / implied", renter_implied))
    buyer_components.sort(key=lambda x: x[1], reverse=True)
    renter_components.sort(key=lambda x: x[1], reverse=True)
    return buyer_components, renter_components


# ---------- report builder ----------

def build_pdf_report(
    df: pd.DataFrame,
    cfg: dict[str, Any],
    *,
    buyer_ret_pct: float = 7.0,
    renter_ret_pct: float = 7.0,
    apprec_pct: float = 3.0,
    close_cash: float | None = None,
    monthly_pmt: float | None = None,
    win_pct: float | None = None,
    scenario_name: str = "Custom Scenario",
    bias_result: dict[str, Any] | None = None,
    report_context: dict[str, Any] | None = None,
) -> bytes:
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise RuntimeError("PDF export requires a non-empty simulation dataframe.")

    try:
        from weasyprint import CSS, HTML
    except Exception as exc:
        raise RuntimeError("weasyprint is required for PDF export. Install it with: pip install weasyprint") from exc

    price = float(cfg.get("price", 0.0) or 0.0)
    down = float(cfg.get("down", 0.0) or 0.0)
    years = int(float(cfg.get("years", 25) or 25))
    province = html.escape(str(cfg.get("province", "—")))
    now = datetime.date.today().strftime("%B %d, %Y")

    # terminal metrics
    buyer_nw = _safe_last(df, ["Buyer Net Worth", "Buyer NW", "buyer_nw"])
    renter_nw = _safe_last(df, ["Renter Net Worth", "Renter NW", "renter_nw"])
    buyer_equity = _safe_last(df, ["Buyer Home Equity", "Home Equity", "Equity"])
    buyer_unrec = _safe_last(df, ["Buyer Unrecoverable"])
    renter_unrec = _safe_last(df, ["Renter Unrecoverable"])
    buyer_liq = _clean_number(_safe_last(df, ["Buyer Liquidation NW"], default=float("nan")))
    renter_liq = _clean_number(_safe_last(df, ["Renter Liquidation NW"], default=float("nan")))
    delta = buyer_nw - renter_nw
    delta_abs = abs(delta)
    liq_delta = None if buyer_liq is None or renter_liq is None else buyer_liq - renter_liq

    if delta > 5_000:
        verdict_cls = "verdict-buy"
        verdict_text = f"Buying appears advantageous by {_fmt_currency_abs(delta)} at the {years}-year horizon."
        leader_before_label = "Buying ahead (before tax)"
        leader_tone = "buy"
    elif delta < -5_000:
        verdict_cls = "verdict-rent"
        verdict_text = f"Renting appears advantageous by {_fmt_currency_abs(delta)} at the {years}-year horizon."
        leader_before_label = "Renting ahead (before tax)"
        leader_tone = "rent"
    else:
        verdict_cls = "verdict-neutral"
        verdict_text = f"Outcomes are approximately equal at the {years}-year horizon (Δ = {_fmt_currency_abs(delta)})."
        leader_before_label = "Near tie (before tax)"
        leader_tone = "neutral"

    if liq_delta is None:
        leader_after_label = "After-tax cash-out view"
        leader_after_value = "Unavailable"
        leader_after_tone = "neutral"
    elif liq_delta > 5_000:
        leader_after_label = "Buying ahead after tax"
        leader_after_value = _fmt_currency_abs(liq_delta)
        leader_after_tone = "buy"
    elif liq_delta < -5_000:
        leader_after_label = "Renting ahead after tax"
        leader_after_value = _fmt_currency_abs(liq_delta)
        leader_after_tone = "rent"
    else:
        leader_after_label = "After-tax near tie"
        leader_after_value = _fmt_currency_abs(liq_delta)
        leader_after_tone = "neutral"

    # time series / charts
    years_series = _time_axis_years(df)
    buyer_nw_series = _pick_series(df, ["Buyer Net Worth", "Buyer NW", "buyer_nw"])
    renter_nw_series = _pick_series(df, ["Renter Net Worth", "Renter NW", "renter_nw"])
    buyer_unrec_series = _pick_series(df, ["Buyer Unrecoverable"])
    renter_unrec_series = _pick_series(df, ["Renter Unrecoverable"])
    gap_series = buyer_nw_series - renter_nw_series
    gap_mag_series = gap_series.abs()
    equity_series = _pick_series(df, ["Buyer Home Equity", "Home Equity", "Equity"])

    buyer_nw_low = _pick_series(df, ["Buyer NW Low"])
    buyer_nw_high = _pick_series(df, ["Buyer NW High"])
    renter_nw_low = _pick_series(df, ["Renter NW Low"])
    renter_nw_high = _pick_series(df, ["Renter NW High"])
    has_mc_bands = all(_series_has_signal(s, tol=0.01) for s in [buyer_nw_low, buyer_nw_high, renter_nw_low, renter_nw_high])

    nw_chart = _line_chart(df, buyer_nw_series, renter_nw_series, "Buyer NW", "Renter NW")
    gap_chart = _single_line_chart(df, gap_mag_series, "Gap magnitude", color=BUY_COLOR if delta >= 0 else RENT_COLOR)
    unrec_chart = _line_chart(df, buyer_unrec_series, renter_unrec_series, "Buyer costs", "Renter costs")
    equity_chart = _single_line_chart(df, equity_series, "Home equity", color=BUY_COLOR)
    buyer_band_chart = _band_chart(df, buyer_nw_series, buyer_nw_low, buyer_nw_high, "Buyer", BUY_COLOR) if has_mc_bands else ""
    renter_band_chart = _band_chart(df, renter_nw_series, renter_nw_low, renter_nw_high, "Renter", RENT_COLOR) if has_mc_bands else ""

    # break-even / confidence
    break_even_before = _first_year_gap_nonnegative(gap_series, years_series)
    if break_even_before == "Not reached":
        break_even_before = f"Not reached in {years} years"
    break_even_after = _after_tax_breakeven_text(liq_delta, years)
    confidence_label = "High" if delta_abs >= 50_000 else "Medium" if delta_abs >= 15_000 else "Low"

    # milestone cards / table
    milestone_years = _milestone_years(years, target=12)
    milestones: list[dict[str, float | int]] = []
    for y in milestone_years:
        subset = df[years_series <= y]
        if subset.empty:
            continue
        milestones.append(
            {
                "year": y,
                "buyer_nw": _safe_last(subset, ["Buyer Net Worth", "Buyer NW"]),
                "renter_nw": _safe_last(subset, ["Renter Net Worth", "Renter NW"]),
                "equity": _safe_last(subset, ["Buyer Home Equity", "Home Equity"]),
                "buyer_unrec": _safe_last(subset, ["Buyer Unrecoverable"]),
                "renter_unrec": _safe_last(subset, ["Renter Unrecoverable"]),
            }
        )
    milestone_cards = [
        _milestone_card(
            int(m["year"]),
            float(m["buyer_nw"]),
            float(m["renter_nw"]),
            float(m["equity"]),
            float(m["buyer_unrec"]),
            float(m["renter_unrec"]),
        )
        for m in milestones
    ]
    milestone_table_years = milestone_years[-6:] if len(milestone_years) > 6 else milestone_years
    milestone_rows: list[list[str]] = []
    for y in milestone_table_years:
        subset = df[years_series <= y]
        if subset.empty:
            continue
        bnw = _safe_last(subset, ["Buyer Net Worth", "Buyer NW"])
        rnw = _safe_last(subset, ["Renter Net Worth", "Renter NW"])
        eq = _safe_last(subset, ["Buyer Home Equity", "Home Equity"])
        buc = _safe_last(subset, ["Buyer Unrecoverable"])
        ruc = _safe_last(subset, ["Renter Unrecoverable"])
        adv_label = "Buying ahead" if bnw > rnw else "Renting ahead" if bnw < rnw else "Near tie"
        milestone_rows.append([
            html.escape(f"Year {y}"),
            html.escape(_fmt_currency(bnw)),
            html.escape(_fmt_currency(rnw)),
            html.escape(_fmt_currency(eq)),
            html.escape(_fmt_currency_abs(bnw - rnw)),
            html.escape(adv_label),
            html.escape(_fmt_currency(buc)),
            html.escape(_fmt_currency(ruc)),
        ])

    # cost breakdowns
    buyer_cost_rows, renter_cost_rows = _cost_breakdown_rows(df, buyer_unrec, renter_unrec)
    buyer_cost_table = []
    for name, total in buyer_cost_rows[:8]:
        share = 100.0 * total / max(buyer_unrec, 1.0)
        buyer_cost_table.append([html.escape(name), html.escape(_fmt_currency(total)), html.escape(_fmt_pct(share, 1))])
    renter_cost_table = []
    for name, total in renter_cost_rows[:8]:
        share = 100.0 * total / max(renter_unrec, 1.0)
        renter_cost_table.append([html.escape(name), html.escape(_fmt_currency(total)), html.escape(_fmt_pct(share, 1))])

    avg_buy_out = _clean_number(pd.to_numeric(df.get("Buy Payment", pd.Series(dtype=float)), errors="coerce").dropna().mean())
    avg_rent_out = _clean_number(pd.to_numeric(df.get("Rent Payment", pd.Series(dtype=float)), errors="coerce").dropna().mean())

    # page 1 content
    executive_summary_card = _list_card(
        "Executive Summary",
        [
            f"Verdict: {verdict_text}",
            f"Terminal gap magnitude: {_fmt_currency_abs(delta)} ({leader_before_label.lower()}).",
            f"Final buyer vs renter net worth: {_fmt_currency(buyer_nw)} vs {_fmt_currency(renter_nw)}.",
            f"Cumulative ongoing costs: buyer {_fmt_currency(buyer_unrec)}, renter {_fmt_currency(renter_unrec)}.",
            f"Horizon: {years} years in {html.unescape(province)}.",
        ],
    )
    interpretation_card = _list_card(
        "Interpretation Notes",
        [
            "Results depend heavily on appreciation, returns, rent growth, and mortgage-rate assumptions.",
            "Before-tax values compare modeled wealth. After-tax values use the horizon cash-out / liquidation view when available.",
            "Flip points and sensitivity results show where the verdict can change under one-variable stress.",
            "This report is educational and should not be treated as financial, legal, or tax advice.",
        ],
    )

    decision_cards = [
        _metric_card("Confidence", confidence_label, tone="neutral", foot="Based on absolute terminal gap magnitude."),
        _metric_card(leader_before_label, _fmt_currency_abs(delta), tone=leader_tone),
        _metric_card("Break-even year (before tax)", break_even_before, tone="neutral"),
        _metric_card(leader_after_label, leader_after_value, tone=leader_after_tone, foot="Cash-out / liquidation view at horizon."),
    ]
    decision_html = _layout_table(decision_cards, 4)
    read_html = (
        "<div class='read-strip'><div class='card-title' style='margin-bottom:4px;'>How to read the report</div><ul>"
        + "".join(
            f"<li>{html.escape(item)}</li>"
            for item in [
                "Break-even year = the first year where buying's modeled wealth catches up to or exceeds renting.",
                "When only terminal after-tax cash-out values are available, the after-tax break-even field reports whether parity is reached by horizon.",
                "Confidence is High when |Δ| ≥ $50k, Medium when |Δ| ≥ $15k, else Low.",
            ]
        )
        + "</ul></div>"
    )

    liq_win_pct = _clean_number(getattr(df, "attrs", {}).get("win_pct_liquidation", None))
    key_result_cards = [
        _metric_card("Final buyer net worth", _fmt_currency(buyer_nw)),
        _metric_card("Final renter net worth", _fmt_currency(renter_nw)),
        _metric_card(leader_before_label, _fmt_currency_abs(delta), tone=leader_tone),
        _metric_card("Break-even year (before tax)", break_even_before),
        _metric_card(leader_after_label, leader_after_value, tone=leader_after_tone),
        _metric_card("After-tax break-even", break_even_after),
        _metric_card("Home equity at horizon", _fmt_currency(buyer_equity)),
        _metric_card("Buyer ongoing costs", _fmt_currency(buyer_unrec)),
        _metric_card("Renter ongoing costs", _fmt_currency(renter_unrec)),
        _metric_card("Cash to close", _fmt_currency(close_cash)),
        _metric_card("Monthly owner payment", _fmt_currency(monthly_pmt)),
        _metric_card("Monthly rent", _fmt_currency(cfg.get("rent"))),
    ]
    if has_mc_bands:
        key_result_cards.append(_metric_card("Buyer win rate (MC)", _fmt_pct(win_pct) if win_pct is not None else "Not available"))
        if liq_win_pct is not None:
            key_result_cards.append(_metric_card("Cash-out win rate (MC)", _fmt_pct(liq_win_pct)))

    # page 2 content
    before_tax_view = _list_card(
        "Before-tax decision timing",
        [
            f"{leader_before_label} by {_fmt_currency_abs(delta)} at the horizon.",
            f"Break-even year: {break_even_before}.",
            f"Monthly owner payment: {_fmt_currency(monthly_pmt)} vs rent {_fmt_currency(cfg.get('rent'))}.",
            f"Cash to close: {_fmt_currency(close_cash)}.",
        ],
        soft=False,
    )
    after_tax_items = [
        f"{leader_after_label} {leader_after_value.lower() if leader_after_value != 'Unavailable' else 'is unavailable'} at the horizon." if leader_after_value != "Unavailable" else "After-tax cash-out values are unavailable for this run.",
        f"Break-even status: {break_even_after}.",
    ]
    if buyer_liq is not None:
        after_tax_items.append(f"Buyer cash-out NW: {_fmt_currency(buyer_liq)}.")
    if renter_liq is not None:
        after_tax_items.append(f"Renter cash-out NW: {_fmt_currency(renter_liq)}.")
    after_tax_view = _list_card("After-tax cash-out view", after_tax_items, soft=False)

    break_even_tax_html = _layout_table([before_tax_view, after_tax_view], 2)
    milestone_table_html = _data_table(
        [
            ("Milestone", ""),
            ("Buyer NW", "buy"),
            ("Renter NW", "rent"),
            ("Home Equity", ""),
            ("Gap magnitude", ""),
            ("Leader", ""),
            ("Buyer Costs", "buy"),
            ("Renter Costs", "rent"),
        ],
        milestone_rows,
    )

    # page 3+ net worth content
    buyer_snapshot_rows = [
        ("Final net worth", _fmt_currency(buyer_nw)),
        ("Home equity", _fmt_currency(buyer_equity)),
        ("After-tax cash-out NW", _fmt_currency(buyer_liq)),
        ("Unrecoverable costs", _fmt_currency(buyer_unrec)),
        ("Assumed return", f"{_fmt_input_pct(buyer_ret_pct)}/yr"),
    ]
    renter_snapshot_rows = [
        ("Final net worth", _fmt_currency(renter_nw)),
        ("After-tax cash-out NW", _fmt_currency(renter_liq)),
        ("Unrecoverable costs", _fmt_currency(renter_unrec)),
        ("Assumed return", f"{_fmt_input_pct(renter_ret_pct)}/yr"),
        ("Monthly rent", _fmt_currency(cfg.get("rent"))),
    ]
    networth_summary_html = _layout_table([
        _kv_card("Buyer Snapshot", buyer_snapshot_rows, soft=True),
        _kv_card("Renter Snapshot", renter_snapshot_rows, soft=True),
    ], 2)

    networth_cells = [
        _img_card("Net worth trajectory", "Buyer vs renter net worth over time.", nw_chart),
        _img_card("Gap magnitude over time", "Absolute net-worth gap; the verdict label explains who is ahead.", gap_chart),
    ]
    if has_mc_bands:
        networth_cells.extend([
            _img_card("Buyer net-worth distribution", "Median with 5th–95th percentile band from Monte Carlo results.", buyer_band_chart),
            _img_card("Renter net-worth distribution", "Median with 5th–95th percentile band from Monte Carlo results.", renter_band_chart),
        ])
    else:
        if _series_has_signal(equity_series, tol=10.0) and equity_chart:
            networth_cells.append(_img_card("Buyer home equity trend", "Principal buildup plus home-price appreciation effects over time.", equity_chart))
        else:
            networth_cells.append(_kv_card("Home-equity outlook", _home_equity_outlook(equity_series, years_series), soft=True, extra_note="Equity remained immaterial or flat in this scenario."))
        networth_cells.append(
            _kv_card(
                "Net-worth highlights",
                [
                    ("Final buyer net worth", _fmt_currency(buyer_nw)),
                    ("Final renter net worth", _fmt_currency(renter_nw)),
                    (leader_before_label, _fmt_currency_abs(delta)),
                    ("Break-even year (before tax)", break_even_before),
                    (leader_after_label, leader_after_value),
                    ("After-tax break-even", break_even_after),
                    ("Home equity at horizon", _fmt_currency(buyer_equity)),
                ],
                soft=True,
            )
        )
    networth_charts_html = _layout_table(networth_cells, 2)

    # ongoing cost page
    cost_highlight_rows = [
        ("Buyer ongoing costs", _fmt_currency(buyer_unrec)),
        ("Renter ongoing costs", _fmt_currency(renter_unrec)),
        ("Largest buyer cost", _dominant_label(buyer_cost_rows)),
        ("Largest renter cost", _dominant_label(renter_cost_rows)),
        ("Average buyer monthly outflow", _fmt_currency(avg_buy_out)),
        ("Average renter monthly outflow", _fmt_currency(avg_rent_out)),
    ]
    ongoing_intro_html = _layout_table([
        _img_card("Cumulative ongoing costs", "Buyer vs renter running non-recoverable costs.", unrec_chart),
        _kv_card("Cost highlights", cost_highlight_rows, soft=True),
    ], 2)
    buyer_costs_table_html = _kv_card(
        "Buyer cost breakdown",
        [],
        soft=False,
    )
    buyer_costs_table_html = (
        "<div class='card'><div class='card-title'>Buyer cost breakdown</div><div class='card-subtitle'>Totals over the full horizon. Includes an implied row if closing or selling costs are not explicit in the time series.</div>"
        + _data_table([("Category", ""), ("Total", ""), ("Share", "")], buyer_cost_table)
        + "</div>"
    )
    renter_costs_table_html = (
        "<div class='card'><div class='card-title'>Renter cost breakdown</div><div class='card-subtitle'>Totals over the full horizon.</div>"
        + _data_table([("Category", ""), ("Total", ""), ("Share", "")], renter_cost_table)
        + "</div>"
    )
    ongoing_tables_html = _layout_table([buyer_costs_table_html, renter_costs_table_html], 2)

    # bias / sensitivity page
    key_driver_rows = [
        ("Mortgage rate", _fmt_input_pct(cfg.get("rate"))),
        ("Home appreciation", f"{_fmt_input_pct(apprec_pct)}/yr"),
        ("Rent inflation", _fmt_input_pct(cfg.get("rent_inf") if cfg.get("rent_inf") is not None else cfg.get("rent_inflation_rate_annual"))),
        ("Buyer portfolio return", f"{_fmt_input_pct(buyer_ret_pct)}/yr"),
        ("Renter portfolio return", f"{_fmt_input_pct(renter_ret_pct)}/yr"),
        ("Buyer win rate (MC)", _fmt_pct(win_pct) if win_pct is not None else "Not run"),
    ]
    if liq_win_pct is not None:
        key_driver_rows.append(("Cash-out win rate (MC)", _fmt_pct(liq_win_pct)))

    mc_summary_rows: list[tuple[str, str]] = []
    if has_mc_bands:
        mc_summary_rows.extend([
            ("Buyer final NW median", _fmt_currency(buyer_nw)),
            ("Buyer final NW 5th–95th", f"{_fmt_money_short(_safe_last(df, ['Buyer NW Low']))} to {_fmt_money_short(_safe_last(df, ['Buyer NW High']))}"),
            ("Renter final NW median", _fmt_currency(renter_nw)),
            ("Renter final NW 5th–95th", f"{_fmt_money_short(_safe_last(df, ['Renter NW Low']))} to {_fmt_money_short(_safe_last(df, ['Renter NW High']))}"),
        ])
        if buyer_liq is not None and renter_liq is not None:
            bll = _clean_number(_safe_last(df, ["Buyer Liquidation NW Low"], default=float("nan")))
            blh = _clean_number(_safe_last(df, ["Buyer Liquidation NW High"], default=float("nan")))
            rll = _clean_number(_safe_last(df, ["Renter Liquidation NW Low"], default=float("nan")))
            rlh = _clean_number(_safe_last(df, ["Renter Liquidation NW High"], default=float("nan")))
            if all(v is not None for v in [bll, blh, rll, rlh]):
                mc_summary_rows.extend([
                    ("Buyer cash-out NW median", _fmt_currency(buyer_liq)),
                    ("Buyer cash-out 5th–95th", f"{_fmt_money_short(bll)} to {_fmt_money_short(blh)}"),
                    ("Renter cash-out NW median", _fmt_currency(renter_liq)),
                    ("Renter cash-out 5th–95th", f"{_fmt_money_short(rll)} to {_fmt_money_short(rlh)}"),
                ])
    else:
        mc_summary_rows.append(("Monte Carlo summary", "Not available for this run"))

    flip_rows: list[tuple[str, str]] = []
    sens_table_html = ""
    if isinstance(bias_result, dict) and bias_result:
        base_gap = _clean_number(bias_result.get("base_val", 0.0)) or 0.0
        flip_rows.extend([
            ("Current net-worth gap magnitude", _fmt_currency_abs(base_gap)),
            ("Current leader", "Buying ahead" if base_gap > 0 else "Renting ahead" if base_gap < 0 else "Near tie"),
            ("Flip rent", _fmt_currency(bias_result.get("flip_rent"))),
            ("Flip appreciation", _fmt_input_pct(bias_result.get("flip_app"))),
            ("Flip mortgage rate", _fmt_input_pct(bias_result.get("flip_rate"))),
            ("Flip renter return", _fmt_input_pct(bias_result.get("flip_renter_ret"))),
        ])
        adv_flips = bias_result.get("adv_flips") if isinstance(bias_result.get("adv_flips"), dict) else {}
        for name, meta in list(adv_flips.items())[:4]:
            if isinstance(meta, dict):
                val = meta.get("value")
                fmt = str(meta.get("fmt") or "")
                disp = _fmt_input_pct(val) if fmt.startswith("pct") else _fmt_currency(val)
            else:
                disp = _fmt_currency(meta)
            flip_rows.append((str(name), disp))

        sens = bias_result.get("sens_df")
        if isinstance(sens, pd.DataFrame) and not sens.empty and {"Input", "Increase By", "Impact"}.issubset(sens.columns):
            sens = sens.copy()
            sens["Impact"] = pd.to_numeric(sens["Impact"], errors="coerce")
            sens = sens[np.isfinite(sens["Impact"])]
            if not sens.empty and float(np.nanmax(np.abs(sens["Impact"].to_numpy(dtype="float64")))) > 1.0:
                sens = sens.sort_values("Impact", key=lambda s: np.abs(pd.to_numeric(s, errors="coerce")), ascending=False).head(8)
                sens_rows = [
                    [
                        html.escape(str(row["Input"])),
                        html.escape(str(row["Increase By"])),
                        html.escape(_fmt_currency_abs(row["Impact"])),
                        html.escape("Buying improves" if float(row["Impact"]) > 0 else "Renting improves" if float(row["Impact"]) < 0 else "No material change"),
                    ]
                    for _, row in sens.iterrows()
                ]
                sens_table_html = _data_table(
                    [("Input", ""), ("Increase by", ""), ("Impact on buyer-minus-renter gap", ""), ("Direction", "")],
                    sens_rows,
                )
    if not flip_rows:
        flip_rows = [("Bias dashboard", "Not captured in this session"), ("What to do", "Open Sensitivity & Bias and click Compute Bias Dashboard before exporting.")]
    if not sens_table_html:
        sens_table_html = "<div class='note-inline'>Sensitivity impacts were negligible or not available for this run.</div>"

    bias_top_html = _layout_table([
        _kv_card("Key drivers", key_driver_rows, soft=True),
        _kv_card("Monte Carlo outcome summary", mc_summary_rows, soft=True),
    ], 2)
    bias_bottom_html = _layout_table([
        _kv_card("Bias & flip points", flip_rows, soft=False),
        f"<div class='card'><div class='card-title'>Sensitivity drivers</div>{sens_table_html}</div>",
    ], 2)

    # appendix
    input_rows = _compact_input_rows(cfg)
    input_map = {k: v for k, v in input_rows}
    property_rows = [
        ("Home price", input_map.get("Home price", _fmt_currency(price))),
        ("Down payment", input_map.get("Down payment", _fmt_currency(down))),
        ("Down payment share", _fmt_pct((down / price) * 100.0 if price else None, 1)),
        ("Mortgage rate", input_map.get("Mortgage rate", _fmt_input_pct(cfg.get("rate")))),
        ("Amortization", input_map.get("Amortization", f"{int(cfg.get('amort', 25) or 25)} years")),
        ("Selling costs", input_map.get("Selling costs", _fmt_input_pct(cfg.get("sell_cost_pct") if cfg.get("sell_cost_pct") is not None else cfg.get("selling_cost_pct")))),
        ("Cash to close", _fmt_currency(close_cash)),
    ]
    rent_return_rows = [
        ("Monthly rent", input_map.get("Monthly rent", _fmt_currency(cfg.get("rent")))),
        ("Rent inflation", input_map.get("Rent inflation", _fmt_input_pct(cfg.get("rent_inf") if cfg.get("rent_inf") is not None else cfg.get("rent_inflation_rate_annual")))),
        ("General inflation", input_map.get("General inflation", _fmt_input_pct(cfg.get("general_inf") if cfg.get("general_inf") is not None else cfg.get("general_inflation_rate_annual")))),
        ("Buyer return", f"{_fmt_input_pct(buyer_ret_pct)}/yr"),
        ("Renter return", f"{_fmt_input_pct(renter_ret_pct)}/yr"),
        ("Home appreciation", f"{_fmt_input_pct(apprec_pct)}/yr"),
        ("Horizon", f"{years} years"),
        ("Province", html.unescape(province)),
    ]
    ongoing_input_rows = [
        ("Property tax", input_map.get("Property tax", "—")),
        ("Maintenance", input_map.get("Maintenance", "—")),
        ("Repairs", input_map.get("Repairs", "—")),
        ("Condo fees", input_map.get("Condo fees", "—")),
        ("Home insurance", input_map.get("Home insurance", "—")),
        ("Renter insurance", input_map.get("Renter insurance", "—")),
        ("Owner utilities", input_map.get("Owner utilities", "—")),
        ("Renter utilities", input_map.get("Renter utilities", "—")),
        ("Moving cost / move", input_map.get("Moving cost / move", "—")),
        ("Moving frequency", input_map.get("Moving frequency", "—")),
    ]
    ongoing_context_rows = [
        ("Final buyer ongoing costs", _fmt_currency(buyer_unrec)),
        ("Final renter ongoing costs", _fmt_currency(renter_unrec)),
        ("Average buyer monthly outflow", _fmt_currency(avg_buy_out)),
        ("Average renter monthly outflow", _fmt_currency(avg_rent_out)),
    ]
    mode_rows: list[tuple[str, str]] = []
    if isinstance(report_context, dict) and report_context:
        for section_key in ["meta", "assumptions", "compare"]:
            rows = report_context.get(section_key)
            if isinstance(rows, list):
                mode_rows.extend((str(k), str(v)) for k, v in rows[:6])
    appendix_cards = [
        _kv_card("Property & financing", property_rows, soft=False, appendix=True),
        _kv_card("Rent, returns & horizon", rent_return_rows, soft=False, appendix=True),
        _kv_card("Ongoing assumptions & context", ongoing_input_rows + ongoing_context_rows, soft=False, appendix=True),
        _kv_card("Export context & limitations", mode_rows or [("Export context", "Default scenario export")], soft=False, appendix=True, extra_note="Use the simulator tabs for interactive drill-down, scenario comparison, and assumption testing."),
    ]
    appendix_html = _layout_table(appendix_cards, 2)

    html_content = f"""<!DOCTYPE html>
<html lang='en'>
<head><meta charset='UTF-8'><title>Rent vs Buy Analysis</title></head>
<body>
  <div class='report-header'>
    <div class='report-title'>Rent vs Buy Analysis</div>
    <div class='report-subtitle'>{html.escape(str(scenario_name))} · {province} · {years}-Year Horizon</div>
    <div class='report-date'>Generated: {now}</div>
  </div>
  <p class='disclaimer'>Educational purposes only. Not financial, legal, or tax advice. Results depend on assumptions and will vary.</p>
  <div class='verdict-box {verdict_cls}'>{html.escape(verdict_text)}</div>

  {_layout_table([executive_summary_card, interpretation_card], 2)}

  {_render_section('Decision timing & confidence', decision_html + read_html)}
  {_render_section('Key Results', _layout_table(key_result_cards, 4))}

  {_render_section('Break-even & Tax View', break_even_tax_html)}
  {_render_section('Milestones', _layout_table(milestone_cards, 4) + milestone_table_html)}

  {_render_section('Net Worth', networth_summary_html + networth_charts_html, page_break=True)}

  {_render_section('Ongoing Costs', ongoing_intro_html + ongoing_tables_html)}

  {_render_section('Sensitivity & Bias', bias_top_html + bias_bottom_html)}

  {_render_section('Appendix', appendix_html)}

  <div class='footer'>Generated by Rent vs Buy Simulator (Canada). Methodology: docs/METHODOLOGY.md</div>
</body>
</html>"""

    return HTML(string=html_content).write_pdf(stylesheets=[CSS(string=_PDF_CSS)])
