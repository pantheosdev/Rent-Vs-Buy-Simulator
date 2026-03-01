#!/usr/bin/env python3
"""QA tests for rbv.core.validation clamping helpers."""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from rbv.core.validation import clamp_rate, clamp_positive, validate_simulation_params


def _test_clamp_rate_normal_passthrough():
    assert clamp_rate(5.0, "TestRate") == 5.0
    assert clamp_rate(0.0, "TestRate") == 0.0
    assert clamp_rate(-5.0, "TestRate") == -5.0
    assert clamp_rate(50.0, "TestRate") == 50.0
    assert clamp_rate(-10.0, "TestRate") == -10.0


def _test_clamp_rate_above_max():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = clamp_rate(999.0, "Mortgage rate", min_val=0.0, max_val=25.0)
    assert result == 25.0
    assert len(caught) == 1
    assert "Clamping" in str(caught[0].message)
    assert "999.0%" in str(caught[0].message)


def _test_clamp_rate_below_min():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = clamp_rate(-50.0, "General inflation", min_val=-5.0, max_val=20.0)
    assert result == -5.0
    assert len(caught) == 1
    assert "Clamping" in str(caught[0].message)
    assert "-50.0%" in str(caught[0].message)


def _test_clamp_rate_at_boundary():
    assert clamp_rate(25.0, "X", min_val=0.0, max_val=25.0) == 25.0
    assert clamp_rate(0.0, "X", min_val=0.0, max_val=25.0) == 0.0


def _test_clamp_positive_normal_passthrough():
    assert clamp_positive(0.0, "Price") == 0.0
    assert clamp_positive(500_000.0, "Price") == 500_000.0
    assert clamp_positive(100.0, "Rent", max_val=100_000.0) == 100.0


def _test_clamp_positive_negative_value():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = clamp_positive(-1.0, "Monthly rent")
    assert result == 0.0
    assert len(caught) == 1
    assert "negative" in str(caught[0].message)


def _test_clamp_positive_above_max():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = clamp_positive(200_000.0, "Monthly rent", max_val=100_000.0)
    assert result == 100_000.0
    assert len(caught) == 1
    assert "exceeds maximum" in str(caught[0].message)


def _test_validate_simulation_params_normal():
    params = validate_simulation_params(
        rate_pct=5.0,
        buyer_ret_pct=7.0,
        renter_ret_pct=7.0,
        apprec_pct=3.0,
        general_inf=0.02,
        rent_inf=0.03,
        years=25,
        price=800_000.0,
        rent=3_000.0,
        down=160_000.0,
    )
    assert params["rate_pct"] == 5.0
    assert params["buyer_ret_pct"] == 7.0
    assert params["renter_ret_pct"] == 7.0
    assert params["apprec_pct"] == 3.0
    assert abs(params["general_inf"] - 0.02) < 1e-9
    assert abs(params["rent_inf"] - 0.03) < 1e-9
    assert params["years"] == 25
    assert params["price"] == 800_000.0
    assert params["rent"] == 3_000.0
    assert params["down"] == 160_000.0


def _test_validate_simulation_params_clamped():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        params = validate_simulation_params(
            rate_pct=500.0,
            buyer_ret_pct=200.0,
            renter_ret_pct=-100.0,
            apprec_pct=9999.0,
            general_inf=5.0,
            rent_inf=5.0,
            years=200,
            price=-100.0,
            rent=-50.0,
            down=100_000_000.0,
        )
    assert params["rate_pct"] == 25.0
    assert params["buyer_ret_pct"] == 50.0
    assert params["renter_ret_pct"] == -20.0
    assert params["apprec_pct"] == 30.0
    assert abs(params["general_inf"] - 0.20) < 1e-9
    assert abs(params["rent_inf"] - 0.25) < 1e-9
    assert params["years"] == 50
    assert params["price"] == 0.0
    assert params["rent"] == 0.0
    assert params["down"] == 50_000_000.0
    assert len(caught) > 0


def _test_validate_simulation_params_years_min():
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        params = validate_simulation_params(
            rate_pct=5.0,
            buyer_ret_pct=7.0,
            renter_ret_pct=7.0,
            apprec_pct=3.0,
            general_inf=0.02,
            rent_inf=0.03,
            years=0,
            price=500_000.0,
            rent=2_000.0,
            down=100_000.0,
        )
    assert params["years"] == 1


def main(argv=None):
    _test_clamp_rate_normal_passthrough()
    _test_clamp_rate_above_max()
    _test_clamp_rate_below_min()
    _test_clamp_rate_at_boundary()
    _test_clamp_positive_normal_passthrough()
    _test_clamp_positive_negative_value()
    _test_clamp_positive_above_max()
    _test_validate_simulation_params_normal()
    _test_validate_simulation_params_clamped()
    _test_validate_simulation_params_years_min()
    print("[QA VALIDATION OK]")


if __name__ == "__main__":
    main()
