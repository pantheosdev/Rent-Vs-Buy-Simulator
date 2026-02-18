#!/usr/bin/env python3
"""DEPRECATED wrapper for smoke_check.py.

The canonical QA scripts live in: rbv/qa/smoke_check.py
This wrapper remains for backward compatibility with existing commands:
  python smoke_check.py

Prefer:
  python run_all_qa.py
  python -m rbv.qa.smoke_check
"""

from rbv.qa.smoke_check import main

if __name__ == "__main__":
    main()
