"""PDF report generation for the RBV Simulator."""

from __future__ import annotations

import datetime
import html
import io
from base64 import b64encode
from typing import Any

import numpy as np
import pandas as pd

from rbv.ui.theme import BUY_COLOR, RENT_COLOR

_PDF_CSS = """
@page { size: A4; margin: 14mm 12mm; }
* { box-sizing: border-box; }
body { font-family: "Segoe UI", Arial, sans-serif; font-size: 9.4pt; color: #1b2235; margin: 0; background: #ffffff; orphans: 3; widows: 3; }
.report-header { border: 1px solid #d7def2; border-top: 4px solid __BUY_COLOR__; margin-bottom: 14px; background: #ffffff; border-radius: 8px; padding: 10px 12px 8px 12px; }
.report-title { font-size: 20pt; font-weight: 700; color: #0B1020; margin: 0 0 4px 0; }
.report-subtitle { font-size: 10pt; color: #4a5a7a; margin: 0; }
.report-date { font-size: 8pt; color: #8a9ab0; text-align: right; margin-top: -24px; }
.disclaimer { font-size: 7.5pt; color: #8a9ab0; border-left: 2px solid #e0e6ef; padding-left: 8px; margin-bottom: 12px; font-style: italic; }

h2 { font-size: 11.5pt; font-weight: 700; color: #0B1020; border-bottom: 2px solid #dbe3f3; padding-bottom: 4px; margin: 14px 0 7px 0; }

.section { break-inside: avoid; page-break-inside: avoid; margin-bottom: 8px; }
h2 { page-break-after: avoid; }
.small-note { font-size: 7.5pt; color: #7081a1; margin-top: -2px; margin-bottom: 8px; }

.kpi-grid { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
.kpi-card { flex: 1 1 140px; border: 1px solid #d8e0f2; border-radius: 8px; padding: 8px 10px; background: #ffffff; box-shadow: 0 1px 2px rgba(11, 16, 32, 0.05); }
.kpi-label { font-size: 7.2pt; color: #5a6a8a; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 3px; }
.kpi-value { font-size: 12pt; font-weight: 700; color: #0B1020; }
.kpi-value.positive { color: #1a8a2e; }
.kpi-value.negative { color: #c0392b; }
.kpi-value.neutral { color: #1460a8; }

.chart-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px; align-items: start; }
.summary-grid { display:grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px; }
.summary-card { border: 1px solid #d0d8e8; border-radius: 8px; padding: 8px 10px; background: #f9fbff; box-shadow: 0 1px 2px rgba(11, 16, 32, 0.04); }
.summary-title { font-size: 8.5pt; font-weight: 700; color: #0B1020; margin: 0 0 4px 0; }
.summary-list { margin: 0; padding-left: 16px; font-size: 8pt; color: #425172; }
.summary-list li { margin-bottom: 3px; }
.chart-card { border: 1px solid #d0d8e8; border-radius: 8px; padding: 8px; background: #ffffff; break-inside: avoid; page-break-inside: avoid; min-height: 215px; }
.chart-title { font-size: 8pt; color: #4a5a7a; margin: 0 0 4px 0; font-weight: 600; }
.chart-subtitle { font-size: 7.2pt; color: #6c7b98; margin: 0 0 6px 0; }
.chart-card img { width: 100%; height: auto; }

table { width: 100%; border-collapse: collapse; font-size: 8.4pt; margin-bottom: 10px; break-inside: avoid; page-break-inside: avoid; }
th { background: #0B1020; color: #E8EEF8; padding: 4px 6px; text-align: left; font-weight: 600; }
td { padding: 3px 6px; border-bottom: 1px solid #e8ecf4; }
tr:nth-child(even) td { background: #f4f7fb; }
.th-buy { background: __BUY_COLOR__; color: #062330; }
.th-rent { background: __RENT_COLOR__; color: #29153f; }

.params-grid { display: flex; flex-wrap: wrap; gap: 6px; }
.param-row { flex: 1 1 235px; display: flex; justify-content: space-between; border-bottom: 1px solid #e8ecf4; padding: 2px 0; gap: 8px; }
.param-label { color: #5a6a8a; }
.param-value { font-weight: 600; text-align: right; }

.verdict-box { border-radius: 6px; padding: 10px 14px; margin-bottom: 10px; font-size: 10.2pt; font-weight: 600; }
.verdict-buy { background: #e8f5eb; border-left: 4px solid #1a8a2e; color: #1a5c22; }
.verdict-rent { background: #fef3e2; border-left: 4px solid #d68910; color: #7d510a; }
.verdict-neutral { background: #e8f0fb; border-left: 4px solid #1460a8; color: #0e3d70; }

.confidence-panel { border: 1px solid #c9d7ee; border-radius: 8px; background: linear-gradient(180deg, #fbfdff 0%, #f3f8ff 100%); padding: 8px 10px; margin: 8px 0 10px 0; break-inside: avoid; page-break-inside: avoid; }
.confidence-title { font-size: 8.6pt; font-weight: 700; color: #0b2a5a; margin: 0 0 4px 0; }
.confidence-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; }
.confidence-item { border: 1px solid #d8e3f5; border-radius: 6px; background: #fff; padding: 6px 7px; }
.confidence-label { font-size: 7pt; color: #5b6e91; text-transform: uppercase; letter-spacing: 0.04em; }
.confidence-value { font-size: 10pt; font-weight: 700; color: #0b2a5a; margin-top: 2px; }
.data-notes { border: 1px dashed #f0b429; background: #fffaf0; border-radius: 8px; padding: 8px 10px; margin-top: 8px; break-inside: avoid; page-break-inside: avoid; }
.data-notes-title { font-size: 8.2pt; font-weight: 700; color: #8b5e00; margin: 0 0 4px 0; }
.data-notes ul { margin: 0; padding-left: 16px; }
.data-notes li { font-size: 7.8pt; color: #7a5a18; margin-bottom: 2px; }
.methodology-note { border: 1px solid #d6e3f8; border-radius: 8px; background: #f7fbff; padding: 8px 10px; margin: 8px 0 10px 0; break-inside: avoid; page-break-inside: avoid; }
.methodology-title { font-size: 8.2pt; font-weight: 700; color: #0e3d70; margin: 0 0 4px 0; }
.methodology-note ul { margin: 0; padding-left: 16px; }
.methodology-note li { font-size: 7.8pt; color: #35567f; margin-bottom: 2px; }

.footer { font-size: 7pt; color: #aab8cc; text-align: center; margin-top: 20px; border-top: 1px solid #e0e6ef; padding-top: 6px; }

.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 8px; }
.detail-card { border: 1px solid #d8e0f2; border-radius: 8px; background: #ffffff; padding: 8px; }
.detail-title { font-size: 8.2pt; font-weight: 700; margin: 0 0 6px 0; }
.detail-title.buy { color: #0b7a8f; }
.detail-title.rent { color: #7d45af; }
.detail-row { display: flex; justify-content: space-between; gap: 8px; font-size: 7.8pt; border-bottom: 1px solid #edf1f8; padding: 2px 0; }
.detail-row:last-child { border-bottom: none; }
.detail-key { color: #5a6a8a; }
.detail-value { color: #1f2c45; font-weight: 600; }
""".replace("__BUY_COLOR__", BUY_COLOR).replace("__RENT_COLOR__", RENT_COLOR)


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


def _fmt_input_pct(val: float | None, decimals: int = 2) -> str:
    if val is None:
        return "—"
    try:
        x = float(val)
        if abs(x) <= 1.0:
            x *= 100.0
        return f"{x:.{decimals}f}%"
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


def _fig_to_uri(fig: Any, plt_mod: Any) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=140, bbox_inches="tight")
    plt_mod.close(fig)
    return f"data:image/png;base64,{b64encode(buf.getvalue()).decode('utf-8')}"


def _line_chart(df: pd.DataFrame, title: str, s1: pd.Series, s2: pd.Series, l1: str, l2: str) -> str:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return ""
    try:
        x = _time_axis_years(df)
        fig, ax = plt.subplots(figsize=(5.3, 2.5), facecolor="white")
        ax.plot(x, s1, color=BUY_COLOR, linewidth=2.0, label=l1)
        ax.plot(x, s2, color=RENT_COLOR, linewidth=2.0, label=l2)
        ax.set_title(title, fontsize=9)
        ax.set_facecolor("white")
        ax.grid(alpha=0.22, color="#cad5ea")
        ax.tick_params(labelsize=8)
        ax.set_xlabel("Years", fontsize=8)
        ax.legend(loc="best", fontsize=7)
        return _fig_to_uri(fig, plt)
    except Exception:
        # Keep PDF export available even when chart rendering fails at runtime.
        return ""


def _single_line_chart(df: pd.DataFrame, title: str, s1: pd.Series, l1: str) -> str:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return ""
    try:
        x = _time_axis_years(df)
        fig, ax = plt.subplots(figsize=(5.3, 2.5), facecolor="white")
        ax.plot(x, s1, color=BUY_COLOR, linewidth=2.0, label=l1)
        ax.axhline(0.0, color="#94a3b8", linewidth=1.0, linestyle="--", alpha=0.7)
        ax.set_title(title, fontsize=9)
        ax.set_facecolor("white")
        ax.grid(alpha=0.22, color="#cad5ea")
        ax.tick_params(labelsize=8)
        ax.set_xlabel("Years", fontsize=8)
        ax.legend(loc="best", fontsize=7)
        return _fig_to_uri(fig, plt)
    except Exception:
        return ""




def _band_chart(df: pd.DataFrame, title: str, med: pd.Series, low: pd.Series, high: pd.Series, label: str, color: str) -> str:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return ""
    try:
        x = _time_axis_years(df)
        fig, ax = plt.subplots(figsize=(5.3, 2.5), facecolor="white")
        ax.fill_between(x, low, high, color=color, alpha=0.20, linewidth=0.0, label=f"{label} 5–95%")
        ax.plot(x, med, color=color, linewidth=2.0, label=f"{label} median")
        ax.set_facecolor("white")
        ax.set_title(title, fontsize=9)
        ax.grid(alpha=0.22, color="#cad5ea")
        ax.tick_params(labelsize=8)
        ax.set_xlabel("Years", fontsize=8)
        ax.legend(loc="best", fontsize=7)
        return _fig_to_uri(fig, plt)
    except Exception:
        return ""

def _compact_input_rows(cfg: dict[str, Any]) -> list[tuple[str, str]]:
    fields = [
        (("price",), "Home price", "money"),
        (("down",), "Down payment", "money"),
        (("rate",), "Mortgage rate", "pct"),
        (("rent",), "Monthly rent", "money"),
        (("years",), "Horizon", "years"),
        (("amort",), "Amortization", "years"),
        (("province",), "Province", "text"),
        (("sell_cost_pct", "selling_cost_pct"), "Selling costs", "pct"),
        (("p_tax_rate_pct", "property_tax_rate_annual"), "Property tax", "pct"),
        (("maint_rate_pct", "maintenance_rate_annual"), "Maintenance", "pct"),
        (("repair_rate_pct", "repair_rate_annual"), "Repairs", "pct"),
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
    seen_labels: set[str] = set()
    for keys, label, kind in fields:
        if label in seen_labels:
            continue
        key = next((k for k in keys if k in cfg and cfg.get(k) is not None), None)
        if key is None:
            continue
        val = cfg.get(key)
        try:
            if kind == "money":
                disp = _fmt_currency(float(val))
            elif kind == "pct":
                disp = _fmt_input_pct(float(val))
            elif kind == "years":
                yrs = int(float(val))
                if label == "Moving frequency" and yrs >= 9999:
                    disp = "Never"
                else:
                    disp = f"{yrs} years"
            else:
                disp = html.escape(str(val))
        except (TypeError, ValueError):
            disp = html.escape(str(val)) if kind == "text" else "—"
        rows.append((label, disp))
        seen_labels.add(label)
    return rows




def _render_section(title: str, body_html: str) -> str:
    return f"<div class='section'><h2>{html.escape(title)}</h2>{body_html}</div>"


def _render_kv_table(rows_html: str) -> str:
    return f"<table><tbody>{rows_html}</tbody></table>"
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
    except ImportError as exc:
        raise RuntimeError("weasyprint is required for PDF export. Install it with: pip install weasyprint") from exc

    price = float(cfg.get("price", 0.0) or 0.0)
    down = float(cfg.get("down", 0.0) or 0.0)
    years = int(float(cfg.get("years", 25) or 25))
    province = html.escape(str(cfg.get("province", "—")))

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
    nw_chart = _line_chart(df, "Net Worth Trajectory", buyer_nw_series, renter_nw_series, "Buyer NW", "Renter NW")
    unrec_chart = _line_chart(df, "Cumulative Ongoing Costs", buyer_unrec_series, renter_unrec_series, "Buyer costs", "Renter costs")
    gap_series = buyer_nw_series - renter_nw_series
    gap_chart = _single_line_chart(df, "Buyer Advantage (Δ) Over Time", gap_series, "Buyer - Renter")

    buyer_nw_low_series = _pick_series(df, ["Buyer NW Low"])
    buyer_nw_high_series = _pick_series(df, ["Buyer NW High"])
    renter_nw_low_series = _pick_series(df, ["Renter NW Low"])
    renter_nw_high_series = _pick_series(df, ["Renter NW High"])
    buyer_band_chart = _band_chart(df, "Buyer Net Worth Distribution", buyer_nw_series, buyer_nw_low_series, buyer_nw_high_series, "Buyer", BUY_COLOR)
    renter_band_chart = _band_chart(df, "Renter Net Worth Distribution", renter_nw_series, renter_nw_low_series, renter_nw_high_series, "Renter", RENT_COLOR)

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
        f"<td style='font-weight:600;color:{BUY_COLOR if float(m['buyer_nw']) >= float(m['renter_nw']) else RENT_COLOR}'>{_fmt_currency(float(m['buyer_nw']) - float(m['renter_nw']))}</td>"
        f"<td>{_fmt_currency(float(m['buyer_unrec']))}</td><td>{_fmt_currency(float(m['renter_unrec']))}</td></tr>"
        for m in milestones
    ) or "<tr><td colspan='7'>No milestone data available for this run.</td></tr>"

    win_display = _fmt_pct(win_pct) if win_pct is not None else "Deterministic"
    delta_cls = "positive" if delta > 0 else ("negative" if delta < 0 else "neutral")
    now = datetime.date.today().strftime("%B %d, %Y")

    input_rows = _compact_input_rows(cfg)
    input_html = "".join(
        f"<div class='param-row'><span class='param-label'>{html.escape(k)}</span><span class='param-value'>{v}</span></div>"
        for k, v in input_rows
    )

    ongoing_rows = [
        ("Final buyer ongoing costs", _fmt_currency(buyer_unrec)),
        ("Final renter ongoing costs", _fmt_currency(renter_unrec)),
        ("Annual property tax input", _fmt_input_pct(cfg.get("p_tax_rate_pct") if cfg.get("p_tax_rate_pct") is not None else cfg.get("property_tax_rate_annual"))),
        ("Annual maintenance input", _fmt_input_pct(cfg.get("maint_rate_pct") if cfg.get("maint_rate_pct") is not None else cfg.get("maintenance_rate_annual"))),
        ("Annual repairs input", _fmt_input_pct(cfg.get("repair_rate_pct") if cfg.get("repair_rate_pct") is not None else cfg.get("repair_rate_annual"))),
        ("Annual rent inflation input", _fmt_input_pct(cfg.get("rent_inf") if cfg.get("rent_inf") is not None else cfg.get("rent_inflation_rate_annual"))),
        ("Annual general inflation input", _fmt_input_pct(cfg.get("general_inf") if cfg.get("general_inf") is not None else cfg.get("general_inflation_rate_annual"))),
    ]
    ongoing_html = "".join(f"<tr><th>{html.escape(k)}</th><td>{html.escape(v)}</td></tr>" for k, v in ongoing_rows)

    bias_html = ""
    bias_sens_html = ""
    if isinstance(bias_result, dict) and bias_result:
        adv_flips = bias_result.get("adv_flips") if isinstance(bias_result.get("adv_flips"), dict) else {}
        bias_values = [
            ("Current net-worth gap", _fmt_currency(float(bias_result.get("base_val", 0.0) or 0.0))),
            ("Flip rent", _fmt_currency(bias_result.get("flip_rent"))),
            ("Flip appreciation", _fmt_input_pct(bias_result.get("flip_app"))),
            ("Flip mortgage rate", _fmt_input_pct(bias_result.get("flip_rate"))),
            ("Flip renter return", _fmt_input_pct(bias_result.get("flip_renter_ret"))),
        ]
        for k, meta in list(adv_flips.items())[:6]:
            if isinstance(meta, dict):
                v = meta.get("value")
                fmt = str(meta.get("fmt") or "")
                if fmt.startswith("pct"):
                    disp = _fmt_input_pct(v)
                else:
                    disp = _fmt_currency(v)
                bias_values.append((str(k), disp))
            else:
                bias_values.append((str(k), _fmt_input_pct(meta) if "rate" in str(k).lower() or "pct" in str(k).lower() else _fmt_currency(meta)))
        cards = "".join(
            f"<div class='kpi-card'><div class='kpi-label'>{html.escape(k)}</div><div class='kpi-value neutral'>{html.escape(v)}</div></div>"
            for k, v in bias_values
        )
        bias_html = (
            "<h2>Net Worth Bias Dashboard Snapshot</h2>"
            "<div class='small-note'>Latest bias run from this session. Flip points indicate where the verdict tends to change.</div>"
            f"<div class='kpi-grid'>{cards}</div>"
        )

        sens = bias_result.get("sens_df")
        if isinstance(sens, pd.DataFrame) and not sens.empty:
            cols = [c for c in ["Parameter", "Base", "+ Step", "- Step", "Δ(+)", "Δ(-)"] if c in sens.columns]
            if cols:
                sens_rows = []
                for _, row in sens.head(8)[cols].iterrows():
                    sens_rows.append("<tr>" + "".join(f"<td>{html.escape(str(row.get(c, '—')))}</td>" for c in cols) + "</tr>")
                sens_head = "".join(f"<th>{html.escape(str(c))}</th>" for c in cols)
                bias_sens_html = (
                    "<h2>Bias Sensitivity Drivers</h2>"
                    "<div class='small-note'>Top directional sensitivities from the latest Bias & Sensitivity dashboard run.</div>"
                    f"<table><thead><tr>{sens_head}</tr></thead><tbody>{''.join(sens_rows)}</tbody></table>"
                )

    # Decision confidence + data completeness notes.
    gap_abs = abs(delta)
    if gap_abs >= 50_000:
        confidence_label = "High"
    elif gap_abs >= 15_000:
        confidence_label = "Medium"
    else:
        confidence_label = "Low"
    first_nonneg_year: str = "Not reached"
    try:
        gap_nonneg = gap_series[gap_series >= 0]
        if len(gap_nonneg) > 0:
            first_idx = gap_nonneg.index[0]
            first_nonneg_year = f"Year {int(float(time_years.loc[first_idx]))}"
    except (TypeError, ValueError, KeyError):
        first_nonneg_year = "Not available"

    confidence_html = (
        "<div class='confidence-panel'>"
        "<div class='confidence-title'>Decision Confidence Snapshot</div>"
        "<div class='confidence-grid'>"
        f"<div class='confidence-item'><div class='confidence-label'>Confidence</div><div class='confidence-value'>{html.escape(confidence_label)}</div></div>"
        f"<div class='confidence-item'><div class='confidence-label'>Final gap (Δ)</div><div class='confidence-value'>{html.escape(_fmt_currency(delta))}</div></div>"
        f"<div class='confidence-item'><div class='confidence-label'>First non-negative gap</div><div class='confidence-value'>{html.escape(first_nonneg_year)}</div></div>"
        "</div></div>"
    )

    methodology_points = [
        "Confidence is based on absolute terminal net-worth gap (|Δ|): High ≥ $50k, Medium ≥ $15k, else Low.",
        "Flip-point metrics indicate where verdict direction can change under one-variable stress.",
        "Charts/tables may degrade in constrained runtimes; see Data Availability Notes when applicable.",
    ]
    methodology_html = (
        "<div class='methodology-note'>"
        "<div class='methodology-title'>Methodology & Confidence Legend</div>"
        "<ul>"
        + "".join(f"<li>{html.escape(x)}</li>" for x in methodology_points)
        + "</ul></div>"
    )

    data_notes: list[str] = []
    if not nw_chart:
        data_notes.append("Net-worth chart could not be rendered in this runtime.")
    if not unrec_chart:
        data_notes.append("Ongoing-cost chart could not be rendered in this runtime.")
    if not gap_chart:
        data_notes.append("Buyer-advantage chart could not be rendered in this runtime.")
    if not milestones:
        data_notes.append("Milestone table uses fallback because no milestone rows were available.")
    if not input_rows:
        data_notes.append("Scenario input rows were unavailable from the provided config payload.")

    data_notes_html = ""
    if data_notes:
        data_notes_html = (
            "<div class='data-notes'>"
            "<div class='data-notes-title'>Data Availability Notes</div>"
            "<ul>"
            + "".join(f"<li>{html.escape(x)}</li>" for x in data_notes)
            + "</ul></div>"
        )

    summary_points = [
        f"Verdict: {verdict_text}",
        f"Final buyer vs renter net worth: {_fmt_currency(buyer_nw)} vs {_fmt_currency(renter_nw)}.",
        f"Cumulative ongoing costs: buyer {_fmt_currency(buyer_unrec)}, renter {_fmt_currency(renter_unrec)}.",
        f"Horizon: {years} years in {province}.",
    ]
    risk_points = [
        "Interpretation depends heavily on assumptions for returns, appreciation, and inflation.",
        "Bias flip points indicate where the decision can reverse under parameter stress.",
        "Treat this report as educational guidance, not financial advice.",
    ]
    summary_html = (
        "<div class='summary-grid'>"
        "<div class='summary-card'><div class='summary-title'>Executive Summary</div><ul class='summary-list'>"
        + "".join(f"<li>{html.escape(x)}</li>" for x in summary_points)
        + "</ul></div>"
        "<div class='summary-card'><div class='summary-title'>Interpretation Notes</div><ul class='summary-list'>"
        + "".join(f"<li>{html.escape(x)}</li>" for x in risk_points)
        + "</ul></div>"
        "</div>"
    )

    context_html = ""
    if isinstance(report_context, dict) and report_context:
        blocks: list[str] = []
        for section_key, section_title in [
            ("meta", "Export Metadata"),
            ("assumptions", "Assumptions & Policy Snapshot"),
            ("compare", "A/B Compare Snapshot"),
        ]:
            rows = report_context.get(section_key)
            if isinstance(rows, list) and rows:
                rows_html = "".join(
                    f"<tr><th>{html.escape(str(k))}</th><td>{html.escape(str(v))}</td></tr>"
                    for k, v in rows
                )
                blocks.append(_render_section(section_title, _render_kv_table(rows_html)))
        context_html = "".join(blocks)

    key_results_html = (
        "<div class='kpi-grid'>"
        f"<div class='kpi-card'><div class='kpi-label'>Final Buyer Net Worth</div><div class='kpi-value neutral'>{_fmt_currency(buyer_nw)}</div></div>"
        f"<div class='kpi-card'><div class='kpi-label'>Final Renter Net Worth</div><div class='kpi-value neutral'>{_fmt_currency(renter_nw)}</div></div>"
        f"<div class='kpi-card'><div class='kpi-label'>Buyer Advantage (Δ)</div><div class='kpi-value {delta_cls}'>{_fmt_currency(delta)}</div></div>"
        f"<div class='kpi-card'><div class='kpi-label'>Home Equity at Horizon</div><div class='kpi-value neutral'>{_fmt_currency(buyer_equity)}</div></div>"
        f"<div class='kpi-card'><div class='kpi-label'>Buyer Ongoing Costs</div><div class='kpi-value neutral'>{_fmt_currency(buyer_unrec)}</div></div>"
        f"<div class='kpi-card'><div class='kpi-label'>Renter Ongoing Costs</div><div class='kpi-value neutral'>{_fmt_currency(renter_unrec)}</div></div>"
        f"<div class='kpi-card'><div class='kpi-label'>Monthly Payment</div><div class='kpi-value neutral'>{_fmt_currency(monthly_pmt)}</div></div>"
        f"<div class='kpi-card'><div class='kpi-label'>Buyer Win Rate (MC)</div><div class='kpi-value neutral'>{win_display}</div></div>"
        "</div>"
    )

    detail_rows_buy = [
        ("Final net worth", _fmt_currency(buyer_nw)),
        ("Home equity", _fmt_currency(buyer_equity)),
        ("Unrecoverable costs", _fmt_currency(buyer_unrec)),
        ("Assumed return", f"{_fmt_input_pct(buyer_ret_pct)}/yr"),
    ]
    detail_rows_rent = [
        ("Final net worth", _fmt_currency(renter_nw)),
        ("Unrecoverable costs", _fmt_currency(renter_unrec)),
        ("Assumed return", f"{_fmt_input_pct(renter_ret_pct)}/yr"),
        ("Monthly rent", _fmt_currency(cfg.get("rent"))),
    ]
    detail_cards_html = (
        "<div class='detail-grid'>"
        "<div class='detail-card'><div class='detail-title buy'>Buyer Detail Snapshot</div>"
        + "".join(f"<div class='detail-row'><span class='detail-key'>{html.escape(str(k))}</span><span class='detail-value'>{html.escape(str(v))}</span></div>" for k, v in detail_rows_buy)
        + "</div>"
        "<div class='detail-card'><div class='detail-title rent'>Renter Detail Snapshot</div>"
        + "".join(f"<div class='detail-row'><span class='detail-key'>{html.escape(str(k))}</span><span class='detail-value'>{html.escape(str(v))}</span></div>" for k, v in detail_rows_rent)
        + "</div></div>"
    )

    nw_chart_html = f"<img src='{nw_chart}' alt='Net worth chart' />" if nw_chart else "<div class='small-note'>Chart unavailable in this runtime.</div>"
    unrec_chart_html = f"<img src='{unrec_chart}' alt='Costs chart' />" if unrec_chart else "<div class='small-note'>Chart unavailable in this runtime.</div>"
    gap_chart_html = f"<img src='{gap_chart}' alt='Gap chart' />" if gap_chart else "<div class='small-note'>Chart unavailable in this runtime.</div>"
    buyer_band_chart_html = f"<img src='{buyer_band_chart}' alt='Buyer distribution chart' />" if buyer_band_chart else "<div class='small-note'>Distribution chart unavailable in this runtime.</div>"
    renter_band_chart_html = f"<img src='{renter_band_chart}' alt='Renter distribution chart' />" if renter_band_chart else "<div class='small-note'>Distribution chart unavailable in this runtime.</div>"

    trends_html = (
        detail_cards_html
        + "<div class='chart-grid'>"
        f"<div class='chart-card'><div class='chart-title'>Net worth trajectory</div><div class='chart-subtitle'>Uses the same buyer/renter series as the main dashboard.</div>{nw_chart_html}</div>"
        f"<div class='chart-card'><div class='chart-title'>Cumulative ongoing costs</div><div class='chart-subtitle'>Buyer vs renter running non-recoverable costs.</div>{unrec_chart_html}</div>"
        f"<div class='chart-card'><div class='chart-title'>Buyer advantage over time</div><div class='chart-subtitle'>Positive values favour buying; negative values favour renting.</div>{gap_chart_html}</div>"
        f"<div class='chart-card'><div class='chart-title'>Buyer net-worth distribution</div><div class='chart-subtitle'>Median with 5th–95th percentile band when Monte Carlo data is available.</div>{buyer_band_chart_html}</div>"
        f"<div class='chart-card'><div class='chart-title'>Renter net-worth distribution</div><div class='chart-subtitle'>Median with 5th–95th percentile band when Monte Carlo data is available.</div>{renter_band_chart_html}</div>"
        "</div>"
        f"<table><thead><tr><th>Milestone</th><th class='th-buy'>Buyer NW</th><th class='th-rent'>Renter NW</th><th>Home Equity</th><th>Buyer Advantage</th><th class='th-buy'>Buyer Costs</th><th class='th-rent'>Renter Costs</th></tr></thead><tbody>{milestone_rows}</tbody></table>"
    )


    scenario_inputs_html = (
        f"<div class='params-grid'>{input_html}"
        f"<div class='param-row'><span class='param-label'>Down Payment Share</span><span class='param-value'>{_fmt_pct((down / price * 100.0) if price else None)}</span></div>"
        f"<div class='param-row'><span class='param-label'>Cash to Close</span><span class='param-value'>{_fmt_currency(close_cash)}</span></div>"
        f"<div class='param-row'><span class='param-label'>Buyer Return</span><span class='param-value'>{_fmt_input_pct(buyer_ret_pct)}/yr</span></div>"
        f"<div class='param-row'><span class='param-label'>Renter Return</span><span class='param-value'>{_fmt_input_pct(renter_ret_pct)}/yr</span></div>"
        f"<div class='param-row'><span class='param-label'>Home Appreciation</span><span class='param-value'>{_fmt_input_pct(apprec_pct)}/yr</span></div>"
        "</div>"
    )

    bias_context_html = f"{bias_html}{bias_sens_html}" if (bias_html or bias_sens_html) else ""

    html_content = f"""<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'><title>Rent vs Buy Analysis</title></head><body>
<div class='report-header'><div class='report-title'>Rent vs Buy Analysis</div><div class='report-subtitle'>{html.escape(str(scenario_name))} · {province} · {years}-Year Horizon</div><div class='report-date'>Generated: {now}</div></div>
<p class='disclaimer'>Educational purposes only. Not financial, legal, or tax advice. Results depend on assumptions and will vary.</p>
<div class='verdict-box {verdict_cls}'>{html.escape(verdict_text)}</div>

{summary_html}

{confidence_html}

{methodology_html}

{data_notes_html}

{_render_section('Key Results', key_results_html)}

{_render_section('Trends & Milestones', trends_html)}

{_render_section('Scenario Inputs', scenario_inputs_html)}

{_render_section('Ongoing-Cost Context', _render_kv_table(ongoing_html))}

{_render_section('Bias & Sensitivity Context', bias_context_html) if bias_context_html else ''}

{context_html}

<div class='footer'>Generated by Rent vs Buy Simulator (Canada). Methodology: docs/METHODOLOGY.md</div>
</body></html>"""

    return HTML(string=html_content).write_pdf(stylesheets=[CSS(string=_PDF_CSS)])
