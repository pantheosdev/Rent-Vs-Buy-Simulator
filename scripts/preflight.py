"""RBV release preflight.

Runs the checks that most commonly catch "looks good locally" issues before a public push:
- no stray __pycache__
- no obvious secrets
- no absolute local paths
- QA suite passes

Usage:
  python scripts/preflight.py
  python scripts/preflight.py --skip-qa
  python scripts/preflight.py --run-vr-smoke

Notes:
- Visual regression compare is intentionally NOT run by default because it
  requires Playwright + a baseline. Use --run-vr-smoke to at least ensure
  snapshots can be produced.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ABS_PATH_PATTERNS = [
    re.compile(r"[A-Za-z]:\\Users\\", re.IGNORECASE),
    re.compile(r"[A-Za-z]:\\.*\\OneDrive\\", re.IGNORECASE),
    re.compile(r"/Users/"),
]

SECRET_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),  # OpenAI-style keys
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),  # AWS access key id
    re.compile(r"\bAIza[0-9A-Za-z\-_]{30,}\b"),  # Google API key
]

TEXT_EXTS = {
    ".py",
    ".md",
    ".txt",
    ".yml",
    ".yaml",
    ".toml",
    ".json",
    ".css",
    ".js",
    ".html",
}

SKIP_DIR_PREFIXES = (
    ".git/",
    ".venv/",
    "venv/",
    "ENV/",
    "__pycache__/",
    "tools/visual_regression/output/",
    "tools/visual_regression/diffs/",
    "rbv/qa/_artifacts/",
)


def _run(cmd: list[str]) -> None:
    p = subprocess.run(cmd, cwd=str(ROOT), text=True)
    if p.returncode != 0:
        raise SystemExit(p.returncode)


def _iter_files() -> list[Path]:
    out: list[Path] = []
    for p in ROOT.rglob("*"):
        if p.is_dir():
            continue
        rel = p.relative_to(ROOT).as_posix()
        if rel.startswith(SKIP_DIR_PREFIXES):
            continue
        out.append(p)
    return out


def _cleanup_pycache() -> None:
    """Delete __pycache__ folders so local runs don't trip preflight."""
    bad = [p for p in ROOT.rglob('__pycache__') if p.is_dir()]
    if not bad:
        return
    print('RBV preflight: removing __pycache__ directories')
    for b in bad:
        try:
            # Recursively delete contents
            for child in b.rglob('*'):
                if child.is_file():
                    child.unlink(missing_ok=True)
            b.rmdir()
        except Exception:
            # Best effort only
            pass


def _check_no_large_files(max_mb: int) -> None:
    limit = max_mb * 1024 * 1024
    bad: list[tuple[Path, int]] = []
    for p in _iter_files():
        try:
            sz = p.stat().st_size
        except OSError:
            continue
        if sz > limit:
            bad.append((p, sz))
    if bad:
        print(f"FAIL: Large files (> {max_mb}MB) found:")
        for p, sz in sorted(bad, key=lambda x: x[1], reverse=True):
            print(f"  - {p.relative_to(ROOT)} ({sz/1024/1024:.1f}MB)")
        raise SystemExit(1)


def _check_text_for_patterns(label: str, patterns: list[re.Pattern[str]]) -> None:
    hits: list[tuple[Path, str]] = []
    for p in _iter_files():
        if label == 'absolute local paths' and p.relative_to(ROOT).as_posix() == 'scripts/preflight.py':
            continue
        if p.suffix.lower() not in TEXT_EXTS:
            continue
        try:
            data = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pat in patterns:
            if pat.search(data):
                hits.append((p, pat.pattern))
                break

    if hits:
        print(f"FAIL: {label} patterns detected:")
        for p, pat in hits[:50]:
            print(f"  - {p.relative_to(ROOT)} (pattern: {pat})")
        if len(hits) > 50:
            print(f"  ... plus {len(hits) - 50} more")
        raise SystemExit(1)


def _check_required_files() -> None:
    required = [
        "README.md",
        "LICENSE",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "SECURITY.md",
        "CHANGELOG.md",
        ".github/workflows/qa.yml",
        ".github/workflows/release.yml",
        "docs/RELEASE_CHECKLIST.md",
        "scripts/preflight.py",
    ]
    missing = [r for r in required if not (ROOT / r).exists()]
    if missing:
        print("FAIL: required files missing:")
        for r in missing:
            print(f"  - {r}")
        raise SystemExit(1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-qa", action="store_true")
    ap.add_argument("--run-vr-smoke", action="store_true")
    ap.add_argument("--max-mb", type=int, default=15)
    args = ap.parse_args()

    print("RBV preflight: starting")
    _check_required_files()
    _cleanup_pycache()
    _check_no_large_files(max_mb=args.max_mb)
    _check_text_for_patterns("absolute local paths", ABS_PATH_PATTERNS)
    _check_text_for_patterns("secret-like tokens", SECRET_PATTERNS)

    # Ruff lint/format (public CI stability)
    if shutil.which("ruff") is None:
        print("FAIL: ruff not installed. Install dev deps:\n  pip install -r requirements-dev.txt")
        raise SystemExit(1)
    print("RBV preflight: running ruff")
    # Apply formatting locally so you don't end up with a CI-only formatter mismatch.
    _run(["ruff", "format", "."])
    _run(["ruff", "check", "."])

    if not args.skip_qa:
        print("RBV preflight: running QA suite")
        _run([sys.executable, "run_all_qa.py"])

    if args.run_vr_smoke:
        print("RBV preflight: running visual regression smoke")
        _run([sys.executable, "tools/visual_regression/vr_playwright.py", "--smoke"])

    print("RBV preflight: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
