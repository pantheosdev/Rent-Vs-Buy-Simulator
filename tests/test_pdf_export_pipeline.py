import pandas as pd

from rbv.ui.pdf_export import build_report_context, finalize_pdf_with_fallback, try_build_rich_pdf


def _df():
    return pd.DataFrame(
        {
            "Year": [1, 2],
            "Buyer Net Worth": [1000, 1200],
            "Renter Net Worth": [900, 1100],
            "Buyer Home Equity": [300, 500],
            "Buyer Unrecoverable": [100, 200],
            "Renter Unrecoverable": [80, 180],
        }
    )


def test_build_report_context_includes_compare_when_present():
    ctx = build_report_context(
        {"first_time": True, "sim_mode": "Deterministic", "num_sims": 1},
        {"scenario_hash": "abc"},
        compare_export={"metrics_rows": [1, 2], "state_diff_rows": [1], "meta": {"a_hash": "A", "b_hash": "B"}},
        version_line="v1",
        generated_at="2025-01-01 00:00:00",
    )
    assert "meta" in ctx and "assumptions" in ctx and "compare" in ctx
    assert ("Scenario hash", "abc") in ctx["meta"]


def test_try_build_rich_pdf_success_path_returns_bytes():
    def _builder(df, cfg, **kwargs):
        assert cfg["rent_inf"] == 2.5
        assert kwargs["report_context"]["meta"]
        return b"%PDF-ok"

    out, warn = try_build_rich_pdf(
        _df(),
        {"years": 2, "province": "ON", "rent_inf": 2.5, "scenario_select": "X"},
        {"scenario_hash": "h"},
        compare_export=None,
        version_line="v1",
        generated_at="2025-01-01 00:00:00",
        bias_result=None,
        close_cash=None,
        monthly_pmt=None,
        win_pct=None,
        build_pdf_report=_builder,
    )
    assert out == b"%PDF-ok"
    assert warn is None


def test_try_build_rich_pdf_failure_path_returns_warning():
    def _builder(*_a, **_k):
        raise RuntimeError("boom")

    out, warn = try_build_rich_pdf(
        _df(),
        {"years": 2, "province": "ON"},
        {"scenario_hash": "h"},
        compare_export=None,
        version_line="v1",
        generated_at="2025-01-01 00:00:00",
        bias_result=None,
        close_cash=None,
        monthly_pmt=None,
        win_pct=None,
        build_pdf_report=_builder,
    )
    assert out is None
    assert "Rich PDF renderer failed" in str(warn)


def test_finalize_pdf_with_fallback_success_records_warning():
    sink: dict[str, str] = {}

    def _legacy():
        return b"%PDF-fallback"

    out, err = finalize_pdf_with_fallback(
        rich_warning="Rich PDF renderer failed: x",
        legacy_builder=_legacy,
        warning_sink=lambda m: sink.setdefault("w", m),
    )
    assert out == b"%PDF-fallback"
    assert err is None
    assert sink.get("w") == "Rich PDF renderer failed: x"


def test_finalize_pdf_with_fallback_failure_includes_rich_context():
    def _legacy():
        raise RuntimeError("legacy boom")

    out, err = finalize_pdf_with_fallback(
        rich_warning="Rich PDF renderer failed: x",
        legacy_builder=_legacy,
    )
    assert out is None
    assert "fallback attempted after" in str(err)
