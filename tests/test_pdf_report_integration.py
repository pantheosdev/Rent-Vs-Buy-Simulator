import pandas as pd
import pytest

from rbv.ui.pdf_report import build_pdf_report


def test_build_pdf_report_real_weasyprint_smoke():
    pytest.importorskip("weasyprint")
    pytest.importorskip("matplotlib")

    df = pd.DataFrame(
        {
            "Year": [1, 2, 3],
            "Buyer Net Worth": [100_000, 120_000, 145_000],
            "Renter Net Worth": [95_000, 110_000, 130_000],
            "Buyer Home Equity": [30_000, 45_000, 60_000],
            "Buyer Unrecoverable": [8_000, 15_000, 23_000],
            "Renter Unrecoverable": [7_500, 14_000, 21_000],
        }
    )

    pdf_bytes = build_pdf_report(
        df,
        {
            "years": 3,
            "province": "ON",
            "price": 700_000,
            "down": 140_000,
            "rate": 5.2,
            "rent": 2600,
            "p_tax_rate_pct": 1.0,
            "maint_rate_pct": 1.0,
            "repair_rate_pct": 0.5,
            "sell_cost_pct": 5.0,
            "rent_inf": 2.5,
            "general_inf": 2.0,
        },
        scenario_name="Integration Smoke",
    )

    assert isinstance(pdf_bytes, (bytes, bytearray))
    assert bytes(pdf_bytes).startswith(b"%PDF")
    assert len(pdf_bytes) > 1500
