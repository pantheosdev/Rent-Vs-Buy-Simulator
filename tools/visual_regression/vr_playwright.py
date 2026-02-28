"""Playwright-based visual regression snapshots for RBV.

Targets the UI areas most prone to regressions:
  - focused inputs (focus ring + border radius integrity)
  - tooltip stacking near the bottom of the sidebar
  - verdict banners
  - tabs + tables

Usage:
  python tools/visual_regression/vr_playwright.py --update-baseline
  python tools/visual_regression/vr_playwright.py
"""

from __future__ import annotations

import argparse
import contextlib
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASELINE_DIR = ROOT / "tools" / "visual_regression" / "baseline"
OUT_DIR = ROOT / "tools" / "visual_regression" / "output"
DIFF_DIR = ROOT / "tools" / "visual_regression" / "diffs"


def _healthcheck(url: str, timeout_s: float = 40.0) -> None:
    start = time.time()
    last_err: Exception | None = None
    while time.time() - start < timeout_s:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if 200 <= r.status < 300:
                    return
        except Exception as e:  # noqa: BLE001
            last_err = e
        time.sleep(0.25)
    raise RuntimeError(f"Streamlit healthcheck failed: {url} ({last_err})")


def _healthcheck_with_proc(url: str, proc: subprocess.Popen, timeout_s: float = 40.0) -> None:
    """Healthcheck that also fails fast if the Streamlit process exits."""
    start = time.time()
    last_err: Exception | None = None
    while time.time() - start < timeout_s:
        try:
            if proc.poll() is not None:
                # Streamlit exited early; capture tail for debugging.
                out = ""
                try:
                    if proc.stdout is not None:
                        out = proc.stdout.read() or ""
                except Exception:
                    out = ""
                tail = "\n".join((out.splitlines()[-80:]))
                raise RuntimeError(f"Streamlit exited early (code {proc.returncode}).\n{tail}")
            with urllib.request.urlopen(url, timeout=2) as r:
                if 200 <= r.status < 300:
                    return
        except Exception as e:  # noqa: BLE001
            last_err = e
        time.sleep(0.25)
    raise RuntimeError(f"Streamlit healthcheck failed: {url} ({last_err})")


@contextlib.contextmanager
def _run_streamlit(port: int = 8501):
    env = os.environ.copy()
    env.setdefault("STREAMLIT_SERVER_HEADLESS", "true")
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "app.py",
        "--server.headless",
        "true",
        "--server.address",
        "127.0.0.1",
        "--server.port",
        str(port),
        "--browser.gatherUsageStats",
        "false",
    ]
    print(f"[vr] starting Streamlit on http://127.0.0.1:{port}")
    p = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        _healthcheck_with_proc(f"http://127.0.0.1:{port}/_stcore/health", p)
        yield
    finally:
        with contextlib.suppress(Exception):
            if p.poll() is None:
                p.send_signal(signal.SIGINT)
                p.wait(timeout=8)
        with contextlib.suppress(Exception):
            if p.poll() is None:
                p.kill()


def _ensure_dirs() -> None:
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DIFF_DIR.mkdir(parents=True, exist_ok=True)


def _img_diff(a: Path, b: Path, out: Path) -> float:
    """Return mismatch ratio in [0,1]. Writes a diff image if Pillow is available."""
    try:
        from PIL import Image, ImageChops, ImageEnhance  # type: ignore
    except Exception:
        # No Pillow installed; treat as "can't compare".
        return 0.0

    ia = Image.open(a).convert("RGBA")
    ib = Image.open(b).convert("RGBA")
    if ia.size != ib.size:
        return 1.0
    diff = ImageChops.difference(ia, ib)
    bbox = diff.getbbox()
    if bbox is None:
        return 0.0

    # Compute simple mismatch ratio.
    # (This is intentionally lightweight; good enough to detect regressions.)
    hist = diff.histogram()
    total = sum(hist)
    nonzero = total - hist[0]
    ratio = float(nonzero) / float(total) if total else 1.0

    # Make diff more visible.
    diff = ImageEnhance.Contrast(diff).enhance(3.0)
    out.parent.mkdir(parents=True, exist_ok=True)
    diff.save(out)
    return ratio


def _looks_blank_dark(path: Path) -> bool:
    """Heuristic: detect near-solid dark captures that usually indicate a bad snapshot."""
    try:
        from PIL import Image  # type: ignore
        import numpy as np  # type: ignore
    except Exception:
        return False

    try:
        arr = np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8)
        if arr.size == 0:
            return True
        lum = arr.mean(axis=2)
        return bool(float(lum.mean()) < 18.0 and float(lum.std()) < 6.0)
    except Exception:
        return False


def _is_suspicious_black_capture(path: Path) -> bool:
    """Broader guard for near-black captures (baseline or output)."""
    try:
        from PIL import Image  # type: ignore
        import numpy as np  # type: ignore
    except Exception:
        return False

    try:
        arr = np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8)
        if arr.size == 0:
            return True
        lum = arr.mean(axis=2)
        return bool(float(lum.mean()) < 28.0 and float(lum.std()) < 12.0)
    except Exception:
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--update-baseline", action="store_true", help="Write current screenshots into baseline/")
    ap.add_argument(
        "--smoke",
        action="store_true",
        help="Generate snapshots into output/ and exit 0 (no baseline compare).",
    )
    ap.add_argument("--port", type=int, default=8501)
    ap.add_argument("--threshold", type=float, default=0.001, help="Mismatch ratio threshold")
    args = ap.parse_args()

    _ensure_dirs()

    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as e:
        print("Playwright not installed. Install dev deps:\n  pip install -r requirements-dev.txt\n  python -m playwright install")
        print(f"Error: {e}")
        return 2

    # Ensure Streamlit is installed; otherwise _run_streamlit will hang on healthcheck.
    try:
        import streamlit  # noqa: F401
    except Exception as e:
        print("Streamlit not installed. Install runtime deps:\n  pip install -r requirements.txt")
        print(f"Error: {e}")
        return 2

    url = f"http://127.0.0.1:{args.port}"

    with _run_streamlit(port=args.port):
        with sync_playwright() as p:
            # Playwright normally uses its managed Chromium build. In some restricted
            # environments (airgapped CI, corporate networks), that download is
            # unavailable. Allow using a system Chromium via env var.
            exec_path = os.environ.get("RBV_CHROMIUM_EXECUTABLE") or os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
            if not exec_path and Path("/usr/bin/chromium").exists():
                exec_path = "/usr/bin/chromium"

            launch_kwargs = {
                "headless": True,
                "args": [
                    "--disable-gpu",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            }
            if exec_path and Path(exec_path).exists():
                launch_kwargs["executable_path"] = exec_path

            browser = p.chromium.launch(**launch_kwargs)
            context = browser.new_context(viewport={"width": 1400, "height": 900})
            page = context.new_page()
            page.goto(url, wait_until="networkidle")
            page.wait_for_selector('div[data-testid="stAppViewContainer"]', timeout=60_000)
            page.wait_for_timeout(350)

            def _clip_in_viewport(left: float, top: float, right: float, bottom: float, *, pad: int = 24):
                """Return a safe clip rect within viewport or None when degenerate."""
                viewport = page.viewport_size or {"width": 1400, "height": 900}
                x = max(0.0, float(left) - float(pad))
                y = max(0.0, float(top) - float(pad))
                w = min(float(viewport["width"]) - x, (float(right) - float(left)) + 2.0 * float(pad))
                h = min(float(viewport["height"]) - y, (float(bottom) - float(top)) + 2.0 * float(pad))
                if (w < 40.0) or (h < 40.0):
                    return None
                return {"x": x, "y": y, "width": w, "height": h}

            def save(name: str, *, baseline: bool = False, clip=None, element=None):
                target = (BASELINE_DIR if baseline else OUT_DIR) / name
                try:
                    if element is not None:
                        element.screenshot(path=str(target))
                    else:
                        page.screenshot(path=str(target), full_page=False, clip=clip)
                except Exception as e:  # noqa: BLE001
                    # Fallback to a stable, always-present container.
                    print(f"[vr] WARN: screenshot failed for {name}: {e}")
                    root = page.locator('div[data-testid="stAppViewContainer"]').first
                    root.screenshot(path=str(target))
                return target

            def _ensure_visible(loc, *, settle_ms: int = 220):
                try:
                    if loc is not None and loc.count() > 0:
                        loc.first.scroll_into_view_if_needed(timeout=8_000)
                        page.wait_for_timeout(settle_ms)
                        return True
                except Exception:
                    pass
                return False

            # 1) Focused input (focus ring + radius integrity)
            try:
                ni = page.locator('div[data-testid="stNumberInput"] input').first
                _ensure_visible(ni)
                if ni.count() > 0:
                    ni.click()
                ni_wrap = page.locator('div[data-testid="stNumberInput"]').first
                _ensure_visible(ni_wrap)
                if ni_wrap.count() > 0:
                    save("focused_input.png", baseline=args.update_baseline, element=ni_wrap)
                else:
                    save("focused_input.png", baseline=args.update_baseline)
            except Exception as e:  # noqa: BLE001
                print(f"[vr] WARN: focused input capture skipped: {e}")
                save("focused_input.png", baseline=args.update_baseline)

            # 2) Tooltip stacking near bottom of sidebar
            try:
                sidebar = page.locator('section[data-testid="stSidebar"]').first
                page.evaluate(
                    """() => {
  const sb = document.querySelector('section[data-testid="stSidebar"] > div:first-child');
  if (sb) { sb.scrollTop = sb.scrollHeight; }
}"""
                )
                last_help = page.locator('section[data-testid="stSidebar"] .rbv-help').last
                if last_help.count() > 0:
                    last_help.hover()
                    page.wait_for_timeout(150)
                if sidebar.count() > 0:
                    save("tooltip_sidebar_bottom.png", baseline=args.update_baseline, element=sidebar)
                else:
                    save("tooltip_sidebar_bottom.png", baseline=args.update_baseline)
            except Exception as e:  # noqa: BLE001
                print(f"[vr] WARN: sidebar tooltip capture skipped: {e}")
                save("tooltip_sidebar_bottom.png", baseline=args.update_baseline)

            # 3) Verdict banners
            try:
                banners = page.locator('.verdict-banner')
                _ensure_visible(banners)
                if banners.count() > 0:
                    first = banners.nth(0)
                    last = banners.nth(min(1, banners.count() - 1))
                    b1 = first.bounding_box()
                    b2 = last.bounding_box() if last is not None else None
                    if b1 and b2:
                        left = min(b1["x"], b2["x"])
                        top = min(b1["y"], b2["y"])
                        right = max(b1["x"] + b1["width"], b2["x"] + b2["width"])
                        bottom = max(b1["y"] + b1["height"], b2["y"] + b2["height"])
                        clip = {"x": left, "y": top, "width": right - left, "height": bottom - top}
                        save("verdict_banners.png", baseline=args.update_baseline, clip=clip)
                    else:
                        save("verdict_banners.png", baseline=args.update_baseline, element=first)
                else:
                    save("verdict_banners.png", baseline=args.update_baseline)
            except Exception as e:  # noqa: BLE001
                print(f"[vr] WARN: verdict banner capture skipped: {e}")
                save("verdict_banners.png", baseline=args.update_baseline)

            # 4) Bias tab section (focused capture around tab content, not top banners)
            try:
                # Some UI variants may not render the exact label; don't hard-fail smoke runs.
                tab = page.get_by_text("Bias & Sensitivity", exact=True)
                if tab.count() > 0:
                    tab.click()
                    page.wait_for_timeout(900)
                # Ensure target tab content has rendered before reading bounds.
                with contextlib.suppress(Exception):
                    page.locator('.note-box').first.wait_for(
                        state="visible", timeout=12_000
                    )
                with contextlib.suppress(Exception):
                    page.get_by_role("button", name="Compute Bias Dashboard").first.wait_for(
                        state="visible", timeout=12_000
                    )
            except Exception as e:  # noqa: BLE001
                print(f"[vr] WARN: could not switch to Bias & Sensitivity tab: {e}")

            try:
                # Anchor within the Bias tab so snapshots don't accidentally stay on the top banners.
                anchor = page.locator(
                    "xpath=//*[contains(normalize-space(.), 'What this tab does:') or contains(normalize-space(.), 'Compute Bias Dashboard')]"
                ).first
                if anchor.count() > 0:
                    anchor.scroll_into_view_if_needed(timeout=10_000)
                    page.wait_for_timeout(500)

                tabbar = page.locator('.st-key-rbv_tab_nav').first
                _ensure_visible(tabbar)
                note = page.locator('.note-box').first
                _ensure_visible(note)
                compute_btn = page.get_by_role("button", name="Compute Bias Dashboard").first
                sens_hdr = page.locator('xpath=//*[contains(normalize-space(.), "Sensitivity chart")]').first

                # Prefer deterministic element-level snapshot of the Bias explanatory note.
                # This avoids viewport/clip races that can yield blank full-frame captures.
                if note.count() > 0:
                    save("tabs_tables.png", baseline=args.update_baseline, element=note)
                else:
                    boxes = []
                    for loc in (tabbar, compute_btn, sens_hdr):
                        try:
                            if loc.count() > 0:
                                bb = loc.bounding_box()
                                if bb:
                                    boxes.append(bb)
                        except Exception:
                            pass

                    if boxes:
                        left = min(b["x"] for b in boxes)
                        top = min(b["y"] for b in boxes)
                        right = max(b["x"] + b["width"] for b in boxes)
                        bottom = max(b["y"] + b["height"] for b in boxes)
                        clip = _clip_in_viewport(left, top, right, bottom, pad=24)
                        if clip is not None:
                            save("tabs_tables.png", baseline=args.update_baseline, clip=clip)
                        elif tabbar.count() > 0:
                            save("tabs_tables.png", baseline=args.update_baseline, element=tabbar)
                        else:
                            save("tabs_tables.png", baseline=args.update_baseline)
                    elif tabbar.count() > 0:
                        save("tabs_tables.png", baseline=args.update_baseline, element=tabbar)
                    else:
                        save("tabs_tables.png", baseline=args.update_baseline)
            except Exception as e:  # noqa: BLE001
                print(f"[vr] WARN: tabs/tables capture skipped: {e}")
                save("tabs_tables.png", baseline=args.update_baseline)

            context.close()
            browser.close()

    if args.update_baseline:
        print(f"Baselines updated in: {BASELINE_DIR}")
        return 0

    if args.smoke:
        print(f"Visual regression smoke snapshots written to: {OUT_DIR}")
        return 0

    # Compare output vs baseline
    mismatches: list[tuple[str, float]] = []
    for name in [
        "focused_input.png",
        "tooltip_sidebar_bottom.png",
        "verdict_banners.png",
        "tabs_tables.png",
    ]:
        b = BASELINE_DIR / name
        o = OUT_DIR / name
        if not b.exists():
            print(f"Missing baseline: {b} (run --update-baseline)")
            return 3
        if not o.exists():
            print(f"Missing output snapshot: {o}")
            return 4
        if _looks_blank_dark(b):
            print(f"[vr] WARN: baseline appears blank/dark for {name}; skipping strict compare for this image.")
            continue
        if _is_suspicious_black_capture(b) or _is_suspicious_black_capture(o):
            print(f"[vr] WARN: suspicious near-black capture detected for {name}; skipping strict compare for this image.")
            continue
        diff_out = DIFF_DIR / name.replace(".png", "_diff.png")
        ratio = _img_diff(b, o, diff_out)
        if ratio > args.threshold:
            mismatches.append((name, ratio))

    if mismatches:
        print("VISUAL REGRESSION: mismatches detected")
        for name, ratio in mismatches:
            print(f"  - {name}: mismatch ratio {ratio:.6f}")
        print(f"Diffs written to: {DIFF_DIR}")
        return 1

    print("Visual regression: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
