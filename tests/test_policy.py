"""Pytest wrappers for Canada policy QA tests."""

from __future__ import annotations

from rbv.qa.qa_policy_canada import (
    test_b20_stress_test_qualifying_rate,
    test_b20_monthly_payment_at_qualifying_rate,
)
from rbv.core.policy_canada import b20_stress_test_qualifying_rate


def test_b20_qualifying_rate() -> None:
    """B-20 stress test qualifying rate calculations."""
    test_b20_stress_test_qualifying_rate()


def test_b20_payment_at_qualifying_rate() -> None:
    """B-20 monthly payment at qualifying rate."""
    test_b20_monthly_payment_at_qualifying_rate()


def test_b20_qualifying_rate_ui_integration() -> None:
    """Verify qualifying rate calculation used in the sidebar UI produces correct values."""
    # At 4.75% contract rate: max(4.75 + 2, 5.25) = 6.75%
    assert b20_stress_test_qualifying_rate(4.75) == 6.75
    # At 3.0% contract rate: max(3.0 + 2, 5.25) = 5.25% (floor applies)
    assert b20_stress_test_qualifying_rate(3.0) == 5.25
    # At 5.0% contract rate: max(5.0 + 2, 5.25) = 7.0%
    assert b20_stress_test_qualifying_rate(5.0) == 7.0
    # At 0.0% contract rate: max(0.0 + 2, 5.25) = 5.25% (floor applies)
    assert b20_stress_test_qualifying_rate(0.0) == 5.25
