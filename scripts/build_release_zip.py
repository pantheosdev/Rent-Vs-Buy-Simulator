"""Build a clean release zip.

Creates dist/<name>.zip containing the repo contents while excluding:
- .git
- __pycache__
- visual regression outputs/diffs
- QA artifacts

Usage:
  python scripts/build_release_zip.py --name rent-vs-buy-simulator
"""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

EXCLUDE_PREFIXES = (
    ".git/",
    "dist/",
    "tools/visual_regression/output/",
    "tools/visual_regression/diffs/",
    "rbv/qa/_artifacts/",
    ".venv/",
    "venv/",
    ".ruff_cache/",
    ".pytest_cache/",
)


def _should_exclude(rel: str) -> bool:
    # Prefix exclusions
    if rel.startswith(EXCLUDE_PREFIXES):
        return True
    # Anywhere exclusions
    if "/__pycache__/" in rel:
        return True
    if rel.endswith(".pyc"):
        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="rent-vs-buy-simulator")
    ap.add_argument("--outdir", default="dist")
    args = ap.parse_args()

    outdir = ROOT / args.outdir
    outdir.mkdir(parents=True, exist_ok=True)
    outzip = outdir / f"{args.name}.zip"

    with zipfile.ZipFile(outzip, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in ROOT.rglob("*"):
            if p.is_dir():
                continue
            rel = p.relative_to(ROOT).as_posix()
            if _should_exclude(rel):
                continue
            z.write(p, rel)

    print(f"Wrote: {outzip}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
