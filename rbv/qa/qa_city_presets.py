#!/usr/bin/env python3
"""Golden regression for City Presets (R3).

Purpose
- Catch accidental drift in preset catalogs and the exact values they apply.
- Presets are *convenience starters*; these goldens ensure they remain deterministic.

Run:
  python -m rbv.qa.qa_city_presets
  python -m rbv.qa.qa_city_presets --print-baseline
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict


# Ensure repo root is on sys.path regardless of where this script is invoked from.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


_GOLDEN_PATH = Path(__file__).resolve().parent / "goldens" / "city_presets_v1.json"


def _load_expected() -> Dict[str, Any]:
    try:
        return json.loads(_GOLDEN_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise SystemExit(f"[CITY PRESETS QA] Missing golden file: {_GOLDEN_PATH}") from e


def _compute_actual() -> Dict[str, Any]:
    from rbv.ui.defaults import CITY_PRESETS, city_preset_identity, city_preset_patch_values
    from rbv.core.scenario_snapshots import canonicalize_jsonish

    out: Dict[str, Any] = {"schema": "rbv.city_presets_golden.v1", "presets": {}}
    for name in CITY_PRESETS.keys():
        ident = city_preset_identity(name) or {}
        pid = ident.get("id") or str(name)
        patch = city_preset_patch_values(name) or {}
        patch_vals = {k: v for k, v in patch.items() if str(k) != "city_preset"}
        out["presets"][str(pid)] = {
            "name": str(name),
            "version": ident.get("version"),
            "patch": canonicalize_jsonish(patch_vals),
        }
    return out


def _die(msg: str, code: int = 1) -> None:
    print(f"\n[CITY PRESETS QA FAILED] {msg}\n")
    raise SystemExit(code)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--print-baseline", action="store_true", help="Print computed baseline JSON and exit.")
    args = ap.parse_args(argv)

    expected = _load_expected()
    actual = _compute_actual()

    if args.print_baseline:
        print(json.dumps(actual, indent=2, sort_keys=True))
        return 0

    exp_presets = expected.get("presets") if isinstance(expected.get("presets"), dict) else {}
    act_presets = actual.get("presets") if isinstance(actual.get("presets"), dict) else {}
    if not isinstance(exp_presets, dict) or not isinstance(act_presets, dict):
        _die("Malformed golden file (missing presets dict).")

    exp_ids = set(exp_presets.keys())
    act_ids = set(act_presets.keys())
    missing = sorted(exp_ids - act_ids)
    extra = sorted(act_ids - exp_ids)
    if missing:
        _die(f"Missing preset ids vs goldens: {missing}")
    if extra:
        _die(f"Unexpected preset ids (not in goldens): {extra}")

    for pid in sorted(exp_ids):
        e = exp_presets.get(pid) or {}
        a = act_presets.get(pid) or {}
        if e.get("name") != a.get("name"):
            _die(f"Preset name mismatch for {pid}: expected {e.get('name')} vs actual {a.get('name')}")
        if e.get("version") != a.get("version"):
            _die(f"Preset version mismatch for {pid}: expected {e.get('version')} vs actual {a.get('version')}")
        if e.get("patch") != a.get("patch"):
            _die(f"Preset patch mismatch for {pid}. Re-generate goldens if intentional via --print-baseline.")

    print("[CITY PRESETS QA] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
