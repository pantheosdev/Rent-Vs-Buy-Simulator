#!/usr/bin/env python3
"""Run all RBV QA gates (smoke + scenarios + sensitivity + golden).

Usage:
  python run_all_qa.py
  python run_all_qa.py --only smoke,scenarios
  python run_all_qa.py --skip sensitivity
  python run_all_qa.py --list

Exit codes:
  0 = all selected suites passed
  1 = at least one selected suite failed
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _ensure_repo_root_on_syspath() -> Path:
    repo_root = Path(__file__).resolve().parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    return repo_root


def _run_suite(name: str) -> int:
    """Run a suite by name. Returns exit code."""
    if name == "smoke":
        from rbv.qa.smoke_check import main as _main
    elif name == "scenarios":
        from rbv.qa.qa_scenarios import main as _main
    elif name == "sensitivity":
        from rbv.qa.qa_sensitivity import main as _main
    elif name == "golden":
        from rbv.qa.qa_golden import main as _main
    elif name == "city_presets":
        from rbv.qa.qa_city_presets import main as _main
    elif name == "truth_tables":
        from rbv.qa.qa_truth_tables import main as _main
    elif name == "costs_utils":
        from rbv.qa.qa_costs_tab_utils import main as _main
    elif name == "costs_core":
        from rbv.qa.qa_costs_tab_core import main as _main
    elif name == "equity_monitor":
        from rbv.qa.qa_equity_monitor import main as _main
    else:
        raise ValueError(f"Unknown suite: {name}")

    try:
        try:
            _main([])  # prevent suite argparsers from seeing run_all_qa flags
        except TypeError:
            _main()
        return 0
    except SystemExit as e:
        # Normalize exit code: None/0 => 0, otherwise 1..255
        code = e.code
        if code is None:
            return 0
        try:
            return int(code)
        except Exception:
            return 1
    except Exception as e:
        print(f"\n[RUN_ALL_QA] Unhandled exception in '{name}': {e}\n")
        return 1


def main(argv: list[str] | None = None) -> int:
    _ensure_repo_root_on_syspath()

    suites = ["smoke", "scenarios", "sensitivity", "golden", "city_presets", "truth_tables", "costs_utils", "costs_core", "equity_monitor"]

    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--list", action="store_true", help="List available suites and exit.")
    ap.add_argument("--only", type=str, default="", help="Comma-separated suites to run (subset).")
    ap.add_argument("--skip", type=str, default="", help="Comma-separated suites to skip.")
    args = ap.parse_args(argv)

    if args.list:
        print("Available suites:")
        for s in suites:
            print(f" - {s}")
        return 0

    selected = set(suites)
    if args.only.strip():
        requested = {x.strip() for x in args.only.split(",") if x.strip()}
        unknown = sorted(requested.difference(suites))
        if unknown:
            print(f"[RUN_ALL_QA] Unknown suite(s) in --only: {unknown}")
            return 1
        selected = requested

    if args.skip.strip():
        skips = {x.strip() for x in args.skip.split(",") if x.strip()}
        unknown = sorted(skips.difference(suites))
        if unknown:
            print(f"[RUN_ALL_QA] Unknown suite(s) in --skip: {unknown}")
            return 1
        selected = selected.difference(skips)

    ordered = [s for s in suites if s in selected]
    if not ordered:
        print("[RUN_ALL_QA] Nothing to run (selection is empty).")
        return 0

    print("\n[RUN_ALL_QA] Running suites:", ", ".join(ordered), "\n")

    failures: list[tuple[str, int]] = []
    for s in ordered:
        print(f"--- {s.upper()} ---")
        code = _run_suite(s)
        if code != 0:
            failures.append((s, code))
            print(f"[RUN_ALL_QA] Suite '{s}' failed with exit code {code}.\n")
        else:
            print(f"[RUN_ALL_QA] Suite '{s}' passed.\n")

    if failures:
        print("=== RUN_ALL_QA FAILED ===")
        for s, code in failures:
            print(f" - {s}: exit code {code}")
        return 1

    print("=== RUN_ALL_QA PASS ===\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
