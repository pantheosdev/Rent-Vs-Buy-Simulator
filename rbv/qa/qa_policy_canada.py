#!/usr/bin/env python3
"""QA tests for Canada-specific policy helpers including OSFI B-20 stress test.

Run:
  python -m rbv.qa.qa_policy_canada
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root is on sys.path regardless of where this script is invoked from.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _die(msg: str, code: int = 1) -> None:
    print(f"\n[QA_POLICY_CANADA FAILED] {msg}\n")
    raise SystemExit(code)


def _assert_close(name: str, got: float, exp: float, *, atol: float = 1e-9) -> None:
    import math
    try:
        g = float(got)
        e = float(exp)
    except Exception:
        _die(f"{name}: non-numeric (got={got}, exp={exp})")
    if not (math.isfinite(g) and math.isfinite(e)):
        _die(f"{name}: non-finite (got={g}, exp={e})")
    if abs(g - e) > atol:
        _die(f"{name}: got {g:.12g} expected {e:.12g} (atol={atol})")


def _assert_true(name: str, condition: bool) -> None:
    if not condition:
        _die(f"{name}: condition was False")


def test_b20_stress_test_qualifying_rate() -> None:
    from rbv.core.policy_canada import b20_stress_test_qualifying_rate

    # contract + 2 = 6.5 > floor 5.25 => 6.5
    _assert_close("b20_qualifying_rate(4.5)", b20_stress_test_qualifying_rate(4.5), 6.5)

    # contract + 2 = 4.0 < floor 5.25 => 5.25
    _assert_close("b20_qualifying_rate(2.0)", b20_stress_test_qualifying_rate(2.0), 5.25)

    # contract + 2 = 5.25 == floor 5.25 => 5.25
    _assert_close("b20_qualifying_rate(3.25)", b20_stress_test_qualifying_rate(3.25), 5.25)

    # contract + 2 = 5.26 > floor 5.25 => 5.26
    _assert_close("b20_qualifying_rate(3.26)", b20_stress_test_qualifying_rate(3.26), 5.26)

    print("[PASS] b20_stress_test_qualifying_rate")


def test_b20_monthly_payment_at_qualifying_rate() -> None:
    from rbv.core.policy_canada import b20_monthly_payment_at_qualifying_rate

    # principal=640_000, contract=5.0%, amortization=300 months
    # qualifying rate = max(5.0+2.0, 5.25) = 7.0%
    qual_rate, pmt_qual, pmt_contract = b20_monthly_payment_at_qualifying_rate(640_000, 5.0, 300)

    _assert_close("b20_payment qualifying_rate", qual_rate, 7.0)
    _assert_true("b20_payment pmt_qual > pmt_contract", pmt_qual > pmt_contract)

    print("[PASS] b20_monthly_payment_at_qualifying_rate")


def main(argv: list[str] | None = None) -> None:
    test_b20_stress_test_qualifying_rate()
    test_b20_monthly_payment_at_qualifying_rate()
    print("\n[QA_POLICY_CANADA] All tests passed.\n")


if __name__ == "__main__":
    main()
