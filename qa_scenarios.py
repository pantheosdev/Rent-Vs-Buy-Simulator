#!/usr/bin/env python3
"""DEPRECATED wrapper for qa_scenarios.py.

The canonical QA scripts live in: rbv/qa/qa_scenarios.py
This wrapper remains for backward compatibility with existing commands:
  python qa_scenarios.py

Prefer:
  python run_all_qa.py
  python -m rbv.qa.qa_scenarios
"""

from rbv.qa.qa_scenarios import main

if __name__ == "__main__":
    main()
