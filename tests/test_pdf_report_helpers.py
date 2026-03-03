import re
import sys
import types

import pandas as pd
import pytest

from rbv.ui.pdf_report import _PDF_CSS, _compact_input_rows, _fmt_input_pct, _time_axis_years, build_pdf_report


def test_fmt_input_pct_supports_fraction_and_percent_inputs():
    assert _fmt_input_pct(0.05) == "5.00%"
    assert _fmt_input_pct(5.0) == "5.00%"


def test_compact_input_rows_supports_live_session_aliases():
    rows = dict(
        _compact_input_rows(
            {
                "sell_cost_pct": 5,
                "p_tax_rate_pct": 1.1,
                "maint_rate_pct": 1.0,
                "repair_rate_pct": 0.5,
                "rent_inf": 2.5,
                "general_inf": 2.0,
            }
        )
    )
    assert rows["Selling costs"] == "5.00%"
    assert rows["Property tax"] == "1.10%"
    assert rows["Rent inflation"] == "2.50%"


def test_time_axis_years_uses_month_column_when_year_absent():
    df = pd.DataFrame({"Month": [12, 24, 36]})
    years = _time_axis_years(df)
    assert years.tolist() == [1.0, 2.0, 3.0]


def test_compact_input_rows_prefers_first_alias_and_avoids_duplicates():
    rows = _compact_input_rows(
        {
            "sell_cost_pct": 5,
            "selling_cost_pct": 4,
            "condo": 250,
            "condo_fee_monthly": 300,
            "h_ins": 120,
            "home_insurance_monthly": 200,
            "r_ins": 30,
            "rent_insurance_monthly": 40,
        }
    )
    labels = [k for k, _ in rows]
    assert labels.count("Selling costs") == 1
    assert labels.count("Condo fees") == 1
    assert labels.count("Home insurance") == 1
    assert labels.count("Renter insurance") == 1

    data = dict(rows)
    assert data["Selling costs"] == "5.00%"
    assert data["Condo fees"] == "$250"
    assert data["Home insurance"] == "$120"
    assert data["Renter insurance"] == "$30"


def test_line_chart_gracefully_falls_back_on_render_errors(monkeypatch):
    from rbv.ui import pdf_report

    def _boom(_df):
        raise RuntimeError("boom")

    monkeypatch.setattr(pdf_report, "_time_axis_years", _boom)
    df = pd.DataFrame({"Year": [1, 2], "a": [1, 2], "b": [2, 3]})
    out = pdf_report._line_chart(
        df,
        "title",
        pd.Series([1.0, 2.0]),
        pd.Series([2.0, 3.0]),
        "a",
        "b",
    )
    assert out == ""


def test_compact_input_rows_formats_moving_frequency_never_sentinel():
    rows = dict(_compact_input_rows({"moving_freq": 9999, "moving_cost": 1200}))
    assert rows["Moving frequency"] == "Never"
    assert rows["Moving cost / move"] == "$1,200"


def test_build_pdf_report_includes_ongoing_and_bias_sections(monkeypatch):
    captured = {"html": None}

    class _FakeHTML:
        def __init__(self, string):
            captured["html"] = string

        def write_pdf(self, stylesheets=None):
            return b"%PDF-fake"

    class _FakeCSS:
        def __init__(self, string):
            self.string = string

    fake_mod = types.SimpleNamespace(HTML=_FakeHTML, CSS=_FakeCSS)
    monkeypatch.setitem(sys.modules, "weasyprint", fake_mod)

    df = pd.DataFrame(
        {
            "Year": [1, 2, 3],
            "Buyer Net Worth": [10_000, 20_000, 30_000],
            "Renter Net Worth": [8_000, 19_000, 29_000],
            "Buyer Home Equity": [5_000, 10_000, 15_000],
            "Buyer Unrecoverable": [1_000, 2_000, 3_000],
            "Renter Unrecoverable": [900, 1_900, 2_800],
        }
    )
    cfg = {
        "price": 800_000,
        "down": 160_000,
        "years": 25,
        "province": "<Ontario>",
        "p_tax_rate_pct": 1.0,
        "maint_rate_pct": 1.0,
        "repair_rate_pct": 0.5,
        "rent_inf": 2.5,
        "general_inf": 2.0,
    }
    bias = {
        "base_val": 1000,
        "flip_rent": 3200,
        "flip_app": 4.0,
        "flip_rate": 5.5,
        "flip_renter_ret": 8.0,
        "adv_flips": {"Flip property tax": {"value": 1.4, "fmt": "pct"}},
        "sens_df": pd.DataFrame(
            [
                {
                    "Parameter": "Rent",
                    "Base": 3000,
                    "+ Step": 3200,
                    "- Step": 2800,
                    "Δ(+)": 100,
                    "Δ(-)": -100,
                }
            ]
        ),
    }

    out = build_pdf_report(
        df,
        cfg,
        scenario_name="A<script>",
        bias_result=bias,
        report_context={
            "meta": [("Scenario hash", "abc123")],
            "assumptions": [("Simulation mode", "Deterministic")],
            "compare": [("Compare metrics rows", "4")],
        },
    )
    assert out.startswith(b"%PDF")
    html = captured["html"] or ""
    assert "Ongoing-Cost Context" in html
    assert "Bias Sensitivity Drivers" in html
    assert "Assumptions &amp; Policy Snapshot" in html
    assert "A/B Compare Snapshot" in html
    assert "Executive Summary" in html
    assert "Buyer advantage over time" in html
    assert "Decision Confidence Snapshot" in html
    assert "&lt;Ontario&gt;" in html
    assert "A&lt;script&gt;" in html


def test_pdf_css_has_print_layout_tuning_rules():
    assert "orphans: 3" in _PDF_CSS
    assert "widows: 3" in _PDF_CSS
    assert "page-break-inside: avoid" in _PDF_CSS
    assert "page-break-after: avoid" in _PDF_CSS


def test_build_pdf_report_section_order_snapshot(monkeypatch):
    captured = {"html": None}

    class _FakeHTML:
        def __init__(self, string):
            captured["html"] = string

        def write_pdf(self, stylesheets=None):
            return b"%PDF-fake"

    class _FakeCSS:
        def __init__(self, string):
            self.string = string

    monkeypatch.setitem(sys.modules, "weasyprint", types.SimpleNamespace(HTML=_FakeHTML, CSS=_FakeCSS))

    df = pd.DataFrame({
        "Year": [1, 2],
        "Buyer Net Worth": [1000, 2000],
        "Renter Net Worth": [900, 1950],
        "Buyer Home Equity": [400, 800],
        "Buyer Unrecoverable": [100, 220],
        "Renter Unrecoverable": [80, 170],
    })

    _ = build_pdf_report(df, {"years": 2, "province": "ON", "price": 1, "down": 1})
    html = re.sub(r"\s+", " ", captured["html"] or "")

    markers = [
        "Executive Summary",
        "<h2>Key Results</h2>",
        "<h2>Trends & Milestones</h2>",
        "<h2>Scenario Inputs</h2>",
        "<h2>Ongoing-Cost Context</h2>",
    ]
    idx = [html.find(m) for m in markers]
    assert all(i >= 0 for i in idx)
    assert idx == sorted(idx)


def test_build_pdf_report_shows_data_availability_notes_when_charts_missing(monkeypatch):
    captured = {"html": None}

    class _FakeHTML:
        def __init__(self, string):
            captured["html"] = string

        def write_pdf(self, stylesheets=None):
            return b"%PDF-fake"

    class _FakeCSS:
        def __init__(self, string):
            self.string = string

    monkeypatch.setitem(sys.modules, "weasyprint", types.SimpleNamespace(HTML=_FakeHTML, CSS=_FakeCSS))
    from rbv.ui import pdf_report
    monkeypatch.setattr(pdf_report, "_line_chart", lambda *a, **k: "")
    monkeypatch.setattr(pdf_report, "_single_line_chart", lambda *a, **k: "")

    df = pd.DataFrame({
        "Year": [1, 2],
        "Buyer Net Worth": [1000, 1500],
        "Renter Net Worth": [900, 1400],
        "Buyer Home Equity": [300, 700],
        "Buyer Unrecoverable": [100, 220],
        "Renter Unrecoverable": [80, 180],
    })
    _ = build_pdf_report(df, {"years": 2, "province": "ON", "price": 1, "down": 1})
    html = captured["html"] or ""
    assert "Data Availability Notes" in html
    assert "could not be rendered" in html


@pytest.mark.parametrize(
    "buyer_last,renter_last,expected_class,expected_phrase",
    [
        (200_000, 120_000, "verdict-buy", "Buying appears advantageous"),
        (120_000, 200_000, "verdict-rent", "Renting appears advantageous"),
        (150_000, 151_000, "verdict-neutral", "Outcomes are approximately equal"),
    ],
)
def test_build_pdf_report_golden_verdict_snapshots(monkeypatch, buyer_last, renter_last, expected_class, expected_phrase):
    captured = {"html": None}

    class _FakeHTML:
        def __init__(self, string):
            captured["html"] = string

        def write_pdf(self, stylesheets=None):
            return b"%PDF-fake"

    class _FakeCSS:
        def __init__(self, string):
            self.string = string

    monkeypatch.setitem(sys.modules, "weasyprint", types.SimpleNamespace(HTML=_FakeHTML, CSS=_FakeCSS))

    df = pd.DataFrame(
        {
            "Year": [1, 2, 3],
            "Buyer Net Worth": [100_000, 150_000, buyer_last],
            "Renter Net Worth": [100_000, 140_000, renter_last],
            "Buyer Home Equity": [30_000, 50_000, 70_000],
            "Buyer Unrecoverable": [10_000, 20_000, 30_000],
            "Renter Unrecoverable": [9_000, 18_000, 28_000],
        }
    )

    _ = build_pdf_report(df, {"years": 3, "province": "ON", "price": 1, "down": 1}, scenario_name="Golden")
    html = re.sub(r"\s+", " ", captured["html"] or "")

    # Golden-ish structural assertions for representative buy/rent/tie outcomes.
    assert expected_class in html
    assert expected_phrase in html
    assert "Decision Confidence Snapshot" in html
    assert "<h2>Trends & Milestones</h2>" in html
    assert "<h2>Ongoing-Cost Context</h2>" in html
