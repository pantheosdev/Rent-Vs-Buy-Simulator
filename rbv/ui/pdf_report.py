"""PDF report generation for the RBV Simulator.

Generates a branded, printable rent-vs-buy analysis report using WeasyPrint
to convert an HTML template to PDF.

This module has no Streamlit dependencies and can be used standalone or
called from app.py to produce a downloadable report.
"""

from __future__ import annotations

import datetime
from typing import Any

import pandas as pd

# ---------------------------------------------------------------------------
# CSS for the PDF report (dark fintech palette adapted for print)
# ---------------------------------------------------------------------------
_PDF_CSS = """
@page {
    size: A4;
    margin: 20mm 18mm 20mm 18mm;
}

* { box-sizing: border-box; }

body {
    font-family: "Segoe UI", Arial, Helvetica, sans-serif;
    font-size: 10pt;
    color: #1a2340;
    background: #fff;
    margin: 0;
}

.report-header {
    border-bottom: 3px solid #14D8FF;
    padding-bottom: 8px;
    margin-bottom: 16px;
}

.report-title {
    font-size: 20pt;
    font-weight: 700;
    color: #0B1020;
    margin: 0 0 4px 0;
}

.report-subtitle {
    font-size: 10pt;
    color: #4a5a7a;
    margin: 0;
}

.report-date {
    font-size: 8pt;
    color: #8a9ab0;
    text-align: right;
    margin-top: -28px;
}

.disclaimer {
    font-size: 7.5pt;
    color: #8a9ab0;
    border-left: 2px solid #e0e6ef;
    padding-left: 8px;
    margin-bottom: 14px;
    font-style: italic;
}

h2 {
    font-size: 12pt;
    font-weight: 700;
    color: #0B1020;
    border-bottom: 1px solid #d0d8e8;
    padding-bottom: 3px;
    margin: 16px 0 8px 0;
}

.kpi-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 12px;
}

.kpi-card {
    flex: 1 1 140px;
    border: 1px solid #d0d8e8;
    border-radius: 6px;
    padding: 8px 10px;
    background: #f7f9fc;
}

.kpi-label {
    font-size: 7.5pt;
    color: #5a6a8a;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 3px;
}

.kpi-value {
    font-size: 13pt;
    font-weight: 700;
    color: #0B1020;
}

.kpi-value.positive { color: #1a8a2e; }
.kpi-value.negative { color: #c0392b; }
.kpi-value.neutral  { color: #1460a8; }

table {
    width: 100%;
    border-collapse: collapse;
    font-size: 8.5pt;
    margin-bottom: 12px;
}

th {
    background: #0B1020;
    color: #E8EEF8;
    padding: 4px 8px;
    text-align: left;
    font-weight: 600;
}

td {
    padding: 3px 8px;
    border-bottom: 1px solid #e8ecf4;
}

tr:nth-child(even) td { background: #f4f7fb; }

.params-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}

.param-row {
    flex: 1 1 200px;
    display: flex;
    justify-content: space-between;
    border-bottom: 1px solid #e8ecf4;
    padding: 2px 0;
}

.param-label { color: #5a6a8a; }
.param-value { font-weight: 600; }

.verdict-box {
    border-radius: 6px;
    padding: 10px 14px;
    margin-bottom: 12px;
    font-size: 10.5pt;
    font-weight: 600;
}

.verdict-buy    { background: #e8f5eb; border-left: 4px solid #1a8a2e; color: #1a5c22; }
.verdict-rent   { background: #fef3e2; border-left: 4px solid #d68910; color: #7d510a; }
.verdict-neutral { background: #e8f0fb; border-left: 4px solid #1460a8; color: #0e3d70; }

.footer {
    font-size: 7pt;
    color: #aab8cc;
    text-align: center;
    margin-top: 24px;
    border-top: 1px solid #e0e6ef;
    padding-top: 6px;
}
"""


def _fmt_currency(val: float | None, decimals: int = 0) -> str:
    if val is None:
        return "—"
    try:
        if decimals == 0:
            return f"${float(val):,.0f}"
        return f"${float(val):,.{decimals}f}"
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
                return float(df[col].iloc[-1])
            except (IndexError, ValueError, TypeError):
                pass
    return default


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
) -> bytes:
    """Generate a PDF report from simulation results.

    Args:
        df: Simulation output DataFrame from run_simulation_core.
        cfg: Engine cfg dict used for the simulation.
        buyer_ret_pct: Buyer assumed investment return (%).
        renter_ret_pct: Renter assumed investment return (%).
        apprec_pct: Home appreciation rate (%).
        close_cash: Total cash outlay at closing ($).
        monthly_pmt: Monthly mortgage payment ($).
        win_pct: Percentage of MC simulations where buyer wins (None in deterministic mode).
        scenario_name: Display label for the scenario.

    Returns:
        PDF file content as bytes.
    """
    try:
        from weasyprint import CSS, HTML
    except ImportError as exc:
        raise RuntimeError(
            "weasyprint is required for PDF export. "
            "Install it with: pip install weasyprint"
        ) from exc

    price = cfg.get("price", 0.0)
    down = cfg.get("down", 0.0)
    years = cfg.get("years", 25)
    rate = cfg.get("rate", 0.0)
    province = cfg.get("province", "—")
    rent0 = cfg.get("rent", 0.0)

    # Extract final net-worth values from the simulation DataFrame
    buyer_nw = _safe_last(df, ["Buyer Net Worth", "Buyer NW", "buyer_nw"])
    renter_nw = _safe_last(df, ["Renter Net Worth", "Renter NW", "renter_nw"])
    buyer_equity = _safe_last(df, ["Buyer Home Equity", "Home Equity", "Equity"])
    delta = buyer_nw - renter_nw

    # Determine verdict
    if delta > 5_000:
        verdict_cls = "verdict-buy"
        verdict_text = f"Buying appears advantageous by {_fmt_currency(delta)} at the {years}-year horizon."
    elif delta < -5_000:
        verdict_cls = "verdict-rent"
        verdict_text = f"Renting appears advantageous by {_fmt_currency(abs(delta))} at the {years}-year horizon."
    else:
        verdict_cls = "verdict-neutral"
        verdict_text = f"Outcomes are approximately equal at the {years}-year horizon (Δ = {_fmt_currency(abs(delta))})."

    # Build a milestone table (every 5 years or at horizon)
    milestones: list[dict] = []
    month_col = "Month" if "Month" in df.columns else df.columns[0]
    for y in list(range(5, years, 5)) + [years]:
        target_month = y * 12
        subset = df[df[month_col] <= target_month]
        if subset.empty:
            continue
        row = subset.iloc[-1]
        milestones.append({
            "year": y,
            "buyer_nw": _safe_last(subset, ["Buyer Net Worth", "Buyer NW"]),
            "renter_nw": _safe_last(subset, ["Renter Net Worth", "Renter NW"]),
            "equity": _safe_last(subset, ["Buyer Home Equity", "Home Equity"]),
        })

    milestone_rows = "".join(
        f"<tr>"
        f"<td>Year {m['year']}</td>"
        f"<td>{_fmt_currency(m['buyer_nw'])}</td>"
        f"<td>{_fmt_currency(m['renter_nw'])}</td>"
        f"<td>{_fmt_currency(m['equity'])}</td>"
        f"<td style='font-weight:600;color:{'#1a8a2e' if m['buyer_nw'] >= m['renter_nw'] else '#c0392b'}'>"
        f"{_fmt_currency(m['buyer_nw'] - m['renter_nw'])}</td>"
        f"</tr>"
        for m in milestones
    )

    win_display = _fmt_pct(win_pct) if win_pct is not None else "Deterministic"
    delta_cls = "positive" if delta > 0 else ("negative" if delta < 0 else "neutral")
    now = datetime.date.today().strftime("%B %d, %Y")

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Rent vs Buy Analysis — {scenario_name}</title>
</head>
<body>

<div class="report-header">
  <div class="report-title">Rent vs Buy Analysis</div>
  <div class="report-subtitle">{scenario_name} · {province} · {years}-Year Horizon</div>
  <div class="report-date">Generated: {now}</div>
</div>

<p class="disclaimer">
  Educational purposes only. Not financial, legal, or tax advice.
  Results depend on assumptions; actual outcomes will vary.
</p>

<div class="verdict-box {verdict_cls}">{verdict_text}</div>

<h2>Key Results</h2>
<div class="kpi-grid">
  <div class="kpi-card">
    <div class="kpi-label">Final Buyer Net Worth</div>
    <div class="kpi-value neutral">{_fmt_currency(buyer_nw)}</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Final Renter Net Worth</div>
    <div class="kpi-value neutral">{_fmt_currency(renter_nw)}</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Buyer Advantage (Δ)</div>
    <div class="kpi-value {delta_cls}">{_fmt_currency(delta)}</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Home Equity at Horizon</div>
    <div class="kpi-value neutral">{_fmt_currency(buyer_equity)}</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Monthly Payment</div>
    <div class="kpi-value neutral">{_fmt_currency(monthly_pmt)}</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Buyer Win Rate (MC)</div>
    <div class="kpi-value neutral">{win_display}</div>
  </div>
</div>

<h2>Net Worth Over Time</h2>
<table>
  <thead>
    <tr>
      <th>Milestone</th>
      <th>Buyer NW</th>
      <th>Renter NW</th>
      <th>Home Equity</th>
      <th>Buyer Advantage</th>
    </tr>
  </thead>
  <tbody>
    {milestone_rows}
  </tbody>
</table>

<h2>Scenario Inputs</h2>
<div class="params-grid">
  <div class="param-row">
    <span class="param-label">Home Price</span>
    <span class="param-value">{_fmt_currency(price)}</span>
  </div>
  <div class="param-row">
    <span class="param-label">Down Payment</span>
    <span class="param-value">{_fmt_currency(down)} ({_fmt_pct(down / price * 100) if price else '—'})</span>
  </div>
  <div class="param-row">
    <span class="param-label">Mortgage Rate</span>
    <span class="param-value">{_fmt_pct(rate)} (semi-annual compounding)</span>
  </div>
  <div class="param-row">
    <span class="param-label">Monthly Rent</span>
    <span class="param-value">{_fmt_currency(rent0)}/mo</span>
  </div>
  <div class="param-row">
    <span class="param-label">Cash to Close</span>
    <span class="param-value">{_fmt_currency(close_cash)}</span>
  </div>
  <div class="param-row">
    <span class="param-label">Province</span>
    <span class="param-value">{province}</span>
  </div>
  <div class="param-row">
    <span class="param-label">Horizon</span>
    <span class="param-value">{years} years</span>
  </div>
  <div class="param-row">
    <span class="param-label">Home Appreciation</span>
    <span class="param-value">{_fmt_pct(apprec_pct)}/yr</span>
  </div>
  <div class="param-row">
    <span class="param-label">Buyer Investment Return</span>
    <span class="param-value">{_fmt_pct(buyer_ret_pct)}/yr</span>
  </div>
  <div class="param-row">
    <span class="param-label">Renter Investment Return</span>
    <span class="param-value">{_fmt_pct(renter_ret_pct)}/yr</span>
  </div>
</div>

<div class="footer">
  Generated by Rent vs Buy Simulator (Canada) · https://rent-vs-buy-canada.streamlit.app/
  <br>For educational purposes only. Methodology: docs/METHODOLOGY.md
</div>

</body>
</html>"""

    pdf_bytes: bytes = HTML(string=html_content).write_pdf(
        stylesheets=[CSS(string=_PDF_CSS)],
    )
    return pdf_bytes
