import re
from pathlib import Path

import pandas as pd

from rbv.ui import pdf_report
from rbv.ui.pdf_report import build_pdf_report


def _normalize_html(html: str) -> str:
    out = re.sub(r"Generated: [A-Za-z]+\s+\d{2},\s+\d{4}", "Generated: <DATE>", html)
    out = re.sub(r"\s+", " ", out).strip()
    return out


def test_build_pdf_report_html_snapshot(monkeypatch):
    captured = {"html": None}

    class _FakeHTML:
        def __init__(self, string):
            captured["html"] = string

        def write_pdf(self, stylesheets=None):
            return b"%PDF-fake"

    class _FakeCSS:
        def __init__(self, string):
            self.string = string

    monkeypatch.setattr(pdf_report, "_line_chart", lambda *a, **k: "data:image/png;base64,CHART")
    monkeypatch.setattr(pdf_report, "_single_line_chart", lambda *a, **k: "data:image/png;base64,GAP")
    monkeypatch.setattr(pdf_report, "HTML", _FakeHTML, raising=False)
    monkeypatch.setattr(pdf_report, "CSS", _FakeCSS, raising=False)

    # monkeypatch module import path used inside build_pdf_report
    import sys
    import types
    monkeypatch.setitem(sys.modules, "weasyprint", types.SimpleNamespace(HTML=_FakeHTML, CSS=_FakeCSS))

    df = pd.DataFrame(
        {
            "Year": [1, 2, 3],
            "Buyer Net Worth": [120_000, 140_000, 160_000],
            "Renter Net Worth": [110_000, 130_000, 145_000],
            "Buyer Home Equity": [40_000, 55_000, 70_000],
            "Buyer Unrecoverable": [8_000, 17_000, 25_000],
            "Renter Unrecoverable": [7_500, 16_000, 24_000],
        }
    )

    _ = build_pdf_report(
        df,
        {
            "years": 3,
            "province": "ON",
            "price": 800_000,
            "down": 160_000,
            "rate": 5.0,
            "rent": 2800,
            "p_tax_rate_pct": 1.0,
            "maint_rate_pct": 1.0,
            "repair_rate_pct": 0.5,
            "rent_inf": 2.5,
            "general_inf": 2.0,
        },
        scenario_name="Snapshot Scenario",
    )

    html = _normalize_html(captured["html"] or "")
    snap_path = Path("tests/snapshots/pdf_report_html_snapshot.txt")
    expected = snap_path.read_text(encoding='utf-8').strip()
    assert html == expected

