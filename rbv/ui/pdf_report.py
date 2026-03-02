"""PDF report generation for the RBV Simulator."""

from __future__ import annotations

import datetime
import html
import io
from base64 import b64encode
from typing import Any

import numpy as np
import pandas as pd

_PDF_CSS = """
@page { size: A4; margin: 16mm 14mm; }
* { box-sizing: border-box; }
body { font-family: "Segoe UI", Arial, sans-serif; font-size: 9.5pt; color: #1a2340; margin: 0; }
.report-header { border-bottom: 3px solid #14D8FF; padding-bottom: 8px; margin-bottom: 14px; }
.report-title { font-size: 20pt; font-weight: 700; color: #0B1020; margin: 0 0 4px 0; }
.report-subtitle { font-size: 10pt; color: #4a5a7a; margin: 0; }
.report-date { font-size: 8pt; color: #8a9ab0; text-align: right; margin-top: -24px; }
.disclaimer { font-size: 7.5pt; color: #8a9ab0; border-left: 2px solid #e0e6ef; padding-left: 8px; margin-bottom: 12px; font-style: italic; }

h2 { font-size: 11.5pt; font-weight: 700; color: #0B1020; border-bottom: 1px solid #d0d8e8; padding-bottom: 3px; margin: 14px 0 7px 0; }
.small-note { font-size: 7.5pt; color: #7081a1; margin-top: -2px; margin-bottom: 8px; }

.kpi-grid { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
.kpi-card { flex: 1 1 140px; border: 1px solid #d0d8e8; border-radius: 6px; padding: 7px 10px; background: #f7f9fc; }
.kpi-label { font-size: 7.2pt; color: #5a6a8a; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 3px; }
.kpi-value { font-size: 12pt; font-weight: 700; color: #0B1020; }
.kpi-value.positive { color: #1a8a2e; }
.kpi-value.negative { color: #c0392b; }
.kpi-value.neutral { color: #1460a8; }

.chart-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px; }
.chart-card { border: 1px solid #d0d8e8; border-radius: 6px; padding: 6px; background: #fcfdff; }
.chart-title { font-size: 8pt; color: #4a5a7a; margin: 0 0 4px 0; font-weight: 600; }
.chart-card img { width: 100%; height: auto; }

table { width: 100%; border-collapse: collapse; font-size: 8.4pt; margin-bottom: 10px; }
th { background: #0B1020; color: #E8EEF8; padding: 4px 6px; text-align: left; font-weight: 600; }
td { padding: 3px 6px; border-bottom: 1px solid #e8ecf4; }
tr:nth-child(even) td { background: #f4f7fb; }

.params-grid { display: flex; flex-wrap: wrap; gap: 6px; }
.param-row { flex: 1 1 235px; display: flex; justify-content: space-between; border-bottom: 1px solid #e8ecf4; padding: 2px 0; gap: 8px; }
.param-label { color: #5a6a8a; }
.param-value { font-weight: 600; text-align: right; }

.verdict-box { border-radius: 6px; padding: 10px 14px; margin-bottom: 10px; font-size: 10.2pt; font-weight: 600; }
.verdict-buy { background: #e8f5eb; border-left: 4px solid #1a8a2e; color: #1a5c22; }
.verdict-rent { background: #fef3e2; border-left: 4px solid #d68910; color: #7d510a; }
.verdict-neutral { background: #e8f0fb; border-left: 4px solid #1460a8; color: #0e3d70; }

.footer { font-size: 7pt; color: #aab8cc; text-align: center; margin-top: 20px; border-top: 1px solid #e0e6ef; padding-top: 6px; }
"""


def _fmt_currency(val: float | None, decimals: int = 0) -> str:
    if val is None:
        return "—"
    try:
        return f"${float(val):,.{decimals}f}" if decimals else f"${float(val):,.0f}"
    except (TypeError, ValueError):
        return "—"


def _fmt_pct(val: float | None, decimals: int = 1) -> str:
    if val is None:
        return "—"
    try:
        return f"{float(val):.{decimals}f}%"
    except (TypeError, ValueError):
        return "—"


def _safe_last(df: pd.DataFrame, candidates: list[str], default: float = 0.0) -> float:
    for col in candidates:
        if col in df.columns:
            try:
                return float(pd.to_numeric(df[col], errors="coerce").dropna().iloc[-1])
            except (IndexError, ValueError, TypeError):
                pass
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


def _fig_to_uri(fig: Any) -> str:
    import matplotlib.pyplot as plt

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=140, bbox_inches="tight")
    plt.close(fig)
    return f"data:image/png;base64,{b64encode(buf.getvalue()).decode('utf-8')}"


def _line_chart(df: pd.DataFrame, title: str, s1: pd.Series, s2: pd.Series, l1: str, l2: str) -> str:
    import matplotlib.pyplot as plt

    x = _time_axis_years(df)
    fig, ax = plt.subplots(figsize=(5.3, 2.5))
    ax.plot(x, s1, color="#1460a8", linewidth=1.8, label=l1)
    ax.plot(x, s2, color="#c0392b", linewidth=1.8, label=l2)
    ax.set_title(title, fontsize=9)
    ax.grid(alpha=0.25)
    ax.tick_params(labelsize=8)
    ax.set_xlabel("Years", fontsize=8)
    ax.legend(loc="best", fontsize=7)
    return _fig_to_uri(fig)


def _compact_input_rows(cfg: dict[str, Any]) -> list[tuple[str, str]]:
    fields = [
        ("price", "Home price", "money"),
        ("down", "Down payment", "money"),
        ("rate", "Mortgage rate", "pct"),
        ("rent", "Monthly rent", "money"),
        ("years", "Horizon", "years"),
        ("amort", "Amortization", "years"),
        ("province", "Province", "text"),
        ("property_tax_rate_annual", "Property tax", "pct"),
        ("maintenance_rate_annual", "Maintenance", "pct"),
        ("repair_rate_annual", "Repairs", "pct"),
        ("selling_cost_pct", "Selling costs", "pct"),
        ("condo_fee_monthly", "Condo fees", "money"),
        ("home_insurance_monthly", "Home insurance", "money"),
        ("rent_insurance_monthly", "Renter insurance", "money"),
        ("rent_inflation_rate_annual", "Rent inflation", "pct"),
        ("general_inflation_rate_annual", "General inflation", "pct"),
        ("p_tax_rate_pct", "Property tax", "pct"),
        ("maint_rate_pct", "Maintenance", "pct"),
        ("repair_rate_pct", "Repairs", "pct"),
        ("sell_cost_pct", "Selling costs", "pct"),
        ("rent_inf", "Rent inflation", "pct"),
        ("general_inf", "General inflation", "pct"),
    ]
    rows: list[tuple[str, str]] = []
    seen: set[str] = set()
    for key, label, kind in fields:
        if key not in cfg or cfg.get(key) is None:
            continue
        if label in seen:
            continue
        val = cfg.get(key)
        if kind == "money":
            disp = _fmt_currency(float(val))
        elif kind == "pct":
            disp = _fmt_pct(float(val))
        elif kind == "years":
            disp = f"{int(float(val))} years"
        else:
            disp = str(val)
        rows.append((label, disp))
        seen.add(label)
    return rows


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
) -> bytes:
    try:
        from weasyprint import CSS, HTML
    except ImportError as exc:
        raise RuntimeError("weasyprint is required for PDF export. Install it with: pip install weasyprint") from exc

    price = float(cfg.get("price", 0.0) or 0.0)
    down = float(cfg.get("down", 0.0) or 0.0)
    years = int(float(cfg.get("years", 25) or 25))
    province = cfg.get("province", "—")

    buyer_nw = _safe_last(df, ["Buyer Net Worth", "Buyer NW", "buyer_nw"])
    renter_nw = _safe_last(df, ["Renter Net Worth", "Renter NW", "renter_nw"])
    buyer_equity = _safe_last(df, ["Buyer Home Equity", "Home Equity", "Equity"])
    buyer_unrec = _safe_last(df, ["Buyer Unrecoverable"])
    renter_unrec = _safe_last(df, ["Renter Unrecoverable"])
    delta = buyer_nw - renter_nw

    if delta > 5_000:
        verdict_cls = "verdict-buy"
        verdict_text = f"Buying appears advantageous by {_fmt_currency(delta)} at the {years}-year horizon."
    elif delta < -5_000:
        verdict_cls = "verdict-rent"
        verdict_text = f"Renting appears advantageous by {_fmt_currency(abs(delta))} at the {years}-year horizon."
    else:
        verdict_cls = "verdict-neutral"
        verdict_text = f"Outcomes are approximately equal at the {years}-year horizon (Δ = {_fmt_currency(abs(delta))})."

    buyer_nw_series = _pick_series(df, ["Buyer Net Worth", "Buyer NW", "buyer_nw"])
    renter_nw_series = _pick_series(df, ["Renter Net Worth", "Renter NW", "renter_nw"])
    buyer_unrec_series = _pick_series(df, ["Buyer Unrecoverable"])
    renter_unrec_series = _pick_series(df, ["Renter Unrecoverable"])
    try:
        nw_chart = _line_chart(df, "Net Worth Trajectory", buyer_nw_series, renter_nw_series, "Buyer NW", "Renter NW")
        unrec_chart = _line_chart(df, "Cumulative Ongoing Costs", buyer_unrec_series, renter_unrec_series, "Buyer costs", "Renter costs")
    except Exception:
        nw_chart = ""
        unrec_chart = ""

    milestones: list[dict[str, float | int]] = []
    time_years = _time_axis_years(df)
    for y in sorted({*range(5, max(6, years), 5), years}):
        subset = df[time_years <= y]
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

    milestone_rows = "".join(
        f"<tr><td>Year {m['year']}</td><td>{_fmt_currency(float(m['buyer_nw']))}</td>"
        f"<td>{_fmt_currency(float(m['renter_nw']))}</td><td>{_fmt_currency(float(m['equity']))}</td>"
        f"<td style='font-weight:600;color:{'#1a8a2e' if float(m['buyer_nw']) >= float(m['renter_nw']) else '#c0392b'}'>{_fmt_currency(float(m['buyer_nw']) - float(m['renter_nw']))}</td>"
        f"<td>{_fmt_currency(float(m['buyer_unrec']))}</td><td>{_fmt_currency(float(m['renter_unrec']))}</td></tr>"
        for m in milestones
    )

    win_display = _fmt_pct(win_pct) if win_pct is not None else "Deterministic"
    delta_cls = "positive" if delta > 0 else ("negative" if delta < 0 else "neutral")
    now = datetime.date.today().strftime("%B %d, %Y")

    input_rows = _compact_input_rows(cfg)
    input_html = "".join(
        f"<div class='param-row'><span class='param-label'>{k}</span><span class='param-value'>{v}</span></div>"
        for k, v in input_rows
    )

    bias_html = ""
    if isinstance(bias_result, dict) and bias_result:
        bias_values = [
            ("Current net-worth gap", _fmt_currency(float(bias_result.get("base_val", 0.0)))),
            ("Flip rent", _fmt_currency(bias_result.get("flip_rent"))),
            ("Flip appreciation", _fmt_pct(bias_result.get("flip_app"))),
            ("Flip mortgage rate", _fmt_pct(bias_result.get("flip_rate"))),
            ("Flip renter return", _fmt_pct(bias_result.get("flip_renter_ret"))),
        ]
        cards = "".join(
            f"<div class='kpi-card'><div class='kpi-label'>{k}</div><div class='kpi-value neutral'>{v}</div></div>"
            for k, v in bias_values
        )
        bias_html = (
            "<h2>Net Worth Bias Dashboard Snapshot</h2>"
            "<div class='small-note'>Latest bias run from this session. Flip points indicate where the verdict tends to change.</div>"
            f"<div class='kpi-grid'>{cards}</div>"
        )

    _scenario_name = html.escape(str(scenario_name))
    _province = html.escape(str(province))
    _chart_html = (
        f"<div class='chart-grid'>"
        f"<div class='chart-card'><div class='chart-title'>Net worth trajectory</div><img src='{nw_chart}' alt='Net worth chart' /></div>"
        f"<div class='chart-card'><div class='chart-title'>Cumulative ongoing costs</div><img src='{unrec_chart}' alt='Costs chart' /></div>"
        f"</div>"
        if nw_chart and unrec_chart
        else "<div class='small-note'>Charts unavailable for this export environment; numeric tables are still included.</div>"
    )

    html_content = f"""<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'><title>Rent vs Buy Analysis</title></head><body>
<div class='report-header'><div class='report-title'>Rent vs Buy Analysis</div><div class='report-subtitle'>{_scenario_name} · {_province} · {years}-Year Horizon</div><div class='report-date'>Generated: {now}</div></div>
<p class='disclaimer'>Educational purposes only. Not financial, legal, or tax advice. Results depend on assumptions and will vary.</p>
<div class='verdict-box {verdict_cls}'>{verdict_text}</div>

<h2>Key Results</h2>
<div class='kpi-grid'>
<div class='kpi-card'><div class='kpi-label'>Final Buyer Net Worth</div><div class='kpi-value neutral'>{_fmt_currency(buyer_nw)}</div></div>
<div class='kpi-card'><div class='kpi-label'>Final Renter Net Worth</div><div class='kpi-value neutral'>{_fmt_currency(renter_nw)}</div></div>
<div class='kpi-card'><div class='kpi-label'>Buyer Advantage (Δ)</div><div class='kpi-value {delta_cls}'>{_fmt_currency(delta)}</div></div>
<div class='kpi-card'><div class='kpi-label'>Home Equity at Horizon</div><div class='kpi-value neutral'>{_fmt_currency(buyer_equity)}</div></div>
<div class='kpi-card'><div class='kpi-label'>Buyer Ongoing Costs</div><div class='kpi-value neutral'>{_fmt_currency(buyer_unrec)}</div></div>
<div class='kpi-card'><div class='kpi-label'>Renter Ongoing Costs</div><div class='kpi-value neutral'>{_fmt_currency(renter_unrec)}</div></div>
<div class='kpi-card'><div class='kpi-label'>Monthly Payment</div><div class='kpi-value neutral'>{_fmt_currency(monthly_pmt)}</div></div>
<div class='kpi-card'><div class='kpi-label'>Buyer Win Rate (MC)</div><div class='kpi-value neutral'>{win_display}</div></div>
</div>

<h2>Trends & Milestones</h2>
{_chart_html}
<table><thead><tr><th>Milestone</th><th>Buyer NW</th><th>Renter NW</th><th>Home Equity</th><th>Buyer Advantage</th><th>Buyer Costs</th><th>Renter Costs</th></tr></thead><tbody>{milestone_rows}</tbody></table>

<h2>Scenario Inputs</h2>
<div class='params-grid'>{input_html}
<div class='param-row'><span class='param-label'>Down Payment Share</span><span class='param-value'>{_fmt_pct((down / price * 100.0) if price else None)}</span></div>
<div class='param-row'><span class='param-label'>Cash to Close</span><span class='param-value'>{_fmt_currency(close_cash)}</span></div>
<div class='param-row'><span class='param-label'>Buyer Return</span><span class='param-value'>{_fmt_pct(buyer_ret_pct)}/yr</span></div>
<div class='param-row'><span class='param-label'>Renter Return</span><span class='param-value'>{_fmt_pct(renter_ret_pct)}/yr</span></div>
<div class='param-row'><span class='param-label'>Home Appreciation</span><span class='param-value'>{_fmt_pct(apprec_pct)}/yr</span></div>
</div>

{bias_html}

<div class='footer'>Generated by Rent vs Buy Simulator (Canada). Methodology: docs/METHODOLOGY.md</div>
</body></html>"""

    return HTML(string=html_content).write_pdf(stylesheets=[CSS(string=_PDF_CSS)])
