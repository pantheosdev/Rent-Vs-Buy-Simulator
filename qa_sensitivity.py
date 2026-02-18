#!/usr/bin/env python3
"""DEPRECATED wrapper for qa_sensitivity.py.

The canonical QA scripts live in: rbv/qa/qa_sensitivity.py
This wrapper remains for backward compatibility with existing commands:
  python qa_sensitivity.py

Prefer:
  python run_all_qa.py
  python -m rbv.qa.qa_sensitivity
"""

from rbv.qa.qa_sensitivity import main

if __name__ == "__main__":
    main()
