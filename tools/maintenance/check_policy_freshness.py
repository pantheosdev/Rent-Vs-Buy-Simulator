"""Policy freshness checker.

Purpose:
- Provide a lightweight reminder that jurisdictional policy thresholds (tax brackets, insured mortgage caps, etc.)
  drift over time. We keep explicit *last reviewed* markers in code and use CI to remind us to update annually.

Behavior:
- Exits non-zero if any marker is older than MAX_DAYS (default: 365).
- Emits GitHub Actions warnings as the deadline approaches.
"""

from __future__ import annotations

import datetime as dt
import importlib
import sys
from pathlib import Path

# Ensure repo root is on sys.path so `import rbv.*` works when run as a script.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from typing import Iterable, Tuple

MAX_DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 365
WARN_DAYS = int(sys.argv[2]) if len(sys.argv) > 2 else 330

MARKERS: Iterable[Tuple[str, str]] = [
    ("rbv.core.taxes", "TAX_RULES_LAST_REVIEWED"),
    ("rbv.core.policy_canada", "POLICY_LAST_REVIEWED"),
]


def _get_marker(mod_name: str, attr: str) -> dt.date | None:
    try:
        m = importlib.import_module(mod_name)
    except Exception:
        return None
    try:
        v = getattr(m, attr, None)
    except Exception:
        return None
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    return None


def main() -> int:
    today = dt.date.today()
    failed = False

    for mod_name, attr in MARKERS:
        d = _get_marker(mod_name, attr)
        if d is None:
            print(f"::warning::Missing policy marker {mod_name}.{attr} (cannot verify freshness)")
            continue

        age = (today - d).days
        if age >= MAX_DAYS:
            print(f"::error::{mod_name}.{attr} is {age} days old (last reviewed {d.isoformat()}). Update required.")
            failed = True
        elif age >= WARN_DAYS:
            print(
                f"::warning::{mod_name}.{attr} is {age} days old (last reviewed {d.isoformat()}). Plan an annual policy review."
            )
        else:
            print(f"OK: {mod_name}.{attr} last reviewed {d.isoformat()} ({age} days ago)")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
