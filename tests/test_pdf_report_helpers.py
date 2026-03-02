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
