"""Pytest wrappers for Canada policy QA tests."""

from __future__ import annotations

from rbv.qa.qa_policy_canada import (
    test_b20_stress_test_qualifying_rate,
    test_b20_monthly_payment_at_qualifying_rate,
)


def test_b20_qualifying_rate() -> None:
    """B-20 stress test qualifying rate calculations."""
    test_b20_stress_test_qualifying_rate()


def test_b20_payment_at_qualifying_rate() -> None:
    """B-20 monthly payment at qualifying rate."""
    test_b20_monthly_payment_at_qualifying_rate()
