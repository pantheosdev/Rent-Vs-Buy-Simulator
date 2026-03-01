"""Coverage phase 2 — fills gaps identified after the phase-1 audit run.

Targets:
  scenario_snapshots.py  (0% → covered)
  validation.py          (36% → covered)
  mortgage.py            (65% → covered)
  policy_canada.py       (67% → covered)
  government_programs.py (77% → covered)
  taxes.py               (64% → covered)
  equity_monitor.py      (98% → 100%)
  costs_utils.py         (0% → covered)
"""

from __future__ import annotations

import datetime as dt
import math
import warnings

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# scenario_snapshots.py
# ---------------------------------------------------------------------------
from rbv.core.scenario_snapshots import (
    ScenarioConfig,
    ScenarioSnapshot,
    _filter_state,
    _normalize_float,
    _to_float_or_none,
    build_compare_export_payload,
    build_scenario_config,
    build_scenario_snapshot,
    canonicalize_jsonish,
    compare_metric_rows,
    compare_metric_rows_to_csv_text,
    extract_terminal_metrics,
    parse_scenario_payload,
    rows_to_csv_text,
    scenario_hash_from_state,
    scenario_state_diff_rows,
    scenario_state_diff_rows_to_csv_text,
)


class TestNormalizeFloat:
    def test_integer_return(self) -> None:
        assert _normalize_float(3.0) == 3
        assert isinstance(_normalize_float(3.0), int)

    def test_float_return(self) -> None:
        v = _normalize_float(3.14)
        assert isinstance(v, float)
        assert v == pytest.approx(3.14)

    def test_signed_zero_collapsed(self) -> None:
        assert _normalize_float(-0.0) == 0.0

    def test_tiny_value_collapsed_to_zero(self) -> None:
        assert _normalize_float(1e-16) == 0

    def test_nan_returns_none(self) -> None:
        assert _normalize_float(float("nan")) is None

    def test_inf_returns_none(self) -> None:
        assert _normalize_float(float("inf")) is None

    def test_negative_inf_returns_none(self) -> None:
        assert _normalize_float(float("-inf")) is None

    def test_exception_returns_none(self) -> None:
        assert _normalize_float("not-a-number") is None  # type: ignore[arg-type]


class TestCanonicalizeJsonish:
    def test_none(self) -> None:
        assert canonicalize_jsonish(None) is None

    def test_string(self) -> None:
        assert canonicalize_jsonish("hello") == "hello"

    def test_bool_true(self) -> None:
        assert canonicalize_jsonish(True) is True

    def test_bool_false(self) -> None:
        assert canonicalize_jsonish(False) is False

    def test_int(self) -> None:
        result = canonicalize_jsonish(42)
        assert result == 42
        assert isinstance(result, int)

    def test_float(self) -> None:
        result = canonicalize_jsonish(3.14)
        assert isinstance(result, float)

    def test_float_nan_returns_none(self) -> None:
        assert canonicalize_jsonish(float("nan")) is None

    def test_datetime(self) -> None:
        d = dt.datetime(2025, 1, 15, 10, 30, 0)
        result = canonicalize_jsonish(d)
        assert "2025-01-15" in result

    def test_date(self) -> None:
        d = dt.date(2025, 6, 1)
        result = canonicalize_jsonish(d)
        assert result == "2025-06-01"

    def test_dict_sorted_keys(self) -> None:
        result = canonicalize_jsonish({"z": 1, "a": 2})
        assert list(result.keys()) == ["a", "z"]

    def test_list(self) -> None:
        result = canonicalize_jsonish([3, 1, 2])
        assert result == [3, 1, 2]

    def test_tuple(self) -> None:
        result = canonicalize_jsonish((1, 2, 3))
        assert result == [1, 2, 3]

    def test_set_sorted(self) -> None:
        result = canonicalize_jsonish({3, 1, 2})
        assert isinstance(result, list)
        assert sorted(result) == sorted(result)

    def test_object_with_isoformat(self) -> None:
        class FakeTimestamp:
            def isoformat(self) -> str:
                return "2025-03-01T00:00:00"

        result = canonicalize_jsonish(FakeTimestamp())
        assert result == "2025-03-01T00:00:00"

    def test_json_serializable_object(self) -> None:
        result = canonicalize_jsonish({"key": [1, 2]})
        assert result == {"key": [1, 2]}

    def test_unknown_type_stringified(self) -> None:
        class Weird:
            def __str__(self) -> str:
                return "weird_obj"

        result = canonicalize_jsonish(Weird())
        assert result == "weird_obj"


class TestFilterState:
    def test_non_dict_returns_empty(self) -> None:
        assert _filter_state(None) == {}  # type: ignore[arg-type]
        assert _filter_state("string") == {}  # type: ignore[arg-type]

    def test_no_allowed_keys_returns_all(self) -> None:
        state = {"a": 1, "b": 2}
        assert _filter_state(state) == {"a": 1, "b": 2}

    def test_allowed_keys_filters(self) -> None:
        state = {"a": 1, "b": 2, "c": 3}
        result = _filter_state(state, allowed_keys=["a", "c"])
        assert result == {"a": 1, "c": 3}
        assert "b" not in result


class TestScenarioConfig:
    def test_from_state_basic(self) -> None:
        cfg = ScenarioConfig.from_state({"price": 800_000, "down": 160_000})
        assert cfg.state["price"] == 800_000

    def test_from_state_with_allowed_keys(self) -> None:
        cfg = ScenarioConfig.from_state({"price": 800_000, "down": 160_000}, allowed_keys=["price"])
        assert "price" in cfg.state
        assert "down" not in cfg.state

    def test_canonical_state_is_dict(self) -> None:
        cfg = ScenarioConfig(state={"price": 800_000.0})
        cs = cfg.canonical_state
        assert isinstance(cs, dict)

    def test_canonical_json_is_deterministic(self) -> None:
        cfg1 = ScenarioConfig(state={"b": 2, "a": 1})
        cfg2 = ScenarioConfig(state={"a": 1, "b": 2})
        assert cfg1.canonical_json() == cfg2.canonical_json()

    def test_deterministic_hash_length(self) -> None:
        cfg = ScenarioConfig(state={"price": 500_000})
        h = cfg.deterministic_hash()
        assert len(h) == 64  # sha256 hex

    def test_to_dict_keys(self) -> None:
        cfg = ScenarioConfig(state={"price": 500_000})
        d = cfg.to_dict()
        assert "schema" in d
        assert "state" in d
        assert "hash" in d

    def test_from_payload_nested_config(self) -> None:
        payload = {"config": {"state": {"price": 700_000}, "schema": "rbv.scenario_config.v1"}}
        cfg = ScenarioConfig.from_payload(payload)
        assert cfg.state.get("price") == 700_000

    def test_from_payload_state_dict(self) -> None:
        payload = {"state": {"price": 600_000}, "schema": "rbv.scenario_config.v1"}
        cfg = ScenarioConfig.from_payload(payload)
        assert cfg.state.get("price") == 600_000

    def test_from_payload_bare_dict(self) -> None:
        """Back-compat: bare dict treated as state."""
        payload = {"price": 500_000, "down": 100_000}
        cfg = ScenarioConfig.from_payload(payload)
        assert cfg.state.get("price") == 500_000

    def test_from_payload_none(self) -> None:
        cfg = ScenarioConfig.from_payload(None)
        assert isinstance(cfg.state, dict)


class TestScenarioSnapshot:
    def test_basic_construction(self) -> None:
        cfg = ScenarioConfig(state={"price": 800_000})
        snap = ScenarioSnapshot(config=cfg)
        assert snap.slot == "active"

    def test_scenario_hash(self) -> None:
        cfg = ScenarioConfig(state={"price": 800_000})
        snap = ScenarioSnapshot(config=cfg)
        assert len(snap.scenario_hash) == 64

    def test_to_dict_keys(self) -> None:
        cfg = ScenarioConfig(state={"price": 800_000})
        snap = ScenarioSnapshot(config=cfg, label="Base case")
        d = snap.to_dict()
        assert "schema" in d
        assert "config" in d
        assert "state" in d
        assert "scenario_hash" in d
        assert d["label"] == "Base case"

    def test_from_payload_full(self) -> None:
        payload = {
            "state": {"price": 650_000},
            "slot": "compare_a",
            "label": "Test",
            "version": "2.93.7",
            "meta": {"city": "Toronto"},
        }
        snap = ScenarioSnapshot.from_payload(payload)
        assert snap.slot == "compare_a"
        assert snap.label == "Test"
        assert snap.version == "2.93.7"
        assert snap.meta.get("city") == "Toronto"

    def test_from_payload_none(self) -> None:
        snap = ScenarioSnapshot.from_payload(None)
        assert snap.slot == "active"

    def test_from_payload_config_as_raw_dict(self) -> None:
        """ScenarioSnapshot.__post_init__ handles config that is not a ScenarioConfig instance."""
        payload = {"config": {"state": {"price": 500_000}}, "slot": "active"}
        snap = ScenarioSnapshot.from_payload(payload)
        assert isinstance(snap.config, ScenarioConfig)


class TestBuildHelpers:
    def test_build_scenario_config(self) -> None:
        cfg = build_scenario_config({"price": 900_000})
        assert isinstance(cfg, ScenarioConfig)

    def test_scenario_hash_from_state_stable(self) -> None:
        h1 = scenario_hash_from_state({"a": 1, "b": 2})
        h2 = scenario_hash_from_state({"b": 2, "a": 1})
        assert h1 == h2

    def test_build_scenario_snapshot(self) -> None:
        snap = build_scenario_snapshot(
            {"price": 700_000},
            slot="compare_b",
            label="Scenario B",
            version="2.93.7",
            meta={"region": "Vancouver"},
        )
        assert isinstance(snap, ScenarioSnapshot)
        assert snap.slot == "compare_b"
        assert snap.label == "Scenario B"


class TestToFloatOrNone:
    def test_valid(self) -> None:
        assert _to_float_or_none(3.14) == pytest.approx(3.14)

    def test_nan_returns_none(self) -> None:
        assert _to_float_or_none(float("nan")) is None

    def test_inf_returns_none(self) -> None:
        assert _to_float_or_none(float("inf")) is None

    def test_exception_returns_none(self) -> None:
        assert _to_float_or_none("bad") is None

    def test_string_number(self) -> None:
        assert _to_float_or_none("42.5") == pytest.approx(42.5)


class TestExtractTerminalMetrics:
    def test_none_df(self) -> None:
        m = extract_terminal_metrics(None)
        assert m["buyer_nw_final"] is None
        assert m["renter_nw_final"] is None

    def test_empty_df(self) -> None:
        df = pd.DataFrame()
        m = extract_terminal_metrics(df)
        assert m["buyer_nw_final"] is None

    def test_valid_df(self) -> None:
        df = pd.DataFrame({
            "Month": range(1, 13),
            "Buyer Net Worth": [i * 1000 for i in range(1, 13)],
            "Renter Net Worth": [i * 900 for i in range(1, 13)],
            "Buyer PV NW": [i * 950 for i in range(1, 13)],
            "Renter PV NW": [i * 850 for i in range(1, 13)],
            "Buyer Unrecoverable": [500.0] * 12,
            "Renter Unrecoverable": [300.0] * 12,
        })
        m = extract_terminal_metrics(df, close_cash=50_000, monthly_payment=2500, win_pct=65.0)
        assert m["buyer_nw_final"] == pytest.approx(12_000)
        assert m["renter_nw_final"] == pytest.approx(10_800)
        assert m["advantage_final"] == pytest.approx(1_200)
        assert m["close_cash"] == pytest.approx(50_000)
        assert m["monthly_payment"] == pytest.approx(2500)
        assert m["win_pct"] == pytest.approx(65.0)
        assert m["pv_advantage_final"] is not None


class TestCompareMetricRows:
    def test_both_none(self) -> None:
        rows = compare_metric_rows(None, None)
        assert len(rows) > 0
        for r in rows:
            assert r["a"] is None
            assert r["b"] is None

    def test_delta_computed(self) -> None:
        a = {"buyer_nw_final": 100_000.0}
        b = {"buyer_nw_final": 120_000.0}
        rows = compare_metric_rows(a, b)
        buyer_row = next(r for r in rows if r["metric"] == "Final Buyer Net Worth")
        assert buyer_row["delta"] == pytest.approx(20_000.0)
        assert buyer_row["pct_delta"] == pytest.approx(20.0)

    def test_tiny_delta_collapsed_to_zero(self) -> None:
        a = {"buyer_nw_final": 100_000.0}
        b = {"buyer_nw_final": 100_000.0 + 1e-12}
        rows = compare_metric_rows(a, b)
        buyer_row = next(r for r in rows if r["metric"] == "Final Buyer Net Worth")
        assert buyer_row["delta"] == pytest.approx(0.0)

    def test_zero_a_nonzero_delta_pct_none_or_zero(self) -> None:
        a = {"buyer_nw_final": 0.0}
        b = {"buyer_nw_final": 0.0}
        rows = compare_metric_rows(a, b)
        buyer_row = next(r for r in rows if r["metric"] == "Final Buyer Net Worth")
        assert buyer_row["pct_delta"] == pytest.approx(0.0)


class TestScenarioStateDiffRows:
    def test_identical_states_empty(self) -> None:
        rows = scenario_state_diff_rows({"a": 1, "b": 2}, {"a": 1, "b": 2})
        assert rows == []

    def test_changed_values(self) -> None:
        rows = scenario_state_diff_rows({"price": 700_000}, {"price": 800_000})
        assert len(rows) == 1
        assert rows[0]["key"] == "price"

    def test_tiny_float_noise_ignored(self) -> None:
        rows = scenario_state_diff_rows({"rate": 5.0}, {"rate": 5.0 + 1e-12})
        assert rows == []

    def test_added_key(self) -> None:
        rows = scenario_state_diff_rows({"a": 1}, {"a": 1, "b": 2})
        assert any(r["key"] == "b" for r in rows)


class TestParseScenarioPayload:
    def test_v1_payload(self) -> None:
        payload = {
            "state": {"price": 750_000},
            "slot": "active",
            "schema": "rbv.scenario_snapshot.v1",
            "version": "2.93.7",
            "meta": {"preset": "Vancouver"},
        }
        state, meta = parse_scenario_payload(payload)
        assert state.get("price") == 750_000
        assert meta["slot"] == "active"
        assert "scenario_hash" in meta
        assert meta.get("preset") == "Vancouver"  # lifted from payload_meta

    def test_none_payload(self) -> None:
        state, meta = parse_scenario_payload(None)
        assert isinstance(state, dict)
        assert isinstance(meta, dict)


class TestRowsToCsvText:
    def test_empty(self) -> None:
        result = rows_to_csv_text([])
        assert result.strip() == ""

    def test_basic_rows(self) -> None:
        rows = [{"metric": "Net Worth", "a": 100_000, "b": 120_000}]
        result = rows_to_csv_text(rows)
        assert "Net Worth" in result
        assert "metric" in result

    def test_explicit_columns(self) -> None:
        rows = [{"metric": "NW", "a": 1, "b": 2, "extra": 99}]
        result = rows_to_csv_text(rows, columns=["metric", "a", "b"])
        assert "extra" not in result

    def test_dict_value_serialized_as_json(self) -> None:
        rows = [{"key": "x", "val": {"nested": True}}]
        result = rows_to_csv_text(rows)
        assert "nested" in result

    def test_compare_metric_rows_to_csv_text(self) -> None:
        rows = compare_metric_rows({"buyer_nw_final": 100_000}, {"buyer_nw_final": 110_000})
        csv = compare_metric_rows_to_csv_text(rows)
        assert "metric" in csv

    def test_scenario_state_diff_rows_to_csv_text(self) -> None:
        rows = scenario_state_diff_rows({"price": 500_000}, {"price": 600_000})
        csv = scenario_state_diff_rows_to_csv_text(rows)
        assert "key" in csv


class TestBuildCompareExportPayload:
    def test_structure(self) -> None:
        payload_a = {"state": {"price": 500_000}}
        payload_b = {"state": {"price": 600_000}}
        metric_rows = compare_metric_rows({}, {})
        diff_rows = scenario_state_diff_rows({"price": 500_000}, {"price": 600_000})
        result = build_compare_export_payload(
            payload_a=payload_a,
            payload_b=payload_b,
            metric_rows=metric_rows,
            state_diff_rows=diff_rows,
            meta={"session": "test"},
        )
        assert result["schema"] == "rbv.compare_export.v1"
        assert "exported_at" in result
        assert "A" in result["snapshots"]
        assert "B" in result["snapshots"]
        assert isinstance(result["metrics"], list)
        assert isinstance(result["state_diffs"], list)

    def test_none_inputs(self) -> None:
        result = build_compare_export_payload(
            payload_a=None,
            payload_b=None,
            metric_rows=None,
            state_diff_rows=None,
        )
        assert result["schema"] == "rbv.compare_export.v1"


# ---------------------------------------------------------------------------
# validation.py
# ---------------------------------------------------------------------------
from rbv.core.validation import (
    _coerce_date,
    clamp_positive,
    clamp_rate,
    get_validation_warnings,
)


class TestCoerceDate:
    def test_date_passthrough(self) -> None:
        d = dt.date(2025, 6, 1)
        assert _coerce_date(d) == d

    def test_iso_string(self) -> None:
        result = _coerce_date("2025-06-01")
        assert result == dt.date(2025, 6, 1)

    def test_iso_timestamp_sliced(self) -> None:
        result = _coerce_date("2025-06-01T10:30:00")
        assert result == dt.date(2025, 6, 1)

    def test_invalid_string_returns_today(self) -> None:
        result = _coerce_date("not-a-date")
        assert isinstance(result, dt.date)

    def test_none_returns_today(self) -> None:
        result = _coerce_date(None)
        assert isinstance(result, dt.date)


class TestGetValidationWarnings:
    _BASE = {
        "price": 800_000.0,
        "down": 160_000.0,
        "nm": 300,
        "asof_date": dt.date(2025, 1, 1),
        "first_time_buyer": False,
        "new_construction": False,
    }

    def test_valid_config_no_warnings(self) -> None:
        result = get_validation_warnings(self._BASE)
        assert result == []

    def test_high_ltv_warning(self) -> None:
        cfg = {**self._BASE, "price": 500_000.0, "down": 10_000.0}  # LTV = 98%
        result = get_validation_warnings(cfg)
        assert any("LTV" in w or "loan-to-value" in w.lower() for w in result)

    def test_min_down_payment_warning(self) -> None:
        # Price $400k, min down = 5% = $20k; provide $5k
        cfg = {**self._BASE, "price": 400_000.0, "down": 5_000.0}
        result = get_validation_warnings(cfg)
        assert any("minimum" in w.lower() or "down payment" in w.lower() for w in result)

    def test_insured_amortization_warning_ftb_required(self) -> None:
        # LTV > 80%, amort 30yr, pre-Dec 2024 (no 30yr allowed)
        cfg = {
            "price": 600_000.0,
            "down": 90_000.0,  # 15% down → LTV 85%
            "nm": 360,  # 30 years
            "asof_date": dt.date(2024, 1, 1),  # pre_2024_08_01 → max 25
            "first_time_buyer": False,
            "new_construction": False,
        }
        result = get_validation_warnings(cfg)
        assert any("amortization" in w.lower() for w in result)

    def test_no_warning_for_conventional_high_amort(self) -> None:
        # LTV <= 80% → no insurance required → no amortization warning
        cfg = {**self._BASE, "nm": 360}  # 30 yr, but 20% down so conventional
        result = get_validation_warnings(cfg)
        assert not any("amortization" in w.lower() for w in result)

    def test_missing_nm_skips_amort_check(self) -> None:
        cfg = {**self._BASE}
        del cfg["nm"]
        result = get_validation_warnings(cfg)
        assert isinstance(result, list)

    def test_invalid_price_clamped(self) -> None:
        cfg = {**self._BASE, "price": "bad", "down": 0}
        result = get_validation_warnings(cfg)
        assert isinstance(result, list)

    def test_ftb_flag_prevents_amort_warning_post_dec2024(self) -> None:
        cfg = {
            "price": 600_000.0,
            "down": 90_000.0,
            "nm": 360,
            "asof_date": dt.date(2025, 1, 1),  # ftb_or_new_build → 30yr OK for FTB
            "first_time_buyer": True,
            "new_construction": False,
        }
        result = get_validation_warnings(cfg)
        assert not any("amortization" in w.lower() for w in result)

    def test_new_build_flag_prevents_amort_warning_post_dec2024(self) -> None:
        cfg = {
            "price": 600_000.0,
            "down": 90_000.0,
            "nm": 360,
            "asof_date": dt.date(2025, 1, 1),
            "first_time_buyer": False,
            "new_construction": True,
        }
        result = get_validation_warnings(cfg)
        assert not any("amortization" in w.lower() for w in result)


class TestClampHelpers:
    def test_clamp_rate_above_max(self) -> None:
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = clamp_rate(99.0, "rate", min_val=0.0, max_val=25.0)
        assert result == pytest.approx(25.0)

    def test_clamp_rate_below_min(self) -> None:
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = clamp_rate(-5.0, "rate", min_val=0.0, max_val=25.0)
        assert result == pytest.approx(0.0)

    def test_clamp_rate_in_range(self) -> None:
        result = clamp_rate(5.0, "rate", min_val=0.0, max_val=25.0)
        assert result == pytest.approx(5.0)

    def test_clamp_positive_negative(self) -> None:
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = clamp_positive(-100.0, "val")
        assert result == pytest.approx(0.0)

    def test_clamp_positive_above_max(self) -> None:
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = clamp_positive(500.0, "val", max_val=100.0)
        assert result == pytest.approx(100.0)

    def test_clamp_positive_in_range(self) -> None:
        result = clamp_positive(50.0, "val", max_val=100.0)
        assert result == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# mortgage.py
# ---------------------------------------------------------------------------
from rbv.core.mortgage import (
    _annual_nominal_pct_to_monthly_rate,
    _monthly_rate_to_annual_nominal_pct,
    ird_penalty_for_simulation,
    ird_prepayment_penalty,
)


class TestAnnualToMonthlyEdgeCases:
    def test_nan_input_returns_zero_rate(self) -> None:
        result = _annual_nominal_pct_to_monthly_rate(float("nan"), canadian=True)
        assert math.isfinite(result)

    def test_inf_input_returns_finite(self) -> None:
        result = _annual_nominal_pct_to_monthly_rate(float("inf"), canadian=True)
        assert math.isfinite(result)

    def test_very_negative_canadian_clamps(self) -> None:
        # Very large negative rate: base = 1 + r/2 <= 0, should clamp
        result = _annual_nominal_pct_to_monthly_rate(-300.0, canadian=True)
        assert result >= -1.0


class TestMonthlyToAnnual:
    def test_roundtrip_canadian(self) -> None:
        mr = _annual_nominal_pct_to_monthly_rate(5.0, canadian=True)
        back = _monthly_rate_to_annual_nominal_pct(mr, canadian=True)
        assert back == pytest.approx(5.0, rel=1e-8)

    def test_roundtrip_us(self) -> None:
        mr = _annual_nominal_pct_to_monthly_rate(5.0, canadian=False)
        back = _monthly_rate_to_annual_nominal_pct(mr, canadian=False)
        assert back == pytest.approx(5.0, rel=1e-8)

    def test_nan_input(self) -> None:
        result = _monthly_rate_to_annual_nominal_pct(float("nan"), canadian=True)
        assert math.isfinite(result)

    def test_inf_input(self) -> None:
        result = _monthly_rate_to_annual_nominal_pct(float("inf"), canadian=True)
        assert math.isfinite(result)


class TestIrdPrepaymentPenalty:
    def test_basic_penalty(self) -> None:
        penalty = ird_prepayment_penalty(500_000, 5.0, 3.5, 36)
        assert penalty > 0

    def test_comparison_rate_above_contract_rate(self) -> None:
        # Rate went up → IRD = 0, only 3-month rule applies
        penalty = ird_prepayment_penalty(500_000, 4.0, 6.0, 36)
        assert penalty >= 0  # 3-month interest

    def test_zero_balance_returns_zero(self) -> None:
        assert ird_prepayment_penalty(0, 5.0, 3.5, 36) == pytest.approx(0.0)

    def test_zero_remaining_months_returns_zero(self) -> None:
        assert ird_prepayment_penalty(500_000, 5.0, 3.5, 0) == pytest.approx(0.0)

    def test_invalid_balance_input(self) -> None:
        penalty = ird_prepayment_penalty("bad", 5.0, 3.5, 36)  # type: ignore[arg-type]
        assert penalty == pytest.approx(0.0)

    def test_zero_rate_differential(self) -> None:
        # Equal rates → IRD = 0, only 3-month interest
        penalty = ird_prepayment_penalty(500_000, 5.0, 5.0, 36)
        three_month = 500_000 * _annual_nominal_pct_to_monthly_rate(5.0, True) * 3.0
        assert penalty == pytest.approx(three_month)

    def test_invalid_months_input(self) -> None:
        penalty = ird_prepayment_penalty(500_000, 5.0, 3.5, "bad")  # type: ignore[arg-type]
        assert penalty == pytest.approx(0.0)

    def test_ird_exceeds_three_month(self) -> None:
        # Large rate drop + long remaining term → IRD > 3 months
        penalty = ird_prepayment_penalty(800_000, 5.0, 2.0, 48)
        three_month = 800_000 * _annual_nominal_pct_to_monthly_rate(5.0, True) * 3.0
        assert penalty >= three_month


class TestIrdPenaltyForSimulation:
    def test_no_penalty_term_already_elapsed(self) -> None:
        penalty = ird_penalty_for_simulation(
            original_principal=500_000,
            contract_rate_pct=5.0,
            monthly_payment=2_800,
            months_elapsed=60,
            term_months=60,
        )
        assert penalty == pytest.approx(0.0)

    def test_penalty_with_default_comparison_rate(self) -> None:
        penalty = ird_penalty_for_simulation(
            original_principal=500_000,
            contract_rate_pct=5.0,
            monthly_payment=2_800,
            months_elapsed=24,
            term_months=60,
            comparison_rate_pct=None,
            rate_drop_pp=1.5,
        )
        assert penalty >= 0.0

    def test_penalty_with_explicit_comparison_rate(self) -> None:
        penalty = ird_penalty_for_simulation(
            original_principal=500_000,
            contract_rate_pct=5.0,
            monthly_payment=2_800,
            months_elapsed=24,
            term_months=60,
            comparison_rate_pct=3.5,
        )
        assert penalty >= 0.0

    def test_zero_principal_returns_zero(self) -> None:
        penalty = ird_penalty_for_simulation(
            original_principal=0,
            contract_rate_pct=5.0,
            monthly_payment=0,
            months_elapsed=12,
            term_months=60,
        )
        assert penalty == pytest.approx(0.0)

    def test_invalid_inputs_dont_raise(self) -> None:
        penalty = ird_penalty_for_simulation(
            original_principal="bad",  # type: ignore[arg-type]
            contract_rate_pct=5.0,
            monthly_payment=2_800,
            months_elapsed="bad",  # type: ignore[arg-type]
            term_months="bad",  # type: ignore[arg-type]
        )
        assert penalty == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# policy_canada.py
# ---------------------------------------------------------------------------
from rbv.core.policy_canada import (
    b20_monthly_payment_at_qualifying_rate,
    b20_stress_test_qualifying_rate,
    foreign_buyer_tax_amount,
    foreign_buyer_tax_rate,
    insured_30yr_amortization_policy_stage,
    insured_amortization_rule_label,
    insured_max_amortization_years,
    insured_mortgage_price_cap,
    mortgage_default_insurance_sales_tax_rate,
)


class TestInsuredMortgagePriceCap:
    def test_pre_dec2024(self) -> None:
        cap = insured_mortgage_price_cap(dt.date(2024, 6, 1))
        assert cap == pytest.approx(1_000_000.0)

    def test_post_dec2024(self) -> None:
        cap = insured_mortgage_price_cap(dt.date(2025, 1, 1))
        assert cap == pytest.approx(1_500_000.0)


class TestInsured30yrStages:
    def test_pre_2024_08_01(self) -> None:
        stage = insured_30yr_amortization_policy_stage(dt.date(2024, 1, 1))
        assert stage == "pre_2024_08_01"

    def test_ftb_and_new_build(self) -> None:
        stage = insured_30yr_amortization_policy_stage(dt.date(2024, 9, 1))
        assert stage == "ftb_and_new_build"

    def test_ftb_or_new_build(self) -> None:
        stage = insured_30yr_amortization_policy_stage(dt.date(2025, 1, 1))
        assert stage == "ftb_or_new_build"


class TestInsuredMaxAmortization:
    def test_pre_2024_always_25(self) -> None:
        assert insured_max_amortization_years(dt.date(2024, 1, 1)) == 25
        assert insured_max_amortization_years(dt.date(2024, 1, 1), first_time_buyer=True) == 25
        assert insured_max_amortization_years(dt.date(2024, 1, 1), new_construction=True) == 25

    def test_ftb_and_new_build_stage_both_required(self) -> None:
        d = dt.date(2024, 9, 1)
        assert insured_max_amortization_years(d, first_time_buyer=True, new_construction=True) == 30
        assert insured_max_amortization_years(d, first_time_buyer=True, new_construction=False) == 25
        assert insured_max_amortization_years(d, first_time_buyer=False, new_construction=True) == 25

    def test_ftb_or_new_build_stage_either_sufficient(self) -> None:
        d = dt.date(2025, 1, 1)
        assert insured_max_amortization_years(d, first_time_buyer=True) == 30
        assert insured_max_amortization_years(d, new_construction=True) == 30
        assert insured_max_amortization_years(d) == 25


class TestInsuredAmortizationRuleLabel:
    def test_all_three_labels(self) -> None:
        pre = insured_amortization_rule_label(dt.date(2024, 1, 1))
        mid = insured_amortization_rule_label(dt.date(2024, 9, 1))
        post = insured_amortization_rule_label(dt.date(2025, 1, 1))
        assert "25" in pre
        assert "new build" in mid.lower() or "new builds" in mid.lower()
        assert "or" in post.lower()


class TestB20StressTest:
    def test_floor_applies_when_rate_low(self) -> None:
        assert b20_stress_test_qualifying_rate(2.0) == pytest.approx(5.25)

    def test_plus_two_applies_when_rate_high(self) -> None:
        assert b20_stress_test_qualifying_rate(5.0) == pytest.approx(7.0)

    def test_monthly_payment_tuple(self) -> None:
        q_rate, pmt_q, pmt_c = b20_monthly_payment_at_qualifying_rate(640_000, 5.0, 300)
        assert q_rate == pytest.approx(7.0)
        assert pmt_q > pmt_c  # qualifying payment always higher


class TestForeignBuyerTax:
    def test_bc_pre_2016_zero(self) -> None:
        assert foreign_buyer_tax_rate("British Columbia", dt.date(2015, 1, 1)) == pytest.approx(0.0)

    def test_bc_2016_15pct(self) -> None:
        assert foreign_buyer_tax_rate("British Columbia", dt.date(2016, 9, 1)) == pytest.approx(0.15)

    def test_bc_2018_20pct(self) -> None:
        assert foreign_buyer_tax_rate("BC", dt.date(2019, 1, 1)) == pytest.approx(0.20)

    def test_ontario_pre_2017_zero(self) -> None:
        assert foreign_buyer_tax_rate("Ontario", dt.date(2016, 1, 1)) == pytest.approx(0.0)

    def test_ontario_2017_15pct(self) -> None:
        assert foreign_buyer_tax_rate("Ontario", dt.date(2018, 1, 1)) == pytest.approx(0.15)

    def test_ontario_2022_20pct(self) -> None:
        assert foreign_buyer_tax_rate("Ontario", dt.date(2022, 6, 1)) == pytest.approx(0.20)

    def test_ontario_2023_25pct(self) -> None:
        assert foreign_buyer_tax_rate("ON", dt.date(2024, 1, 1)) == pytest.approx(0.25)

    def test_other_province_zero(self) -> None:
        assert foreign_buyer_tax_rate("Alberta", dt.date(2024, 1, 1)) == pytest.approx(0.0)

    def test_foreign_buyer_tax_amount(self) -> None:
        amount = foreign_buyer_tax_amount(1_000_000, "British Columbia", dt.date(2024, 1, 1))
        assert amount == pytest.approx(200_000.0)

    def test_foreign_buyer_tax_amount_invalid_price(self) -> None:
        amount = foreign_buyer_tax_amount("bad", "BC", dt.date(2024, 1, 1))  # type: ignore[arg-type]
        assert amount == pytest.approx(0.0)


class TestMortgageInsuranceSalesTax:
    def test_ontario_8pct(self) -> None:
        rate = mortgage_default_insurance_sales_tax_rate("Ontario", dt.date(2025, 1, 1))
        assert rate == pytest.approx(0.08)

    def test_ontario_abbreviation(self) -> None:
        rate = mortgage_default_insurance_sales_tax_rate("ON", dt.date(2025, 1, 1))
        assert rate == pytest.approx(0.08)

    def test_saskatchewan_6pct(self) -> None:
        rate = mortgage_default_insurance_sales_tax_rate("Saskatchewan", dt.date(2025, 1, 1))
        assert rate == pytest.approx(0.06)

    def test_quebec_9pct_pre2027(self) -> None:
        rate = mortgage_default_insurance_sales_tax_rate("Quebec", dt.date(2025, 6, 1))
        assert rate == pytest.approx(0.09)

    def test_quebec_9975pct_post2027(self) -> None:
        rate = mortgage_default_insurance_sales_tax_rate("Quebec", dt.date(2027, 3, 1))
        assert rate == pytest.approx(0.09975)

    def test_other_province_zero(self) -> None:
        rate = mortgage_default_insurance_sales_tax_rate("Alberta", dt.date(2025, 1, 1))
        assert rate == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# government_programs.py
# ---------------------------------------------------------------------------
from rbv.core.government_programs import (
    hbp_annual_repayment,
    hbp_max_withdrawal,
    hbp_repayment_monthly_schedule,
)


class TestHbpMaxWithdrawal:
    def test_pre_2024_limit(self) -> None:
        limit = hbp_max_withdrawal(dt.date(2023, 1, 1))
        assert limit == pytest.approx(35_000.0)

    def test_post_2024_limit(self) -> None:
        limit = hbp_max_withdrawal(dt.date(2024, 6, 1))
        assert limit == pytest.approx(60_000.0)

    def test_none_defaults_to_today(self) -> None:
        limit = hbp_max_withdrawal(None)
        assert limit in (35_000.0, 60_000.0)


class TestHbpAnnualRepayment:
    def test_invalid_input_returns_zero_repayment(self) -> None:
        result = hbp_annual_repayment("bad")  # type: ignore[arg-type]
        assert result == pytest.approx(0.0)

    def test_negative_clamped_to_zero(self) -> None:
        result = hbp_annual_repayment(-10_000.0)
        assert result == pytest.approx(0.0)


class TestHbpRepaymentMonthlySchedule:
    def test_grace_period_zero(self) -> None:
        schedule = hbp_repayment_monthly_schedule(35_000, 12)
        # All in grace period (default 2 years, so 24 months) → all zero for 12 months
        assert all(v == 0.0 for v in schedule)

    def test_repayment_starts_after_grace(self) -> None:
        grace_months = 24
        repay_months = 15 * 12
        schedule = hbp_repayment_monthly_schedule(35_000, grace_months + repay_months + 12)
        # Month 0..23 = grace = 0
        assert schedule[0] == 0.0
        assert schedule[grace_months - 1] == 0.0
        # Month 24 = first repayment
        expected_monthly = 35_000 / (15 * 12)
        assert schedule[grace_months] == pytest.approx(expected_monthly)
        # Month after repayment window = 0
        assert schedule[grace_months + repay_months] == pytest.approx(0.0)

    def test_invalid_withdrawal_returns_zero_schedule(self) -> None:
        schedule = hbp_repayment_monthly_schedule("bad", 12)  # type: ignore[arg-type]
        assert all(v == 0.0 for v in schedule)

    def test_invalid_sim_months_clamps_to_1(self) -> None:
        schedule = hbp_repayment_monthly_schedule(35_000, "bad")  # type: ignore[arg-type]
        assert len(schedule) == 1


# ---------------------------------------------------------------------------
# taxes.py
# ---------------------------------------------------------------------------
from rbv.core.taxes import (
    _as_bool,
    _normalize_province_key,
    bc_fthb_exemption_amount,
    calc_deed_transfer_tax_nova_scotia_default,
    calc_land_title_fee_alberta,
    calc_land_title_fee_saskatchewan,
    calc_land_transfer_tax_manitoba,
    calc_ltt_toronto_municipal,
    calc_property_transfer_tax_new_brunswick,
    calc_real_property_transfer_tax_pei,
    calc_registration_fee_newfoundland,
    calc_transfer_duty_quebec_baseline,
    calc_transfer_duty_quebec_big_city,
    calc_transfer_tax,
)


class TestAsBool:
    def test_bool_passthrough(self) -> None:
        assert _as_bool(True) is True
        assert _as_bool(False) is False

    def test_int_truthy(self) -> None:
        assert _as_bool(1) is True
        assert _as_bool(0) is False

    def test_string_true(self) -> None:
        for s in ("true", "True", "1", "yes", "y", "on", "t"):
            assert _as_bool(s) is True

    def test_string_false(self) -> None:
        for s in ("false", "False", "0", "no", "n", "off", "", "none", "null", "f"):
            assert _as_bool(s) is False


class TestNormalizeProvinceKey:
    def test_abbreviations(self) -> None:
        assert _normalize_province_key("ON") == "ontario"
        assert _normalize_province_key("BC") == "british columbia"
        assert _normalize_province_key("AB") == "alberta"
        assert _normalize_province_key("QC") == "quebec"
        assert _normalize_province_key("MB") == "manitoba"
        assert _normalize_province_key("NS") == "nova scotia"
        assert _normalize_province_key("NB") == "new brunswick"
        assert _normalize_province_key("PEI") == "prince edward island"
        assert _normalize_province_key("NL") == "newfoundland and labrador"
        assert _normalize_province_key("SK") == "saskatchewan"
        assert _normalize_province_key("NT") == "northwest territories"
        assert _normalize_province_key("YT") == "yukon"
        assert _normalize_province_key("NU") == "nunavut"

    def test_unknown_returns_normalized(self) -> None:
        result = _normalize_province_key("Unknown")
        assert result == "unknown"

    def test_none_returns_empty(self) -> None:
        assert _normalize_province_key(None) == ""


class TestCalcLttTorontoMunicipal:
    def test_below_3m(self) -> None:
        # Should equal the Ontario schedule (mirrored)
        tax = calc_ltt_toronto_municipal(1_000_000.0)
        assert tax > 0

    def test_above_3m_pre2026(self) -> None:
        tax = calc_ltt_toronto_municipal(4_000_000.0, asof_date=dt.date(2025, 1, 1))
        assert tax > calc_ltt_toronto_municipal(3_000_000.0)

    def test_above_3m_post2026(self) -> None:
        tax_post = calc_ltt_toronto_municipal(4_000_000.0, asof_date=dt.date(2026, 6, 1))
        tax_pre = calc_ltt_toronto_municipal(4_000_000.0, asof_date=dt.date(2025, 1, 1))
        assert tax_post > tax_pre  # higher luxury rates post Apr 2026

    def test_zero_price(self) -> None:
        assert calc_ltt_toronto_municipal(0) == pytest.approx(0.0)


class TestBcFthbExemption:
    def test_below_500k_fully_exempt(self) -> None:
        ex = bc_fthb_exemption_amount(400_000.0, dt.date(2025, 1, 1))
        from rbv.core.taxes import calc_ptt_bc
        assert ex == pytest.approx(calc_ptt_bc(400_000.0))

    def test_above_phaseout_post2024_zero(self) -> None:
        # Post-Apr 2024: phaseout_to = 860k
        ex = bc_fthb_exemption_amount(900_000.0, dt.date(2025, 1, 1))
        assert ex == pytest.approx(0.0)

    def test_in_phaseout_zone_post2024(self) -> None:
        # Between 835k and 860k → partial exemption
        ex = bc_fthb_exemption_amount(847_500.0, dt.date(2025, 1, 1))
        assert 0.0 < ex < 8_000.0

    def test_below_full_to_post2024(self) -> None:
        # Between 500k and 835k → full $8,000 exemption
        ex = bc_fthb_exemption_amount(700_000.0, dt.date(2025, 1, 1))
        assert ex == pytest.approx(8_000.0)

    def test_pre_2024_legacy_thresholds(self) -> None:
        # Pre-Apr 2024: full exemption ≤ 500k (already covered), phaseout 500k→525k
        ex_in = bc_fthb_exemption_amount(512_500.0, dt.date(2023, 1, 1))
        assert 0 < ex_in < 8_000.0

    def test_above_525k_pre2024_zero(self) -> None:
        ex = bc_fthb_exemption_amount(530_000.0, dt.date(2023, 1, 1))
        assert ex == pytest.approx(0.0)

    def test_zero_price(self) -> None:
        assert bc_fthb_exemption_amount(0, dt.date(2025, 1, 1)) == pytest.approx(0.0)


class TestProvinceSpecificTaxes:
    def test_land_title_fee_alberta(self) -> None:
        fee = calc_land_title_fee_alberta(500_000.0)
        assert fee > 0

    def test_land_title_fee_alberta_zero(self) -> None:
        assert calc_land_title_fee_alberta(0) == pytest.approx(0.0)

    def test_land_title_fee_saskatchewan_zero(self) -> None:
        assert calc_land_title_fee_saskatchewan(0) == pytest.approx(0.0)

    def test_land_title_fee_saskatchewan_below_500(self) -> None:
        assert calc_land_title_fee_saskatchewan(400) == pytest.approx(0.0)

    def test_land_title_fee_saskatchewan_500_to_6300(self) -> None:
        assert calc_land_title_fee_saskatchewan(1_000.0) == pytest.approx(25.0)

    def test_land_title_fee_saskatchewan_above_6300(self) -> None:
        fee = calc_land_title_fee_saskatchewan(100_000.0)
        assert fee == pytest.approx(25.0 + (100_000 - 6_300) * 0.004)

    def test_calc_land_transfer_tax_manitoba(self) -> None:
        tax = calc_land_transfer_tax_manitoba(300_000.0)
        assert tax > 0

    def test_transfer_duty_quebec_baseline_2024(self) -> None:
        tax = calc_transfer_duty_quebec_baseline(500_000.0, dt.date(2024, 1, 1))
        assert tax > 0

    def test_transfer_duty_quebec_baseline_2025(self) -> None:
        tax = calc_transfer_duty_quebec_baseline(500_000.0, dt.date(2025, 6, 1))
        assert tax > 0

    def test_transfer_duty_quebec_baseline_2026plus(self) -> None:
        tax = calc_transfer_duty_quebec_baseline(500_000.0, dt.date(2026, 6, 1))
        assert tax > 0

    def test_transfer_duty_quebec_big_city(self) -> None:
        tax = calc_transfer_duty_quebec_big_city(1_000_000.0)
        assert tax > 0

    def test_new_brunswick_1pct(self) -> None:
        tax = calc_property_transfer_tax_new_brunswick(500_000.0)
        assert tax == pytest.approx(5_000.0)

    def test_nova_scotia_default_rate(self) -> None:
        tax = calc_deed_transfer_tax_nova_scotia_default(500_000.0)
        assert tax == pytest.approx(7_500.0)

    def test_nova_scotia_custom_rate(self) -> None:
        tax = calc_deed_transfer_tax_nova_scotia_default(500_000.0, rate=0.02)
        assert tax == pytest.approx(10_000.0)

    def test_pei_below_30k(self) -> None:
        assert calc_real_property_transfer_tax_pei(25_000.0) == pytest.approx(0.0)

    def test_pei_above_30k(self) -> None:
        tax = calc_real_property_transfer_tax_pei(500_000.0)
        assert tax == pytest.approx((500_000 - 30_000) * 0.01)

    def test_pei_above_1m(self) -> None:
        tax = calc_real_property_transfer_tax_pei(1_500_000.0)
        expected = (1_000_000 - 30_000) * 0.01 + (1_500_000 - 1_000_000) * 0.02
        assert tax == pytest.approx(expected)

    def test_newfoundland_zero_price(self) -> None:
        assert calc_registration_fee_newfoundland(0) == pytest.approx(0.0)

    def test_newfoundland_below_500(self) -> None:
        assert calc_registration_fee_newfoundland(300.0) == pytest.approx(100.0)

    def test_newfoundland_above_500(self) -> None:
        fee = calc_registration_fee_newfoundland(100_000.0)
        increments = math.floor((100_000 - 500) / 100)
        assert fee == pytest.approx(min(5000.0, 100.0 + increments * 0.40))


class TestCalcTransferTaxExtended:
    def test_with_override_amount(self) -> None:
        result = calc_transfer_tax("Ontario", 800_000, False, False, override_amount=5_000.0)
        assert result["total"] == pytest.approx(5_000.0)
        assert "Override" in result["note"]

    def test_bc_fthb_applied(self) -> None:
        result_fthb = calc_transfer_tax("BC", 600_000, True, False, asof_date=dt.date(2025, 1, 1))
        result_no_fthb = calc_transfer_tax("BC", 600_000, False, False, asof_date=dt.date(2025, 1, 1))
        assert result_fthb["total"] < result_no_fthb["total"]

    def test_toronto_above_3m_note(self) -> None:
        result = calc_transfer_tax("Ontario", 4_000_000, False, True, asof_date=dt.date(2025, 1, 1))
        assert "3M" in result["note"] or "$3M" in result["note"] or "Toronto" in result["note"]

    def test_saskatchewan(self) -> None:
        result = calc_transfer_tax("Saskatchewan", 500_000, False, False)
        assert result["total"] > 0

    def test_manitoba(self) -> None:
        result = calc_transfer_tax("Manitoba", 500_000, False, False)
        assert result["total"] > 0

    def test_new_brunswick_with_assessed_value(self) -> None:
        result = calc_transfer_tax("New Brunswick", 500_000, False, False, assessed_value=550_000)
        # Uses max(price, assessed_value) = 550k → 1% = $5,500
        assert result["total"] == pytest.approx(5_500.0)

    def test_nova_scotia_with_rate(self) -> None:
        result = calc_transfer_tax("Nova Scotia", 500_000, False, False, ns_deed_transfer_rate=0.02)
        assert result["total"] == pytest.approx(10_000.0)
        assert "2%" in result["note"] or "2.0%" in result["note"] or "rate" in result["note"].lower()

    def test_nova_scotia_default_rate_note(self) -> None:
        result = calc_transfer_tax("Nova Scotia", 500_000, False, False)
        assert "1.5%" in result["note"] or "default" in result["note"].lower()

    def test_pei_with_assessed_value(self) -> None:
        result = calc_transfer_tax("Prince Edward Island", 500_000, False, False, assessed_value=520_000)
        assert result["total"] > 0

    def test_newfoundland(self) -> None:
        result = calc_transfer_tax("Newfoundland and Labrador", 500_000, False, False)
        assert result["total"] > 0

    def test_territory_zero_with_note(self) -> None:
        result = calc_transfer_tax("Northwest Territories", 500_000, False, False)
        assert result["total"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# equity_monitor.py — line 71 (no "Month" column in df)
# ---------------------------------------------------------------------------
from rbv.core.equity_monitor import detect_negative_equity, format_underwater_warning


class TestEquityMonitorLine71:
    def test_no_month_column_uses_index(self) -> None:
        """Line 71 branch: df has no 'Month' column → use index + 1."""
        df = pd.DataFrame({
            "Buyer Home Equity": [-50_000.0, -30_000.0, 10_000.0],
        })
        result = detect_negative_equity(df)
        assert result["has_negative_equity"] is True
        assert result["first_underwater_month"] == 1  # index 0 + 1

    def test_format_warning_with_underwater_at_horizon(self) -> None:
        analysis = {
            "has_negative_equity": True,
            "months_underwater": 5,
            "max_negative_equity": -25_000.0,
            "first_underwater_month": 3,
            "underwater_at_horizon": True,
        }
        msg = format_underwater_warning(analysis)
        assert msg is not None
        assert "STILL underwater" in msg

    def test_format_warning_not_underwater_at_horizon(self) -> None:
        analysis = {
            "has_negative_equity": True,
            "months_underwater": 5,
            "max_negative_equity": -25_000.0,
            "first_underwater_month": 3,
            "underwater_at_horizon": False,
        }
        msg = format_underwater_warning(analysis)
        assert msg is not None
        assert "STILL" not in msg

    def test_format_warning_no_negative_equity(self) -> None:
        assert format_underwater_warning({"has_negative_equity": False}) is None


# ---------------------------------------------------------------------------
# costs_utils.py
# ---------------------------------------------------------------------------
import numpy as np

from rbv.ui.costs_utils import (
    has_finite_signal,
    normalize_month_like_series,
    safe_numeric_mean,
    safe_numeric_series,
)


class TestSafeNumericSeries:
    def test_existing_column(self) -> None:
        df = pd.DataFrame({"A": [1.0, 2.0, 3.0]})
        ser = safe_numeric_series(df, "A")
        assert list(ser) == pytest.approx([1.0, 2.0, 3.0])

    def test_missing_column_returns_zeros(self) -> None:
        df = pd.DataFrame({"A": [1.0]})
        ser = safe_numeric_series(df, "B")
        assert list(ser) == [0.0]

    def test_none_df_returns_empty(self) -> None:
        ser = safe_numeric_series(None, "A")  # type: ignore[arg-type]
        assert len(ser) == 0

    def test_cache_hit(self) -> None:
        df = pd.DataFrame({"A": [1.0, 2.0]})
        cache: dict = {}
        ser1 = safe_numeric_series(df, "A", cache=cache)
        ser2 = safe_numeric_series(df, "A", cache=cache)
        assert ser1 is ser2

    def test_non_numeric_coerced(self) -> None:
        df = pd.DataFrame({"A": ["bad", "1.5", "2.5"]})
        ser = safe_numeric_series(df, "A")
        assert ser.iloc[0] == pytest.approx(0.0)
        assert ser.iloc[1] == pytest.approx(1.5)


class TestSafeNumericMean:
    def test_basic_mean(self) -> None:
        df = pd.DataFrame({"A": [1.0, 3.0]})
        assert safe_numeric_mean(df, "A") == pytest.approx(2.0)

    def test_missing_column_returns_zero(self) -> None:
        df = pd.DataFrame({"A": [1.0]})
        assert safe_numeric_mean(df, "B") == pytest.approx(0.0)

    def test_none_df_returns_zero(self) -> None:
        assert safe_numeric_mean(None, "A") == pytest.approx(0.0)  # type: ignore[arg-type]

    def test_cache_hit(self) -> None:
        df = pd.DataFrame({"A": [2.0, 4.0]})
        cache: dict = {}
        v1 = safe_numeric_mean(df, "A", cache=cache)
        v2 = safe_numeric_mean(df, "A", cache=cache)
        assert v1 == v2 == pytest.approx(3.0)


class TestHasFiniteSignal:
    def test_with_signal(self) -> None:
        s = pd.Series([0.0, 1.0, 2.0])
        assert has_finite_signal(s) is True

    def test_all_zeros(self) -> None:
        s = pd.Series([0.0, 0.0, 0.0])
        assert has_finite_signal(s) is False

    def test_all_nan(self) -> None:
        s = pd.Series([float("nan"), float("nan")])
        assert has_finite_signal(s) is False

    def test_tiny_values_below_eps(self) -> None:
        s = pd.Series([0.001, 0.002])
        assert has_finite_signal(s, eps=0.01) is False


class TestNormalizeMonthLikeSeries:
    def test_basic(self) -> None:
        df = pd.DataFrame({"Month": [1.0, 2.0, 3.0]})
        ser = normalize_month_like_series(df, "Month")
        assert list(ser) == pytest.approx([1.0, 2.0, 3.0])

    def test_missing_column_returns_fallback(self) -> None:
        df = pd.DataFrame({"Other": [1.0, 2.0, 3.0]})
        ser = normalize_month_like_series(df, "Month")
        assert list(ser) == pytest.approx([1.0, 2.0, 3.0])

    def test_outlier_triggers_fallback(self) -> None:
        # max value far exceeds n * outlier_mult → fallback
        df = pd.DataFrame({"Month": [1.0, 2.0, 10_000_000.0]})
        ser = normalize_month_like_series(df, "Month")
        assert list(ser) == pytest.approx([1.0, 2.0, 3.0])

# ---------------------------------------------------------------------------
# Targeted exception-branch coverage supplement
# ---------------------------------------------------------------------------
import numpy as np


class _FloatRaiser:
    """Custom object whose __float__ raises — triggers except Exception branches."""
    def __float__(self) -> float:
        raise TypeError("intentionally not convertible to float")


class TestExceptionBranchCoverage:
    """Targeted tests that exercise defensive exception handlers."""

    # --- hbp_max_withdrawal: pre-1992 fallback (line 51) ---
    def test_hbp_max_withdrawal_pre_1992_fallback(self) -> None:
        from rbv.core.government_programs import hbp_max_withdrawal
        limit = hbp_max_withdrawal(dt.date(1990, 1, 1))
        assert limit == pytest.approx(35_000.0)

    # --- fhsa_balance: exception branches for bad inputs ---
    def test_fhsa_balance_bad_contribution_type(self) -> None:
        from rbv.core.government_programs import fhsa_balance
        bal, cum = fhsa_balance(_FloatRaiser(), 5, 5.0)  # type: ignore[arg-type]
        assert bal == pytest.approx(0.0)

    def test_fhsa_balance_bad_years_type(self) -> None:
        from rbv.core.government_programs import fhsa_balance
        bal, cum = fhsa_balance(8_000.0, _FloatRaiser(), 5.0)  # type: ignore[arg-type]
        assert bal == pytest.approx(0.0)

    def test_fhsa_balance_bad_return_type(self) -> None:
        from rbv.core.government_programs import fhsa_balance
        bal, cum = fhsa_balance(8_000.0, 5, _FloatRaiser())  # type: ignore[arg-type]
        assert isinstance(bal, float)

    # --- fhsa_tax_savings: exception branches ---
    def test_fhsa_tax_savings_bad_contribution(self) -> None:
        from rbv.core.government_programs import fhsa_tax_savings
        result = fhsa_tax_savings(_FloatRaiser(), 33.0)  # type: ignore[arg-type]
        assert result == pytest.approx(0.0)

    def test_fhsa_tax_savings_bad_rate(self) -> None:
        from rbv.core.government_programs import fhsa_tax_savings
        result = fhsa_tax_savings(40_000.0, _FloatRaiser())  # type: ignore[arg-type]
        assert result == pytest.approx(0.0)

    # --- scenario_snapshots: numpy generic ---
    def test_canonicalize_numpy_scalar(self) -> None:
        v = np.float64(3.14)
        result = canonicalize_jsonish(v)
        assert result == pytest.approx(3.14)

    def test_canonicalize_numpy_int(self) -> None:
        v = np.int64(42)
        result = canonicalize_jsonish(v)
        assert result == 42

    # --- validation.py: bad "down" input (lines 97-98) ---
    def test_get_validation_warnings_bad_down(self) -> None:
        cfg = {"price": 800_000.0, "down": _FloatRaiser()}
        result = get_validation_warnings(cfg)
        assert isinstance(result, list)

    # --- validation.py: bad "nm" input (lines 135-136) ---
    def test_get_validation_warnings_bad_nm(self) -> None:
        cfg = {"price": 800_000.0, "down": 160_000.0, "nm": _FloatRaiser()}
        result = get_validation_warnings(cfg)
        assert isinstance(result, list)

    # --- mortgage.py: except branch in _annual_nominal_pct_to_monthly_rate (18-19) ---
    def test_annual_to_monthly_bad_object(self) -> None:
        result = _annual_nominal_pct_to_monthly_rate(_FloatRaiser(), canadian=True)  # type: ignore[arg-type]
        assert math.isfinite(result)

    # --- mortgage.py: except branch in _monthly_rate_to_annual_nominal_pct (38-39) ---
    def test_monthly_to_annual_bad_object(self) -> None:
        result = _monthly_rate_to_annual_nominal_pct(_FloatRaiser(), canadian=True)  # type: ignore[arg-type]
        assert math.isfinite(result)

    # --- mortgage.py: base <= 0 clamp in Canadian compounding (line 24/46) ---
    def test_very_negative_rate_canadian_base_clamp(self) -> None:
        # rate = -500% → base = 1 + (-5)/2 = -1.5 <= 0 → clamped to 1e-12
        result = _annual_nominal_pct_to_monthly_rate(-500.0, canadian=True)
        assert math.isfinite(result)
        assert result >= -1.0

    # --- mortgage.py: ird except branches for bad rate inputs (126-131) ---
    def test_ird_penalty_bad_contract_rate(self) -> None:
        with pytest.raises(Exception):
            # float("bad") raises in ird_prepayment_penalty at the mr_contract line
            ird_prepayment_penalty(500_000, _FloatRaiser(), 3.5, 36)  # type: ignore[arg-type]

    def test_ird_penalty_comparison_rate_bad(self) -> None:
        # cmp_rate except branch (130-131): float(_FloatRaiser()) raises → caught → cmp_rate=0.0
        penalty = ird_prepayment_penalty(500_000, 5.0, _FloatRaiser(), 36)  # type: ignore[arg-type]
        assert penalty >= 0.0

    # --- mortgage.py: ird_penalty_for_simulation except branch (224-225) ---
    def test_ird_penalty_simulation_bad_rate_drop(self) -> None:
        penalty = ird_penalty_for_simulation(
            original_principal=500_000,
            contract_rate_pct=5.0,
            monthly_payment=2_800,
            months_elapsed=24,
            term_months=60,
            comparison_rate_pct=None,
            rate_drop_pp=_FloatRaiser(),  # type: ignore[arg-type]
        )
        assert penalty >= 0.0

    # --- policy_canada.py: min_down_payment bad price (49-50) ---
    def test_min_down_payment_bad_price(self) -> None:
        from rbv.core.policy_canada import min_down_payment_canada
        result = min_down_payment_canada(_FloatRaiser(), dt.date(2025, 1, 1))  # type: ignore[arg-type]
        assert result == pytest.approx(0.0)

    # --- policy_canada.py: cmhc except branch (144-145) ---
    def test_cmhc_premium_rate_bad_ltv_type(self) -> None:
        from rbv.core.policy_canada import cmhc_premium_rate_from_ltv
        result = cmhc_premium_rate_from_ltv(_FloatRaiser())  # type: ignore[arg-type]
        assert result == pytest.approx(0.0)

    # --- taxes.py: _safe_float except branch (54-55) ---
    def test_safe_float_bad_type(self) -> None:
        from rbv.core.taxes import _safe_float
        result = _safe_float(_FloatRaiser(), default=99.0)  # type: ignore[arg-type]
        assert result == pytest.approx(99.0)

    # --- taxes.py: _as_bool unknown string (line 73) ---
    def test_as_bool_unknown_string_fallback(self) -> None:
        # "maybe" is not in true/false sets → falls through to bool(value)
        result = _as_bool("maybe")
        assert result is True  # non-empty string is truthy
