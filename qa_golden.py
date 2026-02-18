#!/usr/bin/env python3
"""Wrapper for qa_golden.py.

Canonical location:
  rbv/qa/qa_golden.py

This wrapper remains for backward compatibility:
  python qa_golden.py

Prefer:
  python run_all_qa.py
  python -m rbv.qa.qa_golden
"""

from rbv.qa.qa_golden import main

if __name__ == "__main__":
    main()
