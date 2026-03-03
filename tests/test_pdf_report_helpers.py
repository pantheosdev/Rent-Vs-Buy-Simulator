import pandas as pd

from rbv.ui.pdf_report import _compact_input_rows, _fmt_input_pct, _time_axis_years


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
