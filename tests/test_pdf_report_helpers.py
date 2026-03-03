import sys
import types

import pandas as pd

from rbv.ui.pdf_report import _compact_input_rows, _fmt_input_pct, _time_axis_years, build_pdf_report


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
    assert "&lt;Ontario&gt;" in html
    assert "A&lt;script&gt;" in html
