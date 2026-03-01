"""Pytest wrappers for the equity monitor QA suite."""

from __future__ import annotations

from rbv.qa.qa_equity_monitor import main as _qa_main


def test_equity_monitor() -> None:
    """All equity monitor QA cases pass."""
    _qa_main([])
