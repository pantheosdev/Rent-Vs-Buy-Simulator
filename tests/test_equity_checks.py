"""Negative equity detection tests."""
from rbv.qa.qa_equity_checks import main as equity_main


def test_equity_checks():
    equity_main()
