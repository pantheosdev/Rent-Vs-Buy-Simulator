import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import math
import time
import plotly.graph_objects as go
import plotly.io as pio
import html
import json
import hashlib
import random
import re
import os
import sys
import traceback
# Ensure the local package (rbv/) is importable when running via an absolute path
sys.path.insert(0, os.path.dirname(__file__))

import datetime
import io
import zipfile
import functools
import contextlib
import copy

# --- Global patch: strip Streamlit widget help tooltips (prevents sidebar "?" icons entirely)
# and suppress "default value + Session State" warnings by removing default kwargs when a key already exists.
# v167: Keep UI stable by avoiding Streamlit/BaseWeb native help tooltips and redundant defaults.

# --- Modular imports (v1 split) ---
from rbv.core.taxes import (
    PROVINCES,
    PROV_TAX_RULES_MD,
    calc_deed_transfer_tax_nova_scotia_default, calc_land_title_fee_alberta, calc_land_title_fee_saskatchewan, calc_land_transfer_tax_manitoba, calc_ltt_ontario, calc_ltt_toronto_municipal, calc_property_transfer_tax_new_brunswick, calc_ptt_bc, calc_real_property_transfer_tax_pei, calc_registration_fee_newfoundland, calc_transfer_duty_quebec_standard, calc_transfer_tax,
)
from rbv.core.mortgage import _annual_nominal_pct_to_monthly_rate, _monthly_rate_to_annual_nominal_pct
from rbv.core.policy_canada import (
    min_down_payment_canada,
    insured_mortgage_price_cap,
    cmhc_premium_rate_from_ltv,
    mortgage_default_insurance_sales_tax_rate,
    insured_max_amortization_years,
    insured_amortization_rule_label,
)
from rbv.core.engine import run_simulation_core, run_heatmap_mc_batch
from rbv.ui.theme import inject_global_css, BUY_COLOR, RENT_COLOR, BG_BLACK, SURFACE_CARD, SURFACE_INPUT, BORDER, TEXT_MUTED
# Deploy-safe imports: Streamlit Cloud can briefly run app.py during partial rollouts.
# Fail gracefully (UI error) instead of crashing on import.
try:
    from rbv.ui.defaults import PRESETS, build_session_defaults
except Exception:
    st.error(
        "Startup import failed (rbv.ui.defaults). This can happen during a partial deployment. "
        "Reload in 1–2 minutes; if it persists, redeploy from GitHub."
    )
    st.code(traceback.format_exc())
    st.stop()

# City presets are optional; if they fail to import during rollout, degrade to Custom-only.
try:
    from rbv.ui.defaults import (
        CITY_PRESETS,
        CITY_PRESET_CUSTOM,
        apply_city_preset_values,
        build_city_preset_change_summary,
        city_preset_filter_region_options,
        city_preset_filter_type_options,
        city_preset_filtered_options,
        city_preset_metadata,
        city_preset_options,
        city_preset_preview_summary_lines,
        city_preset_values,
    )
except Exception:
    CITY_PRESET_CUSTOM = "Custom"
    CITY_PRESETS = {}

    def city_preset_options():
        return [CITY_PRESET_CUSTOM]

    def city_preset_filter_region_options():
        return ["All regions"]

    def city_preset_filter_type_options():
        return ["All homes"]

    def city_preset_filtered_options(*, region=None, home_type=None, query=None):
        return [CITY_PRESET_CUSTOM]

    def city_preset_metadata(name):
        return {"name": str(name or CITY_PRESET_CUSTOM)}

    def city_preset_preview_summary_lines(name, *, max_items: int = 5):
        return []

    def city_preset_values(name):
        return None

    def apply_city_preset_values(state, preset_name):
        # No-op fallback; keep app running
        return []

    def build_city_preset_change_summary(changes, *, max_items: int = 8):
        return []
from rbv.core.scenario_snapshots import (
    build_scenario_config,
    build_scenario_snapshot,
    parse_scenario_payload,
    scenario_hash_from_state,
)

# PR10/PR11 compatibility shim: if a deployment picks up app.py before compare/export helper
# symbols are available in rbv.core.scenario_snapshots, keep app import working and fall back
# to local equivalents. Canonical implementations still live in scenario_snapshots.py when present.
try:
    from rbv.core.scenario_snapshots import (
        build_compare_export_payload,
        compare_metric_rows,
        compare_metric_rows_to_csv_text,
        extract_terminal_metrics,
        scenario_state_diff_rows,
        scenario_state_diff_rows_to_csv_text,
    )
except ImportError:
    from rbv.core import scenario_snapshots as _rbv_snap_mod

    def _rbv__to_float_or_none(v):
        try:
            x = float(v)
        except Exception:
            return None
        if not math.isfinite(x):
            return None
        return x

    def extract_terminal_metrics(df, *, close_cash=None, monthly_payment=None, win_pct=None):
        out = {
            "buyer_nw_final": None,
            "renter_nw_final": None,
            "advantage_final": None,
            "buyer_pv_nw_final": None,
            "renter_pv_nw_final": None,
            "pv_advantage_final": None,
            "buyer_unrecoverable_final": None,
            "renter_unrecoverable_final": None,
            "close_cash": _rbv__to_float_or_none(close_cash),
            "monthly_payment": _rbv__to_float_or_none(monthly_payment),
            "win_pct": _rbv__to_float_or_none(win_pct),
        }
        try:
            if df is None or len(df) == 0:
                return out
            row = df.iloc[-1]
        except Exception:
            return out

        def _row(col):
            try:
                return _rbv__to_float_or_none(row.get(col))
            except Exception:
                try:
                    return _rbv__to_float_or_none(row[col])
                except Exception:
                    return None

        out["buyer_nw_final"] = _row("Buyer Net Worth")
        out["renter_nw_final"] = _row("Renter Net Worth")
        if (out["buyer_nw_final"] is not None) and (out["renter_nw_final"] is not None):
            out["advantage_final"] = float(out["buyer_nw_final"] - out["renter_nw_final"])
        out["buyer_pv_nw_final"] = _row("Buyer PV NW")
        out["renter_pv_nw_final"] = _row("Renter PV NW")
        if (out["buyer_pv_nw_final"] is not None) and (out["renter_pv_nw_final"] is not None):
            out["pv_advantage_final"] = float(out["buyer_pv_nw_final"] - out["renter_pv_nw_final"])
        out["buyer_unrecoverable_final"] = _row("Buyer Unrecoverable")
        out["renter_unrecoverable_final"] = _row("Renter Unrecoverable")
        return out

    def compare_metric_rows(metrics_a, metrics_b, *, atol=1e-9):
        a = dict(metrics_a or {})
        b = dict(metrics_b or {})
        specs = [
            ("Final Buyer Net Worth", "buyer_nw_final"),
            ("Final Renter Net Worth", "renter_nw_final"),
            ("Final Net Advantage", "advantage_final"),
            ("Final Buyer PV NW", "buyer_pv_nw_final"),
            ("Final Renter PV NW", "renter_pv_nw_final"),
            ("Final PV Advantage", "pv_advantage_final"),
            ("Final Buyer Unrecoverable", "buyer_unrecoverable_final"),
            ("Final Renter Unrecoverable", "renter_unrecoverable_final"),
            ("Cash to Close", "close_cash"),
            ("Monthly Payment", "monthly_payment"),
            ("Win %", "win_pct"),
        ]
        rows = []
        for label, key in specs:
            va = _rbv__to_float_or_none(a.get(key))
            vb = _rbv__to_float_or_none(b.get(key))
            delta = None
            pct_delta = None
            if (va is not None) and (vb is not None):
                d = float(vb - va)
                if abs(d) <= float(atol):
                    d = 0.0
                delta = d
                if abs(va) > float(atol):
                    pct_delta = (d / abs(va)) * 100.0
                elif abs(d) <= float(atol):
                    pct_delta = 0.0
            rows.append({"metric": label, "a": va, "b": vb, "delta": delta, "pct_delta": pct_delta})
        return rows

    def scenario_state_diff_rows(state_a, state_b, *, atol=1e-9):
        canonicalize = getattr(_rbv_snap_mod, "canonicalize_jsonish", lambda x: x)
        a = canonicalize(state_a or {})
        b = canonicalize(state_b or {})
        rows = []
        for k in sorted(set(a.keys()) | set(b.keys())):
            va = a.get(k)
            vb = b.get(k)
            if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                try:
                    if math.isfinite(float(va)) and math.isfinite(float(vb)) and abs(float(va) - float(vb)) <= float(atol):
                        continue
                except Exception:
                    pass
            if va != vb:
                rows.append({"key": str(k), "a": va, "b": vb})
        return rows

    def compare_metric_rows_to_csv_text(rows):
        try:
            return pd.DataFrame(list(rows or []), columns=["metric", "a", "b", "delta", "pct_delta"]).to_csv(index=False)
        except Exception:
            return "metric,a,b,delta,pct_delta\n"

    def scenario_state_diff_rows_to_csv_text(rows):
        try:
            return pd.DataFrame(list(rows or []), columns=["key", "a", "b"]).to_csv(index=False)
        except Exception:
            return "key,a,b\n"

    def build_compare_export_payload(*, payload_a=None, payload_b=None, metric_rows=None, state_diff_rows=None, meta=None):
        canonicalize = getattr(_rbv_snap_mod, "canonicalize_jsonish", lambda x: x)
        return {
            "schema": "rbv.compare_export.v1",
            "meta": canonicalize(meta or {}),
            "snapshots": {"A": canonicalize(payload_a or {}), "B": canonicalize(payload_b or {})},
            "metrics": [canonicalize(r) for r in (metric_rows or [])],
            "state_diffs": [canonicalize(r) for r in (state_diff_rows or [])],
        }
# --- Cross-session caching for simulation runs ---
# Streamlit reruns the script on every interaction; Monte Carlo runs can be expensive.
# st.session_state caches are per-user; st.cache_data provides shared caching across sessions.
@st.cache_data(show_spinner=False, max_entries=128)
def _rbv_cached_run_simulation_core(
    cfg_json: str,
    buyer_ret_pct: float,
    renter_ret_pct: float,
    apprec_pct: float,
    invest_diff: bool,
    rent_closing: bool,
    mkt_corr: float,
    mc_seed: int | None,
    force_use_volatility: bool,
    num_sims_override: int | None,
    extra_kwargs_items: tuple,
):
    cfg = json.loads(cfg_json)
    extra = dict(extra_kwargs_items) if extra_kwargs_items else {}
    return run_simulation_core(
        cfg,
        buyer_ret_pct,
        renter_ret_pct,
        apprec_pct,
        invest_diff,
        rent_closing,
        mkt_corr,
        mc_seed=mc_seed,
        force_use_volatility=force_use_volatility,
        num_sims_override=num_sims_override,
        **extra,
    )



# --- UI helpers (Sprint 2/3: sidebar + tables + charts polish) ---
def sidebar_hint(text: str) -> None:
    'Small, low-noise hint text in the sidebar (replaces verbose captions).'
    if isinstance(text, str) and text.strip():
        st.markdown(f'<div class="rbv-hint">{html.escape(text)}</div>', unsafe_allow_html=True)

def sidebar_pills(items: list[str]) -> None:
    'Render a compact row of pills in the sidebar (for mode summaries, etc.).'
    safe = [html.escape(str(x)) for x in (items or []) if str(x).strip()]
    if not safe:
        return
    pills = ''.join([f'<div class="rbv-pill">{x}</div>' for x in safe])
    st.markdown(f'<div class="rbv-pill-row">{pills}</div>', unsafe_allow_html=True)

def _rbv_rgba(hex_color: str, alpha: float) -> str:
    'Convert #RRGGBB to rgba(r,g,b,a) string.'
    h = (hex_color or '').lstrip('#')
    if len(h) != 6:
        return f'rgba(255,255,255,{alpha})'
    r = int(h[0:2], 16); g = int(h[2:4], 16); b = int(h[4:6], 16)
    a = float(alpha)
    a = 0.0 if a < 0 else (1.0 if a > 1 else a)
    return f'rgba({r},{g},{b},{a:.3f})'

def _rbv_install_plotly_template() -> None:
    'Install a minimal dark-fintech Plotly template used across all charts.'
    try:
        tmpl = go.layout.Template(
            layout=dict(
                font=dict(
                    family='Manrope, Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif',
                    size=12,
                    color='rgba(241,241,243,0.92)'
                ),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                colorway=[BUY_COLOR, RENT_COLOR, 'rgba(210,210,220,0.80)', 'rgba(155,155,170,0.75)'],
                margin=dict(l=10, r=10, t=34, b=8),
                legend=dict(
                    orientation='h',
                    y=1.02, yanchor='bottom',
                    x=0.0, xanchor='left',
                    bgcolor='rgba(0,0,0,0)',
                    borderwidth=0,
                    font=dict(size=11, color='rgba(241,241,243,0.86)')
                ),
                title=dict(x=0.0, xanchor='left', font=dict(size=14, color='rgba(241,241,243,0.96)')),
                hoverlabel=dict(
                    bgcolor='#141417',
                    bordercolor='rgba(255,255,255,0.12)',
                    font=dict(color='#E6EDF7')
                ),
                xaxis=dict(
                    showgrid=True, gridcolor='rgba(255,255,255,0.08)',
                    zeroline=True, zerolinecolor='rgba(255,255,255,0.12)',
                    tickfont=dict(size=11, color='rgba(241,241,243,0.82)'),
                    titlefont=dict(size=12, color='rgba(241,241,243,0.88)')
                ),
                yaxis=dict(
                    showgrid=True, gridcolor='rgba(255,255,255,0.08)',
                    zeroline=True, zerolinecolor='rgba(255,255,255,0.12)',
                    tickfont=dict(size=11, color='rgba(241,241,243,0.82)'),
                    titlefont=dict(size=12, color='rgba(241,241,243,0.88)')
                ),
            )
        )
        pio.templates['rbv_dark_fintech'] = tmpl
        pio.templates.default = 'rbv_dark_fintech'
    except Exception:
        pass

def _rbv_apply_plotly_theme(fig: go.Figure, *, height: int | None = None) -> go.Figure:
    'Final, lightweight normalization pass on any figure.'
    try:
        if height is not None:
            fig.update_layout(height=int(height))
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        m = fig.layout.margin
        if m is not None and (getattr(m, 'l', None) == 0 and getattr(m, 'r', None) == 0):
            fig.update_layout(margin=dict(
                l=10, r=10,
                t=max(28, int(getattr(m, 't', 0) or 0)),
                b=max(8, int(getattr(m, 'b', 0) or 0)),
            ))
        if fig.layout.hovermode is None:
            fig.update_layout(hovermode='x unified')
    except Exception:
        pass
    return fig


_RBV_DEFAULT_KW = {
    "number_input": "value",
    "slider": "value",
    "selectbox": "index",
    "multiselect": "default",
    "radio": "index",
    "checkbox": "value",
    "toggle": "value",
    "text_input": "value",
    "text_area": "value",
    "date_input": "value",
    "time_input": "value",
}

def _rbv_patch_widget(fn, default_kw=None):
    @functools.wraps(fn)
    def _wrapped(*args, **kwargs):
        # Never allow Streamlit/BaseWeb help tooltips (removes the native '?' icons)
        kwargs.pop("help", None)

        # If the widget is keyed and already has a Session State value,
        # do not pass an explicit default (prevents Streamlit warning).
        k = kwargs.get("key", None)
        if k is not None and default_kw and (default_kw in kwargs) and (k in st.session_state):
            kwargs.pop(default_kw, None)

        return fn(*args, **kwargs)
    return _wrapped

_RBV_WIDGET_FNS = [
    "number_input",
    "slider",
    "selectbox",
    "multiselect",
    "radio",
    "checkbox",
    "toggle",
    "text_input",
    "text_area",
    "date_input",
    "time_input",
    "file_uploader",
]

try:
    for _w in _RBV_WIDGET_FNS:
        _dk = _RBV_DEFAULT_KW.get(_w)
        try:
            if hasattr(st, _w):
                setattr(st, _w, _rbv_patch_widget(getattr(st, _w), default_kw=_dk))
        except Exception:
            pass
        # Patch sidebar generator methods too (covers st.sidebar.<widget>(...) usages)
        try:
            if hasattr(st, "sidebar") and hasattr(st.sidebar, _w):
                setattr(st.sidebar, _w, _rbv_patch_widget(getattr(st.sidebar, _w), default_kw=_dk))
        except Exception:
            pass
except Exception:
    # If Streamlit changes widget signatures, fail open (app runs) rather than crashing.
    # Worst-case: native help icons may reappear until the patch is updated.
    pass

# --- Per-session caches (avoid NameError and avoid cross-user leakage) ---
# Keep caches in st.session_state so each Streamlit session/user has isolated cache dictionaries.
def _rbv_get_session_cache(name: str) -> dict:
    if name not in st.session_state or not isinstance(st.session_state.get(name), dict):
        st.session_state[name] = {}
    return st.session_state[name]

_eval_cache = _rbv_get_session_cache("_eval_cache")
_eval_mc_cache = _rbv_get_session_cache("_eval_mc_cache")

# Keep evaluation caches bounded (prevents slowdowns / memory bloat on long sessions)
def _rbv_cache_soft_cap(cache: dict, max_items: int = 5000):
    try:
        if isinstance(cache, dict) and len(cache) > int(max_items):
            # Coarse eviction: clear (fast + predictable). Cached values are only performance hints.
            cache.clear()
    except Exception:
        pass


_heatmap_cache = _rbv_get_session_cache("_heatmap_cache")
if "_heatmap_cache_order" not in st.session_state:
    st.session_state["_heatmap_cache_order"] = []

_liq_breakeven_cache = _rbv_get_session_cache("_liq_breakeven_cache")

# --- Phase 3D+: Soft cancel for long-running computations ---
# Streamlit can interrupt a running script when a widget event triggers a rerun.
# We expose a "Stop current run" button (sidebar) that sets this flag; on the next rerun we show a notice.
if "_rbv_cancel_requested" not in st.session_state:
    st.session_state["_rbv_cancel_requested"] = False
if "_rbv_cancel_notice" not in st.session_state:
    st.session_state["_rbv_cancel_notice"] = False
if "_rbv_active_longrun" not in st.session_state:
    # Set by long-running blocks (heatmap, bias scan, etc.) so cancellation can be made deterministic.
    # Example: {"kind": "heatmap", "sig": "<cache_key>"}
    st.session_state["_rbv_active_longrun"] = None
if "_rbv_cancel_freeze" not in st.session_state:
    # When a run is stopped, we freeze auto-recompute for that same long-run signature.
    st.session_state["_rbv_cancel_freeze"] = None
if "_rbv_heatmap_autorun" not in st.session_state:
    st.session_state["_rbv_heatmap_autorun"] = True

def _rbv_request_cancel():
    try:
        st.session_state["_rbv_cancel_requested"] = True
    except Exception:
        pass

# If a cancel was requested, acknowledge it once on the next rerun.
try:
    if bool(st.session_state.get("_rbv_cancel_requested", False)):
        st.session_state["_rbv_cancel_requested"] = False
        st.session_state["_rbv_cancel_notice"] = True

        # Freeze auto-run for the long computation that was active when cancellation occurred.
        _active = st.session_state.get("_rbv_active_longrun", None)
        if isinstance(_active, dict) and _active.get("kind") and _active.get("sig"):
            st.session_state["_rbv_cancel_freeze"] = {
                "kind": str(_active.get("kind")),
                "sig": str(_active.get("sig")),
            }
            if str(_active.get("kind")) == "heatmap":
                st.session_state["_rbv_heatmap_autorun"] = False
        st.session_state["_rbv_active_longrun"] = None
except Exception:
    pass



# --- Phase 3C: Diagnostics harness ---
# We accumulate non-fatal checks across the app (main run, heatmap, solvers) and surface them
# in a collapsed "Simulation Diagnostics" expander.
def _rbv_diag_reset():
    st.session_state["_rbv_diag"] = []


def _rbv_diag_add(level: str, title: str, detail: str = ""):
    try:
        arr = st.session_state.get("_rbv_diag", None)
        if not isinstance(arr, list):
            arr = []
        arr.append({
            "level": str(level or "INFO").upper(),
            "title": str(title or ""),
            "detail": str(detail or ""),
        })
        st.session_state["_rbv_diag"] = arr
    except Exception:
        pass


def _rbv_diag_isfinite(x) -> bool:
    try:
        return bool(np.isfinite(float(x)))
    except Exception:
        return False

# --- Custom sidebar label + tooltip (avoids Streamlit/BaseWeb help tooltips entirely) ---
def sidebar_label(label: str, tooltip: str | None = None):
    """Render a sidebar label with an optional custom dark tooltip (no Streamlit/BaseWeb help=)."""
    safe_label = html.escape(label)
    icon_html = rbv_help_html(tooltip or "", small=False) if tooltip else ""
    if icon_html:
        row = f'<div class="rbv-label-row"><div class="rbv-label-text">{safe_label}</div>{icon_html}</div>'
    else:
        row = f'<div class="rbv-label-row"><div class="rbv-label-text">{safe_label}</div></div>'
    st.markdown(row, unsafe_allow_html=True)


def rbv_help_html(tooltip: str, small: bool = False) -> str:
    """Return HTML for a dark-theme hover help icon (independent of Streamlit/BaseWeb tooltips)."""
    if not tooltip:
        return ""
    safe_tip = html.escape(str(tooltip)).replace("\n", "<br>")
    cls = "rbv-help-icon rbv-sm" if small else "rbv-help-icon"
    bubble_cls = "rbv-help-bubble rbv-sm-bubble" if small else "rbv-help-bubble"
    return (
        f'<span class="rbv-help"><span class="{cls}">i</span>'
        f'<span class="{bubble_cls}">{safe_tip}</span></span>'
    )


# --- Main-content label row + widget wrappers (custom dark tooltips; preserve keys) ---
def rbv_label_row(label: str, tooltip: str | None = None, *, small_icon: bool = False):
    """Render a label row with an optional custom tooltip bubble (no Streamlit/BaseWeb help=)."""
    safe_label = html.escape(label)
    icon_html = rbv_help_html(tooltip or "", small=bool(small_icon)) if tooltip else ""
    if icon_html:
        row = f'<div class="rbv-label-row"><div class="rbv-label-text">{safe_label}</div>{icon_html}</div>'
    else:
        row = f'<div class="rbv-label-row"><div class="rbv-label-text">{safe_label}</div></div>'
    st.markdown(row, unsafe_allow_html=True)


def _rbv_pop_help(kwargs: dict) -> dict:
    """Drop Streamlit native help= arguments to avoid BaseWeb/white popovers."""
    if not kwargs:
        return {}
    d = dict(kwargs)
    d.pop("help", None)
    return d


def rbv_number_input(label: str, *, tooltip: str | None = None, **kwargs):
    kwargs = _rbv_pop_help(kwargs)
    rbv_label_row(label, tooltip)
    return st.number_input(label, label_visibility="collapsed", **kwargs)


def rbv_slider(label: str, *, tooltip: str | None = None, **kwargs):
    kwargs = _rbv_pop_help(kwargs)
    rbv_label_row(label, tooltip)
    return st.slider(label, label_visibility="collapsed", **kwargs)


def rbv_selectbox(label: str, options, *, tooltip: str | None = None, **kwargs):
    kwargs = _rbv_pop_help(kwargs)
    rbv_label_row(label, tooltip)
    return st.selectbox(label, options, label_visibility="collapsed", **kwargs)


def rbv_radio(label: str, options, *, tooltip: str | None = None, **kwargs):
    kwargs = _rbv_pop_help(kwargs)
    rbv_label_row(label, tooltip)
    # Streamlit can still render the widget label even when label_visibility="collapsed"
    # (notably for horizontal radios). Use a blank widget label and rely on our custom label row.
    return st.radio(" ", options, label_visibility="collapsed", **kwargs)


def rbv_checkbox(label: str, *, tooltip: str | None = None, **kwargs):
    kwargs = _rbv_pop_help(kwargs)
    rbv_label_row(label, tooltip)
    return st.checkbox(" ", label_visibility="collapsed", **kwargs)


def rbv_text_input(label: str, *, tooltip: str | None = None, **kwargs):
    kwargs = _rbv_pop_help(kwargs)
    rbv_label_row(label, tooltip)
    return st.text_input(label, label_visibility="collapsed", **kwargs)

# --- Sidebar tooltip text (shown via custom hover icon) ---
RBV_SIDEBAR_TOOLTIPS = {
    "Public Mode (simple UI)": "When ON, hides power-user controls and uses safe presets. Turn OFF for Power Mode.",
    "Monte Carlo results": "Choose Stable for reproducible results, or New random run for a fresh random draw each rerun.",
    "Power overrides": "Optional manual overrides for sim counts/grid. Presets still apply when you change Fast/Quality.",
    "Province": "Select the province for land transfer / welcome tax rules.",
    "Toronto Property?": "If yes, applies Toronto Municipal Land Transfer Tax (MLTT) in addition to Ontario LTT (rates depend on date).",
    "First-Time Buyer?": "If eligible, applies applicable first-time buyer rebates where modeled.",
    "Purchase Price ($)": "Home purchase price at month 0.",
    "Down Payment ($)": "Cash paid up front. Remainder is financed by the mortgage (unless you set a smaller loan elsewhere).",
    "Transfer Tax Override ($)": "If set > 0, overrides computed land transfer/welcome tax and becomes the ground truth closing tax.",
    "Legal & Closing Costs ($)": "Legal fees and other closing costs (excluding transfer tax).",
    "Home Inspection ($)": "One-time inspection cost at purchase.",
    "Mortgage Rate Mode": "Choose how the mortgage rate behaves (fixed vs resets/renewals).",
    "Mortgage Rate (Fixed %)": "Nominal annual mortgage rate used for the payment calculation.",
    "Canadian mortgage compounding (semi-annual)": "If enabled, converts the nominal rate using Canadian semi-annual compounding before monthly payments.",
    "Amortization Period (Years)": "Total amortization length used to compute the monthly mortgage payment. Note: 30-year amortization has eligibility restrictions in Canada (policy-dependent).",
    "Reset Frequency (Years)": "How often the mortgage rate resets/renews (approximation).",
    "Rate at Reset (%)": "Mortgage rate applied after a reset/renewal occurs.",
    "Rate Change Per Reset (pp)": "Staircase applied at renewals: Renewal 1 = reset rate; Renewal 2 = reset rate + step; Renewal 3 = reset rate + 2×step; etc.",
    "Stress test: +2% rate shock at Year 5": "Adds a temporary rate shock (e.g., +2%) starting at year 5 for the configured duration.",
    "Add crisis shock event": "Adds a one-time drawdown event for home and/or portfolio at a specified year.",
    "Crisis year": "Year (from start) when the crisis drawdown is applied.",
    "Home price drawdown (%)": "One-time % drop in home value applied at the crisis year.",
    "Stock drawdown (%)": "One-time % drop in the investment portfolio applied at the crisis year.",
    "Monthly Rent ($)": "Starting monthly rent at month 0.",
    "Rent Inflation (%)": "Annual market rent growth rate (subject to rent control cap if enabled).",
    "Utilities ($/mo)": "Renter utilities cost. Set to 0 if you assume utilities are the same as the owner side.",
    "Insurance ($/mo)": "Renter insurance cost per month.",
    "Moving Costs ($)": "One-time moving cost each time the renter moves (if moving is enabled).",
    "Moving Frequency (Years)": "How often the renter moves (used to apply moving costs).",
    "Renter Invests Closing Costs?": "If enabled, renter invests the cash the buyer would have spent on closing costs.",
    "Invest Monthly Surplus?": "If enabled, the side with lower monthly housing costs invests the difference each month.",
    "Allow portfolio drawdown to fund deficits": "If enabled, portfolios can go negative/withdrawn to cover monthly deficits (instead of clipping at zero).",
    "Investment Tax Modeling": "Choose how investment taxes are approximated (pre-tax, annual drag, or deferred capital gains at the end).",
    "Tax on Investment Gains (%)": "Annual return drag applied to both portfolios when using the “Annual drag” tax mode.",
    "Effective Capital Gains Tax at End (%)": "Tax rate applied to unrealized gains when liquidating portfolios at the horizon in “Deferred CG” mode.",
    "Liquidation view at horizon (cash-in-hand)": "Shows a liquidation (after-tax/after-selling) view at the horizon for clarity.",
    "Buyer Investment Return (%)": "Nominal annual return used for the buyer’s invested cashflows/portfolio.",
    "Renter Investment Return (%)": "Nominal annual return used for the renter’s invested cashflows/portfolio.",
    "Enable Volatility": "Turns on Monte Carlo volatility for home and portfolio returns.",
    "Number of Simulations": "Monte Carlo simulation count. Higher = smoother estimates but slower.",
    "Monte Carlo seed": "Seed for repeatable Monte Carlo runs. Leave blank for a stable derived seed.",
    "Seed": "Leave blank to auto-derive a stable seed from your inputs (recommended for comparing scenarios). In 'New random run' mode, the manual seed is ignored.",
    "Randomize seed each run": "If enabled, uses a new random seed every run (results will vary run-to-run).",
    "Investment Volatility (Std Dev %)": "Annualized volatility (standard deviation) for the portfolio return process in Monte Carlo.",
    "Appreciation Volatility (Std Dev %)": "Annualized volatility (standard deviation) for the home appreciation process in Monte Carlo.",
    "Correlation (ρ)": "Correlation between home and portfolio shocks in Monte Carlo. Negative values mean they tend to move opposite.",
    "Home Appreciation (%)": "Baseline nominal annual home appreciation rate (drift).",
    "General Inflation Rate (%)": "CPI/general inflation used to grow many non-housing costs over time.",
    "PV (Discount) Rate (%)": "Discount rate used to compute present value (PV) versions of dollars and deltas.",
    "Property Tax Rate (%)": "Annual property tax rate as % of home value.",
    "Property Tax Growth Model": "Toronto realism: MPAC assessments lag market prices and municipalities smooth year-over-year bill changes. Hybrid is a simple, realistic approximation: market pressure capped by CPI + 0.5%/yr.",
    "Hybrid cap add-on (%/yr)": "Extra room above CPI used only in Hybrid mode. Default 0.5%/yr keeps taxes responsive to market pressure without assuming bills rise 1:1 with home prices.",
    "Maintenance (Repairs/Reno) Rate (%)": "Annual maintenance/repairs budget as % of home value.",
    "Repair Costs Rate (%)": "Additional repair reserve rate as % of home value (separate from maintenance).",
    "Condo Fees ($/mo)": "Monthly condo/HOA fees (0 for freehold).",
    "Condo Fee Inflation Mode": "How condo fees grow over time: CPI + spread, or a custom fixed rate.",
    "Condo Fee Inflation Spread vs CPI (%/yr)": "Adds this many % per year on top of CPI for condo fee inflation (CPI+spread mode).",
    "Condo Fee Inflation (%)": "Custom condo fee inflation rate (only used in custom mode).",
    "Selling Cost (%)": "Selling costs as % of sale price (e.g., realtor commission).",
    "Home Sale Legal/Closing Fee at Exit ($)": "Legal/closing fee paid on sale (added when “Assume sold at horizon” is enabled).",
    "Assume home sold at horizon (apply selling costs)": "If enabled, applies selling costs and liquidation at the horizon; otherwise treats the home as held.",
    "After-tax household income ($/mo)": "If income constraints are enabled, this caps how much total spending you can cover each month.",
    "Non-housing spending ($/mo)": "If income constraints are enabled, this models other spending outside housing each month.",
    "Income growth (%/yr)": "Annual growth rate for income/spending when income constraints are enabled.",
    "Enable income/budget constraints (experimental)": "If enabled, the model constrains cashflows by after-tax income and non-housing spending (experimental).",
    "⚡ Fast Mode": "Reduces expensive computations (especially heatmaps/Monte Carlo) for quicker interaction.",
    "Economic Scenario": "Preset bundle of assumptions (baseline / high inflation / stagnation) applied to key inputs.",
    "Analysis Duration (Years)": "How many years to simulate (monthly cashflows, investing, and PV discounting).",
    "Apply Rent Control Cap?": "Caps rent growth at the configured maximum (use only if your unit is legally rent-controlled). Effective rent growth = min(Rent Inflation, Cap).",
    "Rent Control Cap (%)": "Maximum annual rent increase allowed under rent control (e.g., provincial guideline).",
    "Main Monte Carlo sims": "Number of simulations for the main Monte Carlo net worth chart. Higher = smoother percentiles / win% but slower (and uses more memory).",
    "Heatmap Monte Carlo sims": "Monte Carlo simulations per heatmap cell (only used when the selected heatmap metric is stochastic). Higher = less noisy cells but slower.",
    "Bias Monte Carlo sims": "Monte Carlo simulations used inside the breakeven/bias solver. Higher = more stable breakeven results but slower.",
    "Heatmap grid size (N×N)": "Resolution of the heatmap grid. Higher N means more detail but compute grows roughly with N².",
    "Bias grid size (N×N)": "Resolution of the bias scan grid (used for breakeven). Higher N improves accuracy but can be slow.",
}

# --- Custom tooltip styles (independent of BaseWeb) ---
# --- Harden Streamlit/BaseWeb help tooltips so every sidebar "?" is consistent (opaque, padded, non-clipping) ---
# --- Assumptions Markdown (dedented to avoid code-block rendering) ---
ASSUMPTIONS_MD = """
### 📝 Model Logic & Assumptions

> **Educational use only — not financial advice.** This is a planning / scenario tool. Real outcomes depend on taxes, underwriting, personal budgeting, market regimes, and policy changes.

#### ✅ Audit & Stress-Test Notes (What this model explicitly handles)
- **Bidirectional cashflow investing:** If **buying is cheaper than renting**, the **buyer** invests the surplus; if renting is cheaper, the **renter** invests the surplus.
- **Separate inflation channels:** **General Inflation** grows fees/utilities/insurance; **Home Appreciation** drives property-linked items (tax/maintenance as modeled).
- **Monte Carlo correlation (ρ):** Housing and portfolio shocks can be positively or negatively correlated (ρ ∈ [-1, +1]).
- **Transfer taxes:** Province rules use **marginal brackets** and inputs are rounded to cents to avoid edge-case float artifacts at bracket cutoffs.
- **Maintenance clarity:** “Maintenance (Repairs/Reno)” is separate from **Condo Fees** to reduce double-counting risk.

**1. Inflation Dynamics**
- **Asset Inflation:** Property Taxes, Maintenance, and Repair costs scale with the **Home Price** (Appreciation). If housing booms, these costs rise faster than general inflation.
- **CPI Inflation:** Condo Fees, Insurance, and Utilities scale with **General Inflation** (CPI).
- **Rent Inflation:** Modeled explicitly via the **Rent Inflation** input (optionally capped if Rent Control is enabled).

**2. Tax Limitations**
- **Pre‑Tax Focus:** By default, the simulator models *economic* net worth. You can optionally enable an **after‑tax liquidation view** at the horizon.
- **Capital Gains (Portfolios):** Choose **Pre‑tax**, **Annual return drag**, or **Deferred capital gains at end**. Drag applies equally to *both* portfolios (buyer & renter). Deferred CG taxes only the *gains* at the horizon (buy‑and‑hold approximation).
- **Primary Residence Exemption:** Assumes the home is a principal residence (tax‑free capital gains in many jurisdictions like Canada/USA).

**3. Market Correlations & Volatility**
- In Monte Carlo mode, stocks and housing can be correlated (default **0.8**).
- Higher correlation means “good/bad times” tend to hit both assets together.
- **Random Seed :** If provided, Monte Carlo becomes reproducible (same inputs → same outcomes). Leave blank to derive a stable seed from your current inputs (recommended for comparing scenarios).

**4. Optional Policy & Rate Features**
- **Rent control cap:** If enabled, rent inflation is capped at the specified maximum (useful for rent‑controlled units).
- **Mortgage rate resets:** If enabled, the mortgage rate is reset every *N* years and the remaining balance is re‑amortized over the remaining term (simple renewal approximation). If a reset step is set, the reset rate moves by that amount each renewal.

**5. Why both Inflation & PV Rate?**
- **General Inflation:** Makes future numbers *bigger* (e.g., Condo fees rise from **\\$500 → \\$900**). This shows the nominal dollars you might see in your bank account later.
- **PV (Present Value) Rate:** The “Discount Rate.” It converts future dollars into today’s purchasing power so different timelines can be compared fairly.
"""

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Rent Vs Buy Analysis", layout="wide", page_icon="🏡")

# App version (for debug snapshots)
try:
    _vpath = os.path.join(os.path.dirname(__file__), 'VERSION.txt')
    with open(_vpath, 'r', encoding='utf-8') as _vf:
        st.session_state['_rbv_version'] = (_vf.read() or '').strip() or 'v2.92.10'
except Exception:
    st.session_state['_rbv_version'] = 'v2.92.10'

inject_global_css(st)
_rbv_install_plotly_template()

# Reset diagnostics for this rerun
try:
    _rbv_diag_reset()
except Exception:
    pass
try:
    # Keep the global progress overlay centered within the MAIN content area (not the full viewport).
    components.html(
        """<script>
(function(){
  const doc = window.parent && window.parent.document ? window.parent.document : document;
  // Guard so this helper doesn't reinstall on Streamlit reruns.
  if (doc && doc.defaultView && doc.defaultView.__rbv_global_js_installed){
    return;
  }
  if (doc && doc.defaultView){
    doc.defaultView.__rbv_global_js_installed = true;
  }
  function qs(sel){
    try { return doc.querySelector(sel); } catch(e){ return null; }
  }

  // --- Tooltip auto-flip (up/down) near viewport edges ---
  function _rbv_measureBubble(wrap){
    const bubble = wrap ? wrap.querySelector('.rbv-help-bubble') : null;
    if (!bubble) return null;
    const prevDisp = bubble.style.display;
    const prevVis = bubble.style.visibility;
    const prevPos = bubble.style.position;
    // Force measurable box without flashing.
    bubble.style.display = 'block';
    bubble.style.visibility = 'hidden';
    bubble.style.position = 'absolute';
    let r = null;
    try { r = bubble.getBoundingClientRect(); } catch(e) {}
    bubble.style.display = prevDisp;
    bubble.style.visibility = prevVis;
    bubble.style.position = prevPos;
    return r;
  }

  function _rbv_flipTooltipIfNeeded(wrap){
    if (!wrap) return;
    const pad = 10;
    const vh = (doc.defaultView && doc.defaultView.innerHeight) ? doc.defaultView.innerHeight : (window.innerHeight || 0);
    const vw = (doc.defaultView && doc.defaultView.innerWidth) ? doc.defaultView.innerWidth : (window.innerWidth || 0);
    if (!vh) return;

    // Reset placement classes and measure DOWN placement.
    wrap.classList.remove('rbv-tip-up');
    wrap.classList.remove('rbv-tip-left');

    let down = _rbv_measureBubble(wrap);
    if (!down) return;

    // Horizontal flip: if the bubble would overflow the LEFT edge, left-align it under the icon.
    if (vw && (down.left < pad)){
      wrap.classList.add('rbv-tip-left');
      const down2 = _rbv_measureBubble(wrap);
      // If left-align made it worse (rare), revert.
      if (down2 && (down2.right > (vw - pad)) && (down.right <= (vw - pad))){
        wrap.classList.remove('rbv-tip-left');
      } else if (down2){
        down = down2;
      }
    }

    const downOverflow = (down.bottom > (vh - pad));
    if (!downOverflow){
      wrap.classList.remove('rbv-tip-up');
      return;
    }

    // Try UP placement.
    wrap.classList.add('rbv-tip-up');
    let up = _rbv_measureBubble(wrap);
    if (!up) return;

    // Re-check horizontal constraints in UP mode.
    if (vw && (up.left < pad)){
      wrap.classList.add('rbv-tip-left');
      const up2 = _rbv_measureBubble(wrap);
      if (up2) up = up2;
    }

    // If UP overflows the top badly and DOWN would have fit, revert.
    if ((up.top < pad) && (down.bottom <= (vh - pad))){
      wrap.classList.remove('rbv-tip-up');
    }
  }

  function _rbv_installTooltipAutoflip(){
    try {
      if (!doc || doc.__rbvTooltipFlipInstalled) return;
      doc.__rbvTooltipFlipInstalled = true;

      let raf = 0;
      function schedule(wrap){
        if (raf) cancelAnimationFrame(raf);
        raf = requestAnimationFrame(() => { _rbv_flipTooltipIfNeeded(wrap); });
      }

      function findWrap(e){
        try {
          const t = e && e.target ? e.target : null;
          if (!t || !t.closest) return null;
          return t.closest('.rbv-help');
        } catch(err){ return null; }
      }

      doc.addEventListener('mouseenter', (e) => {
        const wrap = findWrap(e);
        if (wrap) schedule(wrap);
      }, true);
      doc.addEventListener('focusin', (e) => {
        const wrap = findWrap(e);
        if (wrap) schedule(wrap);
      }, true);

      // Re-evaluate on scroll/resize for the currently hovered tooltip.
      function activeWrap(){
        try { return doc.querySelector('.rbv-help:hover') || null; } catch(e){ return null; }
      }
      const reflow = () => {
        const w = activeWrap();
        if (w) schedule(w);
      };
      window.addEventListener('resize', reflow, {passive:true});
      window.addEventListener('scroll', reflow, {passive:true});
    } catch(e) {}
  }
  function update(){
    // Sidebar width (for fallback centering)
    const sb = qs('[data-testid="stSidebar"]') || qs('section[data-testid="stSidebar"]') || qs('aside');
    const w = sb ? sb.getBoundingClientRect().width : 0;
    doc.documentElement.style.setProperty('--rbv-sidebar-w', w + 'px');

    // Main content bounds (centers the global progress overlay in the main column)
    // Prefer stable testid selectors when available.
    const mainBlock = qs('div[data-testid="stMainBlockContainer"]');
    const main = qs('section.main') || qs('section[data-testid="stMain"]') || qs('div[data-testid="stMain"]');
    const bc = main ? (main.querySelector('div.block-container') || main.querySelector('div[data-testid="stMainBlockContainer"]')) : null;
    const target = mainBlock || bc || main;

    const vw = (doc.documentElement && doc.documentElement.clientWidth) ? doc.documentElement.clientWidth : (window.innerWidth || 0);

    if (target){
      try {
        const r = target.getBoundingClientRect();
        if (r && r.width && (r.width > 0)){
          let left = r.left;
          let width = r.width;

          // Guard: some Streamlit containers report left≈0 even when the sidebar is taking space.
          // If so, clamp left/width to the visible main area (viewport minus sidebar).
          if (vw && w && (left < (w * 0.5))){
            left = w;
            width = Math.max(0, vw - left);
          } else if (vw) {
            // Clamp width to the remaining viewport so centering can't drift.
            width = Math.min(width, Math.max(0, vw - left));
            if (width <= 0){
              left = w;
              width = Math.max(0, vw - left);
            }
          }

          doc.documentElement.style.setProperty('--rbv-main-left', left + 'px');
          doc.documentElement.style.setProperty('--rbv-main-width', width + 'px');
          return;
        }
      } catch(e) {}
    }

    // Fallback: approximate main content as the viewport minus sidebar width.
    const mainW = Math.max(0, vw - w);
    doc.documentElement.style.setProperty('--rbv-main-left', w + 'px');
    doc.documentElement.style.setProperty('--rbv-main-width', mainW + 'px');
  }
  let updateRaf = 0;
  let mutationDebounce = 0;
  function scheduleUpdate(){
    if (updateRaf) return;
    updateRaf = requestAnimationFrame(() => {
      updateRaf = 0;
      update();
    });
  }

  function scheduleUpdateDebounced(ms){
    if (mutationDebounce) clearTimeout(mutationDebounce);
    mutationDebounce = setTimeout(() => {
      mutationDebounce = 0;
      scheduleUpdate();
    }, ms || 80);
  }

  scheduleUpdate();
  _rbv_installTooltipAutoflip();

  // Event-driven geometry updates (faster than polling setInterval every 500ms).
  window.addEventListener('resize', scheduleUpdate, {passive:true});
  window.addEventListener('scroll', scheduleUpdate, {passive:true});

  // Observe structural changes that can move/resize the main block during Streamlit reruns.
  try {
    if (window.ResizeObserver){
      const ro = new ResizeObserver(() => scheduleUpdate());
      const mainNode = qs('section.main') || qs('section[data-testid="stMain"]') || qs('div[data-testid="stMain"]');
      const sideNode = qs('[data-testid="stSidebar"]') || qs('section[data-testid="stSidebar"]') || qs('aside');
      if (mainNode) ro.observe(mainNode);
      if (sideNode) ro.observe(sideNode);
      if (doc && doc.documentElement) ro.observe(doc.documentElement);
    }
  } catch(e) {}

  // Mutation observer catches Streamlit DOM swaps/reflows after widget updates.
  // Debounced + childList-focused to avoid excessive callback pressure.
  try {
    if (window.MutationObserver && doc && doc.body){
      const mo = new MutationObserver(() => scheduleUpdateDebounced(100));
      mo.observe(doc.body, {subtree:true, childList:true});
    }
  } catch(e) {}
})();
</script>""",
        height=0,
    )
except Exception:
    pass

# Streamlit/BaseWeb selectboxes can remain open when users click the chevron again.
# Add a safe DOM-level helper so clicking the right-edge toggle area on an open select
# dispatches Escape and closes the menu without forcing a selection.
try:
    components.html(
        """<script>
(function(){
  const doc = (window.parent && window.parent.document) ? window.parent.document : document;
  if (!doc || doc.__rbvSelectArrowCloseInstalled) return;
  doc.__rbvSelectArrowCloseInstalled = true;

  function findTrigger(target){
    try{
      if (!target || !target.closest) return null;
      return target.closest('[data-baseweb=\"select\"] [role=\"combobox\"], [data-baseweb=\"select\"] [role=\"button\"]');
    } catch(e){ return null; }
  }

  doc.addEventListener('click', function(e){
    const trigger = findTrigger(e.target);
    if (!trigger) return;
    const expanded = String(trigger.getAttribute('aria-expanded') || '').toLowerCase() === 'true';
    if (!expanded) return;
    let r = null;
    try { r = trigger.getBoundingClientRect(); } catch(err) {}
    if (!r || !r.width) return;
    const toggleZone = Math.min(44, Math.max(30, r.width * 0.22));
    if ((e.clientX || 0) < (r.right - toggleZone)) return;
    try { e.preventDefault(); e.stopPropagation(); } catch(err) {}
    try {
      trigger.dispatchEvent(new KeyboardEvent('keydown', {key:'Escape', code:'Escape', keyCode:27, which:27, bubbles:true}));
    } catch(err) {}
    try { trigger.blur(); } catch(err) {}
  }, true);
})();
</script>""",
        height=0,
    )
except Exception:
    pass


# --- 2. PRESETS & SESSION STATE ---
# Economic scenario presets + default seeding live in rbv.ui.defaults (single source of truth)

# Initialize Session State
defaults = build_session_defaults("Baseline")

for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val



# --- Phase 4/Release: Scenario save/load + exports + friendly validation ---
def _rbv_version_line() -> str:
    try:
        _base = os.path.dirname(__file__)
        _vp = os.path.join(_base, "VERSION.txt")
        with open(_vp, "r", encoding="utf-8") as _f:
            _ln = _f.readline().strip()
        return _ln or "rbv"
    except Exception:
        return "rbv"

def _rbv_basic_validation_errors() -> list:
    errs = []
    try:
        price = float(st.session_state.get("price", 0) or 0)
        down = float(st.session_state.get("down", 0) or 0)
        rent = float(st.session_state.get("rent", 0) or 0)
        years = int(st.session_state.get("years", 0) or 0)
        rate = float(st.session_state.get("rate", 0) or 0)
    except Exception:
        return ["One or more numeric inputs could not be parsed."]
    if price <= 0:
        errs.append("Purchase price must be greater than 0.")
    if down < 0:
        errs.append("Down payment must be 0 or greater.")
    if price > 0 and down > price:
        errs.append("Down payment cannot exceed purchase price.")
    # Canada-specific minimum down-payment rule (tiered; depends on insured cap).
    try:
        import datetime as _dt
        _asof = st.session_state.get("tax_rules_asof", _dt.date.today())
        if isinstance(_asof, str):
            _asof = _dt.date.fromisoformat(str(_asof)[:10])
        elif isinstance(_asof, _dt.datetime):
            _asof = _asof.date()
        elif not isinstance(_asof, _dt.date):
            _asof = _dt.date.today()
        _min_down = float(min_down_payment_canada(price, _asof))
        if price > 0 and (down + 1e-9) < _min_down:
            _pct = 100.0 * _min_down / float(price)
            errs.append(f"Down payment is below the minimum for this price. Minimum is ${_min_down:,.0f} ({_pct:.1f}%).")
    except Exception:
        pass
    if rent < 0:
        errs.append("Monthly rent must be 0 or greater.")
    if years < 1:
        errs.append("Years must be at least 1.")
    if rate < 0:
        errs.append("Mortgage rate must be 0% or greater.")
    return errs

def _rbv_scenario_allowed_keys() -> list:
    base = list(defaults.keys()) if isinstance(defaults, dict) else []
    extra = ["public_mode", "mc_randomize", "public_seed_mode", "sim_mode", "num_sims", "hm_grid_size", "hm_mc_sims", "bias_mc_sims", "mc_seed", "invest_surplus_input", "budget_enabled", "crisis_enabled", "budget_allow_withdraw", "rate_mode", "rate_reset_years", "rate_reset_to", "rate_reset_step_pp"]
    # Keep this conservative: only keys we explicitly support for public import/export.
    return list(dict.fromkeys(base + extra))

def _rbv_capture_scenario_state() -> dict:
    state = {}
    for k in _rbv_scenario_allowed_keys():
        if k in st.session_state:
            state[k] = st.session_state.get(k)
    return state

def _rbv_make_scenario_config():
    return build_scenario_config(
        _rbv_capture_scenario_state(),
        allowed_keys=_rbv_scenario_allowed_keys(),
    )


def _rbv_make_scenario_payload(*, slot: str = "active", label: str | None = None, extra_meta: dict | None = None) -> dict:
    state = _rbv_capture_scenario_state()

    meta = dict(extra_meta or {})
    # Always include a small amount of UI context for explainability/debugging.
    try:
        meta.setdefault("scenario_select", state.get("scenario_select"))
        meta.setdefault("province", state.get("province"))
        meta.setdefault("city_preset", state.get("city_preset"))
    except Exception:
        pass

    # Attach preset identity + overrides in meta (does not affect simulation math).
    try:
        from rbv.ui.defaults import city_preset_identity, city_preset_overrides_from_state, city_preset_patch_values

        _cp = state.get("city_preset")
        _ident = city_preset_identity(_cp)
        if isinstance(_ident, dict) and _ident.get("id"):
            meta["city_preset_identity"] = _ident
            _patch = city_preset_patch_values(_cp) or {}
            # Store only values (exclude the marker itself for clarity)
            if isinstance(_patch, dict):
                meta["city_preset_patch"] = {k: v for k, v in _patch.items() if str(k) != "city_preset"}
            meta["city_preset_overrides"] = city_preset_overrides_from_state(state, _cp)
    except Exception:
        # best-effort only; never fail snapshot export because of extra metadata
        pass

    snap = build_scenario_snapshot(
        state,
        slot=slot,
        label=label,
        app="Rent vs Buy Simulator",
        version=_rbv_version_line(),
        meta=meta,
        allowed_keys=_rbv_scenario_allowed_keys(),
    )
    return snap.to_dict()


def _rbv_scenario_hash_short() -> str:
    try:
        return _rbv_make_scenario_config().deterministic_hash()[:12]
    except Exception:
        return "n/a"


def _rbv_apply_scenario_state(state: dict) -> None:
    if not isinstance(state, dict):
        return
    allowed = set(_rbv_scenario_allowed_keys())
    for k, v in state.items():
        if k not in allowed:
            continue
        try:
            if k in ("years", "num_sims", "hm_grid_size", "hm_mc_sims", "bias_mc_sims", "special_assessment_year", "special_assessment_month_in_year"):
                st.session_state[k] = int(v)
            elif k in ("canadian_compounding", "assume_sale_end", "is_principal_residence", "show_liquidation_view", "use_volatility", "public_mode", "mc_randomize", "reg_shelter_enabled", "expert_mode"):
                st.session_state[k] = bool(v)
            elif k in ("scenario_select", "investment_tax_mode", "condo_inf_mode", "mc_seed", "sim_mode", "public_seed_mode", "cg_inclusion_policy"):
                st.session_state[k] = "" if v is None else str(v)
            else:
                # numeric defaults
                st.session_state[k] = float(v) if v is not None else st.session_state.get(k)
        except Exception:
            # best-effort; skip malformed entries
            pass

    # Back-compat: if an imported scenario uses advanced toggles but lacks expert_mode, enable expert mode.
    try:
        if "expert_mode" not in state:
            _pol = str(st.session_state.get("cg_inclusion_policy", "") or "")
            if _pol.startswith("Hypothetical") or bool(st.session_state.get("reg_shelter_enabled", False)):
                st.session_state["expert_mode"] = True
    except Exception:
        pass


def _rbv_parse_imported_scenario(obj: dict) -> tuple[dict, dict]:
    """Parse legacy or PR9 scenario payloads and return (state, meta)."""
    try:
        return parse_scenario_payload(obj if isinstance(obj, dict) else {})
    except Exception:
        # Back-compat fallback: older exports may be bare state dicts.
        if isinstance(obj, dict) and isinstance(obj.get("state"), dict):
            return dict(obj.get("state") or {}), {}
        return (dict(obj) if isinstance(obj, dict) else {}), {}


def _rbv_compare_slot_key(slot: str) -> str:
    s = str(slot or "A").strip().upper()[:1] or "A"
    return f"_rbv_compare_snapshot_{s}"


def _rbv_save_compare_snapshot(slot: str) -> None:
    _slot = str(slot or "A").strip().upper()[:1] or "A"
    _label = f"Scenario {_slot}"
    _payload = _rbv_make_scenario_payload(
        slot=_slot,
        label=_label,
        extra_meta={
            "scenario_select": st.session_state.get("scenario_select"),
            "province": st.session_state.get("province"),
        },
    )
    st.session_state[_rbv_compare_slot_key(_slot)] = _payload
    _h = str((_payload or {}).get("scenario_hash") or "")[:12]
    st.session_state["_rbv_loaded_scenario_msg"] = f"Saved current inputs to {_label} ({_h})."


def _rbv_load_compare_snapshot(slot: str) -> None:
    _slot = str(slot or "A").strip().upper()[:1] or "A"
    _payload = st.session_state.get(_rbv_compare_slot_key(_slot))
    if not isinstance(_payload, dict):
        st.session_state["_rbv_loaded_scenario_msg"] = f"Scenario {_slot} slot is empty."
        return
    _state, _meta = _rbv_parse_imported_scenario(_payload)
    _rbv_apply_scenario_state(_state)
    _h = str((_meta or {}).get("scenario_hash") or (_payload or {}).get("scenario_hash") or "")[:12]
    st.session_state["_rbv_loaded_scenario_msg"] = f"Loaded Scenario {_slot} ({_h})."
    st.rerun()


def _rbv_clear_compare_snapshot(slot: str) -> None:
    _slot = str(slot or "A").strip().upper()[:1] or "A"
    st.session_state.pop(_rbv_compare_slot_key(_slot), None)
    st.session_state["_rbv_loaded_scenario_msg"] = f"Cleared Scenario {_slot}."


def _rbv_compare_slot_summary(slot: str) -> str:
    _slot = str(slot or "A").strip().upper()[:1] or "A"
    _payload = st.session_state.get(_rbv_compare_slot_key(_slot))
    if not isinstance(_payload, dict):
        return f"{_slot}: empty"
    _h = str(_payload.get("scenario_hash") or scenario_hash_from_state(_payload.get("state") or {}))[:12]
    _meta = _payload.get("meta") if isinstance(_payload.get("meta"), dict) else {}
    _province = _meta.get("province") or ((_payload.get("state") or {}).get("province") if isinstance(_payload.get("state"), dict) else None)
    _preset = _meta.get("scenario_select") or ((_payload.get("state") or {}).get("scenario_select") if isinstance(_payload.get("state"), dict) else None)
    _ts = str(_payload.get("exported_at") or "")[:19].replace("T", " ")
    _bits = [f"{_slot}", str(_preset or "Custom"), str(_province or "-")]
    if _ts:
        _bits.append(_ts)
    _bits.append(_h)
    return " • ".join(_bits)


def _rbv_swap_compare_snapshots() -> None:
    ka = _rbv_compare_slot_key("A")
    kb = _rbv_compare_slot_key("B")
    a_payload = st.session_state.get(ka)
    b_payload = st.session_state.get(kb)
    if (not isinstance(a_payload, dict)) and (not isinstance(b_payload, dict)):
        st.session_state["_rbv_loaded_scenario_msg"] = "Swap skipped (A and B are both empty)."
        return
    st.session_state[ka], st.session_state[kb] = b_payload, a_payload
    st.session_state["_rbv_loaded_scenario_msg"] = "Swapped Scenario A ↔ B."


def _rbv_copy_compare_snapshot(src_slot: str, dst_slot: str) -> None:
    src = str(src_slot or "A").strip().upper()[:1] or "A"
    dst = str(dst_slot or "B").strip().upper()[:1] or "B"
    payload = st.session_state.get(_rbv_compare_slot_key(src))
    if not isinstance(payload, dict):
        st.session_state["_rbv_loaded_scenario_msg"] = f"Copy skipped: Scenario {src} slot is empty."
        return
    cloned = copy.deepcopy(payload)
    cloned["slot"] = dst
    cloned["label"] = f"Scenario {dst}"
    st.session_state[_rbv_compare_slot_key(dst)] = cloned
    _h = str(cloned.get("scenario_hash") or "")[:12]
    st.session_state["_rbv_loaded_scenario_msg"] = f"Copied Scenario {src} → {dst} ({_h})."


def _rbv_compare_extra_engine_kwargs_from_session() -> dict:
    _g = st.session_state.get
    return {
        "crisis_enabled": bool(_g("crisis_enabled", False)),
        "crisis_year": float(_g("crisis_year", 5)),
        "crisis_stock_dd": float(_g("crisis_stock_dd", 30.0)) / 100.0,
        "crisis_house_dd": float(_g("crisis_house_dd", 20.0)) / 100.0,
        "crisis_duration_months": int(_g("crisis_duration_months", 1)),
        "budget_enabled": bool(_g("budget_enabled", False)),
        "monthly_income": float(_g("monthly_income", 0.0) or 0.0),
        "monthly_nonhousing": float(_g("monthly_nonhousing", 0.0) or 0.0),
        "income_growth_pct": float(_g("income_growth_pct", 0.0) or 0.0),
        "budget_allow_withdraw": bool(_g("budget_allow_withdraw", True)),
    }


def _rbv_compare_recompute_cfg_derived(cfg: dict) -> dict:
    """Recompute derived closing/mortgage fields from session state for snapshot compare runs."""
    out = dict(cfg or {})
    try:
        price_v = float(st.session_state.get("price", out.get("price", 0.0)) or 0.0)
        down_v = float(st.session_state.get("down", out.get("down", 0.0)) or 0.0)
        rate_v = float(st.session_state.get("rate", out.get("rate", 0.0)) or 0.0)
        amort_v = int(st.session_state.get("amort", 25) or 25)
        province_v = str(st.session_state.get("province", out.get("province", "Ontario")) or "Ontario")
        first_time_v = bool(st.session_state.get("first_time", True))
        toronto_v = bool(st.session_state.get("toronto", False))
        assessed_value_v = None
        try:
            if st.session_state.get("assessed_value") not in (None, ""):
                assessed_value_v = float(st.session_state.get("assessed_value"))
        except Exception:
            assessed_value_v = None
        ns_deed_rate = None
        try:
            if province_v == "Nova Scotia":
                ns_deed_rate = float(st.session_state.get("ns_deed_transfer_rate_pct", 1.5) or 1.5) / 100.0
        except Exception:
            ns_deed_rate = None

        transfer_tax_override_v = 0.0
        try:
            transfer_tax_override_v = float(st.session_state.get("transfer_tax_override", 0.0) or 0.0)
        except Exception:
            transfer_tax_override_v = 0.0

        asof_raw = st.session_state.get("tax_rules_asof", out.get("asof_date", datetime.date.today().isoformat()))
        if isinstance(asof_raw, datetime.datetime):
            asof_date_v = asof_raw.date()
        elif isinstance(asof_raw, datetime.date):
            asof_date_v = asof_raw
        else:
            try:
                asof_date_v = datetime.date.fromisoformat(str(asof_raw)[:10])
            except Exception:
                asof_date_v = datetime.date.today()

        loan_v = max(0.0, price_v - down_v)
        ltv_v = (loan_v / price_v) if price_v > 0 else 0.0
        insured_v = bool(ltv_v > 0.8)
        dp_source_v = str(st.session_state.get("down_payment_source", out.get("down_payment_source", "Traditional")) or "Traditional")
        cmhc_r_v = float(cmhc_premium_rate_from_ltv(float(ltv_v), dp_source_v)) if insured_v else 0.0
        prem_v = loan_v * cmhc_r_v
        pst_rate_v = float(mortgage_default_insurance_sales_tax_rate(province_v, asof_date_v))
        pst_v = prem_v * pst_rate_v
        mort_v = loan_v + prem_v

        tt_v = calc_transfer_tax(
            province_v,
            float(price_v),
            first_time_v,
            toronto_v,
            override_amount=transfer_tax_override_v,
            asof_date=asof_date_v,
            assessed_value=assessed_value_v,
            ns_deed_transfer_rate=ns_deed_rate,
        )
        total_ltt_v = float((tt_v or {}).get("total", 0.0) or 0.0)
        lawyer_v = float(st.session_state.get("purchase_legal_fee", 1500.0) or 1500.0)
        insp_v = float(st.session_state.get("home_inspection", 500.0) or 500.0)
        other_close_v = float(st.session_state.get("other_closing_costs", 0.0) or 0.0)
        close_v = total_ltt_v + lawyer_v + insp_v + other_close_v + pst_v
        nm_v = max(1, int(amort_v) * 12)

        out["mort"] = float(mort_v)
        out["pst"] = float(pst_v)
        out["close"] = float(close_v)
        out["nm"] = int(nm_v)
        out["asof_date"] = asof_date_v.isoformat()
    except Exception:
        pass
    return out


@contextlib.contextmanager
def _rbv_temp_scenario_overlay(state: dict | None):
    payload_state = dict(state or {})
    allowed = set(_rbv_scenario_allowed_keys())
    touched = [k for k in payload_state.keys() if k in allowed]
    sentinel = object()
    prev = {k: st.session_state.get(k, sentinel) for k in touched}
    _rbv_apply_scenario_state(payload_state)
    try:
        yield
    finally:
        for k in touched:
            try:
                if prev.get(k, sentinel) is sentinel:
                    st.session_state.pop(k, None)
                else:
                    st.session_state[k] = prev[k]
            except Exception:
                pass


def _rbv_compare_run_from_payload(payload: dict | None) -> dict | None:
    if not isinstance(payload, dict):
        return None
    state, meta = _rbv_parse_imported_scenario(payload)
    if not isinstance(state, dict):
        return None

    with _rbv_temp_scenario_overlay(state):
        cfg = _rbv_compare_recompute_cfg_derived(_build_cfg())
        cfg_json = json.dumps(cfg, sort_keys=True, separators=(",", ":"), default=str)
        buyer_ret_pct = float(st.session_state.get("buyer_ret", 0.0) or 0.0)
        renter_ret_pct = float(st.session_state.get("renter_ret", 0.0) or 0.0)
        apprec_pct = float(st.session_state.get("apprec", 0.0) or 0.0)
        invest_diff = bool(st.session_state.get("invest_surplus_input", True)) and (not bool(st.session_state.get("budget_enabled", False)))
        rent_closing = bool(st.session_state.get("renter_uses_closing_input", True))
        mkt_corr = float(st.session_state.get("market_corr_input", 0.0) or 0.0)
        extra_kwargs = _rbv_compare_extra_engine_kwargs_from_session()

        # Compare preview intentionally uses deterministic mode for speed and stable deltas.
        df_cmp, fig_cmp, close_cash_cmp, m_pmt_cmp, win_pct_cmp = _rbv_cached_run_simulation_core(
            cfg_json,
            buyer_ret_pct,
            renter_ret_pct,
            apprec_pct,
            invest_diff,
            rent_closing,
            mkt_corr,
            None,
            False,
            None,
            tuple(sorted(extra_kwargs.items())),
        )
        metrics = extract_terminal_metrics(
            df_cmp,
            close_cash=close_cash_cmp,
            monthly_payment=m_pmt_cmp,
            win_pct=win_pct_cmp,
        )
    return {
        "payload": payload,
        "state": state,
        "meta": meta or {},
        "cfg": cfg,
        "df": df_cmp,
        "fig": fig_cmp,
        "close_cash": close_cash_cmp,
        "m_pmt": m_pmt_cmp,
        "win_pct": win_pct_cmp,
        "metrics": metrics,
    }


def _rbv_fmt_compare_metric(value: object, metric_label: str) -> str:
    try:
        if value is None:
            return "—"
        x = float(value)
        if not math.isfinite(x):
            return "—"
        if metric_label == "Win %":
            return f"{x:.1f}%"
        if abs(x) >= 1000:
            return f"${x:,.0f}"
        if abs(x) >= 1:
            return f"${x:,.2f}"
        return f"{x:.4f}"
    except Exception:
        return str(value)


def _rbv_fmt_compare_delta(value: object, metric_label: str, pct_value: object | None = None) -> str:
    try:
        if value is None:
            return "—"
        x = float(value)
        if not math.isfinite(x):
            return "—"
        if metric_label == "Win %":
            out = f"{x:+.2f} pp"
        elif abs(x) >= 1000:
            out = f"${x:+,.0f}"
        elif abs(x) >= 1:
            out = f"${x:+,.2f}"
        else:
            out = f"{x:+.4f}"
        try:
            if pct_value is not None and math.isfinite(float(pct_value)):
                out += f" ({float(pct_value):+.1f}%)"
        except Exception:
            pass
        return out
    except Exception:
        return str(value)


def _rbv_render_compare_preview() -> None:
    """PR10 (R2-2): deterministic A/B preview chart + delta summary from saved slots."""
    with st.expander("Scenario Compare A vs B (preview)", expanded=False):
        payload_a = st.session_state.get(_rbv_compare_slot_key("A"))
        payload_b = st.session_state.get(_rbv_compare_slot_key("B"))

        st.caption(_rbv_compare_slot_summary("A"))
        st.caption(_rbv_compare_slot_summary("B"))

        if not isinstance(payload_a, dict) or not isinstance(payload_b, dict):
            st.session_state.pop("_rbv_compare_last_export", None)
            st.info("Save snapshots into both **A** and **B** in the sidebar to render the PR10 compare preview.")
            return

        cmp_a = _rbv_compare_run_from_payload(payload_a)
        cmp_b = _rbv_compare_run_from_payload(payload_b)
        if not isinstance(cmp_a, dict) or not isinstance(cmp_b, dict):
            st.session_state.pop("_rbv_compare_last_export", None)
            st.warning("Unable to compute one or both compare snapshots. Re-save A/B from the current version and try again.")
            return

        dfa = cmp_a.get("df")
        dfb = cmp_b.get("df")
        if dfa is None or dfb is None:
            st.session_state.pop("_rbv_compare_last_export", None)
            st.warning("Compare preview dataframes are unavailable.")
            return

        # Summary metrics (terminal deltas B − A)
        rows = compare_metric_rows(cmp_a.get("metrics"), cmp_b.get("metrics"), atol=1e-9)
        diff_rows_for_export = []
        by_metric = {str(r.get("metric")): r for r in rows}

        row_adv = by_metric.get("Final Net Advantage", {})
        row_pv = by_metric.get("Final PV Advantage", {})
        row_close = by_metric.get("Cash to Close", {})
        row_pmt = by_metric.get("Monthly Payment", {})
        row_win = by_metric.get("Win %", {})

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("A final net advantage", _rbv_fmt_compare_metric(row_adv.get("a"), "Final Net Advantage"))
        with c2:
            st.metric("B final net advantage", _rbv_fmt_compare_metric(row_adv.get("b"), "Final Net Advantage"))
        with c3:
            st.metric("Δ final net adv (B−A)", _rbv_fmt_compare_delta(row_adv.get("delta"), "Final Net Advantage", row_adv.get("pct_delta")))
        with c4:
            # Prefer win% delta if available; else fall back to monthly payment delta.
            if row_win and row_win.get("delta") is not None:
                st.metric("Δ win % (B−A)", _rbv_fmt_compare_delta(row_win.get("delta"), "Win %", row_win.get("pct_delta")))
            else:
                st.metric("Δ monthly payment", _rbv_fmt_compare_delta(row_pmt.get("delta"), "Monthly Payment", row_pmt.get("pct_delta")))

        # Compact secondary callouts.
        st.caption(
            " • ".join(
                [
                    f"Cash to close Δ: {_rbv_fmt_compare_delta(row_close.get('delta'), 'Cash to Close', row_close.get('pct_delta'))}",
                    f"PV advantage Δ: {_rbv_fmt_compare_delta(row_pv.get('delta'), 'Final PV Advantage', row_pv.get('pct_delta'))}",
                    f"Monthly payment Δ: {_rbv_fmt_compare_delta(row_pmt.get('delta'), 'Monthly Payment', row_pmt.get('pct_delta'))}",
                ]
            )
        )

        # Dual rendering overlay: Buyer/Renter NW for A vs B (same chart, deterministic).
        try:
            xa = pd.to_numeric(dfa.get("Month"), errors="coerce") / 12.0
            xb = pd.to_numeric(dfb.get("Month"), errors="coerce") / 12.0
            fig_cmp = go.Figure()
            fig_cmp.add_trace(go.Scatter(x=xa, y=dfa.get("Buyer Net Worth"), name="Buyer A", mode='lines', line=dict(color=BUY_COLOR, width=2)))
            fig_cmp.add_trace(go.Scatter(x=xa, y=dfa.get("Renter Net Worth"), name="Renter A", mode='lines', line=dict(color=RENT_COLOR, width=2)))
            fig_cmp.add_trace(go.Scatter(x=xb, y=dfb.get("Buyer Net Worth"), name="Buyer B", mode='lines', line=dict(color=BUY_COLOR, width=2, dash='dash')))
            fig_cmp.add_trace(go.Scatter(x=xb, y=dfb.get("Renter Net Worth"), name="Renter B", mode='lines', line=dict(color=RENT_COLOR, width=2, dash='dash')))
            fig_cmp.update_layout(
                template=pio.templates.default,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                hovermode='x unified',
                height=360,
                margin=dict(l=0, r=0, t=8, b=0),
                legend=dict(orientation='h', y=1.10, x=0.5, xanchor='center'),
                font=dict(family="Manrope, Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif", color="rgba(241,241,243,0.92)"),
            )
            fig_cmp.update_xaxes(title_text="Years", gridcolor="rgba(255,255,255,0.12)")
            fig_cmp.update_yaxes(title_text="Net worth", tickprefix="$", tickformat=",", gridcolor="rgba(255,255,255,0.12)")
            st.plotly_chart(_rbv_apply_plotly_theme(fig_cmp, height=360), use_container_width=True)
            st.caption("Solid = A, dashed = B. Compare preview runs deterministically for speed/stability.")
        except Exception:
            st.caption("Compare overlay chart unavailable for this pair.")

        # Delta engine table (B − A) for key terminal metrics.
        try:
            tbl_rows = []
            for r in rows:
                metric = str(r.get("metric") or "")
                a_val = r.get("a")
                b_val = r.get("b")
                d_val = r.get("delta")
                p_val = r.get("pct_delta")
                if metric == "Win %":
                    a_txt = _rbv_fmt_compare_metric(a_val, metric)
                    b_txt = _rbv_fmt_compare_metric(b_val, metric)
                    d_txt = _rbv_fmt_compare_delta(d_val, metric, p_val)
                else:
                    a_txt = _rbv_fmt_compare_metric(a_val, metric)
                    b_txt = _rbv_fmt_compare_metric(b_val, metric)
                    d_txt = _rbv_fmt_compare_delta(d_val, metric, p_val)
                tbl_rows.append({"Metric": metric, "A": a_txt, "B": b_txt, "Δ (B−A)": d_txt})
            if tbl_rows:
                st.markdown(render_fin_table(pd.DataFrame(tbl_rows), table_key="compare_metrics_ab"), unsafe_allow_html=True)
        except Exception:
            pass

        # State diff table for explainability.
        try:
            diff_rows = scenario_state_diff_rows(cmp_a.get("state"), cmp_b.get("state"), atol=1e-9)
            diff_rows_for_export = list(diff_rows or [])
            if diff_rows:
                view_rows = []
                for r in diff_rows[:30]:
                    view_rows.append({
                        "Input": str(r.get("key")),
                        "A": str(r.get("a")),
                        "B": str(r.get("b")),
                    })
                st.caption(f"Changed inputs: {len(diff_rows)}" + (" (showing first 30)" if len(diff_rows) > 30 else ""))
                st.markdown(render_fin_table(pd.DataFrame(view_rows), table_key="compare_state_diff_ab"), unsafe_allow_html=True)
            else:
                st.success("A and B snapshots are identical on all tracked scenario inputs (delta engine expects ~0 changes).")
        except Exception:
            pass

        # PR11 export cache: capture latest compare preview outputs for Export / Share downloads.
        try:
            st.session_state["_rbv_compare_last_export"] = {
                "schema": "rbv.compare_preview_cache.v1",
                "payload_a": payload_a,
                "payload_b": payload_b,
                "metrics_rows": rows,
                "state_diff_rows": diff_rows_for_export,
                "a_timeseries_csv": dfa.to_csv(index=False) if isinstance(dfa, pd.DataFrame) else None,
                "b_timeseries_csv": dfb.to_csv(index=False) if isinstance(dfb, pd.DataFrame) else None,
                "meta": {
                    "a_slot_summary": _rbv_compare_slot_summary("A"),
                    "b_slot_summary": _rbv_compare_slot_summary("B"),
                    "a_hash": str((cmp_a.get("meta") or {}).get("scenario_hash") or ""),
                    "b_hash": str((cmp_b.get("meta") or {}).get("scenario_hash") or ""),
                },
            }
        except Exception:
            st.session_state.pop("_rbv_compare_last_export", None)



# --- Shareable scenario URL (compact, bookmarkable) ---
# Encodes the allowed scenario state into a URL-safe token stored in query param `s`.
import base64
import zlib

def _rbv_state_to_share_token(state: dict) -> str:
    raw = json.dumps(state or {}, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    comp = zlib.compress(raw, level=9)
    return base64.urlsafe_b64encode(comp).decode("ascii").rstrip("=")

def _rbv_share_token_to_state(token: str) -> dict:
    t = (token or "").strip()
    if not t:
        return {}
    pad = "=" * ((4 - (len(t) % 4)) % 4)
    comp = base64.urlsafe_b64decode((t + pad).encode("ascii"))
    raw = zlib.decompress(comp)
    obj = json.loads(raw.decode("utf-8"))
    return obj if isinstance(obj, dict) else {}

def _rbv_get_query_params() -> dict:
    try:
        # Streamlit >= 1.31
        return dict(st.query_params)
    except Exception:
        try:
            return st.experimental_get_query_params()
        except Exception:
            return {}

def _rbv_set_query_params(**kwargs) -> None:
    try:
        st.query_params.clear()
        for k, v in kwargs.items():
            if v is None:
                continue
            st.query_params[k] = str(v)
    except Exception:
        try:
            st.experimental_set_query_params(**{k: v for k, v in kwargs.items() if v is not None})
        except Exception:
            pass

def _rbv_maybe_load_scenario_from_url() -> None:
    qp = _rbv_get_query_params() or {}
    token = qp.get("s", None)
    if isinstance(token, (list, tuple)):
        token = token[0] if token else None
    if not token:
        return
    if st.session_state.get("_rbv_loaded_share_token") == str(token):
        return

    try:
        state = _rbv_share_token_to_state(str(token))
        if state:
            _rbv_apply_scenario_state(state)
            st.session_state["_rbv_loaded_share_token"] = str(token)
            st.session_state.setdefault("_rbv_diag", []).append({"kind": "info", "message": "Loaded scenario from share link."})
    except Exception as e:
        st.session_state.setdefault("_rbv_diag", []).append({"kind": "warn", "message": f"Failed to load scenario from URL: {e}"})

def _rbv_build_results_bundle_bytes(df: pd.DataFrame, close_cash=None, m_pmt=None, win_pct=None) -> bytes:
    buf = io.BytesIO()
    payload = _rbv_make_scenario_payload()
    diag = st.session_state.get("_rbv_diag", [])
    hm = st.session_state.get("_rbv_last_heatmap", None)
    bias = st.session_state.get("_bias_dash_result", None)

    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as z:
        # Scenario + metadata
        z.writestr("scenario.json", json.dumps(payload, indent=2, default=str))
        z.writestr("version.txt", str(_rbv_version_line()))
        z.writestr("diagnostics.json", json.dumps(diag, indent=2, default=str))

        # Core time series
        try:
            if isinstance(df, pd.DataFrame):
                z.writestr("core_timeseries.csv", df.to_csv(index=False))
        except Exception:
            pass

        # Core summary
        try:
            summary = {
                "win_pct": None if win_pct is None else float(win_pct),
                "monthly_payment": None if m_pmt is None else float(m_pmt),
                "closing_cash": None if close_cash is None else float(close_cash),
            }
            if isinstance(df, pd.DataFrame) and len(df) > 0:
                last = df.iloc[-1].to_dict()
                # keep a small set if present
                for k in ["Buyer Net Worth", "Renter Net Worth", "Buyer_NW", "Renter_NW", "buyer_net_worth", "renter_net_worth"]:
                    if k in last:
                        summary[k] = last.get(k)
            z.writestr("core_summary.json", json.dumps(summary, indent=2, default=str))
        except Exception:
            pass

        # Heatmap (last computed)
        try:
            if isinstance(hm, dict) and isinstance(hm.get("Z"), np.ndarray):
                Z = hm.get("Z")
                app = hm.get("app")
                rentv = hm.get("rent")
                if isinstance(app, (list, tuple, np.ndarray)) and isinstance(rentv, (list, tuple, np.ndarray)):
                    _dfZ = pd.DataFrame(Z, index=[float(x) for x in rentv], columns=[float(x) for x in app])
                    z.writestr(f"heatmap_{str(hm.get('metric','metric')).replace(' ','_')}.csv", _dfZ.to_csv())
        except Exception:
            pass

        # Bias dashboard (last computed)
        try:
            if isinstance(bias, dict):
                _b = dict(bias)
                sens_df = _b.pop("sens_df", None)
                z.writestr("bias_dashboard.json", json.dumps(_b, indent=2, default=str))
                if isinstance(sens_df, pd.DataFrame):
                    z.writestr("bias_sensitivity.csv", sens_df.to_csv(index=False))
        except Exception:
            pass

    return buf.getvalue()

# --- CALLBACKS ---
def apply_preset():
    """Applies values from the selected dropdown preset."""
    selection = st.session_state.scenario_select
    if selection in PRESETS:
        vals = PRESETS[selection]
        st.session_state.rate = vals['rate']
        st.session_state.apprec = vals['apprec']
        st.session_state.general_inf = vals['general_inf']
        st.session_state.rent_inf = vals['rent_inf']
        st.session_state.buyer_ret = vals['buyer_ret']
        st.session_state.renter_ret = vals['renter_ret']

def check_custom():
    """Checks if current inputs match any preset; if not, switches dropdown to 'Custom'."""
    current = {
        'rate': st.session_state.rate,
        'apprec': st.session_state.apprec,
        'general_inf': st.session_state.general_inf,
        'rent_inf': st.session_state.rent_inf,
        'buyer_ret': st.session_state.buyer_ret,
        'renter_ret': st.session_state.renter_ret
    }

    match_found = False
    for name, vals in PRESETS.items():
        if all(np.isclose(current[k], vals[k]) for k in vals):
            if st.session_state.scenario_select != name:
                st.session_state.scenario_select = name
            match_found = True
            break

    if not match_found:
        if st.session_state.scenario_select != "Custom":
            st.session_state.scenario_select = "Custom"


def _rbv_fmt_short_value(v):
    if isinstance(v, bool):
        return "ON" if v else "OFF"
    try:
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            x = float(v)
            if abs(x) >= 1000.0:
                return f"{x:,.0f}"
            if abs(x).is_integer():
                return f"{x:.0f}"
            return f"{x:.2f}".rstrip("0").rstrip(".")
    except Exception:
        pass
    if v is None:
        return "—"
    return str(v)


def apply_city_preset() -> None:
    """Apply selected city preset to session state (R3 preview)."""
    selection = str(st.session_state.get("city_preset", CITY_PRESET_CUSTOM) or CITY_PRESET_CUSTOM)
    changes = apply_city_preset_values(st.session_state, selection)
    st.session_state["_rbv_city_preset_last_name"] = selection
    if selection == CITY_PRESET_CUSTOM:
        st.session_state["_rbv_city_preset_last_summary_lines"] = []
        st.session_state["_rbv_city_preset_last_banner"] = "City preset cleared (Custom). Manual values are unchanged."
        return

    lines = build_city_preset_change_summary(changes, max_items=8)
    st.session_state["_rbv_city_preset_last_summary_lines"] = lines
    if changes:
        st.session_state["_rbv_city_preset_last_banner"] = f"Applied {selection}: {len(changes)} field{'s' if len(changes) != 1 else ''} updated."
    else:
        st.session_state["_rbv_city_preset_last_banner"] = f"{selection} already matches current inputs."


def _render_city_preset_summary_sidebar() -> None:
    banner = str(st.session_state.get("_rbv_city_preset_last_banner", "") or "").strip()
    if banner:
        sidebar_hint(banner)
    lines = st.session_state.get("_rbv_city_preset_last_summary_lines", [])
    if isinstance(lines, list) and lines:
        safe_items = "".join([f"<li>{html.escape(str(x))}</li>" for x in lines if str(x).strip()])
        if safe_items:
            st.markdown(f"<ul class='rbv-hint' style='margin:4px 0 8px 16px; padding-left:10px;'>{safe_items}</ul>", unsafe_allow_html=True)

# --- 3. DARK FINTECH THEME (CSS) ---
# --- UI override: sidebar inputs + tooltip styling + help-icon alignment (robust) ---
# --- FINAL THEME PATCHES (v101): verdict banner + tooltip consistency + dropdown menus ---
# --- Transfer/Property Tax helpers (Canada) ---
# This app includes built-in estimates for common provincial transfer taxes / registration fees.
# Some provinces (notably NS and QC) can vary by municipality; in those cases we provide a reasonable
# default and encourage using 'Transfer Tax Override' for a precise local estimate.

# --- v2_26: UNIFY NUMBER INPUT + SELECT VISUALS (single cohesive border + rounded corners) ---
# --- v126: TOOLTIP PADDING FIX (prevents clipped first letter in sidebar help tooltips) ---
# --- 4. SIDEBAR INPUTS ---
# --- DEFAULTS FOR EXPANDER-ONLY INPUTS (avoid NameError on reruns) ---
# These are overridden inside the sidebar expanders below.
r_ins = 30
r_util = 0
moving_cost = 3000
moving_freq = 5



# --- Defensive defaults (Streamlit rerun-safe) ---
# Streamlit can rerun scripts before conditional widgets initialize variables.
# These defaults prevent NameError; sidebar inputs will override them normally.
years = st.session_state.get("years", 25)
general_inf = st.session_state.get("general_inf", 2.5) / 100
discount_rate = 0.03
tax_r = 0.0

invest_surplus_input = True
renter_uses_closing_input = True
market_corr_input = 0.8

use_volatility = bool(st.session_state.get("use_volatility", False))
# Always derive vol/sim defaults from session state so MC features (heatmap/bias) stay consistent
# even when the sidebar volatility widgets are collapsed.
ret_std = float(st.session_state.get("ret_std_pct", 15.0)) / 100.0
apprec_std = float(st.session_state.get("apprec_std_pct", 5.0)) / 100.0
num_sims = int(st.session_state.get("num_sims", 1000))
mc_seed_text = ""

# Buying defaults
price = 800000.0
down = 160000.0
rate = st.session_state.get("rate", 4.0)
amort = 25
apprec = st.session_state.get("apprec", 3.5) / 100
sell_cost = 0.05
buyer_inv_ret = st.session_state.get("buyer_ret", 7.5)

lawyer = float(st.session_state.get("purchase_legal_fee", 1800.0) or 1800.0)
insp = float(st.session_state.get("home_inspection", 500.0) or 500.0)
other_closing = float(st.session_state.get("other_closing_costs", 0.0) or 0.0)
province = str(st.session_state.get("province", "Ontario") or "Ontario")
if province not in PROVINCES:
    province = "Ontario"
toronto = bool(st.session_state.get("toronto", False))
first_time = bool(st.session_state.get("first_time", True))
# Province-specific transfer-tax helpers
assessed_value = float(st.session_state.get("assessed_value", price) or price) if province in ("New Brunswick", "Prince Edward Island") else None
ns_deed_transfer_rate = (float(st.session_state.get("ns_deed_transfer_rate_pct", 1.5) or 1.5) / 100.0) if province == "Nova Scotia" else None

transfer_tax_override = 0.0

p_tax_rate = 0.01
maint_rate = 0.01
repair_rate = 0.005
condo = 0.0
h_ins = 120.0
o_util = 0.0

# Renting defaults
rent = 3000.0
rent_inf = st.session_state.get("rent_inf", 2.5) / 100
renter_inv_ret = st.session_state.get("renter_ret", 7.5)
moving_cost = 1500.0
moving_freq = 5
r_ins = 30.0
r_util = 0.0

# Grok improvements defaults

# Ensure engine passthrough kwargs are always defined (prevents NameError on reruns)
extra_engine_kwargs = {}

rate_mode = "Fixed"
rate_reset_years = 5
rate_reset_to = rate
rate_reset_step_pp = 0.0
rent_control_enabled = False
rent_control_cap = 0.025

# Mortgage renewal stress test defaults
rate_shock_enabled = False
rate_shock_start_year = 5
rate_shock_duration_years = 5
rate_shock_pp = 2.0



# Load scenario from share-link (URL param) before rendering widgets
_rbv_maybe_load_scenario_from_url()

with st.sidebar:
    # Stop long-running computations (Heatmap / Bias / Monte Carlo). Clicking triggers a rerun which interrupts at the next UI update.
    try:
        # Destructive action: render as a red (secondary) button.
        try:
            st.button(
                "Stop current run",
                use_container_width=True,
                key="rbv_cancel_btn",
                on_click=_rbv_request_cancel,
                type="secondary",
            )
        except TypeError:
            st.button(
                "Stop current run",
                use_container_width=True,
                key="rbv_cancel_btn",
                on_click=_rbv_request_cancel,
            )
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
    except Exception:
        pass
        # --- Sidebar hover-tooltips (custom, dark; avoids Streamlit/BaseWeb help icons) ---
    # IMPORTANT: Streamlit reruns this script in the same Python process. If we wrap st.* widgets
    # repeatedly, wrappers stack and labels/tooltips duplicate. Make this patch idempotent.
    _RBV_SB_WIDGETS = ["number_input", "slider", "selectbox", "multiselect", "radio", "checkbox", "toggle", "text_input"]

    try:
        if not hasattr(st, "__rbv_sb_orig_funcs"):
            st.__rbv_sb_orig_funcs = {}
            for _wname in _RBV_SB_WIDGETS:
                if hasattr(st, _wname):
                    st.__rbv_sb_orig_funcs[_wname] = getattr(st, _wname)
        else:
            # Restore true originals each rerun (prevents wrapper nesting).
            for _wname, _fn in getattr(st, "__rbv_sb_orig_funcs", {}).items():
                try:
                    setattr(st, _wname, _fn)
                except Exception:
                    pass
    except Exception:
        pass

    def _rbv_sb_wrap(_orig_fn):
        def _wrapped(label=None, *args, **kwargs):
            _label = label if label is not None else kwargs.get("label", "")
            _help_tip = kwargs.pop("help", None)
            if isinstance(_label, str) and _label.strip():
                # Prefer an explicit help= string; otherwise consult our tooltip registry.
                # If neither exists, render the label without an info icon (no generic "Adjust..." tooltips).
                _tip = _help_tip if isinstance(_help_tip, str) and _help_tip.strip() else RBV_SIDEBAR_TOOLTIPS.get(_label, None)
                sidebar_label(_label, _tip)
                kwargs.setdefault("label_visibility", "collapsed")
            try:
                return _orig_fn(_label, *args, **kwargs)
            except TypeError as _e:
                # Backward-compat if a Streamlit version does not support label_visibility on this widget
                if "label_visibility" in kwargs:
                    kwargs.pop("label_visibility", None)
                    return _orig_fn(_label, *args, **kwargs)
                raise
        return _wrapped

    try:
        for _wname, _fn in getattr(st, "__rbv_sb_orig_funcs", {}).items():
            setattr(st, _wname, _rbv_sb_wrap(_fn))
    except Exception:
        pass

    # --- HEADER 1: Settings (White) ---
    st.markdown('<div class="sidebar-header-gen">⚙️ Settings</div>', unsafe_allow_html=True)
    # Phase 3 UX simplification: basic vs advanced control density.
    st.session_state.setdefault("ui_mode", "Advanced")
    _ui_mode = st.radio(
        "Interface mode",
        ["Basic", "Advanced"],
        horizontal=True,
        index=(0 if str(st.session_state.get("ui_mode", "Advanced")) == "Basic" else 1),
        key="ui_mode",
    )
    _show_advanced_controls = (_ui_mode == "Advanced")
    _prev_ui_mode = st.session_state.get("_rbv_ui_mode_prev", _ui_mode)
    if _prev_ui_mode != _ui_mode:
        st.session_state["_rbv_ui_mode_prev"] = _ui_mode
        # Force CSS reinjection on mode transitions: Streamlit can recreate DOM/style tags
        # during reruns and dedupe logic may otherwise skip an identical stylesheet.
        st.session_state["_rbv_force_css_reinject"] = True
        st.rerun()
    else:
        st.session_state["_rbv_ui_mode_prev"] = _ui_mode
    if not _show_advanced_controls:
        st.caption("Basic mode hides expert controls to reduce clutter. Switch to **Advanced** for full modeling options.")
    # Public/Power mode toggle removed (v2_41).

    # Scenario save/load (public-friendly)
    with st.expander("Scenario", expanded=False):
        if not _show_advanced_controls:
            st.info("Quick flow: **Download/Load** for backup, then use **Save → A/B** and **Load A/B** to compare two scenarios.")
        try:
            _payload = _rbv_make_scenario_payload()
            _json = json.dumps(_payload, indent=2, default=str)
            try:
                st.download_button(
                    "Download scenario (.json)",
                    data=_json,
                    file_name="rbv_scenario.json",
                    mime="application/json",
                    use_container_width=True,
                    type="primary",
                )
            except TypeError:
                st.download_button(
                    "Download scenario (.json)",
                    data=_json,
                    file_name="rbv_scenario.json",
                    mime="application/json",
                    use_container_width=True,
                )
        except Exception:
            pass

        # Shareable link (URL param). Click to update your browser URL, then copy it from the address bar.
        try:
            if st.button("Generate share link", use_container_width=True, key="rbv_share_link_btn"):
                _state = _rbv_capture_scenario_state()
                _tok = _rbv_state_to_share_token(_state)
                st.session_state["_rbv_share_token"] = _tok
                _rbv_set_query_params(s=_tok)
                st.rerun()
        except Exception:
            pass

        try:
            _tok_now = st.session_state.get("_rbv_share_token")
            if not _tok_now:
                _qp = _rbv_get_query_params() or {}
                _tok_now = _qp.get("s", None)
                if isinstance(_tok_now, (list, tuple)):
                    _tok_now = _tok_now[0] if _tok_now else None
            if _tok_now:
                st.text_input("Share token (URL param)", value=f"s={_tok_now}", disabled=True)
                st.caption("Tip: the URL in your browser has been updated. Copy it to bookmark/share this scenario.")
        except Exception:
            pass




        _up = st.file_uploader("Load scenario (.json)", type=["json"], key="rbv_scenario_upload")
        if _up is not None:
            try:
                _raw = _up.getvalue()
                _h = hashlib.sha256(_raw).hexdigest()[:12]
                if st.session_state.get("_rbv_loaded_scenario_hash") != _h:
                    try:
                        _obj = json.loads(_raw.decode("utf-8"))
                    except Exception:
                        _obj = json.loads(_raw)
                    _state, _meta = _rbv_parse_imported_scenario(_obj if isinstance(_obj, dict) else {})
                    _rbv_apply_scenario_state(_state)
                    _canon_h = str((_meta or {}).get("scenario_hash") or scenario_hash_from_state(_state, allowed_keys=_rbv_scenario_allowed_keys()))
                    st.session_state["_rbv_loaded_scenario_hash"] = _h
                    st.session_state["_rbv_loaded_scenario_msg"] = f"Scenario loaded ({_canon_h[:12]})."
                    st.rerun()
            except Exception:
                st.session_state["_rbv_loaded_scenario_msg"] = "Failed to load scenario JSON."

        _msg = st.session_state.get("_rbv_loaded_scenario_msg", "")
        if isinstance(_msg, str) and _msg.strip():
            sidebar_hint(_msg)

        # PR9/PR10: local A/B compare snapshots (state + deterministic hash) + slot ops.
        st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
        sidebar_label("Scenario Compare slots (A/B)", "Save, load, swap, and copy scenario snapshots. PR10 renders deterministic A/B deltas side-by-side from these slots.")
        _col_save_a, _col_save_b = st.columns(2)
        with _col_save_a:
            if st.button("Save → A", key="rbv_save_ab_a", use_container_width=True):
                _rbv_save_compare_snapshot("A")
        with _col_save_b:
            if st.button("Save → B", key="rbv_save_ab_b", use_container_width=True):
                _rbv_save_compare_snapshot("B")

        _col_load_a, _col_load_b = st.columns(2)
        with _col_load_a:
            if st.button("Load A", key="rbv_load_ab_a", use_container_width=True):
                _rbv_load_compare_snapshot("A")
        with _col_load_b:
            if st.button("Load B", key="rbv_load_ab_b", use_container_width=True):
                _rbv_load_compare_snapshot("B")

        _col_swap, _col_copy = st.columns(2)
        with _col_swap:
            if st.button("Swap A ↔ B", key="rbv_swap_ab", use_container_width=True):
                _rbv_swap_compare_snapshots()
                st.rerun()
        with _col_copy:
            if st.button("Copy A → B", key="rbv_copy_a_to_b", use_container_width=True):
                _rbv_copy_compare_snapshot("A", "B")
                st.rerun()

        _col_copy_ba, _col_clr_a, _col_clr_b = st.columns([1.2, 1, 1])
        with _col_copy_ba:
            if st.button("Copy B → A", key="rbv_copy_b_to_a", use_container_width=True):
                _rbv_copy_compare_snapshot("B", "A")
                st.rerun()
        with _col_clr_a:
            if st.button("Clear A", key="rbv_clear_ab_a", use_container_width=True):
                _rbv_clear_compare_snapshot("A")
        with _col_clr_b:
            if st.button("Clear B", key="rbv_clear_ab_b", use_container_width=True):
                _rbv_clear_compare_snapshot("B")

        st.caption(f"Active scenario hash: {_rbv_scenario_hash_short()}")
        st.caption(_rbv_compare_slot_summary("A"))
        st.caption(_rbv_compare_slot_summary("B"))
    with st.expander("Economic Scenario", expanded=False):
        st.selectbox(
            "Economic Scenario",
            ["Baseline", "High Inflation", "Stagnation", "Custom"],
            key="scenario_select",
            on_change=apply_preset,
            label_visibility="collapsed",
        )


    with st.expander("Simulation Horizon", expanded=True):
        if not _show_advanced_controls:
            st.caption("Set your analysis years first. Longer horizons increase uncertainty and can widen Buy vs Rent outcome ranges.")
        years = st.number_input("Analysis Duration (Years)", min_value=1, max_value=50, step=1, key='years', label_visibility="collapsed")

        general_inf = st.number_input(
            "General Inflation Rate (%)",
            min_value=-5.0, max_value=15.0,
            step=0.1, format="%.2f",
            key="general_inf", on_change=check_custom,
            label_visibility="collapsed",
        ) / 100

        # --- TOOLTIPS (ESCAPED DOLLAR SIGNS) ---
        discount_rate = st.number_input(
            "PV (Discount) Rate (%)",
            value=3.0, step=0.1, format="%.2f",
            key="discount_rate",
            label_visibility="collapsed",
        ) / 100

    with st.expander("Taxes & Cash-out", expanded=False):
        if not _show_advanced_controls:
            st.info("For most users: keep **Pre-tax** for quick comparisons, then check **Deferred capital gains at end** to view after-tax cash-out results.")
        # Tax schedule "as of" date (used for date-dependent rules like Toronto MLTT >$3M brackets).
        _asof_default = datetime.date.today()
        _raw_asof = st.session_state.get("tax_rules_asof", _asof_default)
        if isinstance(_raw_asof, str):
            try:
                _raw_asof = datetime.date.fromisoformat(_raw_asof[:10])
            except Exception:
                _raw_asof = _asof_default
        elif isinstance(_raw_asof, datetime.datetime):
            _raw_asof = _raw_asof.date()
        elif not isinstance(_raw_asof, datetime.date):
            _raw_asof = _asof_default

        sidebar_label("Tax rules as of", "Date used to select date-dependent tax schedules (e.g., Toronto MLTT luxury brackets).")
        st.date_input("Tax rules as of", value=_raw_asof, key="tax_rules_asof", label_visibility="collapsed")



        # --- Investment Taxes  ---
        # Legacy label migration (older versions used "Annual return drag (simple)")
        if st.session_state.get("investment_tax_mode") == "Annual return drag (simple)":
            st.session_state["investment_tax_mode"] = "Annual return drag"

        investment_tax_mode = st.selectbox(
            "Investment Tax Modeling",
            options=[
                "Pre-tax (no investment taxes)",
                "Annual return drag",
                "Deferred capital gains at end (liquidation)",
            ],
            key="investment_tax_mode",
            label_visibility="collapsed",
        )
        sidebar_hint('Main net worth charts are pre-tax. Use the cash-out view to see deferred capital gains. "Annual return drag" affects both portfolios and will change net worth paths when the tax rate is > 0%.')

        # Default values (overridden by the active mode)
        tax_r = 0.0            # annual drag (%)
        cg_tax_end = 0.0       # effective CG tax on gains at liquidation (%)

        if investment_tax_mode == "Annual return drag":
            tax_r = st.number_input(
                "Tax on Investment Gains (%)",
                value=float(st.session_state.get("tax_r", 0.0)),
                min_value=0.0,
                max_value=50.0,
                step=1.0,
                format="%.2f",
                key="tax_r",
            )
        elif investment_tax_mode == "Deferred capital gains at end (liquidation)":
            cg_tax_end = st.number_input(
                "Effective Capital Gains Tax at End (%)",
                min_value=0.0,
                max_value=60.0,
                step=0.5,
                format="%.2f",
                key="cg_tax_end",
            )
        else:
            sidebar_hint("Pre-tax view: investment taxes are not applied.")



        # --- Results display (cash-out view at horizon) ---
        sidebar_label("Cash-out view at horizon", "Shows an end-of-horizon 'cash in hand' view: home equity (net of selling costs if enabled) plus the after-tax investment portfolio. This helps compare outcomes on a liquidation basis.")
        if "show_liquidation_view" not in st.session_state:
            st.session_state["show_liquidation_view"] = True

        show_liquidation_view = st.checkbox(
            "Show cash-out view at horizon (after-tax / after-selling)",
            key="show_liquidation_view",
        )

        # If liquidation view is enabled but we're not already in deferred-CG mode, expose the CG-at-end rate used only for the cash-out view.
        if show_liquidation_view and investment_tax_mode != "Deferred capital gains at end (liquidation)":
            cg_tax_end = st.number_input(
                "Effective Capital Gains Tax at End (%)",
                min_value=0.0,
                max_value=60.0,
                step=0.5,
                format="%.2f",
                key="cg_tax_end",
            )
        # Whether to assume the home is sold at the horizon (affects selling costs + cash-out composition).
        # If disabled, the cash-out view excludes home equity (home treated as held).
        st.session_state.setdefault("assume_sale_end", True)
        assume_sale_end = bool(st.session_state.get("assume_sale_end", True))

        if show_liquidation_view:
            assume_sale_end = st.checkbox(
                "Assume home sold at horizon (apply selling costs)",
                key="assume_sale_end",
            )
            if not bool(assume_sale_end):
                st.caption("Home treated as held at horizon — cash-out view excludes home equity and selling costs.")

        st.session_state.setdefault("is_principal_residence", True)
        if show_liquidation_view and bool(assume_sale_end):
            is_principal_residence = st.checkbox(
                "Home is principal residence (no capital gains tax on sale)",
                key="is_principal_residence",
            )
            if not bool(is_principal_residence):
                st.warning("Non-principal residence: home sale may be subject to capital gains tax (simplified sensitivity).")
        else:
            is_principal_residence = bool(st.session_state.get("is_principal_residence", True))
        home_sale_legal_fee = 0.0
        if show_liquidation_view and bool(assume_sale_end):
            home_sale_legal_fee = st.number_input(
                "Home Sale Legal/Closing Fee at Exit ($)",
                min_value=0.0,
                step=100.0,
                format="%.0f",
                key="home_sale_legal_fee",
            )
        elif show_liquidation_view and (not bool(assume_sale_end)):
            # Keep the key stable but force 0 for correctness when home is held.
            st.session_state["home_sale_legal_fee"] = 0.0


        # --- Advanced (opt-in) cash-out layers ---
        # These should never silently change baseline results: they are sensitivity knobs only.
        expert_mode = bool(st.session_state.get("expert_mode", False))

        if show_liquidation_view:
            st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
            sidebar_label(
                "Expert mode",
                "Shows advanced sensitivity toggles (hypothetical policy + registered shelter approximation). Off by default.",
            )

            def _rbv_on_expert_mode_change():
                if not bool(st.session_state.get("expert_mode", False)):
                    # When expert mode is disabled, force advanced toggles back to safe defaults.
                    st.session_state["cg_inclusion_policy"] = "Current (50% inclusion)"
                    st.session_state.setdefault("cg_inclusion_threshold", 250000.0)
                    st.session_state["reg_shelter_enabled"] = False

            st.checkbox(
                "Expert mode (show sensitivity toggles)",
                key="expert_mode",
                on_change=_rbv_on_expert_mode_change,
            )

            # Micro-UX: make it obvious that advanced sensitivity controls exist but are intentionally hidden.
            if bool(st.session_state.get("expert_mode", False)):
                st.caption("🔓 Expert mode enabled — advanced sensitivities unlocked below.")
            else:
                st.caption("🔒 Advanced settings are locked — enable Expert mode to unlock policy + registered-shelter toggles.")

            expert_mode = bool(st.session_state.get("expert_mode", False))

            if not expert_mode:
                # Enforce safe defaults even if a prior session had advanced values.
                st.session_state["cg_inclusion_policy"] = "Current (50% inclusion)"
                st.session_state.setdefault("cg_inclusion_threshold", 250000.0)
                st.session_state["reg_shelter_enabled"] = False
                sidebar_hint("Expert mode is off: cash-out uses your 'Effective Capital Gains Tax at End (%)' under current 50% inclusion; no registered-shelter approximation is applied.")

        if show_liquidation_view and expert_mode:
            st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
            sidebar_label(
                "Capital gains inclusion policy (expert)",
                "Optional sensitivity toggle applied only to portfolio gains in the cash-out view. Does not model a full tax engine.",
            )

            cg_inclusion_policy = st.selectbox(
                "Capital gains inclusion policy",
                options=[
                    "Current (50% inclusion)",
                    "Hypothetical tiered (2/3 inclusion over threshold)",
                ],
                key="cg_inclusion_policy",
                label_visibility="collapsed",
            )

            if str(cg_inclusion_policy).startswith("Hypothetical"):
                st.number_input(
                    "Tier threshold ($ gains in liquidation year)",
                    min_value=0.0,
                    step=10_000.0,
                    format="%.0f",
                    key="cg_inclusion_threshold",
                )
                sidebar_hint("Sensitivity only: above the threshold, the effective CG tax rate is scaled by 4/3 (50% → 66.67% inclusion).")
            else:
                # Keep threshold defined for config stability (unused in 'Current' mode)
                st.session_state.setdefault("cg_inclusion_threshold", 250000.0)

            st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
            sidebar_label(
                "Registered-account shelter (TFSA/RRSP) — conservative approximation",
                "Optional sensitivity knob that reduces taxable portfolio gains in the cash-out view, using a pro-rata shelter based on available room.",
            )
            reg_shelter_enabled = st.checkbox(
                "Enable registered shelter approximation",
                value=bool(st.session_state.get("reg_shelter_enabled", False)),
                key="reg_shelter_enabled",
            )

            if reg_shelter_enabled:
                st.number_input(
                    "Registered room available now ($)",
                    min_value=0.0,
                    step=5_000.0,
                    format="%.0f",
                    key="reg_initial_room",
                )
                st.number_input(
                    "New room per year ($/yr)",
                    min_value=0.0,
                    step=1_000.0,
                    format="%.0f",
                    key="reg_annual_room",
                )
                sidebar_hint("Conservative: shelters gains pro‑rata based on sheltered basis; does not model RRSP refunds or withdrawal taxation.")



    if _show_advanced_controls:
        with st.expander("🧠 Behavioral & Advanced", expanded=False):
            # IMPORTANT UX / modeling guardrail:
            # Turning off surplus investing can massively bias results and is easy to misinterpret.
            # We therefore lock it ON unless Expert mode is enabled.
            _expert_mode = bool(st.session_state.get("expert_mode", False))
            if (not _expert_mode) and ("invest_surplus_input" in st.session_state) and (not bool(st.session_state.get("invest_surplus_input", True))):
                st.session_state["invest_surplus_input"] = True
            invest_surplus_input = st.checkbox(
                "Invest Monthly Surplus?",
                value=bool(st.session_state.get("invest_surplus_input", True)),
                key="invest_surplus_input",
                disabled=(not _expert_mode),
            )
            if not _expert_mode:
                st.caption("Standard mode: surplus investing is locked **ON** (economic realism + safer comparisons).")
            if "renter_uses_closing_input" not in st.session_state:
                st.session_state["renter_uses_closing_input"] = True
            renter_uses_closing_input = st.checkbox(
                "Renter Invests Closing Costs?",
                key="renter_uses_closing_input",
            )

            st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)
            market_corr_input = st.slider("Correlation (ρ)", -1.0, 1.0, value=0.8, key="market_corr_input")

            st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)
            crisis_enabled = st.checkbox(
                "Add crisis shock event",
                value=bool(st.session_state.get("crisis_enabled", False)),
                key="crisis_enabled",
            )
            _years_cap = int(st.session_state.get("years", 25))
            if crisis_enabled:
                crisis_year = st.number_input("Crisis year", min_value=1, max_value=_years_cap, value=min(5, _years_cap), step=1)
                crisis_duration_months = st.select_slider("Shock duration (months)", options=[1, 3, 6, 12], value=1)
                crisis_stock_dd = st.slider("Stock drawdown (%)", 0, 90, 35) / 100
                crisis_house_dd = st.slider("Home price drawdown (%)", 0, 90, 20) / 100
                # ⚠️ Compounding warning — each % applies PER MONTH over the duration
                if crisis_duration_months > 1:
                    _total_stock = 1 - (1 - crisis_stock_dd) ** crisis_duration_months
                    _total_house = 1 - (1 - crisis_house_dd) ** crisis_duration_months
                    st.caption(
                        f"⚠️ **Compounding note:** each drawdown % applies *every month* of the shock duration. "
                        f"Over {crisis_duration_months} months: stock total drop ≈ **{_total_stock:.0%}**, "
                        f"home total drop ≈ **{_total_house:.0%}**. "
                        f"For a one-time correction (e.g. '20% total'), set duration to **1 month**."
                    )
            else:
                crisis_year = 5
                crisis_duration_months = 1
                crisis_stock_dd = 0.35
                crisis_house_dd = 0.20

            st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)
            budget_enabled = st.checkbox(
                "Enable income/budget constraints (experimental)",
                value=bool(st.session_state.get("budget_enabled", False)),
                key="budget_enabled",
            )
            # If the user disables surplus investing (expert-only), make the modeling consequence explicit.
            if _expert_mode and (not bool(invest_surplus_input)) and (not bool(budget_enabled)):
                st.error(
                    "Surplus investing is **OFF** — the model routes any monthly advantage into **cash (0% yield)** (not invested). "
                    "This can strongly favor the more expensive option in long-horizon net-worth results.",
                    icon="⚠️",
                )
            if budget_enabled and bool(invest_surplus_input):
                st.caption("Budget mode is ON — the model uses income/budget cashflows, so monthly-surplus investing is ignored.")
            if budget_enabled:
                monthly_income = st.number_input("After-tax household income ($/mo)", value=12000, min_value=0, step=100)
                monthly_nonhousing = st.number_input(
                    "Non-housing spending ($/mo)",
                    value=7000,
                    min_value=0,
                    step=100,
                )
                income_growth_pct = st.number_input("Income growth (%/yr)", value=3.0, step=0.1, format="%.2f")
                budget_allow_withdraw = st.checkbox(
                    "Allow portfolio drawdown to fund deficits",
                    value=bool(st.session_state.get("budget_allow_withdraw", True)),
                    key="budget_allow_withdraw",
                )
            else:
                monthly_income = 0.0
                monthly_nonhousing = 0.0
                income_growth_pct = 0.0
                budget_allow_withdraw = True

            st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)
            rate_mode = st.selectbox(
                "Mortgage Rate Mode",
                options=["Fixed", "Reset every N years"],
                index=(0 if st.session_state.get("rate_mode", "Fixed") == "Fixed" else 1),
                key="rate_mode",
    )
            rate_reset_years = None
            rate_reset_to = None
            rate_reset_step_pp = 0.0
            if rate_mode == "Reset every N years":
                rate_reset_years = st.number_input(
                    "Reset Frequency (Years)",
                    value=int(st.session_state.get("rate_reset_years", 5) or 5),
                    key="rate_reset_years",
                    step=1,
                    min_value=1,
                    max_value=10,
    )
                rate_reset_to = st.number_input(
                    "Rate at Reset (%)",
                    value=float(st.session_state.get("rate_reset_to", float(rate)) or float(rate)),
                    key="rate_reset_to",
                    step=0.1,
                    format="%.2f",
                    min_value=0.0,
    )
                rate_reset_step_pp = st.number_input(
                    "Rate Change Per Reset (pp)",
                    value=float(st.session_state.get("rate_reset_step_pp", 0.0) or 0.0),
                    key="rate_reset_step_pp",
                    step=0.1,
                    format="%.2f",
    )
            st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)
            rate_shock_enabled = st.checkbox(
                "Stress test: +2% rate shock at Year 5",
                value=False,
    )
            # Safe defaults (advanced controls kept implicit to avoid UI bloat)
            rate_shock_start_year = 5
            rate_shock_duration_years = 5
            rate_shock_pp = 2.0
    # Engine extras: passed through to the simulator so sensitivity checks + heatmaps stay consistent.
    # Also stash in session_state so downstream calls can always rebuild the dict even if UI branches change.
    extra_engine_kwargs = dict(
        crisis_enabled=bool(locals().get('crisis_enabled', st.session_state.get('crisis_enabled', False))),
        crisis_year=int(locals().get('crisis_year', st.session_state.get('crisis_year', 0) or 0)),
        crisis_stock_dd=float(locals().get('crisis_stock_dd', st.session_state.get('crisis_stock_dd', 0.0) or 0.0)),
        crisis_house_dd=float(locals().get('crisis_house_dd', st.session_state.get('crisis_house_dd', 0.0) or 0.0)),
        crisis_duration_months=int(locals().get('crisis_duration_months', st.session_state.get('crisis_duration_months', 0) or 0)),
        budget_enabled=bool(locals().get('budget_enabled', st.session_state.get('budget_enabled', False))),
        monthly_income=float(locals().get('monthly_income', st.session_state.get('monthly_income', 0.0) or 0.0)),
        monthly_nonhousing=float(locals().get('monthly_nonhousing', st.session_state.get('monthly_nonhousing', 0.0) or 0.0)),
        income_growth_pct=float(locals().get('income_growth_pct', st.session_state.get('income_growth_pct', 0.0) or 0.0)),
        budget_allow_withdraw=bool(locals().get('budget_allow_withdraw', st.session_state.get('budget_allow_withdraw', True))),
    )
    st.session_state['_rbv_extra_engine_kwargs'] = extra_engine_kwargs


    with st.expander("Monte Carlo", expanded=True):
        # --- Performance mode (Fast / Quality) ---
        # We render a single header with a custom help bubble that *dynamically* reflects
        # current presets + any user overrides. The radio widget itself has a blank label
        # to avoid duplicated "Performance mode" headers.
        st.session_state.setdefault("sim_mode", "Fast")
        sim_mode = str(st.session_state.get("sim_mode", "Fast") or "Fast")
        if sim_mode not in ("Fast", "Quality"):
            sim_mode = "Fast"
            st.session_state["sim_mode"] = "Fast"
        fast_mode = (sim_mode == "Fast")

        if not _show_advanced_controls:
            st.info("Using **Basic mode** defaults for simulation controls. Switch sidebar Interface mode to **Advanced** to tune Monte Carlo overrides and behavioral stress settings.")

        # Horizon-aware guidance for advanced overrides.
        # Larger horizons multiply the monthly simulation workload and can trigger slow, non-vectorized fallbacks.
        try:
            years = int(st.session_state.get("years", 25) or 25)
        except Exception:
            years = 25

        def _mc_cap_for_horizon(yrs: int) -> int:
            """Soft cap for Main MC sims used only for a UI warning.

            This does NOT clamp user input. It's a guardrail to reduce accidental long runs.
            """
            if yrs <= 10:
                return 200_000
            if yrs <= 20:
                return 150_000
            if yrs <= 30:
                return 100_000
            if yrs <= 40:
                return 80_000
            return 60_000

        _mc_cap = _mc_cap_for_horizon(years)

        # Mode presets (public-facing simplification: no manual sim/grid tweaking required)
        # Main Monte Carlo sims (single-scenario analysis)
        FAST_DEFAULT_NUM_SIMS = 50_000
        # Quality defaults tuned for Streamlit Cloud reliability while keeping statistical meaning.
        # (User request: keep Quality statistically meaningful while lowering server memory: main MC=90k, grid≈41, heatmap sims=20k; bias sims unchanged.)
        QUALITY_DEFAULT_NUM_SIMS = 90_000

        # Heatmap MC sims (shared across the whole grid via batched execution)
        FAST_HM_MC_SIMS_DEFAULT = 15_000
        QUALITY_HM_MC_SIMS_DEFAULT = 20_000

        # Bias solver MC sims (used inside bisection / flip-point search)
        FAST_BIAS_MC_SIMS_DEFAULT = 15_000
        QUALITY_BIAS_MC_SIMS_DEFAULT = 30_000

        # Heatmap grid defaults
        FAST_HM_GRID_DEFAULT = 31
        QUALITY_HM_GRID_DEFAULT = 41

        # Deterministic heatmaps can render at a higher grid without significant cost (exact batched eval).
        # In Public Mode we automatically bump grid resolution for deterministic heatmap metrics for smoother visuals.
        FAST_HM_GRID_DET_MIN_PUBLIC = 61
        QUALITY_HM_GRID_DET_MIN_PUBLIC = 41

        st.session_state.setdefault("num_sims", FAST_DEFAULT_NUM_SIMS if fast_mode else QUALITY_DEFAULT_NUM_SIMS)
        st.session_state.setdefault("hm_grid_size", FAST_HM_GRID_DEFAULT if fast_mode else QUALITY_HM_GRID_DEFAULT)
        st.session_state.setdefault("hm_mc_sims", FAST_HM_MC_SIMS_DEFAULT if fast_mode else QUALITY_HM_MC_SIMS_DEFAULT)
        st.session_state.setdefault("bias_mc_sims", FAST_BIAS_MC_SIMS_DEFAULT if fast_mode else QUALITY_BIAS_MC_SIMS_DEFAULT)

        # If the user flips mode, push the matching defaults (keeps UX predictable).
        if "_sim_mode_prev" not in st.session_state:
            st.session_state["_sim_mode_prev"] = sim_mode
        if sim_mode != st.session_state.get("_sim_mode_prev"):
            if fast_mode:
                st.session_state["num_sims"] = FAST_DEFAULT_NUM_SIMS
                st.session_state["hm_grid_size"] = FAST_HM_GRID_DEFAULT
                st.session_state["hm_mc_sims"] = FAST_HM_MC_SIMS_DEFAULT
                st.session_state["bias_mc_sims"] = FAST_BIAS_MC_SIMS_DEFAULT
            else:
                st.session_state["num_sims"] = QUALITY_DEFAULT_NUM_SIMS
                st.session_state["hm_grid_size"] = QUALITY_HM_GRID_DEFAULT
                st.session_state["hm_mc_sims"] = QUALITY_HM_MC_SIMS_DEFAULT
                st.session_state["bias_mc_sims"] = QUALITY_BIAS_MC_SIMS_DEFAULT
            st.session_state["_sim_mode_prev"] = sim_mode

        # Compact tooltip: show *current* settings, and explicitly indicate when an override is active.
        _preset_main = FAST_DEFAULT_NUM_SIMS if fast_mode else QUALITY_DEFAULT_NUM_SIMS
        _preset_hm_sims = FAST_HM_MC_SIMS_DEFAULT if fast_mode else QUALITY_HM_MC_SIMS_DEFAULT
        _preset_bias = FAST_BIAS_MC_SIMS_DEFAULT if fast_mode else QUALITY_BIAS_MC_SIMS_DEFAULT
        _preset_grid = FAST_HM_GRID_DEFAULT if fast_mode else QUALITY_HM_GRID_DEFAULT

        _cur_main = int(st.session_state.get('num_sims', 0) or 0)
        _cur_hm_sims = int(st.session_state.get('hm_mc_sims', 0) or 0)
        _cur_bias = int(st.session_state.get('bias_mc_sims', 0) or 0)
        _cur_grid = int(st.session_state.get('hm_grid_size', 0) or 0)

        def _mc_line(label: str, cur: int, preset: int, fmt: str = "{:,}") -> str:
            try:
                cur_s = fmt.format(int(cur))
            except Exception:
                cur_s = str(cur)
            try:
                preset_s = fmt.format(int(preset))
            except Exception:
                preset_s = str(preset)
            if int(cur) != int(preset):
                return f"{label}: {cur_s} (override; preset {preset_s})"
            return f"{label}: {cur_s}"

        _mc_tip = "\n".join([
            f"Mode: {'Fast' if fast_mode else 'Quality'}",
            _mc_line("Main MC sims", _cur_main, _preset_main),
            _mc_line("Heatmap MC sims", _cur_hm_sims, _preset_hm_sims),
            _mc_line("Bias MC sims", _cur_bias, _preset_bias),
            (f"Grid size: {_cur_grid}×{_cur_grid} (override; preset {_preset_grid}×{_preset_grid})" if _cur_grid != _preset_grid else f"Grid size: {_cur_grid}×{_cur_grid}"),
            "Tip: 'Advanced overrides' below can override these presets.",
        ])

        # Single header + tooltip (NO extra info icon on the mode selector itself)
        rbv_label_row("Performance mode", tooltip=_mc_tip, small_icon=False)
        sim_mode = st.radio(
            " ",
            ["Fast", "Quality"],
            index=(0 if sim_mode == "Fast" else 1),
            horizontal=True,
            key="sim_mode",
            label_visibility="collapsed",
        )
        fast_mode = (sim_mode == "Fast")

        if _show_advanced_controls:
            with st.expander("Advanced overrides", expanded=False):
                # Manual overrides (optional). These keys already drive the engine.
                st.number_input(
                    "Main Monte Carlo sims",
                    min_value=1_000,
                    max_value=500_000,
                    step=1_000,
                    key="num_sims",
                )
                try:
                    if int(st.session_state.get("num_sims", 0)) > int(_mc_cap):
                        st.warning(
                            f"Main sims above {int(_mc_cap):,} may trigger a slow fallback loop on a {int(years)}-year horizon. "
                            f"Recommended: ≤ {int(_mc_cap):,}."
                        )
                except Exception:
                    pass

                st.number_input(
                    "Heatmap grid size (N×N)",
                    min_value=11,
                    max_value=101,
                    step=2,
                    key="hm_grid_size",
                )
                st.number_input(
                    "Heatmap Monte Carlo sims",
                    min_value=1_000,
                    max_value=300_000,
                    step=1_000,
                    key="hm_mc_sims",
                )
                st.number_input(
                    "Bias Monte Carlo sims",
                    min_value=1_000,
                    max_value=300_000,
                    step=1_000,
                    key="bias_mc_sims",
                )

            def _on_volatility_toggle():
                """Seed volatility inputs when enabling MC volatility.

                Streamlit can retain prior widget state (often 0.0) across versions/sessions.
                We avoid changing values unless the user is turning volatility ON and both vols are still zero.
                """
                if bool(st.session_state.get("use_volatility", False)):
                    if not st.session_state.get("_vol_seeded_once", False):
                        cur_ret = float(st.session_state.get("ret_std_pct", 0.0) or 0.0)
                        cur_app = float(st.session_state.get("apprec_std_pct", 0.0) or 0.0)

                        # If both are zero, assume user hasn't set vols yet -> apply sensible defaults.
                        if cur_ret == 0.0 and cur_app == 0.0:
                            cur_ret, cur_app = 15.0, 5.0
                            st.session_state["ret_std_pct"] = cur_ret
                            st.session_state["apprec_std_pct"] = cur_app

                        # Drive UI widget keys from the (possibly updated) canonical values.
                        st.session_state["ret_std_pct_ui"] = float(st.session_state.get("ret_std_pct_ui", cur_ret) or cur_ret)
                        st.session_state["apprec_std_pct_ui"] = float(st.session_state.get("apprec_std_pct_ui", cur_app) or cur_app)

                        # If prior UI keys exist but are still zero, sync from canonical.
                        if float(st.session_state.get("ret_std_pct_ui", 0.0) or 0.0) == 0.0:
                            st.session_state["ret_std_pct_ui"] = cur_ret
                        if float(st.session_state.get("apprec_std_pct_ui", 0.0) or 0.0) == 0.0:
                            st.session_state["apprec_std_pct_ui"] = cur_app

                        st.session_state["_vol_seeded_once"] = True
                else:
                    # Allow reseeding on a future toggle-on if values are still zero.
                    st.session_state["_vol_seeded_once"] = False
            # Volatility (Monte Carlo) should be OFF by default for public-friendly performance.
            # Implement as a latching action button (Enable/Disable) rather than a checkbox.
            st.session_state.setdefault("use_volatility", False)
            sidebar_label(
                "Volatility (Monte Carlo)",
                "Runs a Monte Carlo simulation by applying random shocks to housing appreciation and investment returns to model uncertainty.",
            )

            _vol_on = bool(st.session_state.get("use_volatility", False))
            if not _vol_on:
                try:
                    _clicked = st.button(
                        "Enable volatility",
                        key="rbv_enable_vol",
                        use_container_width=True,
                        type="primary",
                    )
                except TypeError:
                    _clicked = st.button(
                        "Enable volatility",
                        key="rbv_enable_vol",
                        use_container_width=True,
                    )
                if _clicked:
                    st.session_state["use_volatility"] = True
                    _on_volatility_toggle()
                    st.rerun()
            else:
                try:
                    _clicked = st.button(
                        "Disable volatility",
                        key="rbv_disable_vol",
                        use_container_width=True,
                        type="secondary",
                    )
                except TypeError:
                    _clicked = st.button(
                        "Disable volatility",
                        key="rbv_disable_vol",
                        use_container_width=True,
                    )
                if _clicked:
                    st.session_state["use_volatility"] = False
                    _on_volatility_toggle()
                    st.rerun()

            use_volatility = bool(st.session_state.get("use_volatility", False))

            if use_volatility:

                # Ensure UI keys exist even if this session started with volatility already enabled.
                st.session_state.setdefault("ret_std_pct_ui", float(st.session_state.get("ret_std_pct", 15.0) or 15.0))
                st.session_state.setdefault("apprec_std_pct_ui", float(st.session_state.get("apprec_std_pct", 5.0) or 5.0))

                # Volatility parameters (core to Monte Carlo; always visible)
                ret_std_pct_ui = st.number_input(
                    "Investment Volatility (Std Dev %)",
                    step=1.0,
                    format="%.2f",
                    key="ret_std_pct_ui",
                    value=float(st.session_state.get("ret_std_pct_ui", 15.0) or 15.0),
                )
                apprec_std_pct_ui = st.number_input(
                    "Appreciation Volatility (Std Dev %)",
                    step=1.0,
                    format="%.2f",
                    key="apprec_std_pct_ui",
                    value=float(st.session_state.get("apprec_std_pct_ui", 5.0) or 5.0),
                )
                # Sync canonical values used by config / seed signatures.
                st.session_state["ret_std_pct"] = float(ret_std_pct_ui)
                st.session_state["apprec_std_pct"] = float(apprec_std_pct_ui)

                ret_std = float(ret_std_pct_ui) / 100.0
                apprec_std = float(apprec_std_pct_ui) / 100.0


                # Guardrail warnings for extreme volatility inputs
                if float(ret_std_pct_ui) > 20.0:
                    st.warning("Investment volatility above 20% is an aggressive stress-test and can produce extreme outcomes. Consider 10–20% for broad-market assumptions.")
                if float(apprec_std_pct_ui) > 10.0:
                    st.warning("Home price volatility above 10% is very high for annualized assumptions. Consider 3–8% unless deliberately stress-testing.")
                num_sims = int(st.session_state.get("num_sims", 50_000 if fast_mode else 100_000))
                st.caption(f"Monte Carlo simulations (from Performance mode): **{num_sims:,}**")
                # Monte Carlo seed & determinism
                # NOTE: Streamlit forbids modifying st.session_state["mc_seed"] AFTER the widget with key="mc_seed"
                # has been instantiated in the same run. Therefore, any auto-fill / migration must happen BEFORE
                # rendering the mc_seed widget below.
                _seed_choice = st.radio(
                    "Monte Carlo results",
                    options=["Stable results (recommended)", "New random run"],
                    index=1 if bool(st.session_state.get("mc_randomize", False)) else 0,
                    horizontal=True,
                    key="public_seed_mode",
                )
                mc_randomize = str(_seed_choice).startswith("New random")
                st.session_state["mc_randomize"] = bool(mc_randomize)

                def _compute_derived_seed_sidebar():
                    _sig_items = {
                        "price": float(st.session_state.get("price", 0.0)) if "price" in st.session_state else None,
                        "down": float(st.session_state.get("down", 0.0)) if "down" in st.session_state else None,
                        "rate": float(st.session_state.get("rate", 0.0)) if "rate" in st.session_state else None,
                        "amort": int(st.session_state.get("amort", 0)) if "amort" in st.session_state else None,
                        "apprec": float(st.session_state.get("apprec", 0.0)),
                        "buyer_ret": float(st.session_state.get("buyer_ret", 0.0)),
                        "renter_ret": float(st.session_state.get("renter_ret", 0.0)),
                        "rent": float(st.session_state.get("rent", 0.0)) if "rent" in st.session_state else None,
                        "rent_inf": float(st.session_state.get("rent_inf", 0.0)) if "rent_inf" in st.session_state else None,
                        "pv": float(st.session_state.get("pv_rate", 0.0)) if "pv_rate" in st.session_state else None,
                        "corr": float(st.session_state.get("market_corr_input", 0.0)) if "market_corr_input" in st.session_state else None,
                        "ret_std": float(st.session_state.get("ret_std_pct", 15.0)) / 100.0,
                        "app_std": float(st.session_state.get("apprec_std_pct", 5.0)) / 100.0,
                        "sims": int(st.session_state.get("num_sims", 0)) if "num_sims" in st.session_state else None,
                    }
                    _sig = json.dumps(_sig_items, sort_keys=True, separators=(",", ":"))
                    _seed = int(hashlib.sha256(_sig.encode("utf-8")).hexdigest()[:8], 16)
                    return int(_seed), _sig

                # Auto-fill a stable derived seed into mc_seed when left blank (only in Stable mode).
                # This must run BEFORE st.text_input(key="mc_seed") below to avoid StreamlitAPIException.
                if use_volatility and (not mc_randomize):
                    _seed_new, _sig_new = _compute_derived_seed_sidebar()
                    _cur = str(st.session_state.get("mc_seed", "")).strip()
                    _auto = bool(st.session_state.get("_mc_seed_autofilled", False))
                    _auto_sig = str(st.session_state.get("_mc_seed_autofill_sig", ""))
                    _auto_val = str(st.session_state.get("_mc_seed_autofill_value", ""))

                    # Fill when blank, and keep it synced if it was auto-filled previously and inputs changed.
                    if (_cur == "") or (_auto and _cur == _auto_val and _auto_sig != _sig_new):
                        st.session_state["mc_seed"] = str(int(_seed_new))
                        st.session_state["_mc_seed_autofilled"] = True
                        st.session_state["_mc_seed_autofill_sig"] = _sig_new
                        st.session_state["_mc_seed_autofill_value"] = str(int(_seed_new))
                else:
                    st.session_state["_mc_seed_autofilled"] = False

                st.text_input(
                    "Seed",
                    key="mc_seed",
                    label_visibility="collapsed",
                )

                # Downstream: treat manual seed as ignored in random mode.
                mc_seed_text = "" if mc_randomize else str(st.session_state.get("mc_seed", "")).strip()
                _eff = str(st.session_state.get("mc_seed_effective", "")).strip()
                _src = str(st.session_state.get("mc_seed_effective_source", "")).strip()
            # Keep variable in sync for downstream logic (e.g., heatmap fallback)
            try:
                num_sims = int(st.session_state.get("num_sims", num_sims))
            except Exception:
                pass



# --- Restore original widget functions after sidebar (prevents sidebar label wrapping from leaking into main UI) ---
# The sidebar wrapper temporarily monkey-patches st.<widget> so the labels render with our custom tooltip system.
# If we don't restore them, main-page widgets will get a *second* label row (appearing as duplicated inputs).
try:
    for _wname, _fn in getattr(st, "__rbv_sb_orig_funcs", {}).items():
        try:
            setattr(st, _wname, _fn)
        except Exception:
            pass
except Exception:
    pass




# ----------------------
# Main page header & primary inputs (v2_41)
st.markdown('<div class="title-banner">Rent vs Buy Analysis</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="rbv-disclaimer">'
    '<div class="rbv-disclaimer-badge">Educational</div>'
    '<div class="rbv-disclaimer-text"><b>Not financial advice.</b> This simulator is for scenario planning only. '
    'It uses simplified tax/policy assumptions and cannot capture underwriting, exemptions, or your personal situation. '
    'Verify numbers with official sources and consult a licensed professional before making decisions.</div>'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown('<div style=\"height:16px;\"></div>', unsafe_allow_html=True)

# Buying & Renting inputs live on the main page (sidebar is for global settings / advanced controls)


st.markdown('<div class="kpi-section-title buy-title">BUYING INPUTS</div>', unsafe_allow_html=True)

# --- Legacy key/value migration (keeps older session_state compatible) ---
if "sell_cost" in st.session_state and "sell_cost_pct" not in st.session_state:
    st.session_state["sell_cost_pct"] = st.session_state.get("sell_cost")
if "prop_tax_rate" in st.session_state and "p_tax_rate_pct" not in st.session_state:
    st.session_state["p_tax_rate_pct"] = st.session_state.get("prop_tax_rate")
if "maint_rate" in st.session_state and "maint_rate_pct" not in st.session_state:
    st.session_state["maint_rate_pct"] = st.session_state.get("maint_rate")
if "repairs_rate" in st.session_state and "repair_rate_pct" not in st.session_state:
    st.session_state["repair_rate_pct"] = st.session_state.get("repairs_rate")

# Closing-cost legacy key migration (rare; keeps old saved scenarios compatible)
if "lawyer" in st.session_state and "purchase_legal_fee" not in st.session_state:
    st.session_state["purchase_legal_fee"] = st.session_state.get("lawyer")
if "insp" in st.session_state and "home_inspection" not in st.session_state:
    st.session_state["home_inspection"] = st.session_state.get("insp")
if "other_closing" in st.session_state and "other_closing_costs" not in st.session_state:
    st.session_state["other_closing_costs"] = st.session_state.get("other_closing")


# Down payment source (affects insured-mortgage premium tier for some insurers at high LTV).
# Default to Traditional for deterministic behavior when the widget is not shown.
if "down_payment_source" not in st.session_state:
    st.session_state["down_payment_source"] = "Traditional"

# Layout goal: 4-up grid with sliders grouped together for a clean/consistent look.
st.markdown('<div class="rbv-input-subhead">City preset (optional)</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="rbv-city-preset-help-note"><b>What this does:</b> City presets are optional quick-starts that prefill city/province context (including transfer-tax toggles where relevant) and common baseline assumptions. After applying, every field remains fully editable.</div>',
    unsafe_allow_html=True,
)
_city_region_opts = city_preset_filter_region_options()
_city_type_opts = city_preset_filter_type_options()
_city_filter_region = str(st.session_state.get("city_preset_filter_region", _city_region_opts[0]) or _city_region_opts[0])
if _city_filter_region not in _city_region_opts:
    _city_filter_region = _city_region_opts[0]
    st.session_state["city_preset_filter_region"] = _city_filter_region
_city_filter_type = str(st.session_state.get("city_preset_filter_type", _city_type_opts[0]) or _city_type_opts[0])
if _city_filter_type not in _city_type_opts:
    _city_filter_type = _city_type_opts[0]
    st.session_state["city_preset_filter_type"] = _city_filter_type
_city_filter_cols = st.columns([1.0, 1.0, 1.0])
with _city_filter_cols[0]:
    rbv_selectbox("Preset region", options=_city_region_opts, index=_city_region_opts.index(_city_filter_region), key="city_preset_filter_region")
with _city_filter_cols[1]:
    rbv_selectbox("Home type", options=_city_type_opts, index=_city_type_opts.index(_city_filter_type), key="city_preset_filter_type")
with _city_filter_cols[2]:
    rbv_text_input("Find preset", key="city_preset_filter_query", placeholder="Search city/province")

_city_opts = city_preset_filtered_options(
    region=st.session_state.get("city_preset_filter_region"),
    home_type=st.session_state.get("city_preset_filter_type"),
    query=st.session_state.get("city_preset_filter_query"),
)
if not _city_opts:
    _city_opts = city_preset_options()
_city_cur = str(st.session_state.get("city_preset", CITY_PRESET_CUSTOM) or CITY_PRESET_CUSTOM)
if _city_cur not in _city_opts:
    if _city_cur != CITY_PRESET_CUSTOM and _city_cur in city_preset_options():
        _city_opts = [*_city_opts, _city_cur]
    else:
        _city_cur = CITY_PRESET_CUSTOM
        st.session_state["city_preset"] = CITY_PRESET_CUSTOM

_city_cols = st.columns([2.4, 1.0, 1.0])
with _city_cols[0]:
    rbv_selectbox(
        "City preset",
        options=_city_opts,
        index=_city_opts.index(_city_cur),
        key="city_preset",
        tooltip="Optional starter values for province, Toronto MLTT toggle, and typical cost anchors. Values remain fully editable after apply.",
    )
with _city_cols[1]:
    st.markdown('<div class="rbv-label-row rbv-label-row-spacer"><div class="rbv-label-text">&nbsp;</div></div>', unsafe_allow_html=True)
    if st.button("Apply preset", key="rbv_apply_city_preset", use_container_width=True):
        apply_city_preset()
with _city_cols[2]:
    st.markdown('<div class="rbv-label-row rbv-label-row-spacer"><div class="rbv-label-text">&nbsp;</div></div>', unsafe_allow_html=True)
    if st.button("Reset", key="rbv_reset_city_preset", use_container_width=True):
        st.session_state["city_preset"] = CITY_PRESET_CUSTOM
        st.session_state["_rbv_city_preset_last_name"] = CITY_PRESET_CUSTOM
        st.session_state["_rbv_city_preset_last_summary_lines"] = []
        st.session_state["_rbv_city_preset_last_banner"] = "City preset cleared (Custom). Manual values are unchanged."

st.caption("Use presets as a starting point only. You can tweak every input after Apply. Tip: press Esc or click outside to close dropdowns.")

_city_preview_name = st.session_state.get("city_preset")
_city_preview = city_preset_values(_city_preview_name)
if isinstance(_city_preview, dict):
    _meta_prev = city_preset_metadata(_city_preview_name)
    _prov_prev = str(_city_preview.get("province", "") or "")
    _mltt_prev = "MLTT on" if bool(_city_preview.get("toronto", False)) else "MLTT off"
    _price_prev = _rbv_fmt_short_value(_city_preview.get("price"))
    _rent_prev = _rbv_fmt_short_value(_city_preview.get("rent"))
    sidebar_hint(f"Preview: {_prov_prev} · {_mltt_prev} · Price ${_price_prev} · Rent ${_rent_prev}/mo")
    sidebar_hint(f"Preset meta: {str(_meta_prev.get('housing_type',''))} · {str(_meta_prev.get('province_code','') or _meta_prev.get('province',''))}")
    for _line in city_preset_preview_summary_lines(_city_preview_name, max_items=4):
        sidebar_hint(_line)
    if bool(_city_preview.get("toronto", False)):
        sidebar_hint("Toronto presets auto-enable the Toronto Municipal Land Transfer Tax toggle.")

    try:
        _tmp_state = dict(st.session_state)
        _pending_changes = apply_city_preset_values(_tmp_state, _city_preview_name)
    except Exception:
        _pending_changes = []
    _pending_lines = build_city_preset_change_summary(_pending_changes, max_items=5)
    if _pending_lines:
        _safe_items = "".join([f"<li>{html.escape(str(x))}</li>" for x in _pending_lines if str(x).strip()])
        if _safe_items:
            st.markdown(f"<div class='rbv-hint' style='margin:2px 0 4px 0;'>If applied now, this preset would update:</div><ul class='rbv-hint' style='margin:0 0 8px 16px; padding-left:10px;'>{_safe_items}</ul>", unsafe_allow_html=True)
elif len(_city_opts) == 1:
    sidebar_hint("No presets match the current filters. Adjust region/type/search filters to see more options.")
_render_city_preset_summary_sidebar()

st.markdown('<div class="rbv-input-subhead">Purchase & Mortgage</div>', unsafe_allow_html=True)

vals = st.session_state  # fallback source for initial widget values
brow1 = st.columns(4)
with brow1[0]:
    price = rbv_number_input(
        "Home purchase price ($)",
        tooltip="Purchase price of the home today. Drives mortgage principal, property tax/maintenance bases, and sale proceeds.",
        min_value=0.0,
        value=float(vals.get("price", 600000)),
        step=1000.0,
        key="price",
    )
with brow1[1]:
    down = rbv_number_input(
        "Down payment ($)",
        tooltip="Upfront cash paid toward the purchase. Reduces mortgage principal and increases initial home equity.",
        min_value=0.0,
        value=float(vals.get("down", 120000)),
        step=1000.0,
        key="down",
    )
    down_pct_disp = (down / price * 100.0) if price else 0.0
    st.caption(f"≈ {down_pct_disp:.1f}% down")
    _loan_preview = max(price - down, 0.0)
    _ltv_preview = (_loan_preview / price) if price > 0 else 0.0
    if _ltv_preview > 0.90 + 1e-12:
        _opts = ["Traditional", "Non-traditional"]
        _cur = str(vals.get("down_payment_source", st.session_state.get("down_payment_source", "Traditional")) or "Traditional")
        _idx = 1 if _cur.strip().lower().startswith("non") else 0
        rbv_selectbox(
            "Down payment source",
            options=_opts,
            index=_idx,
            key="down_payment_source",
            tooltip="If your down payment is non-traditional (e.g., borrowed/unsecured or certain gifts), some insurers may charge a higher premium at 90–95% LTV. Leave Traditional if you're using savings/equity.",
        )
    else:
        # Auto-clear to default when not applicable (prevents “sticky” premiums).
        if str(st.session_state.get("down_payment_source", "Traditional")) != "Traditional":
            st.session_state["down_payment_source"] = "Traditional"

with brow1[2]:
    rate = rbv_number_input(
        "Mortgage rate (%)",
        tooltip=(
            "Nominal annual mortgage rate used for the payment schedule "
            "(before any reset/shock overrides). Rates vary widely by term, lender, and insured/uninsured status — "
            "use your actual quoted rate."
        ),
        min_value=0.0,
        value=float(vals.get("rate", 4.75)),
        step=0.05,
        key="rate",
    )
with brow1[3]:
    amort = rbv_number_input(
        "Amortization (years)",
        tooltip="Total amortization period used to compute the fixed monthly mortgage payment. Note: 30-year amortizations can have eligibility restrictions in Canada (e.g., certain first-time buyer / new-build cases).",
        min_value=1,
        value=int(vals.get("amort", 25)),
        step=1,
        key="amort",
    )


st.markdown('<div class="rbv-input-subsep"></div>', unsafe_allow_html=True)

st.markdown('<div class="rbv-input-subhead">One-time Purchase Costs</div>', unsafe_allow_html=True)

bclose = st.columns(3)
with bclose[0]:
    purchase_legal_fee = rbv_number_input(
        "Legal & closing ($)",
        tooltip="One-time legal and closing fees paid at purchase (excluding land transfer tax).",
        min_value=0.0,
        value=float(vals.get("purchase_legal_fee", 1800.0)),
        step=100.0,
        key="purchase_legal_fee",
    )
with bclose[1]:
    home_inspection = rbv_number_input(
        "Home inspection ($)",
        tooltip="One-time home inspection cost paid at purchase.",
        min_value=0.0,
        value=float(vals.get("home_inspection", 500.0)),
        step=50.0,
        key="home_inspection",
    )
with bclose[2]:
    other_closing_costs = rbv_number_input(
        "Other closing costs ($)",
        tooltip="Other one-time purchase costs (e.g., appraisal, title insurance, adjustments). Excluding land transfer tax and CMHC PST.",
        min_value=0.0,
        value=float(vals.get("other_closing_costs", 0.0)),
        step=100.0,
        key="other_closing_costs",
    )

st.markdown('<div class="rbv-input-subsep"></div>', unsafe_allow_html=True)

st.markdown('<div class="rbv-input-subhead">Returns & Monthly Fees</div>', unsafe_allow_html=True)

brow2 = st.columns(4)
with brow2[0]:
    buyer_ret = rbv_number_input(
        "Buyer invest. return (%)",
        tooltip="Expected annual return on the buyer's invested assets (used when investing surplus/deficit cashflows).",
        value=float(vals.get("buyer_ret", 7.0)),
        step=0.1,
        key="buyer_ret",
    )
with brow2[1]:
    apprec = rbv_number_input(
        "Home appreciation (%)",
        tooltip="Expected annual home-price appreciation rate used to project the home's market value over time.",
        value=float(vals.get("apprec", 3.0)),
        step=0.1,
        key="apprec",
    )
with brow2[2]:
    h_ins = rbv_number_input(
        "Home insurance ($/mo)",
        tooltip="Monthly homeowner insurance premium.",
        min_value=0.0,
        value=float(vals.get("h_ins", 150)),
        step=5.0,
        key="h_ins",
    )
with brow2[3]:
    condo = rbv_number_input(
        "Condo fees ($/mo)",
        tooltip="Monthly condo/HOA fees (set to 0 for freehold). Can be inflated over time below.",
        min_value=0.0,
        value=float(vals.get("condo", 0)),
        step=10.0,
        key="condo",
    )

# Sliders (rates) grouped together

st.markdown('<div class="rbv-input-subsep"></div>', unsafe_allow_html=True)

st.markdown('<div class="rbv-input-subhead">Ongoing Ownership Costs</div>', unsafe_allow_html=True)

brow3 = st.columns(4)
with brow3[0]:
	    sell_cost_pct = rbv_slider(
	        "Selling costs (% of sale price)",
	        tooltip="Transaction costs when selling (e.g., realtor commissions + closing costs) as a percent of sale price.",
	        min_value=0.0,
	        max_value=10.0,
	        value=float(vals.get("sell_cost_pct", 5.0)),
	        step=0.1,
	        key="sell_cost_pct",
	    )
with brow3[1]:
	    p_tax_rate_pct = rbv_slider(
	        "Property tax (% / year)",
	        tooltip=(
                    "Annual property tax rate as a % of assessed value. This varies a lot by municipality and year "
                    "(often roughly ~0.25%–1.25%). Use your city’s published tax rate / calculator."
                ),
	        min_value=0.0,
	        max_value=3.0,
	        value=float(vals.get("p_tax_rate_pct", 1.0)),
	        step=0.05,
	        key="p_tax_rate_pct",
	    )
with brow3[2]:
	    maint_rate_pct = rbv_slider(
	        "Maintenance (% / year)",
	        tooltip="Ongoing maintenance budget as a percent of current home value (paid monthly in the model).",
	        min_value=0.0,
	        max_value=5.0,
	        value=float(vals.get("maint_rate_pct", 1.0)),
	        step=0.05,
	        key="maint_rate_pct",
	    )
with brow3[3]:
	    repair_rate_pct = rbv_slider(
	        "Repairs / CapEx (% / year)",
	        tooltip="Major repairs/capital expenditures as a percent of current home value (paid monthly in the model).",
	        min_value=0.0,
	        max_value=5.0,
	        value=float(vals.get("repair_rate_pct", 0.5)),
	        step=0.05,
	        key="repair_rate_pct",
	    )


st.markdown('<div class="rbv-input-subsep"></div>', unsafe_allow_html=True)

st.markdown('<div class="rbv-input-subhead">One-time Shocks (optional)</div>', unsafe_allow_html=True)

_sa_years_max = int(st.session_state.get("years", 25) or 25)
_sa_row = st.columns([2, 1, 1], gap="small")
with _sa_row[0]:
    rbv_number_input(
        "Special assessment ($)",
        tooltip=(
            "Optional one-time condo/strata special assessment paid by the buyer. "
            "Modeled as an unrecoverable cash outflow at the selected month. Set to 0 to disable."
        ),
        min_value=0.0,
        value=float(vals.get("special_assessment_amount", 0.0)),
        step=500.0,
        key="special_assessment_amount",
    )
with _sa_row[1]:
    rbv_number_input(
        "Assessment year (0 = off)",
        tooltip="Year of the one-time assessment. Use 0 to disable.",
        min_value=0,
        max_value=_sa_years_max,
        value=int(vals.get("special_assessment_year", 0)),
        step=1,
        key="special_assessment_year",
    )
with _sa_row[2]:
    rbv_selectbox(
        "Month in year",
        options=list(range(1, 13)),
        index=max(0, min(11, int(vals.get("special_assessment_month_in_year", 1)) - 1)),
        key="special_assessment_month_in_year",
        tooltip="Month within the selected year when the assessment is paid.",
    )

st.caption("Tip: This shock is buyer-only and unrecoverable; it reduces buyer net worth by cash outflow and opportunity cost. It is off by default.")

st.markdown('<div class="rbv-input-subhead">Utilities & Inflation</div>', unsafe_allow_html=True)

## Layout: keep key items on one clean row (evenly distributed)
# Owner utilities are intentionally simplified to a single fixed monthly amount (no mode selector).
brow4 = st.columns([1.55, 1.00, 1.15])

# Backward-compatible condo fee inflation mode (avoids ValueError on legacy saved values)
_condo_inf_options = ["CPI + spread", "Inflate with general inflation", "Custom %", "No inflation"]
_condo_inf_raw = str(vals.get("condo_inf_mode", "CPI + spread") or "CPI + spread").strip()
_condo_inf_legacy = {
    "Manual %": "Custom %",
    "CPI+spread": "CPI + spread",
    "CPI + Spread": "CPI + spread",
    "CPI +spread": "CPI + spread",
    "CPI+ spread": "CPI + spread",
}
_condo_inf_norm = _condo_inf_legacy.get(_condo_inf_raw, _condo_inf_raw)
if _condo_inf_norm not in _condo_inf_options:
    _condo_inf_norm = "CPI + spread"

with brow4[0]:
    condo_inf_mode = rbv_selectbox(
        "Condo fee inflation",
        options=_condo_inf_options,
        index=_condo_inf_options.index(_condo_inf_norm),
        key="condo_inf_mode",
        tooltip="How condo/HOA fees grow over time. 'CPI + spread' adds a configurable premium above general inflation.",
    )

with brow4[1]:
    if condo_inf_mode == "CPI + spread":
        rbv_number_input(
            "CPI spread (%)",
            min_value=-5.0,
            max_value=10.0,
            value=float(vals.get("condo_inf_spread", 1.5)),
            step=0.1,
            key="condo_inf_spread",
            tooltip="Adds to general inflation for condo fees (e.g., 2.5% CPI + 1.5% = 4.0%).",
        )
    elif condo_inf_mode == "Custom %":
        rbv_number_input(
            "Condo inflation (%)",
            min_value=0.0,
            max_value=20.0,
            value=float(vals.get("condo_inf_custom", 4.0)),
            step=0.1,
            key="condo_inf_custom",
            tooltip="Custom annual condo/HOA fee inflation rate.",
        )
    else:
        # Keep row height stable.
        st.markdown('<div style="height:34px"></div>', unsafe_allow_html=True)

with brow4[2]:
    o_util = rbv_number_input(
        "Owner utilities ($/mo)",
        tooltip="Monthly utilities paid by the homeowner (e.g., electricity, gas, water).",
        min_value=0.0,
        value=float(vals.get("o_util", 200)),
        step=5.0,
        key="o_util",
    )

st.markdown('<div class="rbv-input-subsep"></div>', unsafe_allow_html=True)

st.markdown('<div class="rbv-input-subhead">Taxes & Eligibility</div>', unsafe_allow_html=True)

# Toronto MLTT applies only in Ontario. If the user changes province away from Ontario,
# automatically clear the Toronto flag so taxes remain well-defined.
try:
    _prov_now = str(st.session_state.get("province", "Ontario") or "Ontario")
    if _prov_now != "Ontario" and bool(st.session_state.get("toronto", False)):
        st.session_state["toronto"] = False
except Exception:
    pass

taxrow = st.columns([1.45, 0.95, 0.95])
with taxrow[0]:
    _prov_raw = str(vals.get("province", "Ontario") or "Ontario")
    _prov = _prov_raw if _prov_raw in PROVINCES else "Ontario"
    province = rbv_selectbox(
        "Province",
        options=PROVINCES,
        index=PROVINCES.index(_prov),
        key="province",
        tooltip="Select the province for land transfer / welcome tax rules.",
    )
with taxrow[1]:
    # Public-friendly default: assume first-time buyer unless scenario overrides.
    first_time = rbv_checkbox(
        "First-time buyer",
        tooltip="If eligible, applies modeled first-time buyer rebates/credits where applicable.",
        value=bool(vals.get("first_time", True)),
        key="first_time",
    )
with taxrow[2]:
    if str(province) == "Ontario":
        toronto = rbv_checkbox(
            "Toronto property",
            tooltip="If yes, applies Toronto Municipal Land Transfer Tax (MLTT) in addition to Ontario LTT (rates depend on date).",
            value=bool(vals.get("toronto", False)),
            key="toronto",
        )
    else:
        # Keep layout height stable while making it explicit that Toronto MLTT is Ontario-only.
        toronto = False
        st.markdown('<div style="height:34px"></div>', unsafe_allow_html=True)


# Province-specific transfer tax inputs (only shown when relevant).
if str(province) in ("New Brunswick", "Prince Edward Island"):
    # NB/PEI transfer tax is assessed-value based; in practice the basis is often max(purchase, assessed).
    if "assessed_value" not in st.session_state or st.session_state.get("assessed_value") in (None, ""):
        st.session_state["assessed_value"] = float(vals.get("purchase_price", 0.0) or 0.0) or float(price)
    assessed_value = rbv_number_input(
        "Assessed value ($)",
        min_value=0.0,
        value=float(st.session_state.get("assessed_value") or float(price)),
        step=1000.0,
        key="assessed_value",
        tooltip="NB/PEI transfer tax base uses max(purchase price, assessed value). Defaults to purchase price.",
    )
    sidebar_hint("NB/PEI transfer tax uses the higher of purchase price and assessed value.")

elif str(province) == "Nova Scotia":
    if "ns_deed_transfer_rate_pct" not in st.session_state or st.session_state.get("ns_deed_transfer_rate_pct") in (None, ""):
        st.session_state["ns_deed_transfer_rate_pct"] = 1.5
    _ns_rate_pct = rbv_number_input(
        "Deed transfer tax rate (%)",
        min_value=0.0,
        max_value=5.0,
        value=float(st.session_state.get("ns_deed_transfer_rate_pct") or 1.5),
        step=0.05,
        key="ns_deed_transfer_rate_pct",
        tooltip="Nova Scotia deed transfer tax rates vary by municipality. Set your local rate (default 1.5%).",
    )
    ns_deed_transfer_rate = float(_ns_rate_pct) / 100.0
    st.markdown('<div class="rbv-center-alert">', unsafe_allow_html=True)
    st.info("Rates vary by municipality (Nova Scotia). Adjust the deed transfer tax rate for your area.")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="kpi-section-title rent-title">RENTING INPUTS</div>', unsafe_allow_html=True)

# --- Legacy key/value migration (keeps older session_state compatible) ---
if "move_cost" in st.session_state and "moving_cost" not in st.session_state:
    st.session_state["moving_cost"] = st.session_state.get("move_cost")
if "rent_control_annual_cap" in st.session_state and "rent_control_cap_pct" not in st.session_state:
    st.session_state["rent_control_cap_pct"] = st.session_state.get("rent_control_annual_cap")

# Normalize legacy moving frequency strings (e.g., "Never", "Every 5 years") into numeric years.
_mf_raw_ui = st.session_state.get("moving_freq", 5)
if isinstance(_mf_raw_ui, str):
    s = _mf_raw_ui.strip().lower()
    if s in ("never", "none", ""):
        st.session_state["moving_freq"] = 9999
    else:
        nums = re.findall(r"[-+]?\d*\.?\d+", s)
        st.session_state["moving_freq"] = int(float(nums[0])) if nums else 5

elif isinstance(_mf_raw_ui, (int, float)):
    try:
        if float(_mf_raw_ui) <= 0:
            st.session_state["moving_freq"] = 9999
    except Exception:
        pass


st.markdown('<div class="rbv-input-subhead">Rent & Investing</div>', unsafe_allow_html=True)

rrow1 = st.columns(4)
with rrow1[0]:
    rent = rbv_number_input(
        "Monthly rent ($)",
        tooltip="Current monthly rent payment at month 0.",
        min_value=0.0,
        value=float(vals.get("rent", 2600)),
        step=50.0,
        key="rent",
    )
with rrow1[1]:
    rent_inf = rbv_number_input(
        "Annual rent increase (%)",
        tooltip="Expected annual rent increase rate (before any rent-control caps).",
        min_value=0.0,
        value=float(vals.get("rent_inf", 2.5)),
        step=0.1,
        key="rent_inf",
    )
with rrow1[2]:
    renter_ret = rbv_number_input(
        "Renter invest. return (%)",
        tooltip=(
                "Expected annual return on the renter's invested assets. "
                "Typically set equal to the buyer's return — both parties can invest in the same markets. "
                "A lower renter return assumes the renter is less financially disciplined."
            ),
        value=float(vals.get("renter_ret", 7.0)),
        step=0.1,
        key="renter_ret",
    )
with rrow1[3]:
    moving_cost = rbv_number_input(
        "Moving cost per move ($)",
        tooltip="One-time moving cost paid each time the renter moves.",
        min_value=0.0,
        value=float(vals.get("moving_cost", 1200.0)),
        step=50.0,
        key="moving_cost",
    )

st.markdown('<div class="rbv-input-subsep"></div>', unsafe_allow_html=True)

st.markdown('<div class="rbv-input-subhead">Living Costs, Moves & Controls</div>', unsafe_allow_html=True)

rrow2 = st.columns(4)
with rrow2[0]:
    r_ins = rbv_number_input(
        "Renter insurance ($/mo)",
        tooltip="Monthly renter's insurance premium.",
        min_value=0.0,
        value=float(vals.get("r_ins", 30)),
        step=5.0,
        key="r_ins",
    )
with rrow2[1]:
    r_util = rbv_number_input(
        "Renter utilities ($/mo)",
        tooltip="Monthly utilities paid by the renter (e.g., electricity, internet).",
        min_value=0.0,
        value=float(vals.get("r_util", 150)),
        step=5.0,
        key="r_util",
    )
with rrow2[2]:
    # Store numeric years; use 9999 as a "Never" sentinel (prevents any move events in the engine loop)
    moving_freq_default = int(st.session_state.get("moving_freq", 5))
    if moving_freq_default not in (2, 3, 5, 10, 9999):
        moving_freq_default = 5
    moving_freq = rbv_selectbox(
        "How often do you move? (years)",
        options=[9999, 2, 3, 5, 10],
        format_func=lambda x: "Never" if x == 9999 else f"Every {int(x)} years",
        index=[9999, 2, 3, 5, 10].index(moving_freq_default),
        key="moving_freq",
        tooltip="Controls how often the renter pays moving costs and resets rent if your scenario models move-related rent changes.",
    )
with rrow2[3]:
    rent_control_enabled = rbv_checkbox(
        "Rent control (Ontario-style)",
        tooltip="When enabled, annual rent increases are capped (based on the settings below).",
        value=bool(vals.get("rent_control_enabled", False)),
        key="rent_control_enabled",
    )

if st.session_state.get("rent_control_enabled", False):
    st.markdown('<div class="rbv-input-subsep"></div>', unsafe_allow_html=True)

    st.markdown('<div class="rbv-input-subhead">Rent Control Details</div>', unsafe_allow_html=True)
    rrow3 = st.columns(4)
    with rrow3[0]:
        rent_control_frequency = rbv_selectbox(
            "Control applies...",
            options=["Every year", "Every 2 years", "Every 3 years"],
            index=(["Every year", "Every 2 years", "Every 3 years"].index(vals.get("rent_control_frequency", "Every year")) if vals.get("rent_control_frequency", "Every year") in ["Every year", "Every 2 years", "Every 3 years"] else 0),
            key="rent_control_frequency",
            tooltip="How frequently the cap is enforced (e.g., every 2 years means increases can accumulate between cap checks).",
        )
    with rrow3[1]:
        rent_control_cap_pct = rbv_number_input(
            "Annual cap (%)",
            tooltip="Maximum annual rent increase when rent control applies.",
            min_value=0.0,
            value=float(vals.get("rent_control_cap_pct", 2.5)),
            step=0.1,
            key="rent_control_cap_pct",
        )
    with rrow3[2]:
        st.write("")
    with rrow3[3]:
        st.write("")
st.markdown('<div style="height:18px;"></div>', unsafe_allow_html=True)

# --- Derived Inputs (post-sidebar) ---
# Effective rent inflation: capped if rent control enabled
rent_inf_eff = rent_inf
if 'rent_control_enabled' in locals() and rent_control_enabled and (rent_control_cap is not None):
    rent_inf_eff = min(rent_inf, rent_control_cap)

# Effective mortgage reset settings (None when fixed)
rate_reset_years_eff = rate_reset_years if 'rate_reset_years' in locals() else None
rate_reset_to_eff = rate_reset_to if 'rate_reset_to' in locals() else None
rate_reset_step_pp_eff = rate_reset_step_pp if 'rate_reset_step_pp' in locals() else 0.0

# Effective rate shock settings
rate_shock_enabled_eff = bool(rate_shock_enabled) if 'rate_shock_enabled' in locals() else False
rate_shock_start_year_eff = int(rate_shock_start_year) if 'rate_shock_start_year' in locals() else 5
rate_shock_duration_years_eff = int(rate_shock_duration_years) if 'rate_shock_duration_years' in locals() else 5
rate_shock_pp_eff = float(rate_shock_pp) if 'rate_shock_pp' in locals() else 2.0

# --- Validations ---
loan = max(price - down, 0)
ltv = loan / price if price > 0 else 0
insured = ltv > 0.8

# Policy/tax as-of date (single parse for validations + closing-cost tax logic).
_policy_asof_raw = st.session_state.get("tax_rules_asof", datetime.date.today().isoformat())
if isinstance(_policy_asof_raw, str):
    try:
        _policy_asof = datetime.date.fromisoformat(_policy_asof_raw[:10])
    except Exception:
        _policy_asof = datetime.date.today()
elif isinstance(_policy_asof_raw, datetime.datetime):
    _policy_asof = _policy_asof_raw.date()
elif isinstance(_policy_asof_raw, datetime.date):
    _policy_asof = _policy_asof_raw
else:
    _policy_asof = datetime.date.today()

# Minimum down payment (Canada) — policy helper (rules change over time; see rbv.core.policy_canada).
if price <= 0:
    min_down_amt = 0.0
else:
    min_down_amt = float(min_down_payment_canada(float(price), _policy_asof))

min_down_pct = (min_down_amt / price) if price > 0 else 0.0
if down + 1e-6 < min_down_amt:
    st.error(f"Minimum down payment is about ${min_down_amt:,.0f} ({min_down_pct*100:.1f}%) for this price.")
    st.stop()

# Default insurance eligibility (price cap varies over time; current policy uses a $1.5M cap).
_insured_cap = float(insured_mortgage_price_cap(_policy_asof))
if insured and price >= _insured_cap:
    st.error(f"Default mortgage insurance is not available at/above ${_insured_cap:,.0f} purchase price. Minimum 20% down required.")
    st.stop()
if insured and ltv > 0.95:
    st.error("Maximum LTV for insured mortgages is 95%. Increase down payment to at least 5%.")
    st.stop()

if insured and int(amort) > 25:
    _new_construction = bool(st.session_state.get("new_construction", False))
    _insured_amort_max = int(
        insured_max_amortization_years(
            _policy_asof,
            first_time_buyer=bool(first_time),
            new_construction=_new_construction,
        )
    )
    if int(amort) > _insured_amort_max:
        _rule_label = insured_amortization_rule_label(_policy_asof)
        _extra = ""
        if (
            _policy_asof >= datetime.date(2024, 8, 1)
            and _policy_asof < datetime.date(2024, 12, 15)
            and bool(first_time)
            and not _new_construction
        ):
            _extra = " This as-of window requires BOTH first-time buyer and new build eligibility for 30-year insured amortization."
        st.error(
            f"Insured mortgage amortization exceeds modeled policy limit ({_insured_amort_max} years as of {_policy_asof.isoformat()}). "
            f"Rule: {_rule_label}." + _extra
        )
        st.stop()

# --- Soft Warnings (non-blocking) ---
if years >= 40:
    st.warning("Long horizons (40+ years) can magnify uncertainty and inflation effects. Consider stress-testing with Monte Carlo and sensitivity.")
if st.session_state.apprec <= -3.0:
    st.warning("You entered strongly negative home appreciation. This is a severe housing contraction scenario; results may show prolonged negative equity.")
if bool(st.session_state.get("use_volatility", False)):
    try:
        _rs = float(st.session_state.get("ret_std_pct", 0.0) or 0.0)
        _hs = float(st.session_state.get("apprec_std_pct", 0.0) or 0.0)
        if _rs > 20.0:
            st.warning("Investment volatility above 20% is an aggressive stress-test and can produce extreme outcomes.")
        if _hs > 10.0:
            st.warning("Home price volatility above 10% is a strong stress-test and can produce extreme price paths.")
    except Exception:
        pass
if rate < 0:
    expert_mode_local = bool(st.session_state.get("expert_mode", False))
    if not expert_mode_local:
        st.error("Mortgage rates cannot be negative in standard mode. Set the rate ≥ 0%, or enable Expert mode (Taxes & Cash-out) to model a hypothetical negative-rate scenario.")
        st.stop()
    st.warning("Negative mortgage rates are uncommon. Expert mode is enabled, so the model will compute with a negative rate (hypothetical). Results may be unrealistic; treat this as a sensitivity test.")
if (down / price) < 0.10:
    st.markdown('<div class="rbv-center-alert">', unsafe_allow_html=True)
    st.warning("Low down payments increase leverage and risk. Ensure you understand insurance premiums, qualification rules, and cashflow sensitivity to rates.")
    st.markdown('</div>', unsafe_allow_html=True)

# --- Closing Costs Calculation ---
# Reuse the already-parsed policy as-of date so transfer taxes / insurance PST and
# insured eligibility validations stay on the same policy calendar.
_tax_asof = _policy_asof

tt = calc_transfer_tax(province, float(price), first_time, toronto, override_amount=transfer_tax_override, asof_date=_tax_asof, assessed_value=assessed_value, ns_deed_transfer_rate=ns_deed_transfer_rate)
total_ltt = float(tt["total"])
prov_ltt = float(tt.get("prov", 0.0) or 0.0)
muni_ltt = float(tt.get("muni", 0.0) or 0.0)
# Optional note (shown later in UI if non-empty)
transfer_tax_note = tt.get("note","")

dp_source = str(st.session_state.get("down_payment_source", "Traditional") or "Traditional")
cmhc_r = float(cmhc_premium_rate_from_ltv(float(ltv), dp_source)) if insured else 0.0
prem = loan * cmhc_r
# Provincial sales tax on mortgage default insurance premium (cash due at closing).
_pst_rate = mortgage_default_insurance_sales_tax_rate(str(province or ""), _tax_asof)
pst = prem * float(_pst_rate)
mort = loan + prem
# Closing cost inputs (editable)
lawyer = float(st.session_state.get("purchase_legal_fee", lawyer) or lawyer)
insp = float(st.session_state.get("home_inspection", insp) or insp)
other_closing = float(st.session_state.get("other_closing_costs", other_closing) or other_closing)
close = total_ltt + lawyer + insp + other_closing + pst


# --- Mortgage rate conversion helpers (Canada vs standard monthly compounding) ---
mr = _annual_nominal_pct_to_monthly_rate(rate, bool(st.session_state.get("canadian_compounding", True)))
nm = max(1, int(amort) * 12)
pmt = mort * (mr * (1 + mr)**nm) / ((1 + mr)**nm - 1) if mr > 0 else mort / nm
# --- 5. ENGINE ---


def _build_cfg():
    """Build the engine config dict from current UI state (single source of truth).

    Robust against Streamlit conditional UI branches: never raises NameError if a widget/branch
    is skipped. Fast/Quality mode must only affect Monte Carlo controls; all buy/rent inputs
    remain in the config.
    """
    def _pp(key: str, default_pp: float = 0.0) -> float:
        """Read a percent-valued widget from session_state (e.g., 3.5 for 3.5%)."""
        try:
            return float(st.session_state.get(key, default_pp))
        except Exception:
            return float(default_pp)

    def _frac_from_pp(key: str, default_pp: float = 0.0) -> float:
        """Percent -> fraction (e.g., 3.5 -> 0.035)."""
        return _pp(key, default_pp) / 100.0

    def _g(name: str, default=None):
        """Read from session_state; fall back to globals only for *derived* values.

        IMPORTANT: Do **not** source user inputs from globals. This file defines many
        module-level variables as Streamlit renders widgets; those locals can have
        different units (e.g., percent points vs decimal fractions). Pulling raw inputs
        from globals can silently apply the wrong units.

        We only fall back to globals for a small set of derived values that may be
        computed upstream (mort/close/pst/nm).
        """
        if name in ("mort", "close", "pst", "nm") and name in globals():
            return globals().get(name)
        return st.session_state.get(name, default)

    # ---- Core inputs (prefer already-computed globals; otherwise fall back to session_state with correct unit conversions)
    years = int(st.session_state.get("years", _g("years", 25)))
    price = float(st.session_state.get("price", _g("price", 800000.0)))
    rent = float(st.session_state.get("rent", _g("rent", 3000.0)))
    down = float(st.session_state.get("down", _g("down", 160000.0)))

    # Mortgage rate is stored/used in nominal percent (e.g., 4.5 for 4.5%)
    rate = float(st.session_state.get("rate", _g("rate", 4.0)))

    # Rent inflation is stored in session_state as percent points. Always convert here.
    # (Do not read from globals: widget locals overwrite module globals with different units.)
    rent_inf = _frac_from_pp("rent_inf", 2.5)

    # Selling + annual rates stored in session_state as percent; locals are fractions
    sell_cost = _g("sell_cost", None)
    if sell_cost is None:
        sell_cost = _frac_from_pp("sell_cost_pct", 5.0)

    p_tax_rate = _g("p_tax_rate", None)
    if p_tax_rate is None:
        p_tax_rate = _frac_from_pp("p_tax_rate_pct", 1.0)

    maint_rate = _g("maint_rate", None)
    if maint_rate is None:
        maint_rate = _frac_from_pp("maint_rate_pct", 1.0)

    repair_rate = _g("repair_rate", None)
    if repair_rate is None:
        repair_rate = _frac_from_pp("repair_rate_pct", 0.5)

    # Fees / utilities / insurance are absolute monthly dollars (no scaling)
    condo = float(_g("condo", st.session_state.get("condo", 0.0)) or 0.0)
    h_ins = float(_g("h_ins", st.session_state.get("h_ins", 120.0)) or 0.0)
    o_util = float(_g("o_util", st.session_state.get("o_util", 0.0)) or 0.0)
    r_ins = float(st.session_state.get("r_ins", _g("r_ins", 30.0)) or 0.0)
    r_util = float(st.session_state.get("r_util", _g("r_util", 0.0)) or 0.0)

    moving_cost = float(st.session_state.get("moving_cost", _g("moving_cost", 1500.0)) or 0.0)
    _mf_raw = st.session_state.get("moving_freq", _g("moving_freq", 5))
    # Accept numeric years, or legacy strings like "Never" / "Every 5 years"
    moving_freq = 5.0
    try:
        if isinstance(_mf_raw, str):
            s = _mf_raw.strip().lower()
            if s in ("never", "none", ""):
                moving_freq = 9999.0
            else:
                nums = re.findall(r"[-+]?\d*\.?\d+", s)
                moving_freq = float(nums[0]) if nums else 5.0
        else:
            moving_freq = float(_mf_raw)
    except Exception:
        moving_freq = 5.0

    # Closing + mortgage insurance outputs (computed upstream; default safely if absent)
    mort = float(_g("mort", 0.0) or 0.0)
    close = float(_g("close", 0.0) or 0.0)
    pst = float(_g("pst", 0.0) or 0.0)
    nm = int(_g("nm", years * 12) or (years * 12))

    # PV discount rate widget is expressed in percent points (e.g., 3.0 for 3%).
    # Always convert to fraction for the engine config.
    discount_rate = _frac_from_pp("discount_rate", 3.0)

    # Investment drag tax is a percent (engine uses tax_r/100 internally)
    tax_r = _g("tax_r", None)
    if tax_r is None:
        tax_r = float(st.session_state.get("tax_r", 0.0) or 0.0)

    province = str(st.session_state.get("province", _g("province", "Ontario")))

    # ---- Volatility / MC controls (Fast/Quality affects only these)
    use_volatility = bool(st.session_state.get("use_volatility", _g("use_volatility", False)))
    num_sims = int(st.session_state.get("num_sims", _g("num_sims", 1000)))

    # Std dev widgets stored as percent; engine expects fraction
    ret_std = float(st.session_state.get("ret_std_pct", (_g("ret_std", 0.0) or 0.0) * 100.0)) / 100.0
    apprec_std = float(st.session_state.get("apprec_std_pct", (_g("apprec_std", 0.0) or 0.0) * 100.0)) / 100.0

    # General inflation widget stored as percent; engine expects fraction
    general_inf = _frac_from_pp("general_inf", 0.0)

    # ---- Mortgage path controls (may live in optional UI blocks)
    rate_mode = str(_g("rate_mode", "Fixed") or "Fixed")
    rate_reset_years_eff = _g("rate_reset_years_eff", _g("rate_reset_years", None))
    rate_reset_to_eff = _g("rate_reset_to_eff", _g("rate_reset_to", None))
    rate_reset_step_pp_eff = float(_g("rate_reset_step_pp_eff", _g("rate_reset_step_pp", 0.0)) or 0.0)

    rate_shock_enabled_eff = bool(_g("rate_shock_enabled_eff", _g("rate_shock_enabled", False)) or False)
    rate_shock_start_year_eff = float(_g("rate_shock_start_year_eff", _g("rate_shock_start_year", 5)) or 5)
    rate_shock_duration_years_eff = float(_g("rate_shock_duration_years_eff", _g("rate_shock_duration_years", 5)) or 5)
    rate_shock_pp_eff = float(_g("rate_shock_pp_eff", _g("rate_shock_pp", 0.0)) or 0.0)

    # ---- Rent control (optional)
    rent_control_enabled = bool(st.session_state.get("rent_control_enabled", _g("rent_control_enabled", False)) or False)
    rent_control_cap = _g("rent_control_cap", None)
    rent_control_frequency_years = 1
    if rent_control_enabled:
        # cap stored as percent in session_state; local is fraction
        if "rent_control_cap_pct" in st.session_state:
            rent_control_cap = float(st.session_state.get("rent_control_cap_pct", 2.5)) / 100.0

        # Frequency stored as a label in the UI (e.g., "Every 2 years"); keep backward-compatible parsing.
        _rc_freq_raw = st.session_state.get("rent_control_frequency", _g("rent_control_frequency", "Every year"))
        try:
            if isinstance(_rc_freq_raw, str):
                s = _rc_freq_raw.strip().lower()
                nums = re.findall(r"[-+]?\d+", s)
                rent_control_frequency_years = int(nums[0]) if nums else 1
                if "every year" in s:
                    rent_control_frequency_years = 1
            else:
                rent_control_frequency_years = int(float(_rc_freq_raw))
        except Exception:
            rent_control_frequency_years = 1
        rent_control_frequency_years = max(1, min(10, rent_control_frequency_years))
    else:
        rent_control_cap = None
        rent_control_frequency_years = 1

    # ---- Condo fee inflation (optional)
    # Backward-compatible handling:
    # - If a legacy explicit override `condo_inf` exists, accept it (treat >2 as percent points).
    # - Otherwise compute from `condo_inf_mode` widgets (fraction units for engine).
    condo_inf_val = _g("condo_inf", None)
    try:
        if condo_inf_val is not None:
            condo_inf_val = float(condo_inf_val)
            if condo_inf_val > 2.0:
                condo_inf_val = condo_inf_val / 100.0  # treat legacy percent points as fraction
    except Exception:
        condo_inf_val = None

    if condo_inf_val is None:
        _mode_raw = str(st.session_state.get("condo_inf_mode", "CPI + spread") or "CPI + spread").strip()
        _mode_legacy = {"Manual %": "Custom %", "CPI+spread": "CPI + spread", "CPI + Spread": "CPI + spread"}
        mode = _mode_legacy.get(_mode_raw, _mode_raw)

        if mode == "No inflation":
            condo_inf_val = 0.0
        elif mode == "Inflate with general inflation":
            condo_inf_val = float(general_inf)
        elif mode == "Custom %":
            condo_inf_val = _frac_from_pp("condo_inf_custom", 4.0)
        else:
            # Default / CPI + spread
            spread_pp = _pp("condo_inf_spread", 1.5)
            condo_inf_val = float(general_inf) + (spread_pp / 100.0)

    # ---- Horizon liquidation toggles (may be in optional UI blocks)
    assume_sale_end = bool(st.session_state.get("assume_sale_end", _g("assume_sale_end", True)))
    show_liquidation_view = bool(st.session_state.get("show_liquidation_view", _g("show_liquidation_view", True)))

    cg_tax_end = float(st.session_state.get("cg_tax_end", _g("cg_tax_end", 0.0)) or 0.0)
    home_sale_legal_fee = float(st.session_state.get("home_sale_legal_fee", _g("home_sale_legal_fee", 0.0)) or 0.0)

    # ---- One-time buyer shock (special assessment)
    try:
        sa_amount = float(st.session_state.get("special_assessment_amount", 0.0) or 0.0)
    except Exception:
        sa_amount = 0.0
    try:
        sa_year = int(st.session_state.get("special_assessment_year", 0) or 0)
    except Exception:
        sa_year = 0
    try:
        sa_month_in_year = int(st.session_state.get("special_assessment_month_in_year", 1) or 1)
    except Exception:
        sa_month_in_year = 1
    sa_month_in_year = max(1, min(12, sa_month_in_year))
    sa_month = 0
    if (sa_amount > 0.0) and (sa_year > 0):
        sa_month = (sa_year - 1) * 12 + sa_month_in_year
        # Ignore if outside horizon
        if sa_month > int(years) * 12:
            sa_month = 0
            sa_amount = 0.0

    # ---- Capital gains inclusion policy toggle (cash-out view)
    _pol_ui = str(st.session_state.get("cg_inclusion_policy", "Current (50% inclusion)") or "Current (50% inclusion)")
    cg_inclusion_policy = "proposed_2_3_over_250k" if _pol_ui.startswith("Hypothetical") else "current"
    try:
        cg_inclusion_threshold = float(st.session_state.get("cg_inclusion_threshold", 250000.0) or 250000.0)
    except Exception:
        cg_inclusion_threshold = 250000.0

    # ---- Registered-account shelter approximation
    reg_shelter_enabled = bool(st.session_state.get("reg_shelter_enabled", False))
    try:
        reg_initial_room = float(st.session_state.get("reg_initial_room", 0.0) or 0.0)
    except Exception:
        reg_initial_room = 0.0
    try:
        reg_annual_room = float(st.session_state.get("reg_annual_room", 0.0) or 0.0)
    except Exception:
        reg_annual_room = 0.0

    return {
        "years": years,
        "asof_date": _tax_asof.isoformat() if hasattr(_tax_asof, "isoformat") else str(_tax_asof),
        "price": price,
        "rent": rent,
        "down": down,
        "down_payment_source": str(st.session_state.get("down_payment_source", "Traditional") or "Traditional"),
        "rate": rate,
        "rent_inf": float(rent_inf),
        "sell_cost": float(sell_cost),
        "p_tax_rate": float(p_tax_rate),
        "maint_rate": float(maint_rate),
        "repair_rate": float(repair_rate),
        "condo": float(condo),
        "h_ins": float(h_ins),
        "o_util": float(o_util),
        "r_ins": float(r_ins),
        "r_util": float(r_util),
        "moving_cost": float(moving_cost),
        "moving_freq": float(moving_freq),

        "mort": float(mort),
        "close": float(close),
        "pst": float(pst),
        "nm": int(nm),
        "discount_rate": float(discount_rate),
        "tax_r": float(tax_r),
        "province": str(province),

        "use_volatility": bool(use_volatility),
        "num_sims": int(num_sims),
        "ret_std": float(ret_std),
        "apprec_std": float(apprec_std),
        "general_inf": float(general_inf),

        "rate_mode": str(rate_mode),
        "rate_reset_years_eff": rate_reset_years_eff,
        "rate_reset_to_eff": rate_reset_to_eff,
        "rate_reset_step_pp_eff": rate_reset_step_pp_eff,
        "rate_shock_enabled_eff": bool(rate_shock_enabled_eff),
        "rate_shock_start_year_eff": rate_shock_start_year_eff,
        "rate_shock_duration_years_eff": rate_shock_duration_years_eff,
        "rate_shock_pp_eff": rate_shock_pp_eff,

        "rent_control_enabled": bool(rent_control_enabled),
        "rent_control_cap": float(rent_control_cap) if rent_control_cap is not None else None,
        "rent_control_frequency_years": int(rent_control_frequency_years),

        "condo_inf": float(condo_inf_val) if condo_inf_val is not None else 0.0,
        "assume_sale_end": bool(assume_sale_end),
        "is_principal_residence": bool(is_principal_residence),
        "show_liquidation_view": bool(show_liquidation_view),
        "cg_tax_end": float(cg_tax_end),
        "home_sale_legal_fee": float(home_sale_legal_fee),

        "special_assessment_amount": float(sa_amount),
        "special_assessment_month": int(sa_month),

        "cg_inclusion_policy": str(cg_inclusion_policy),
        "cg_inclusion_threshold": float(cg_inclusion_threshold),

        "reg_shelter_enabled": bool(reg_shelter_enabled),
        "reg_initial_room": float(reg_initial_room),
        "reg_annual_room": float(reg_annual_room),

        "canadian_compounding": bool(st.session_state.get("canadian_compounding", True)),
        "prop_tax_growth_model": str(st.session_state.get("prop_tax_growth_model", "Hybrid (recommended for Toronto)")),
        "prop_tax_hybrid_addon_pct": float(st.session_state.get("prop_tax_hybrid_addon_pct", 0.5)),
        "investment_tax_mode": str(st.session_state.get("investment_tax_mode", "Pre-tax (no investment taxes)")),
    }
def run_simulation(buyer_ret_pct, renter_ret_pct, apprec_pct, invest_diff, rent_closing, mkt_corr,
                   force_deterministic=False, mc_seed=None, rate_override_pct=None, rent_inf_override_pct=None,
                   progress_cb=None, crisis_enabled=False, crisis_year=5, crisis_stock_dd=0.30, crisis_house_dd=0.20,
                   crisis_duration_months=1, budget_enabled=False, monthly_income=0.0, monthly_nonhousing=0.0,
                   income_growth_pct=0.0, budget_allow_withdraw=True, param_overrides=None, force_use_volatility=None,
                   num_sims_override=None, mc_summary_only: bool = False, mc_precomputed_shocks=None):
    """Thin Streamlit wrapper. Builds per-run config and forwards to rbv.core.engine.run_simulation_core."""
    cfg = _build_cfg()

    # Persist the *effective* engine inputs for debugging / reproducibility.
    # This prevents silent UI-to-engine drift (units, stale globals, conditional UI branches).
    try:
        st.session_state["_rbv_last_cfg"] = dict(cfg)
        st.session_state["_rbv_last_params"] = {
            "buyer_ret_pct": float(buyer_ret_pct),
            "renter_ret_pct": float(renter_ret_pct),
            "apprec_pct": float(apprec_pct),
            "invest_diff": bool(invest_diff),
            "rent_closing": bool(rent_closing),
            "mkt_corr": float(mkt_corr),
            "force_deterministic": bool(force_deterministic),
            "mc_seed": None if mc_seed is None else int(mc_seed),
            "rate_override_pct": None if rate_override_pct is None else float(rate_override_pct),
            "rent_inf_override_pct": None if rent_inf_override_pct is None else float(rent_inf_override_pct),
            "budget_enabled": bool(budget_enabled),
        }
    except Exception:
        pass

    return run_simulation_core(
        cfg,
        buyer_ret_pct, renter_ret_pct, apprec_pct, invest_diff, rent_closing, mkt_corr,
        force_deterministic=force_deterministic,
        mc_seed=mc_seed,
        rate_override_pct=rate_override_pct,
        rent_inf_override_pct=rent_inf_override_pct,
        progress_cb=progress_cb,
        crisis_enabled=crisis_enabled,
        crisis_year=crisis_year,
        crisis_stock_dd=crisis_stock_dd,
        crisis_house_dd=crisis_house_dd,
        crisis_duration_months=crisis_duration_months,
        budget_enabled=budget_enabled,
        monthly_income=monthly_income,
        monthly_nonhousing=monthly_nonhousing,
        income_growth_pct=income_growth_pct,
        budget_allow_withdraw=budget_allow_withdraw,
        param_overrides=param_overrides,
        force_use_volatility=force_use_volatility,
        num_sims_override=num_sims_override,
        mc_summary_only=bool(mc_summary_only),
        mc_precomputed_shocks=mc_precomputed_shocks,
    )

# --- Execution ---

# Cancellation notice (shown once after user presses "Stop current run")
# We also freeze the auto-run of the *currently active* long computation (e.g., heatmap)
# so a cancel rerun doesn't immediately re-trigger the same expensive work.
try:
    if bool(st.session_state.get("_rbv_cancel_notice", False)):
        st.session_state["_rbv_cancel_notice"] = False
        st.info("Stopped the previous computation run.")
except Exception:
    pass

# Monte Carlo seed handling
_mc_seed_source = "none"
mc_seed = int(mc_seed_text) if str(mc_seed_text).strip().lstrip("-").isdigit() else None
if use_volatility:
    if mc_seed is not None:
        _mc_seed_source = "custom"
    else:
        # If user didn't provide a seed:
        # - If randomize is enabled, use a fresh random seed each rerun.
        # - Otherwise, derive a stable seed from the current inputs for reproducibility.
        _rand_each = bool(st.session_state.get("mc_randomize", False))
        if _rand_each:
            mc_seed = random.randint(0, 2**31 - 1)
            _mc_seed_source = "random"
        else:
            _sig_items = {
                "price": float(st.session_state.get("price", 0.0)) if "price" in st.session_state else None,
                "down": float(st.session_state.get("down", 0.0)) if "down" in st.session_state else None,
                "rate": float(st.session_state.get("rate", 0.0)) if "rate" in st.session_state else None,
                "amort": int(st.session_state.get("amort", 0)) if "amort" in st.session_state else None,
                "apprec": float(st.session_state.get("apprec", 0.0)),
                "buyer_ret": float(st.session_state.get("buyer_ret", 0.0)),
                "renter_ret": float(st.session_state.get("renter_ret", 0.0)),
                "rent": float(st.session_state.get("rent", 0.0)) if "rent" in st.session_state else None,
                "rent_inf": float(st.session_state.get("rent_inf", 0.0)) if "rent_inf" in st.session_state else None,
                "pv": float(st.session_state.get("pv_rate", 0.0)) if "pv_rate" in st.session_state else None,
                "corr": float(st.session_state.get("market_corr_input", 0.0)) if "market_corr_input" in st.session_state else None,
                "ret_std": float(st.session_state.get("ret_std_pct", 15.0)) / 100.0,
                "app_std": float(st.session_state.get("apprec_std_pct", 5.0)) / 100.0,
                "sims": int(st.session_state.get("num_sims", 0)) if "num_sims" in st.session_state else None,
            }
            _sig = json.dumps(_sig_items, sort_keys=True, separators=(",", ":"))
            mc_seed = int(hashlib.sha256(_sig.encode("utf-8")).hexdigest()[:8], 16)
            _mc_seed_source = "derived"


# === Global fixed progress overlay (visible even when scrolled) ===
# Some long computations (Monte Carlo runs, heatmaps, bias scans) can occur while the user is scrolled far down.
# This overlay keeps progress/ETA visible at all times.
_rbv_global_progress_ph = st.empty()

def _rbv_eta_str_from_seconds(eta_sec):
    try:
        eta_sec = float(eta_sec)
    except Exception:
        return ""
    if not (eta_sec >= 0):
        return ""
    if eta_sec >= 3600:
        h = int(eta_sec // 3600)
        m = int((eta_sec % 3600) // 60)
        s = int(eta_sec % 60)
        return f"{h:d}:{m:02d}:{s:02d}"
    m = int(eta_sec // 60)
    s = int(eta_sec % 60)
    return f"{m:d}:{s:02d}"

def _rbv_global_progress_show(pct, label, eta_sec=None):
    try:
        pct_i = int(max(0, min(100, round(float(pct)))))
    except Exception:
        pct_i = 0
    label_s = str(label) if label is not None else "Computing"
    eta_str = _rbv_eta_str_from_seconds(eta_sec) if eta_sec is not None else ""
    eta_html = f" • ETA: {html.escape(eta_str)}" if eta_str else ""
    # Fixed overlay; inline styles so it works across Streamlit versions.
    _rbv_global_progress_ph.markdown(
        f'''
<div style="position:fixed; top:110px; left:calc(var(--rbv-main-left, 0px) + (var(--rbv-main-width, 100vw) / 2)); transform:translateX(-50%); width:min(760px, calc(var(--rbv-main-width, 100vw) - 24px)); z-index:2147483646; pointer-events:none;">
  <div style="background: rgba(11,15,25,0.96); border:1px solid rgba(255,255,255,0.10); border-radius:14px;
                padding:10px 12px; box-shadow:0 12px 36px rgba(0,0,0,0.58);">
      <div style="display:flex; justify-content:center; gap:10px; align-items:center; text-align:center;">
        <div style="color:#E6EDF7; font-size:12px; line-height:1.2;">
          {html.escape(label_s)}: <span style="color:#9A9A9A;">{pct_i}%</span>{eta_html}
        </div>
      </div>
      <div style="height:10px; margin-top:8px; background: rgba(255,255,255,0.14); border-radius:999px; overflow:hidden;">
        <div style="height:100%; width:{pct_i}%; background: linear-gradient(90deg, {BUY_COLOR}, {RENT_COLOR}); border-radius:999px;"></div>
      </div>
  </div>
</div>
''',
        unsafe_allow_html=True
    )

def _rbv_global_progress_clear():
    try:
        _rbv_global_progress_ph.empty()
    except Exception:
        pass


# === Unify all progress bars into the global overlay (no native Streamlit progress bars) ===
# Some sections historically used st.progress() or placeholder.progress(). We route all of them to the fixed overlay
# so users never see two progress bars with different styles.
def _rbv__pct_from_progress_value(v):
    try:
        vv = float(v)
    except Exception:
        return 0
    # Streamlit progress typically uses 0..1. Accept 0..100 too.
    if 0.0 <= vv <= 1.0:
        return int(round(vv * 100.0))
    return int(round(max(0.0, min(100.0, vv))))

class _RBVProgressProxy:
    def __init__(self, label=None):
        self._label = str(label) if label else "Computing"
    def progress(self, value=0, text=None):
        pct = _rbv__pct_from_progress_value(value)
        lab = str(text) if text else self._label
        try:
            _rbv_global_progress_show(pct, lab)
            if pct >= 100:
                _rbv_global_progress_clear()
        except Exception:
            pass
        return self
    def empty(self):
        try:
            _rbv_global_progress_clear()
        except Exception:
            pass
        return self

# Patch st.progress
try:
    _RBV_ORIG_ST_PROGRESS = getattr(st, "progress", None)
    def _rbv_progress(value=0, text=None):
        p = _RBVProgressProxy(text or "Computing")
        p.progress(value, text=text)
        return p
    st.progress = _rbv_progress
except Exception:
    pass

# Patch DeltaGenerator.progress (covers placeholder.progress / container.progress)
try:
    from streamlit.delta_generator import DeltaGenerator as _RBV_DG
    _RBV_ORIG_DG_PROGRESS = getattr(_RBV_DG, "progress", None)
    def _rbv_dg_progress(self, value=0, text=None):
        pct = _rbv__pct_from_progress_value(value)
        lab = str(text) if text else "Computing"
        try:
            _rbv_global_progress_show(pct, lab)
            if pct >= 100:
                _rbv_global_progress_clear()
        except Exception:
            pass
        return self
    _RBV_DG.progress = _rbv_dg_progress
except Exception:
    pass


# Monte Carlo progress (only when volatility is enabled)
_mc_status = None
_mc_t0 = None
def _mc_progress_cb(done, total):
    global _mc_status, _mc_t0
    try:
        pct = int(done * 100 / max(total, 1))
    except Exception:
        pct = 0

    eta_sec = None
    try:
        if _mc_t0 is not None and done > 0:
            elapsed = max(1e-6, time.time() - _mc_t0)
            sims_per_sec = done / elapsed
            remaining = max(total - done, 0)
            eta_sec = remaining / max(1e-6, sims_per_sec)
            eta_str = _rbv_eta_str_from_seconds(eta_sec)
            if _mc_status is not None:
                _mc_status.markdown(
                    f"<div style='color:#9A9A9A; font-size:12px; text-align:center; width:100%;'>Simulation {done:,} / {total:,} • ETA: {eta_str}</div>",
                    unsafe_allow_html=True
                )
        else:
            if _mc_status is not None:
                _mc_status.markdown(
                    f"<div style='color:#9A9A9A; font-size:12px; text-align:center; width:100%;'>Simulation {done:,} / {total:,}</div>",
                    unsafe_allow_html=True
                )
    except Exception:
        pass

    try:
        _rbv_global_progress_show(pct, "Monte Carlo", eta_sec=eta_sec)
    except Exception:
        pass


# --- Phase 3D: Core simulation caching (prevents reruns on tab/metric toggles) ---
if "_core_sim_cache" not in st.session_state:
    st.session_state["_core_sim_cache"] = {}
if "_core_sim_cache_order" not in st.session_state:
    st.session_state["_core_sim_cache_order"] = []

def _rbv_core_sim_cache_key(cfg_obj: dict) -> str:
    try:
        payload = {
            "cfg": cfg_obj,
            "buyer_ret": float(st.session_state.get("buyer_ret", 0.0)),
            "renter_ret": float(st.session_state.get("renter_ret", 0.0)),
            "apprec": float(st.session_state.get("apprec", 0.0)),
            "invest_diff": bool(invest_surplus_input) and (not bool(budget_enabled)),
            "rent_closing": bool(renter_uses_closing_input),
            "mkt_corr": float(market_corr_input),
            "mc_seed": int(mc_seed) if mc_seed is not None else None,
            "extra_engine_kwargs": extra_engine_kwargs,
        }
        raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:18]
    except Exception:
        return str(time.time())

# --- Public-friendly input validation (fails fast with clear errors) ---
_errs = _rbv_basic_validation_errors()
if _errs:
    st.error("Please fix the following before running the simulation:\n\n- " + "\n- ".join(_errs))
    st.stop()

_cfg_run = _build_cfg()
_core_key = _rbv_core_sim_cache_key(_cfg_run)
_cached_core = st.session_state["_core_sim_cache"].get(_core_key)

if _cached_core is not None:
    df, close_cash, m_pmt, win_pct = _cached_core
else:
    if use_volatility and int(num_sims) > 1:

        _mc_status = st.empty()
        _mc_t0 = time.time()
        _eta0 = None
        try:
            _avg = float(st.session_state.get("_rbv_mc_avg_sec_per_sim", 0.0))
            if _avg > 0:
                _eta0 = _avg * float(int(num_sims))
        except Exception:
            _eta0 = None

        try:
            _rbv_global_progress_show(0, "Monte Carlo", eta_sec=_eta0)
        except Exception:
            pass
        _cfg_json = json.dumps(_cfg_run, sort_keys=True)
        _extra_items = tuple(sorted(st.session_state.get('_rbv_extra_engine_kwargs', extra_engine_kwargs).items()))
        df, close_cash, m_pmt, win_pct = _rbv_cached_run_simulation_core(
            _cfg_json,
            float(st.session_state.buyer_ret),
            float(st.session_state.renter_ret),
            float(st.session_state.apprec),
            bool(invest_surplus_input),
            bool(renter_uses_closing_input),
            float(market_corr_input),
            None if mc_seed is None else int(mc_seed),
            True,
            int(num_sims),
            _extra_items,
        )

        # Update MC speed estimate for next ETA seed
        try:
            _elapsed = max(1e-6, time.time() - _mc_t0)
            _sec_per_sim = _elapsed / max(1, int(num_sims))
            _prev = float(st.session_state.get("_rbv_mc_avg_sec_per_sim", 0.0))
            st.session_state["_rbv_mc_avg_sec_per_sim"] = (0.7 * _prev + 0.3 * _sec_per_sim) if _prev > 0 else _sec_per_sim
        except Exception:
            pass

        try:
            _mc_status.empty()
        except Exception:
            pass
        _rbv_global_progress_clear()

    else:
        _cfg_json = json.dumps(_cfg_run, sort_keys=True)
        _extra_items = tuple(sorted(st.session_state.get('_rbv_extra_engine_kwargs', extra_engine_kwargs).items()))
        df, close_cash, m_pmt, win_pct = _rbv_cached_run_simulation_core(
            _cfg_json,
            float(st.session_state.buyer_ret),
            float(st.session_state.renter_ret),
            float(st.session_state.apprec),
            bool(invest_surplus_input),
            bool(renter_uses_closing_input),
            float(market_corr_input),
            None if mc_seed is None else int(mc_seed),
            False,
            None,
            _extra_items,
        )

    st.session_state["_core_sim_cache"][_core_key] = (df, close_cash, m_pmt, win_pct)

    try:
        order = st.session_state["_core_sim_cache_order"]
        order.append(_core_key)
        # Soft LRU: keep only a few most recent entries (prevents session bloat)
        MAX_KEEP = 4
        if len(order) > MAX_KEEP:
            drop = order[:-MAX_KEEP]
            st.session_state["_core_sim_cache_order"] = order[-MAX_KEEP:]
            for k in drop:
                st.session_state["_core_sim_cache"].pop(k, None)
    except Exception:
        pass

# Extract (optional) Monte Carlo cash-out win% computed by the engine (kept separate from pre-tax verdict)
liq_win_pct = None
try:
    liq_win_pct = df.attrs.get("win_pct_liquidation", None)
except Exception:
    liq_win_pct = None


# --- Phase 3C: Core diagnostics (non-fatal) ---
try:
    # Win% bounds checks
    if win_pct is None:
        _msg = str(getattr(df, "attrs", {}).get("mc_error", "") or "").strip()
        _rbv_diag_add("WARN", "Pre-tax win% unavailable", _msg or "Engine returned win% = None.")
    else:
        wp = float(win_pct)
        if 0.0 <= wp <= 100.0:
            _rbv_diag_add("OK", "Pre-tax win% in bounds", f"{wp:.2f}%")
        else:
            _rbv_diag_add("FAIL", "Pre-tax win% out of bounds", f"win%={wp} (expected 0..100)")

    if liq_win_pct is not None:
        lwp = float(liq_win_pct)
        if 0.0 <= lwp <= 100.0:
            _rbv_diag_add("OK", "After-tax liquidation win% in bounds", f"{lwp:.2f}%")
        else:
            _rbv_diag_add("FAIL", "After-tax liquidation win% out of bounds", f"win%={lwp} (expected 0..100)")

    # Deterministic equivalence when σ=0 (engine sets attrs for degenerate MC)
    if bool(getattr(df, "attrs", {}).get("mc_degenerate", False)):
        det_ok = bool(getattr(df, "attrs", {}).get("mc_det_equiv_ok", False))
        if det_ok:
            _rbv_diag_add("OK", "σ=0 Monte Carlo matches deterministic path")
        else:
            _msg = str(getattr(df, "attrs", {}).get("mc_error", "") or "").strip()
            _rbv_diag_add("FAIL", "σ=0 MC mismatch vs deterministic", _msg or "Mismatch detected.")

    # NaN / non-finite guards for public metrics
    _cols_check = [
        "Buyer Net Worth", "Renter Net Worth",
        "Buyer PV NW", "Renter PV NW",
        "Buyer Unrecoverable", "Renter Unrecoverable",
    ]
    bad = []
    for c in _cols_check:
        if c in df.columns:
            v = df[c].to_numpy(dtype=np.float64, copy=False)
            n_bad = int(np.count_nonzero(~np.isfinite(v)))
            if n_bad:
                bad.append(f"{c} ({n_bad})")
    if bad:
        _rbv_diag_add("FAIL", "Non-finite values in outputs", ", ".join(bad))
    else:
        _rbv_diag_add("OK", "No NaN/Inf in key outputs")
        # Guardrail: surface when the engine had to normalize discount_rate units (prevents PV showing as $0)
        if bool(getattr(df, "attrs", {}).get("discount_rate_autonormalized", False)):
            _rbv_diag_add("WARN", "Discount rate auto-normalized", "PV discount rate looked like percent-points; normalized to fraction.")

except Exception as _e:
    _rbv_diag_add("WARN", "Diagnostics runtime issue", str(_e))




# Persist effective seed for sidebar display (and populate seed box when derived)
try:
    if use_volatility:
        st.session_state["mc_seed_effective"] = "" if mc_seed is None else str(int(mc_seed))
        st.session_state["mc_seed_effective_source"] = str(_mc_seed_source)
    else:
        st.session_state["mc_seed_effective"] = ""
        st.session_state["mc_seed_effective_source"] = ""
except Exception:
    pass

# --- Sidebar Export (CSV) ---
# (Removed in v2_60: redundant with main export.)

# --- Verdict banner (v2_61): build badge lines + colors safely (prevents NameError on rerun) ---
def _rbv_fmt_dollars(v) -> str:
    try:
        return f"${float(v):,.0f}"
    except Exception:
        return "—"

# --- Verdict banner breakeven (restore): show required threshold to tie at horizon ---
def _rbv_verdict_breakeven_msg(cfg_run: dict, winner: str) -> str | None:
    """Breakeven helper for the *pre-tax* verdict banner.

    Volatility OFF: deterministic bisection (no regression).
    Volatility ON: bisection against Monte Carlo *median* terminal outcomes using bias_mc_sims,
    with common random numbers (fixed seed across evaluations) for stability.
    """
    try:
        winner = str(winner or "")
    except Exception:
        winner = ""
    if winner not in ("Buying", "Renting"):
        return None

    buyer_ret_base = float(st.session_state.get("buyer_ret", 0.0))
    renter_ret_base = float(st.session_state.get("renter_ret", 0.0))
    apprec_base = float(st.session_state.get("apprec", 0.0))

    use_vol = bool(st.session_state.get("use_volatility", False))
    bias_sims = int(st.session_state.get("bias_mc_sims", 15000) or 15000)
    mc_mode = bool(use_vol) and (bias_sims > 1)

    # Use the active run's seed (if any) to keep breakeven consistent with displayed MC results.
    # Keep it fixed across bisection evaluations (CRN).
    try:
        _seed = globals().get("mc_seed", 0)
        seed_be = int(_seed) if _seed is not None else 0
    except Exception:
        seed_be = 0

    _extras = st.session_state.get("_rbv_extra_engine_kwargs", globals().get("extra_engine_kwargs", {})) or {}

    payload = {
        "tag": "verdict_be_v2_69",
        "winner": winner,
        "cfg": cfg_run,
        "buyer_ret": buyer_ret_base,
        "renter_ret": renter_ret_base,
        "apprec": apprec_base,
        "invest_diff": bool(st.session_state.get("invest_surplus_input", True)) and (not bool(st.session_state.get("budget_enabled", False))),
        "renter_uses_closing": bool(globals().get("renter_uses_closing_input", True)),
        "corr": float(globals().get("market_corr_input", 0.0)),
        "mc_mode": bool(mc_mode),
        "bias_sims": int(bias_sims),
        "seed_be": int(seed_be),
        "vol": {
            "use_vol": bool(use_vol),
            "ret_std_pct": float(st.session_state.get("ret_std_pct", 0.0) or 0.0),
            "apprec_std_pct": float(st.session_state.get("apprec_std_pct", 0.0) or 0.0),
            "corr": float(st.session_state.get("market_corr_input", globals().get("market_corr_input", 0.0)) or 0.0),
        },
        "extras": _extras,
    }
    ck = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    cache = st.session_state.setdefault("_verdict_breakeven_cache", {})
    if ck in cache:
        return cache[ck]

    def _eval_delta(apprec_pp: float | None = None, renter_ret_pp: float | None = None) -> float:
        ar = float(apprec_pp) if apprec_pp is not None else float(apprec_base)
        rr = float(renter_ret_pp) if renter_ret_pp is not None else float(renter_ret_base)

        if mc_mode:
            df2, *_ = run_simulation_core(
                cfg_run,
                float(buyer_ret_base),
                rr,
                ar,
                bool(invest_surplus_input),
                bool(renter_uses_closing_input),
                float(market_corr_input),
                force_deterministic=False,
                force_use_volatility=True,
                num_sims_override=int(bias_sims),
                mc_seed=int(seed_be),
                mc_summary_only=True,
                **_extras,
            )
        else:
            df2, *_ = run_simulation_core(
                cfg_run,
                float(buyer_ret_base),
                rr,
                ar,
                bool(invest_surplus_input),
                bool(renter_uses_closing_input),
                float(market_corr_input),
                force_deterministic=True,
                force_use_volatility=False,
                num_sims_override=1,
                mc_seed=int(seed_be),
                mc_summary_only=True,
                **_extras,
            )

        try:
            b = float(df2["Buyer Net Worth"].iloc[-1])
            r = float(df2["Renter Net Worth"].iloc[-1])
        except Exception:
            return float("nan")
        return b - r

    def _bisect(func, lo: float, hi: float, iters: int = 18) -> float | None:
        f_lo = func(lo)
        f_hi = func(hi)
        if not (np.isfinite(f_lo) and np.isfinite(f_hi)):
            return None
        if f_lo == 0.0:
            return lo
        if f_hi == 0.0:
            return hi
        if f_lo * f_hi > 0:
            return None
        for _ in range(iters):
            mid = 0.5 * (lo + hi)
            f_mid = func(mid)
            if not np.isfinite(f_mid):
                return None
            if f_lo * f_mid <= 0:
                hi, f_hi = mid, f_mid
            else:
                lo, f_lo = mid, f_mid
        return 0.5 * (lo + hi)

    out = None
    try:
        if winner == "Renting":
            be = _bisect(lambda x: _eval_delta(apprec_pp=x), lo=-10.0, hi=15.0, iters=18)
            if be is not None and np.isfinite(be):
                msg = (
                    f"To break even, the buyer would need a home-price appreciation rate of <b>{float(be):.2f}%/yr</b> "
                    f"(current assumption: {float(apprec_base):.2f}%/yr)."
                )
                out = f"<div style='margin-top:6px; font-size:12px; opacity:0.78; line-height:1.25;'>{msg}</div>"
        else:
            be = _bisect(lambda x: _eval_delta(renter_ret_pp=x), lo=-5.0, hi=20.0, iters=18)
            if be is not None and np.isfinite(be):
                msg = (
                    f"To break even, the renter would need an investment return of <b>{float(be):.2f}%/yr</b> "
                    f"(current assumption: {float(renter_ret_base):.2f}%/yr)."
                )
                out = f"<div style='margin-top:6px; font-size:12px; opacity:0.78; line-height:1.25;'>{msg}</div>"
    except Exception:
        out = None

    cache[ck] = out
    return out

def _rbv_cashout_breakeven_pack(cfg_run: dict, winner: str, fast_mode: bool) -> dict:
    """Breakeven helper for the *after-tax cash-out* banner.

    Volatility OFF: deterministic bisection.
    Volatility ON: bisection against Monte Carlo *median* terminal liquidation outcomes using bias_mc_sims,
    with common random numbers (fixed seed across evaluations).
    """
    try:
        winner = str(winner or "")
    except Exception:
        winner = ""
    if winner not in ("Buying", "Renting"):
        return {}

    buyer_ret_base = float(st.session_state.get("buyer_ret", 7.0))
    renter_ret_base = float(st.session_state.get("renter_ret", 7.0))
    apprec_base = float(st.session_state.get("apprec", 3.0))

    use_vol = bool(st.session_state.get("use_volatility", False))
    bias_sims = int(st.session_state.get("bias_mc_sims", 15000) or 15000)
    mc_mode = bool(use_vol) and (bias_sims > 1)

    try:
        _seed = globals().get("mc_seed", 0)
        seed_be = int(_seed) if _seed is not None else 0
    except Exception:
        seed_be = 0

    _extras = st.session_state.get("_rbv_extra_engine_kwargs", globals().get("extra_engine_kwargs", {})) or {}

    # Ensure liquidation columns are requested, independent of any older scenario states.
    cfg2 = dict(cfg_run or {})
    cfg2["show_liquidation_view"] = True

    payload = {
        "tag": "cashout_be_v2_69",
        "winner": winner,
        "cfg": cfg2,
        "buyer_ret": buyer_ret_base,
        "renter_ret": renter_ret_base,
        "apprec": apprec_base,
        "invest_diff": bool(st.session_state.get("invest_surplus_input", True)) and (not bool(st.session_state.get("budget_enabled", False))),
        "renter_uses_closing": bool(globals().get("renter_uses_closing_input", True)),
        "corr": float(globals().get("market_corr_input", 0.0)),
        "mc_mode": bool(mc_mode),
        "bias_sims": int(bias_sims),
        "seed_be": int(seed_be),
        "fast_mode": bool(fast_mode),
        "vol": {
            "use_vol": bool(use_vol),
            "ret_std_pct": float(st.session_state.get("ret_std_pct", 0.0) or 0.0),
            "apprec_std_pct": float(st.session_state.get("apprec_std_pct", 0.0) or 0.0),
            "corr": float(st.session_state.get("market_corr_input", globals().get("market_corr_input", 0.0)) or 0.0),
        },
        "extras": _extras,
    }
    ck = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    cache = st.session_state.setdefault("_liq_breakeven_cache", {})
    if ck in cache:
        return cache[ck]

    def _eval_delta_liq(apprec_pp: float | None = None, renter_ret_pp: float | None = None) -> float:
        ar = float(apprec_pp) if apprec_pp is not None else float(apprec_base)
        rr = float(renter_ret_pp) if renter_ret_pp is not None else float(renter_ret_base)

        if mc_mode:
            df2, *_ = run_simulation_core(
                cfg2,
                buyer_ret_base,
                rr,
                ar,
                bool(invest_surplus_input),
                bool(renter_uses_closing_input),
                float(market_corr_input),
                force_deterministic=False,
                force_use_volatility=True,
                num_sims_override=int(bias_sims),
                mc_seed=int(seed_be),
                mc_summary_only=True,
                **_extras,
            )
        else:
            df2, *_ = run_simulation_core(
                cfg2,
                buyer_ret_base,
                rr,
                ar,
                bool(invest_surplus_input),
                bool(renter_uses_closing_input),
                float(market_corr_input),
                force_deterministic=True,
                force_use_volatility=False,
                num_sims_override=1,
                mc_seed=int(seed_be),
                mc_summary_only=True,
                **_extras,
            )

        try:
            b = float(df2.get("Buyer Liquidation NW", pd.Series([float("nan")])).iloc[-1])
            r = float(df2.get("Renter Liquidation NW", pd.Series([float("nan")])).iloc[-1])
        except Exception:
            return float("nan")
        return b - r

    def _bisect(func, lo: float, hi: float, iters: int = 18) -> float | None:
        f_lo = func(lo)
        f_hi = func(hi)
        if not (np.isfinite(f_lo) and np.isfinite(f_hi)):
            return None
        if f_lo == 0.0:
            return lo
        if f_hi == 0.0:
            return hi
        if f_lo * f_hi > 0:
            return None
        for _ in range(iters):
            mid = 0.5 * (lo + hi)
            f_mid = func(mid)
            if not np.isfinite(f_mid):
                return None
            if f_lo * f_mid <= 0:
                hi, f_hi = mid, f_mid
            else:
                lo, f_lo = mid, f_mid
        return 0.5 * (lo + hi)

    pack = {
        "winner": winner,
        "assumption": None,
        "break_even": None,
        "needs": None,
        "msg_html": "",
        "details_html": "",
    }

    try:
        if winner == "Buying":
            need = _bisect(lambda x: _eval_delta_liq(renter_ret_pp=x), lo=-5.0, hi=20.0, iters=18)
            pack["needs"] = "renter_ret"
            pack["assumption"] = float(renter_ret_base)
            pack["break_even"] = float(need) if need is not None and np.isfinite(need) else None
        else:
            need = _bisect(lambda x: _eval_delta_liq(apprec_pp=x), lo=-10.0, hi=15.0, iters=18)
            pack["needs"] = "apprec"
            pack["assumption"] = float(apprec_base)
            pack["break_even"] = float(need) if need is not None and np.isfinite(need) else None
    except Exception:
        pack["break_even"] = None

    be = pack.get("break_even")
    assum = pack.get("assumption")
    if be is not None and assum is not None and np.isfinite(be) and np.isfinite(assum):
        if winner == "Renting":
            msg = (
                f"To break even, the buyer would need a home-price appreciation rate of <b>{float(be):.2f}%/yr</b> "
                f"(current assumption: {float(assum):.2f}%/yr)."
            )
        else:
            msg = (
                f"To break even, the renter would need an investment return of <b>{float(be):.2f}%/yr</b> "
                f"(current assumption: {float(assum):.2f}%/yr)."
            )
        pack["msg_html"] = f"<div style='margin-top:6px; font-size:12px; opacity:0.78; line-height:1.25;'>{msg}</div>"
    else:
        pack["msg_html"] = "<div style='margin-top:6px; font-size:12px; opacity:0.78; line-height:1.25;'>Breakeven not available for this scenario.</div>"

    try:
        mode_str = "Monte Carlo (median)" if mc_mode else "Deterministic"
        det = [f"<b>Mode:</b> {mode_str}"]
        if mc_mode:
            det.append(f"<b>Bias MC sims:</b> {int(bias_sims):,} (seed: {int(seed_be)})")
        det.append(f"<b>Current assumptions:</b> appreciation {apprec_base:.2f}%/yr, renter return {renter_ret_base:.2f}%/yr")
        pack["details_html"] = "<div style='font-size:12px; line-height:1.35; opacity:0.92;'>" + "<br/>".join(det) + "</div>"
    except Exception:
        pack["details_html"] = ""

    cache[ck] = pack
    return pack

# --- Tax / liquidation context banner ---
# (Moved into the main verdict banner for clarity)


# --- Pre-tax verdict banner (Before-tax) ---
# NOTE: Keep banner visible and robust even if outputs are missing (avoid silent UI disappearance).
try:
    _final_row = df.iloc[-1] if (df is not None and len(df) > 0) else None
    _b_end = float(_final_row.get("Buyer Net Worth", np.nan)) if _final_row is not None else float("nan")
    _r_end = float(_final_row.get("Renter Net Worth", np.nan)) if _final_row is not None else float("nan")
    _have_pre = bool(np.isfinite(_b_end) and np.isfinite(_r_end))

    if _have_pre:
        _diff = _b_end - _r_end
        _is_buy = (_diff >= 0)
        _c = "var(--buy)" if _is_buy else "var(--rent)"
        _bg = "var(--buy-bg)" if _is_buy else "var(--rent-bg)"
        _label = "Buying" if _is_buy else "Renting"
        _amt = f"${abs(_diff):,.0f}"
        _line = f"{_label} leads by <b>{_amt}</b>"
        _winner = _label
    else:
        _is_buy = True
        _c = "rgba(241,241,243,0.90)"
        _bg = "rgba(255,255,255,0.06)"
        _line = "Before-tax values are unavailable for this run (N/A)."
        _winner = "Buying"

    # Optional: PV delta note (kept secondary; banner itself is explicitly 'Before-tax')
    _sub_bits = []
    try:
        _bpv = float(_final_row.get("Buyer PV NW", np.nan)) if _final_row is not None else float("nan")
        _rpv = float(_final_row.get("Renter PV NW", np.nan)) if _final_row is not None else float("nan")
        if np.isfinite(_bpv) and np.isfinite(_rpv):
            _dpv = _bpv - _rpv
            _pv_label = "Buying" if (_dpv >= 0) else "Renting"
            _sub_bits.append(f"PV delta: {_pv_label} +<b>${abs(_dpv):,.0f}</b>")
    except Exception:
        pass

    # Monte Carlo win probability (pre-tax): show winner-aligned confidence
    try:
        _wp = win_pct
        if _wp is None:
            _wp = getattr(df, "attrs", {}).get("win_pct_pre_tax", None)
        _ns = int(st.session_state.get("num_sims", globals().get("num_sims", 1)) or 1)
        mc_degenerate = bool(getattr(df, "attrs", {}).get("mc_degenerate", False))
        if bool(use_volatility) and (_ns > 1) and (_wp is not None) and (not mc_degenerate):
            _wp = float(_wp)
            _wp = max(0.0, min(100.0, _wp))
            _conf = _wp if bool(_is_buy) else (100.0 - _wp)
            _sub_bits.append(f"Monte Carlo win probability: <b>{_conf:.1f}%</b>")
    except Exception:
        pass

    _sub = " • ".join([s for s in _sub_bits if str(s).strip()]).strip()

    _be_msg = ""
    try:
        if _have_pre:
            _be_msg = _rbv_verdict_breakeven_msg(globals().get("_cfg_run", {}), _winner) or ""
        if not str(_be_msg).strip():
            _be_msg = "<div style='margin-top:6px; font-size:12px; opacity:0.78; line-height:1.25;'>Breakeven not available for this scenario.</div>"
    except Exception:
        _be_msg = "<div style='margin-top:6px; font-size:12px; opacity:0.78; line-height:1.25;'>Breakeven not available for this scenario.</div>"

    st.markdown('<div style="height:14px;"></div>', unsafe_allow_html=True)
    st.markdown(
        f"""<div class=\"verdict-banner\" style=\"--badge-bg:{_bg}; --badge-color:{_c};\">
              <div class=\"verdict-tag\">Before-tax</div>
              <div class=\"verdict-line\">{_line}</div>
              {('<div class="verdict-sub">' + _sub + '</div>') if _sub else ''}
              {_be_msg}
            </div>""",
        unsafe_allow_html=True,
    )
except Exception:
    pass


st.markdown("<div style=\"height:18px\"></div>", unsafe_allow_html=True)

# --- KPI summary values (robust to column naming) ---
def _df_last(df_, candidates, default=0.0):
    for c in candidates:
        if c in df_.columns:
            try:
                return float(df_[c].iloc[-1])
            except Exception:
                pass
    return float(default)

def _df_mean(df_, candidates, default=0.0):
    for c in candidates:
        if c in df_.columns:
            try:
                return float(pd.to_numeric(df_[c], errors="coerce").dropna().mean())
            except Exception:
                pass
    return float(default)


# --- Liquidity / cashflow shortfall (Budget Mode) ---
try:
    if bool(st.session_state.get("budget_enabled", False)):
        b_sf = _df_last(df, ["Buyer Shortfall", "b_shortfall"], 0.0)
        r_sf = _df_last(df, ["Renter Shortfall", "r_shortfall"], 0.0)
        if (b_sf > 0) or (r_sf > 0):
            s1, s2 = st.columns(2)
            with s1:
                st.metric("Buyer cashflow shortfall", f"${b_sf:,.0f}")
            with s2:
                st.metric("Renter cashflow shortfall", f"${r_sf:,.0f}")
except Exception:
    pass

buyer_nw_end   = _df_last(df, ["Buyer Net Worth", "Buyer NW", "Buyer_NW"])
renter_nw_end  = _df_last(df, ["Renter Net Worth", "Renter NW", "Renter_NW"])
buyer_pv_end   = _df_last(df, ["Buyer PV NW", "Buyer PV Net Worth", "Buyer PV"])
renter_pv_end  = _df_last(df, ["Renter PV NW", "Renter PV Net Worth", "Renter PV"])

avg_buy_monthly  = _df_mean(df, ["Buy Payment", "Buyer Monthly Cost", "Buyer Total Monthly Cost"])
avg_rent_monthly = _df_mean(df, ["Rent Payment", "Renter Monthly Cost", "Renter Total Monthly Cost"])
monthly_gap = avg_rent_monthly - avg_buy_monthly
renter_saves = avg_buy_monthly - avg_rent_monthly  # >0 means renting is cheaper per month on average

def _kpi(title: str, value: str, accent: str, help_text: str | None = None, *, neutral: bool = False):
    """Render a compact KPI card with optional hover help icon (custom dark tooltip)."""
    help_html = rbv_help_html(help_text or "", small=True) if help_text else ""
    cls = "kpi-card kpi-neutral" if neutral else "kpi-card"
    st.markdown(
        f"""<div class="{cls}" style="--accent:{accent};">
              <div class="kpi-title"><span>{html.escape(title)}</span>{help_html}</div>
              <div class="kpi-value">{html.escape(value)}</div>
            </div>""",
        unsafe_allow_html=True,
    )


# --- Premium KPI summary (with help icons) ---
st.markdown('<div style="height:14px;"></div>', unsafe_allow_html=True)

# --- Quick-signal KPIs (high-signal sanity metrics) ---
try:
    # Breakeven (first month where Buyer NW >= Renter NW)
    be_year = None
    try:
        _b_series = pd.to_numeric(df.get("Buyer Net Worth"), errors="coerce") if "Buyer Net Worth" in df.columns else None
        _r_series = pd.to_numeric(df.get("Renter Net Worth"), errors="coerce") if "Renter Net Worth" in df.columns else None
        if (_b_series is not None) and (_r_series is not None):
            _d = (_b_series - _r_series).to_numpy()
            _idx = np.where(np.isfinite(_d) & (_d >= 0))[0]
            if len(_idx) > 0:
                _i0 = int(_idx[0])
                if "Month" in df.columns:
                    _m = float(df["Month"].iloc[_i0])
                    be_year = _m / 12.0
                else:
                    be_year = _i0 / 12.0
    except Exception:
        be_year = None

    # Price-to-rent ratio (headline heuristic)
    ptr = None
    try:
        _price = float(st.session_state.get("price", 0.0) or 0.0)
        _rent = float(st.session_state.get("rent", 0.0) or 0.0)
        if _price > 0 and _rent > 0:
            ptr = _price / (_rent * 12.0)
    except Exception:
        ptr = None

    # Surplus investing status (the most important behavioral assumption)
    try:
        _budget = bool(st.session_state.get("budget_enabled", False))
        _inv = bool(st.session_state.get("invest_surplus_input", True)) and (not _budget)
    except Exception:
        _inv = True

    q1, q2, q3, q4 = st.columns(4, gap="small")
    with q1:
        _kpi(
            "Breakeven (NW)",
            (f"{be_year:.1f}y" if (be_year is not None) else "—"),
            "rgba(255,255,255,0.28)",
            "First year where buyer net worth meets/exceeds renter net worth under the current assumptions.",
            neutral=True,
        )
    with q2:
        _kpi(
            "Price-to-rent",
            (f"{ptr:.1f}×" if (ptr is not None) else "—"),
            "rgba(255,255,255,0.28)",
            "Home price divided by annual rent (price ÷ (rent×12)). A rough valuation sanity check.",
            neutral=True,
        )
    with q3:
        _kpi(
            "Surplus investing",
            ("ON" if _inv else "OFF"),
            ("var(--buy)" if _inv else "rgba(255,90,90,0.85)"),
            "If ON, any monthly cost advantage is invested. If OFF, the model tracks it as cash (0% return).",
            neutral=True,
        )
    with q4:
        _kpi(
            "Mode",
            ("Monte Carlo" if bool(st.session_state.get("use_volatility", False)) else "Deterministic"),
            "rgba(255,255,255,0.28)",
            "Monte Carlo shows distributions (win%, bands). Deterministic uses single-point assumptions.",
            neutral=True,
        )

    st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
except Exception:
    # Never block the app on KPI rendering
    pass

col_buy, col_rent = st.columns(2, gap="medium")

with col_buy:
    st.markdown('<div class="kpi-section-title buy-title">BUYING DETAILS</div>', unsafe_allow_html=True)
    b1, b2 = st.columns(2, gap="small")
    with b1:
        _kpi("Cash to Close", f"${close_cash:,.0f}", "var(--buy)",
             "Upfront cash required to buy: down payment + closing costs (transfer tax, legal/closing, inspection, other one-time costs, PST on CMHC premium where applicable).")
    with b2:
        _kpi("Avg Monthly Outflow", f"${avg_buy_monthly:,.0f}", "var(--buy)",
             "Average monthly cash outflow for the buyer over the horizon (mortgage payment incl. principal + recurring ownership costs). Principal paydown builds equity; see the Irrecoverable Costs tab for pure non-equity costs.")

    b3, b4 = st.columns(2, gap="small")
    with b3:
        _kpi("Total NW (Horizon)", f"${buyer_nw_end:,.0f}", "var(--buy)",
             "Buyer net worth at the end of the horizon (home equity + invested portfolio).")
    with b4:
        _kpi("PV NW", f"${buyer_pv_end:,.0f}", "var(--buy)",
             "Present value of buyer net worth, discounting future dollars by the PV (discount) rate.")

with col_rent:
    st.markdown('<div class="kpi-section-title rent-title">RENTING DETAILS</div>', unsafe_allow_html=True)
    r1, r2 = st.columns(2, gap="small")
    with r1:
        _kpi("Avg Monthly Outflow", f"${avg_rent_monthly:,.0f}", "var(--rent)",
             "Average monthly cash outflow for the renter over the horizon (rent + renter costs, if any).")
    with r2:
        label = "Renter Saves" if renter_saves > 0 else "Buyer Saves"
        saves = abs(renter_saves)
        _kpi(label, f"${saves:,.0f}/mo", "var(--rent)" if renter_saves > 0 else "var(--buy)",
             "Average monthly advantage vs the other option (positive means renting is cheaper on average).")
    r3, r4 = st.columns(2, gap="small")
    with r3:
        _kpi("Total NW (Horizon)", f"${renter_nw_end:,.0f}", "var(--rent)",
             "Renter net worth at the end of the horizon (invested portfolio).")
    with r4:
        _kpi("PV NW", f"${renter_pv_end:,.0f}", "var(--rent)",
             "Present value of renter net worth, discounting future dollars by the PV (discount) rate.")



def _fmt_number(x):
    try:
        return f"{x:,.0f}"
    except Exception:
        return str(x)



def _fmt_money(x, decimals=0, prefix="$"):
    """Format numbers as currency for UI tables/cards. Returns em dash for missing values."""
    try:
        if x is None:
            return "—"
        # Handle pandas/np NaN
        import math
        if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
            return "—"
        # Convert numpy scalars
        try:
            x = float(x)
        except Exception:
            return str(x)
        sign = "-" if x < 0 else ""
        x_abs = abs(x)
        if decimals == 0:
            body = f"{x_abs:,.0f}"
        else:
            body = f"{x_abs:,.{decimals}f}"
        return f"{sign}{prefix}{body}"
    except Exception:
        return "—"

# --- Winner badge + "what changed" summary (results header) ---
try:
    # Winner badge based on final nominal Δ NW
    _final_row = df.iloc[-1]
    _final_buy = float(_final_row.get("Buyer Net Worth", np.nan))
    _final_rent = float(_final_row.get("Renter Net Worth", np.nan))


    # What-changed mini summary (trust builder)
    _changes = []
    try:
        if rent_control_enabled:
            _changes.append(f"Rent cap enabled (max {rent_control_cap*100:.2f}%)")
    except Exception:
        pass
    try:
        if rate_mode != "Fixed":
            _changes.append(f"Mortgage renewals: every {int(rate_reset_years)}y" + (f", step {rate_reset_step_pp:+.2f} pp" if abs(rate_reset_step_pp) > 1e-9 else ""))
    except Exception:
        pass
    try:
        if rate_shock_enabled:
            _changes.append(f"Rate shock: +{rate_shock_pp:.2f} pp from year {rate_shock_start_year} for {rate_shock_duration_years}y")
    except Exception:
        pass
    try:
        _changes.append(f"Performance mode: {st.session_state.get('sim_mode', 'Fast')}")
    except Exception:
        pass
    try:
        if transfer_tax_override not in (None, "", 0):
            _changes.append("Transfer tax override is active (override is ground truth)")
    except Exception:
        pass

    if _changes:
        st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
        with st.expander("🔎 What changed in this run?", expanded=False):
            st.markdown("\n".join([f"- {c}" for c in _changes]))

    # Cash-to-close breakdown (kept near other run-level drop-downs, below banners).
    st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)
    with st.expander("💰 Cash to Close breakdown", expanded=False):
        try:
            _items = [
                ("Down payment", float(down)),
                ("Transfer tax (provincial)", float(prov_ltt)),
                ("Legal & closing", float(lawyer)),
                ("Home inspection", float(insp)),
                ("Other closing costs", float(other_closing)),
            ]

            try:
                if float(muni_ltt) > 0:
                    _items.insert(2, ("Transfer tax (municipal)", float(muni_ltt)))
            except Exception:
                pass

            _pst = float(pst) if "pst" in globals() else 0.0
            if _pst > 0:
                _items.append(("PST on CMHC premium", _pst))

            _total_calc = sum(v for _, v in _items)
            _items.append(("Total cash to close", _total_calc))

            # Render as simple key/value rows (no headers, no row numbers).
            for _label, _val in _items:
                _is_total = (str(_label).lower().strip() == "total cash to close")
                st.markdown(
                    f"<div class=\"rbv-kv-row{(' rbv-kv-total' if _is_total else '')}\">"
                    f"<div class=\"rbv-kv-key\">{_label}</div>"
                    f"<div class=\"rbv-kv-val\">{_fmt_money(_val)}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            # Mortgage default insurance (premium is typically capitalized into the mortgage).
            try:
                _prem = float(prem) if "prem" in globals() else 0.0
                _mort = float(mort) if "mort" in globals() else 0.0
                _cmhc_r = float(cmhc_r) if "cmhc_r" in globals() else 0.0
                _ltv = float(ltv) if "ltv" in globals() else 0.0
                if bool(insured) and _prem > 0:
                    st.markdown('<div class="rbv-kv-divider"></div>', unsafe_allow_html=True)
                    st.markdown("**Mortgage default insurance**", unsafe_allow_html=True)
                    st.markdown(
                        f"<div class=\"rbv-kv-row\"><div class=\"rbv-kv-key\">CMHC premium (financed)</div><div class=\"rbv-kv-val\">{_fmt_money(_prem)}</div></div>",
                        unsafe_allow_html=True,
                    )
                    st.caption(
                        f"Premium rate: {_cmhc_r*100:.2f}% at LTV {_ltv*100:.2f}%. The premium is typically added to the mortgage principal (so it's repaid over time in the monthly payment). PST, if applicable, is paid at closing."
                    )
                    if _mort > 0:
                        st.caption(f"Insured mortgage principal (loan + premium): {_fmt_money(_mort)}")
            except Exception:
                pass

            if transfer_tax_note:
                st.caption(str(transfer_tax_note))

            # Cash to close returned by the engine should closely match the computed breakdown.
            try:
                _diff = float(close_cash) - float(_total_calc)
                if abs(_diff) >= 2.0:
                    st.caption(f"Engine Cash to Close: {_fmt_money(float(close_cash))} (diff {(_diff):+,.0f}).")
            except Exception:
                pass
        except Exception:
            st.caption("Breakdown unavailable for current inputs.")
except Exception:
    # Never block the app if the badge fails
    pass



# -----------------------------
# Debug / reproducibility pane
# -----------------------------
try:
    import hashlib, json as _json

    _last_cfg = st.session_state.get("_rbv_last_cfg")
    _last_params = st.session_state.get("_rbv_last_params") or {}
    if isinstance(_last_cfg, dict) and _last_cfg:
        # Build a compact, human-checkable snapshot (units are explicit).
        _snap = {
            "version": str(st.session_state.get("_rbv_version", "")) or "v2.92.10",
            "inputs": {
                "years": _last_cfg.get("years"),
                "price": _last_cfg.get("price"),
                "down": _last_cfg.get("down"),
                "mort": _last_cfg.get("mort"),
                "cash_to_close": _last_cfg.get("close"),
                "mort_rate_nominal_pct": _last_cfg.get("rate"),
                "amort_years": _last_cfg.get("amort_years"),
                "term_years": _last_cfg.get("mortgage_term_years"),
                "rent_monthly": _last_cfg.get("rent"),
                "rent_inf_annual_frac": _last_cfg.get("rent_inf"),
                "discount_rate_annual_frac": _last_cfg.get("discount_rate"),
                "general_inf_annual_frac": _last_cfg.get("general_inf"),
                "sell_cost_frac": _last_cfg.get("sell_cost"),
                "prop_tax_rate_frac": _last_cfg.get("p_tax_rate"),
                "maint_rate_frac": _last_cfg.get("maint_rate"),
                "repair_rate_frac": _last_cfg.get("repair_rate"),
                "condo_monthly": _last_cfg.get("condo"),
                "home_ins_monthly": _last_cfg.get("h_ins"),
                "utilities_monthly": _last_cfg.get("util"),
                "land_transfer_region": _last_cfg.get("land_transfer_region"),
                "first_time_buyer": _last_cfg.get("first_time_buyer"),
                "investment_tax_mode": _last_cfg.get("investment_tax_mode"),
                "tax_r_pct": _last_cfg.get("tax_r"),
            },
            "run_params": dict(_last_params),
        }
        _fp = hashlib.sha256(_json.dumps(_snap, sort_keys=True).encode("utf-8")).hexdigest()[:12]
        _snap["fingerprint"] = _fp

        # Surface suspicious-unit warnings (does not block).
        _warn = []
        try:
            if (_snap["inputs"].get("rent_inf_annual_frac") or 0) > 0.5:
                _warn.append("rent_inf looks like percent-points (expected fraction).")
        except Exception:
            pass
        try:
            if (_snap["inputs"].get("discount_rate_annual_frac") or 0) > 0.5:
                _warn.append("discount_rate looks like percent-points (expected fraction).")
        except Exception:
            pass
        try:
            if (_snap["run_params"].get("buyer_ret_pct") or 0) > 100:
                _warn.append("buyer_ret_pct looks too large (expected annual % like 5–12).")
        except Exception:
            pass

        with st.expander("🧾 Effective inputs used by the engine (debug)", expanded=False):
            st.caption(f"Fingerprint: `{_fp}` — use this to confirm you're running the *exact same* scenario/config across versions.")
            if _warn:
                st.warning("Potential unit issues detected:\n" + "\n".join([f"- {w}" for w in _warn]))
            st.json(_snap)
            st.download_button(
                "Download run snapshot (JSON)",
                data=_json.dumps(_snap, indent=2),
                file_name=f"rbv_run_snapshot_{_fp}.json",
                mime="application/json",
                use_container_width=True,
            )
except Exception:
    pass



def render_fin_table(dframe: pd.DataFrame, index_name: str | None = None, table_key: str = "table") -> str:
    """Render a dark, fintech-styled HTML table that matches the app theme.

    Why HTML? Streamlit's native dataframe renderer can ignore CSS/styler in some versions.
    This keeps *all content* while giving full control over dark-theme visuals and mobile behavior.
    """
    if dframe is None or len(dframe) == 0:
        return '<div class="fin-table-empty">No data.</div>'

    df = dframe.copy()

    # Bring index into the table for display
    idx_name = index_name or (df.index.name if df.index.name else "Index")
    df = df.reset_index()
    if df.columns[0] != idx_name:
        df = df.rename(columns={df.columns[0]: idx_name})

    # Determine numeric columns
    num_cols = set(df.select_dtypes(include=["number"]).columns)

    cols = list(df.columns)

    # Header (align numeric headers with numeric cells)
    ths = []
    for c in cols:
        c_norm = str(c).strip().lower()
        is_num = c in num_cols and c_norm not in {"month", "year", idx_name.strip().lower()}
        th_cls = ' class="num"' if is_num else ""
        ths.append(f"<th{th_cls}>{html.escape(str(c))}</th>")
    thead = "".join(ths)

    # Body
    body_rows = []
    for _, row in df.iterrows():
        tds = []
        for c in cols:
            v = row[c]
            cls = []
            style_attr = ""
            # Delta-style coloring (Δ / PV Δ / Diff / Deficit)
            # Color shows direction (Buyer ahead vs Renter ahead). Displayed value uses absolute magnitude.
            delta_keys = {"diff", "deficit", "delta", "pv delta"}
            c_str = str(c).strip()
            c_norm = c_str.lower()
            is_delta_col = (c_norm in delta_keys) or (c_str in {"Δ", "PV Δ"}) or ("Δ" in c_str)

            def _to_float(val):
                try:
                    if isinstance(val, (int, float, np.integer, np.floating)) and not (isinstance(val, float) and np.isnan(val)):
                        return float(val)
                    if isinstance(val, str):
                        s = val.replace("$", "").replace(",", "").strip()
                        if s in {"", "nan", "NaN"}:
                            return None
                        return float(s)
                except Exception:
                    return None
                return None

            delta_num = None
            if is_delta_col:
                # Prefer the value in the delta column itself if present & parseable
                delta_num = _to_float(v)

                # For the core delta columns, ALWAYS compute direction from the underlying series
                # so styling can't be broken by formatting/coercion of the Δ column itself.
                if c_str == "Δ":
                    b = _to_float(row.get("Buyer NW", row.get("Buyer Net Worth", None)))
                    r = _to_float(row.get("Renter NW", row.get("Renter Net Worth", None)))
                    delta_num = (b - r) if (b is not None and r is not None) else delta_num
                elif c_str == "PV Δ":
                    b = _to_float(row.get("Buyer PV NW", None))
                    r = _to_float(row.get("Renter PV NW", None))
                    delta_num = (b - r) if (b is not None and r is not None) else delta_num

                # Fallback: if delta value missing, try to derive when possible
                if delta_num is None:
                    if c_str == "Δ":
                        b = _to_float(row.get("Buyer NW", row.get("Buyer Net Worth", None)))
                        r = _to_float(row.get("Renter NW", row.get("Renter Net Worth", None)))
                        delta_num = (b - r) if (b is not None and r is not None) else None
                    elif c_str == "PV Δ":
                        b = _to_float(row.get("Buyer PV NW", None))
                        r = _to_float(row.get("Renter PV NW", None))
                        delta_num = (b - r) if (b is not None and r is not None) else None

                if delta_num is not None:
                    cls.append("delta")
                    if delta_num > 0:
                        cls.append("pos")   # Buyer ahead
                    elif delta_num < 0:
                        cls.append("neg")   # Renter ahead
                    else:
                        cls.append("zero")
                        style_attr = ""

            # Numeric formatting (money for most columns; plain for Month/Year)
            if c in num_cols and isinstance(v, (int, float, np.integer, np.floating)):
                # Handle NaN cleanly (avoid "$nan")
                if isinstance(v, float) and np.isnan(v):
                    txt = "—"
                    cls.append("num")
                elif c_norm in {"month", "year"}:
                    txt = _fmt_number(v)
                    cls.append("num")
                else:
                    # For delta columns, remove the minus sign and let color indicate direction
                    txt = _fmt_money(abs(delta_num)) if (is_delta_col and delta_num is not None) else (_fmt_money(abs(v)) if is_delta_col else _fmt_money(v))
                    cls.append("num")
            else:
                txt = html.escape(str(v))

            class_attr = f' class="{" ".join(cls)}"' if cls else ""
            tds.append(f"<td{class_attr}{style_attr}>{txt}</td>")
        body_rows.append("<tr>" + "".join(tds) + "</tr>")

    tbody = "".join(body_rows)

    return (
        f'<div class="fin-table-wrap" data-tablekey="{html.escape(table_key)}">'
        f'  <div class="fin-table-scroll">'
        f'    <table class="fin-table">'
        f'      <thead><tr>{thead}</tr></thead>'
        f'      <tbody>{tbody}</tbody>'
        f'    </table>'
        f'  </div>'
        f'</div>'
    )



# --- Optional Liquidation View (after-tax "cash in hand" at horizon) ---
show_liquidation_view = bool(st.session_state.get("show_liquidation_view", True))
if show_liquidation_view:
    try:
        _b_liq = df.get("Buyer Liquidation NW", pd.Series([None])).iloc[-1]
        _r_liq = df.get("Renter Liquidation NW", pd.Series([None])).iloc[-1]
        _liq_have = pd.notna(_b_liq) and pd.notna(_r_liq)

        if _liq_have:
            _diff_liq = float(_b_liq) - float(_r_liq)
            _liq_is_buy = _diff_liq >= 0
            _liq_c = "var(--buy)" if _liq_is_buy else "var(--rent)"
            _liq_bg = "var(--buy-bg)" if _liq_is_buy else "var(--rent-bg)"
            _liq_label = "Buying" if _liq_is_buy else "Renting"
            _liq_amt = f"${abs(_diff_liq):,.0f}"
            _liq_line = f"{_liq_label} leads by <b>{_liq_amt}</b> <span class=\"verdict-pv\">(cash-out)</span>"
        else:
            # Keep banner visible even if liquidation metrics are unavailable (prevents silent UI disappearance).
            _liq_is_buy = True
            _liq_c = "rgba(241,241,243,0.90)"
            _liq_bg = "rgba(255,255,255,0.06)"
            _liq_label = "Cash-out"
            _liq_amt = "—"
            _liq_line = "Cash-out values are unavailable for this run (N/A)."

        # --- Breakeven (after-tax cash-out) ---
        _liq_be_pack = {}
        try:
            if _liq_have:
                _liq_winner = "Buying" if bool(_liq_is_buy) else "Renting"
                _liq_be_pack = _rbv_cashout_breakeven_pack(globals().get("_cfg_run", {}), _liq_winner, bool(fast_mode))
                _liq_breakeven_msg = str((_liq_be_pack or {}).get("msg_html") or "").strip()
            else:
                _liq_breakeven_msg = "<div style=\"margin-top:6px; font-size:12px; opacity:0.78; line-height:1.25;\">Breakeven requires valid cash-out values for this scenario.</div>"
        except Exception:
            _liq_be_pack = {}
            _liq_breakeven_msg = "<div style=\"margin-top:6px; font-size:12px; opacity:0.78; line-height:1.25;\">Breakeven not available for this scenario.</div>"

        try:
            _mode = str(investment_tax_mode)
        except Exception:
            _mode = ""
        if _mode.startswith("Pre-tax"):
            _tax_note = f"Portfolio CG tax applied at horizon ({float(cg_tax_end):.1f}% rate)."
        elif _mode.startswith("Annual"):
            _tax_note = "Portfolio taxes approximated via annual return drag (no extra CG at cash-out)."
        else:
            _tax_note = f"Deferred CG applied at horizon ({float(cg_tax_end):.1f}% rate)."

        # Optional: show Monte Carlo win probability on a cash-out basis
        _liq_win_note = ""
        try:
            mc_degenerate = bool(getattr(df, "attrs", {}).get("mc_degenerate", False))
            if _liq_have and bool(use_volatility) and (liq_win_pct is not None) and (not mc_degenerate):
                _lw = float(liq_win_pct)
                _lw = max(0.0, min(100.0, _lw))
                _conf_liq = _lw if bool(_liq_is_buy) else (100.0 - _lw)
                _liq_win_note = f"Monte Carlo win probability (cash-out): <b>{_conf_liq:.1f}%</b>"
        except Exception:
            _liq_win_note = ""

        st.markdown('<div style="height:14px;"></div>', unsafe_allow_html=True)

        _liq_sub_bits = []
        try:
            if str(_tax_note).strip():
                _liq_sub_bits.append(str(_tax_note).strip())
            try:
                if not bool(st.session_state.get("assume_sale_end", True)):
                    _liq_sub_bits.append("Home held at horizon (equity excluded).")
            except Exception:
                pass
        except Exception:
            pass
        try:
            if str(_liq_win_note).strip():
                _liq_sub_bits.append(str(_liq_win_note).strip())
        except Exception:
            pass
        _liq_sub = " • ".join(_liq_sub_bits).strip()

        # Use the same premium verdict banner styling for the cash-out view.
        st.markdown(
            f"""<div class=\"verdict-banner\" style=\"--badge-bg:{_liq_bg}; --badge-color:{_liq_c};\">
              <div class=\"verdict-tag\">After-tax</div>
              <div class=\"verdict-line\">{_liq_line}</div>
              {('<div class="verdict-sub">' + _liq_sub + '</div>') if _liq_sub else ''}
              {_liq_breakeven_msg}
            </div>""",
            unsafe_allow_html=True,
        )

        # Cash-out breakeven details (no extra compute button)
        try:
            _details = str((_liq_be_pack or {}).get("details_html") or "").strip()
            if _details:
                st.markdown("<div style=\"height:14px\"></div>", unsafe_allow_html=True)
                with st.expander("Breakeven (after-tax cash-out) — details", expanded=False):
                    st.markdown(_details, unsafe_allow_html=True)
        except Exception:
            pass

    except Exception:
        pass

# Spacer to prevent any overlap between KPI cards and tabs
st.markdown('<div style="height:28px;"></div>', unsafe_allow_html=True)

# --- Tabs ---
_TAB_NET = "Net Worth Analysis"
_TAB_COSTS = "Ongoing Housing Costs"
_TAB_BIAS = "Bias & Sensitivity"
_TAB_ASSUM = "Model Assumptions"

_tab_labels = [_TAB_NET, _TAB_COSTS, _TAB_BIAS, _TAB_ASSUM]
_tab_default = st.session_state.get("rbv_tab_nav", _tab_labels[0])
try:
    _tab_index = _tab_labels.index(_tab_default) if _tab_default in _tab_labels else 0
except Exception:
    _tab_index = 0

# Center the tab "banner" (radio styled as tabs) in the middle of the page
_tl, _tc, _tr = st.columns([1, 3, 1])
with _tc:
    tab = st.radio(
        "Main tabs",
        _tab_labels,
        index=_tab_index,
        horizontal=True,
        key="rbv_tab_nav",
        label_visibility="collapsed",
    )

st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
if tab == _TAB_NET:
    with st.expander("📊 How to read this Graph", expanded=False):
        st.markdown("""
        * **Solid Lines:** The most likely (median) outcome.
        * **Shaded Areas:** The "Cone of Uncertainty" (5th to 95th percentile).
        * **Wide Shading:** Means high volatility (more risk/uncertainty).
        * **Narrow Shading:** Means the outcome is more predictable.
        """)


    # Progress area for long computations in this tab (heatmap, etc.)
    _t1_longrun_bar = st.empty()
    _t1_longrun_status = st.empty()
    st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)

    # Lightweight chart overlays (audit polish)
    _nw_opt_cols = st.columns([1, 1, 3])
    with _nw_opt_cols[0]:
        show_be_marker = st.toggle("Breakeven marker", value=True, key="nw_show_be_marker")
    with _nw_opt_cols[1]:
        shade_negative = st.toggle("Shade negative NW", value=True, key="nw_shade_negative")

    fig = go.Figure()
    x = df['Month'] / 12.0

    # Graphs - Dark Theme Optimized
    fig.add_trace(go.Scatter(x=x, y=df['Buyer Net Worth'], name="Buying", mode='lines', line=dict(color=BUY_COLOR, width=2)))
    fig.add_trace(go.Scatter(x=x, y=df['Renter Net Worth'], name="Renting", mode='lines', line=dict(color=RENT_COLOR, width=2)))

    if use_volatility:
        # VIBRANT COLORS (Opacity 0.3)
        fig.add_trace(go.Scatter(x=x, y=df['Buyer NW High'], name="Buyer High", mode='lines', line=dict(width=0), showlegend=False))
        fig.add_trace(go.Scatter(x=x, y=df['Buyer NW Low'], name="Buyer Low", mode='lines', line=dict(width=0), fill='tonexty', fillcolor=_rbv_rgba(BUY_COLOR, 0.20), showlegend=False))
        fig.add_trace(go.Scatter(x=x, y=df['Renter NW High'], name="Renter High", mode='lines', line=dict(width=0), showlegend=False))
        fig.add_trace(go.Scatter(x=x, y=df['Renter NW Low'], name="Renter Low", mode='lines', line=dict(width=0), fill='tonexty', fillcolor=_rbv_rgba(RENT_COLOR, 0.20), showlegend=False))

    # Optional overlays: negative-region shading + breakeven marker (Δ crosses 0)
    try:
        if bool(locals().get("shade_negative", False)):
            _cols = ["Buyer Net Worth", "Renter Net Worth"]
            if bool(locals().get("use_volatility", False)):
                _cols += ["Buyer NW Low", "Renter NW Low"]
            _vals = []
            for _c in _cols:
                if _c in df.columns:
                    try:
                        _vals.append(pd.to_numeric(df[_c], errors="coerce").to_numpy())
                    except Exception:
                        pass
            if _vals:
                _ymin = float(np.nanmin(np.concatenate(_vals)))
                if np.isfinite(_ymin) and _ymin < 0:
                    _x0 = float(np.nanmin(pd.to_numeric(x, errors="coerce")))
                    _x1 = float(np.nanmax(pd.to_numeric(x, errors="coerce")))
                    fig.add_shape(
                        type="rect", xref="x", yref="y",
                        x0=_x0, x1=_x1, y0=_ymin, y1=0,
                        fillcolor="rgba(255,255,255,0.04)",
                        line_width=0,
                        layer="below",
                    )
    except Exception:
        pass

    try:
        if bool(locals().get("show_be_marker", False)):
            _d = (pd.to_numeric(df.get("Buyer Net Worth"), errors="coerce") - pd.to_numeric(df.get("Renter Net Worth"), errors="coerce")).to_numpy()
            _x = pd.to_numeric(x, errors="coerce").to_numpy() if hasattr(x, "to_numpy") else np.asarray(x, dtype=float)
            _be = None
            if _d.size and _x.size:
                # Find first sign change (including crossing through 0) and linearly interpolate.
                for i in range(1, min(len(_d), len(_x))):
                    a = _d[i-1]; b = _d[i]
                    if not (np.isfinite(a) and np.isfinite(b)):
                        continue
                    if (a == 0) and np.isfinite(_x[i-1]):
                        _be = float(_x[i-1]); break
                    if (a < 0 and b >= 0) or (a > 0 and b <= 0):
                        denom = float(b - a)
                        if denom == 0:
                            _be = float(_x[i]); break
                        t = float(-a) / denom
                        t = 0.0 if t < 0 else (1.0 if t > 1 else t)
                        _be = float(_x[i-1] + t * (_x[i] - _x[i-1]))
                        break
            if _be is not None and np.isfinite(_be):
                fig.add_shape(
                    type="line", xref="x", yref="paper",
                    x0=_be, x1=_be, y0=0, y1=1,
                    line=dict(color="rgba(255,255,255,0.55)", width=1, dash="dot"),
                    layer="above",
                )
                fig.add_annotation(
                    x=_be, y=1.02, yref="paper",
                    text=f"Breakeven ~{_be:.1f}y",
                    showarrow=False,
                    font=dict(size=11, color="rgba(241,241,243,0.86)"),
                    bgcolor="rgba(16,16,18,0.85)",
                    bordercolor="rgba(255,255,255,0.20)",
                    borderwidth=1,
                    xanchor="left",
                    align="left",
                )
    except Exception:
        pass

    # THIN CURSOR (Spikes)
    fig.update_layout(
        template=pio.templates.default,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        hovermode="x unified",
        height=400,
        margin=dict(l=0,r=0,t=10,b=0),
        legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center", font=dict(color="#FFFFFF")),
        font=dict(family="Manrope, Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif", color="rgba(241,241,243,0.92)")
    )
    # Thinner, faint white cursor
    fig.update_xaxes(
        gridcolor="rgba(255,255,255,0.14)",
        showspikes=True,
        spikethickness=0.5,
        spikecolor="rgba(255,255,255,0.25)",
        spikemode="across"
    )
    fig.update_yaxes(tickprefix="$", tickformat=",", gridcolor="rgba(255,255,255,0.14)")
    st.plotly_chart(_rbv_apply_plotly_theme(fig, height=400), use_container_width=True)
    st.caption("Note: Buyer net worth permanently subtracts one-time closing costs (sunk costs), so it can start negative in Month 1.")

    try:
        _rbv_render_compare_preview()
    except Exception:
        pass

    view = st.radio("Time view", ["Yearly", "Monthly"], horizontal=True, label_visibility="collapsed")

    data = (df.groupby('Year').tail(1) if view == "Yearly" else df).copy()

    # Δ columns (direction shown by color; magnitude shown without minus sign)
    # NOTE: Keep the *sign* in the underlying values so color coding works reliably.
    data["Δ"] = pd.to_numeric(data["Buyer Net Worth"], errors="coerce") - pd.to_numeric(data["Renter Net Worth"], errors="coerce")
    data["PV Δ"] = pd.to_numeric(data["Buyer PV NW"], errors="coerce") - pd.to_numeric(data["Renter PV NW"], errors="coerce")

    # Use short column names for a tighter layout
    data = data.rename(columns={
        "Buyer Net Worth": "Buyer NW",
        "Renter Net Worth": "Renter NW",
        "Buyer PV NW": "Buyer PV NW",
        "Renter PV NW": "Renter PV NW",
    })

    cols = ["Buyer NW", "Renter NW", "Δ", "Buyer PV NW", "Renter PV NW", "PV Δ"]

    table_df = data.set_index('Year' if view == "Yearly" else 'Month')[cols]
    st.markdown(
        render_fin_table(table_df, index_name=("Year" if view=="Yearly" else "Month"), table_key="nw_table"),
        unsafe_allow_html=True
    )

    st.markdown("### 🗺️ Breakeven Heatmap")
    with st.container():
        st.caption("Explore where **Buying** or **Renting** wins across a grid of assumptions.")

        hm_axes = st.selectbox(
            "Compare (axes)",
            options=[
                "Home appreciation × Renter investment return",
                "Home appreciation × Rent inflation",
            ],
            index=0,
            key="hm_axes",
        )

        if hm_axes == "Home appreciation × Renter investment return":
            hm_y_axis = "renter_ret"
            hm_y_title = "Renter investment return (%)"
            _rr0 = float(st.session_state.get("renter_ret", 7.0) or 7.0)
            y_lo = max(-5.0, _rr0 - 4.0)
            y_hi = min(20.0, _rr0 + 4.0)
            hm_y_hover = "Renter return"
        else:
            hm_y_axis = "rent_inf"
            hm_y_title = "Rent inflation (%)"
            y_lo, y_hi = 0.0, 6.0
            hm_y_hover = "Rent inflation"

        fast_mode_hm = fast_mode

        hm_metric = st.selectbox(
            "Heatmap metric",
            options=[
                "Expected Δ (deterministic)",
                "PV Δ (deterministic)",
                "Win % (Monte Carlo)",
                "Expected Δ (MC mean)",
                "Expected PV Δ (MC mean)",
            ],
            index=0,
        )

        # Heatmap follows the global two-mode philosophy (no manual N×N / sim tweaking needed).
        is_mc_hm = ("Monte Carlo" in hm_metric) or ("MC mean" in hm_metric)

        grid_size_base = int(st.session_state.get("hm_grid_size", 31 if fast_mode_hm else 51))
        is_det_hm = not is_mc_hm
        is_mcmean_hm = ("MC mean" in str(hm_metric))

        # In Public Mode we bump grid resolution for deterministic metrics aggressively (very fast),
        # and for MC-mean delta metrics moderately (to keep runtime sane).
        FAST_HM_GRID_MCMEAN_MIN_PUBLIC = 41
        QUALITY_HM_GRID_MCMEAN_MIN_PUBLIC = 61

        if is_det_hm:
            det_min = FAST_HM_GRID_DET_MIN_PUBLIC if fast_mode_hm else QUALITY_HM_GRID_DET_MIN_PUBLIC
            grid_size = int(max(grid_size_base, det_min))
            if grid_size != grid_size_base:
                st.caption(f"Heatmap grid: **{grid_size}×{grid_size}** (deterministic smoothness override)")
            else:
                st.caption(f"Heatmap grid (from Performance mode): **{grid_size}×{grid_size}**")
        elif is_mcmean_hm:
            mc_min = FAST_HM_GRID_MCMEAN_MIN_PUBLIC if fast_mode_hm else QUALITY_HM_GRID_MCMEAN_MIN_PUBLIC
            grid_size = int(max(grid_size_base, mc_min))
            if grid_size != grid_size_base:
                st.caption(f"Heatmap grid: **{grid_size}×{grid_size}** (MC mean smoothness override)")
            else:
                st.caption(f"Heatmap grid (from Performance mode): **{grid_size}×{grid_size}**")
        else:
            grid_size = grid_size_base
            st.caption(f"Heatmap grid (from Performance mode): **{grid_size}×{grid_size}**")

        mc_sims = int(st.session_state.get("hm_mc_sims", 15_000 if fast_mode_hm else 30_000)) if is_mc_hm else None
        if is_mc_hm:
            st.caption(f"Heatmap Monte Carlo sims (shared across grid): **{mc_sims:,}**")
            if float(st.session_state.get("ret_std_pct", 0.0) or 0.0) == 0.0 and float(st.session_state.get("apprec_std_pct", 0.0) or 0.0) == 0.0:
                st.caption("Note: Volatility is currently 0%, so the MC heatmap will effectively behave deterministically.")
        # Grid ranges (in %)
        app_vals = np.linspace(-2.0, 8.0, grid_size)
        rent_vals = np.linspace(float(y_lo), float(y_hi), grid_size)

        def _compute_heatmap(
            metric_label: str,
            n: int,
            sims_cell: int | None,
            buyer_ret_pct: float,
            renter_ret_pct: float,
            invest_diff: float,
            rent_closing: bool,
            mkt_corr: float,
            base_rate: float,
            base_rent_inf: float,
            rent_cap_enabled: bool,
            rent_cap_value: float | None,
            progress_cb=None,
        ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
            """Returns (Z, app_vals, rent_vals). Z shape: (len(rent_vals), len(app_vals))."""
            Z = np.full((len(rent_vals), len(app_vals)), np.nan, dtype=float)

            mc_force = ("Monte Carlo" in metric_label) or ("MC mean" in metric_label)

            # Stable base seed for MC heatmap (common random numbers across the entire grid).
            _base_seed_raw = st.session_state.get("mc_seed_effective", st.session_state.get("mc_seed", None))
            try:
                base_seed = int(str(_base_seed_raw).strip())
            except Exception:
                base_seed = None

            def _rent_inf_eff(r: float) -> float:
                if rent_cap_enabled and (rent_cap_value is not None):
                    cap_pct = float(rent_cap_value) * 100.0
                    return min(r, cap_pct)
                return r

            # --- Deterministic heatmap (exact) ---
            if not mc_force:
                # Deterministic heatmaps (Expected Δ / PV Δ) are evaluated exactly via the batched heatmap engine
                # with num_sims=1 and zero volatility. This avoids slow per-cell Python loops and enables higher grids.
                cfg_det = dict(_build_cfg())
                cfg_det["ret_std"] = 0.0
                cfg_det["apprec_std"] = 0.0

                app_vals_eff = np.asarray(app_vals, dtype=float)
                rent_vals_eff = (np.asarray([_rent_inf_eff(float(r)) for r in rent_vals], dtype=float)
                              if hm_y_axis == 'rent_inf' else np.asarray(rent_vals, dtype=float))

                _winZ, dZ, pvZ = run_heatmap_mc_batch(
                    cfg_det,
                    buyer_ret_pct,
                    renter_ret_pct,
                    app_vals_eff,
                    rent_vals_eff,
                    invest_diff,
                    rent_closing,
                    mkt_corr,
                    num_sims=1,
                    mc_seed=base_seed,
                    y_axis=str(hm_y_axis),
                    rate_override_pct=float(base_rate) if base_rate is not None else None,
                    progress_cb=progress_cb,
                    **st.session_state.get('_rbv_extra_engine_kwargs', extra_engine_kwargs),
                )
                if "PV Δ" in metric_label:
                    return pvZ, app_vals, rent_vals
                return dZ, app_vals, rent_vals

            # --- Monte Carlo heatmaps (batched + adaptive refinement for Win %) ---
            cfg_hm = _build_cfg()

            app_vals_eff = np.asarray(app_vals, dtype=float)
            rent_vals_eff = (np.asarray([_rent_inf_eff(float(r)) for r in rent_vals], dtype=float)
                              if hm_y_axis == 'rent_inf' else np.asarray(rent_vals, dtype=float))

            target_sims = int(sims_cell or 0)
            if target_sims <= 0:
                return Z, app_vals, rent_vals

            is_win = ("Win" in metric_label)

            if is_win:
                # Two-pass adaptive sampling:
                # 1) Low-sim coarse pass across full grid
                # 2) Re-run only uncertain cells near the 50% boundary at full sims
                base_sims = int(max(3000, min(6000, target_sims // 5)))
                base_sims = int(min(base_sims, target_sims))

                winZ0, dZ0, pvZ0 = run_heatmap_mc_batch(
                    cfg_hm,
                    float(buyer_ret_pct),
                    float(renter_ret_pct),
                    app_vals_eff,
                    rent_vals_eff,
                    float(invest_diff),
                    bool(rent_closing),
                    float(mkt_corr),
                    num_sims=int(base_sims),
                    mc_seed=base_seed,
                    y_axis=str(hm_y_axis),
                    rate_override_pct=float(base_rate) if base_rate is not None else None,
                    progress_cb=progress_cb,
                    **st.session_state.get('_rbv_extra_engine_kwargs', extra_engine_kwargs),
                )

                winZ = winZ0
                dZ = dZ0
                pvZ = pvZ0

                refined_cells = 0
                if target_sims > base_sims:
                    try:
                        p = np.clip(winZ0 / 100.0, 0.0, 1.0)
                        se = np.sqrt(np.maximum(0.0, p * (1.0 - p)) / float(max(1, base_sims)))
                        ci95 = 1.96 * se * 100.0
                        # Refine only near boundary; threshold grows with estimated uncertainty.
                        margin = np.maximum(2.5, 2.0 * ci95)
                        mask = np.isfinite(winZ0) & (np.abs(winZ0 - 50.0) <= margin)

                        refined_cells = int(np.sum(mask))
                        if refined_cells > 0:
                            winZ1, dZ1, pvZ1 = run_heatmap_mc_batch(
                                cfg_hm,
                                float(buyer_ret_pct),
                                float(renter_ret_pct),
                                app_vals_eff,
                                rent_vals_eff,
                                float(invest_diff),
                                bool(rent_closing),
                                float(mkt_corr),
                                num_sims=int(target_sims),
                                mc_seed=base_seed,
                                y_axis=str(hm_y_axis),
                                rate_override_pct=float(base_rate) if base_rate is not None else None,
                                cell_mask_Z=mask,
                                progress_cb=None,
                                **st.session_state.get('_rbv_extra_engine_kwargs', extra_engine_kwargs),
                            )
                            winZ = np.where(mask, winZ1, winZ0)
                            dZ = np.where(mask, dZ1, dZ0)
                            pvZ = np.where(mask, pvZ1, pvZ0)
                    except Exception:
                        refined_cells = 0

                # Store for Phase 3C diagnostics panel (non-fatal)
                try:
                    st.session_state["_rbv_last_heatmap_adaptive"] = dict(
                        metric=str(metric_label),
                        base_sims=int(base_sims),
                        target_sims=int(target_sims),
                        refined_cells=int(refined_cells),
                        total_cells=int(winZ0.size),
                    )
                except Exception:
                    pass

                return winZ, app_vals, rent_vals

            # MC mean metrics (single-pass at full sims)
            winZ, dZ, pvZ = run_heatmap_mc_batch(
                cfg_hm,
                float(buyer_ret_pct),
                float(renter_ret_pct),
                app_vals_eff,
                rent_vals_eff,
                float(invest_diff),
                bool(rent_closing),
                float(mkt_corr),
                num_sims=int(target_sims),
                mc_seed=base_seed,
                    y_axis=str(hm_y_axis),
                rate_override_pct=float(base_rate) if base_rate is not None else None,
                progress_cb=progress_cb,
                **st.session_state.get('_rbv_extra_engine_kwargs', extra_engine_kwargs),
            )

            if "Expected PV" in metric_label:
                return pvZ, app_vals, rent_vals
            return dZ, app_vals, rent_vals
        rent_cap_enabled_local = bool(rent_control_enabled)
        rent_cap_value_local = rent_control_cap

        if "_heatmap_cache" not in st.session_state:
            st.session_state["_heatmap_cache"] = {}

        # Heatmap cache signature: include core model inputs so the grid never goes stale when users change assumptions.
        def _heatmap_inputs_sig() -> str:
            sig_keys = [
                "price", "rent", "years", "amort", "down", "close", "mort",
                "p_tax_rate", "maint_rate", "repair_rate", "condo", "h_ins", "o_util", "r_ins", "r_util",
                "sell_cost", "moving_cost", "moving_freq",
                "general_inf", "pv_rate", "ret_std", "apprec_std",
                "rate_mode", "rate_reset_years", "rate_reset_to", "rate_reset_step_pp",
                "rate_shock_enabled", "rate_shock_start_year", "rate_shock_duration_years", "rate_shock_pp",
                "canadian_compounding", "assume_sale_end", "cg_tax_end", "tax_r", "home_sale_legal_fee",
                "expert_mode",
                "province", "first_time", "toronto", "transfer_tax_override",
                "insured", "ltv",
                "condo_inf_mode", "condo_inf_spread", "condo_inf_custom",
                "special_assessment_amount", "special_assessment_year", "special_assessment_month_in_year",
                "cg_inclusion_policy", "cg_inclusion_threshold",
                "reg_shelter_enabled", "reg_initial_room", "reg_annual_room",
            ]
            g = globals()
            d = {k: g.get(k) for k in sig_keys if k in g}
            d["extra_engine_kwargs"] = extra_engine_kwargs

            def _clean(x):
                if isinstance(x, (str, int, float, bool)) or x is None:
                    return x
                if isinstance(x, (list, tuple)):
                    return [_clean(v) for v in x]
                if isinstance(x, dict):
                    return {str(kk): _clean(vv) for kk, vv in x.items()}
                return str(x)

            s = json.dumps(_clean(d), sort_keys=True, separators=(",", ":"))
            return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

        hm_sig = _heatmap_inputs_sig()

        # Heatmap seed (CRN + cache correctness)
        _hm_seed_raw = st.session_state.get("mc_seed_effective", st.session_state.get("mc_seed", None))
        try:
            hm_seed = int(str(_hm_seed_raw).strip())
        except Exception:
            hm_seed = None


        hm_key = (
            hm_metric, str(hm_y_axis), int(grid_size),
            int(mc_sims) if (mc_sims is not None and int(mc_sims) > 0) else None,
            int(hm_seed) if (hm_seed is not None) else None,
            float(st.session_state.buyer_ret), float(st.session_state.renter_ret),
            float(invest_surplus_input), bool(renter_uses_closing_input),
            float(market_corr_input), float(rate), float(rent_inf),
            bool(rent_cap_enabled_local),
            float(rent_cap_value_local) if rent_cap_value_local is not None else None,
            str(hm_sig),
        )

        cached = st.session_state["_heatmap_cache"].get(hm_key)
        if cached is not None:
            Z, _app, _rent = cached
            try:
                st.session_state["_rbv_hm_pause_active"] = False
            except Exception:
                pass
        else:
            hm_skipped = False

            # If the user stopped a long heatmap run, avoid immediately re-triggering it on the cancel rerun.
            try:
                _freeze = st.session_state.get("_rbv_cancel_freeze", None)
                if isinstance(_freeze, dict) and str(_freeze.get("kind")) == "heatmap":
                    if str(_freeze.get("sig")) == str(hm_key):
                        st.session_state["_rbv_heatmap_autorun"] = False
                    else:
                        # Inputs changed; thaw heatmap auto-run.
                        st.session_state["_rbv_cancel_freeze"] = None
                        st.session_state["_rbv_heatmap_autorun"] = True
            except Exception:
                pass

            if not bool(st.session_state.get("_rbv_heatmap_autorun", True)):
                hm_skipped = True
                try:
                    st.session_state["_rbv_hm_pause_active"] = True
                except Exception:
                    pass

                st.info("Heatmap computation is paused (it was stopped). Click **Compute heatmap** to run it again.")
                try:
                    _hm_resume = st.button("Compute heatmap", key="rbv_hm_resume", type="primary")
                except TypeError:
                    _hm_resume = st.button("Compute heatmap", key="rbv_hm_resume")
                if _hm_resume:
                    st.session_state["_rbv_heatmap_autorun"] = True
                    st.session_state["_rbv_cancel_freeze"] = None
                    st.experimental_rerun()

                Z = np.full((len(rent_vals), len(app_vals)), np.nan)
                _app, _rent = app_vals, rent_vals
                try:
                    _rbv_global_progress_clear()
                except Exception:
                    pass
                _t1_longrun_bar.empty()
                _t1_longrun_status.empty()
            else:
                try:
                    st.session_state["_rbv_hm_pause_active"] = False
                except Exception:
                    pass

                # Mark this as an active long run so a Stop can deterministically freeze re-compute.
                try:
                    st.session_state["_rbv_active_longrun"] = {"kind": "heatmap", "sig": str(hm_key)}
                except Exception:
                    pass

                total_cells = len(rent_vals) * len(app_vals)
                _t1_longrun_status.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
                status = _t1_longrun_status
                t0 = time.time()
                _eta0 = None
                try:
                    _avg = float(st.session_state.get("_rbv_hm_avg_sec_per_cell", 0.0))
                    if _avg > 0:
                        _eta0 = _avg * float(total_cells)
                except Exception:
                    _eta0 = None


                hm_mode_label = "Fast" if bool(fast_mode) else "Quality"
                try:
                    hm_overlay_label = f"Heatmap ({hm_mode_label}, {int(grid_size)}×{int(grid_size)})"
                except Exception:
                    hm_overlay_label = f"Heatmap ({hm_mode_label})"

                try:
                    _rbv_global_progress_show(0, hm_overlay_label, eta_sec=_eta0)
                except Exception:
                    pass

                # Limit UI updates (keeps compute fast)
                step_box = [None]

                def _cb(done: int, total: int):
                    if step_box[0] is None:
                        step_box[0] = max(1, int(max(total, 1)) // 100)
                    step = step_box[0]
                    if (done % step == 0) or (done == total):
                        pct = int(done * 100 / total)
                        remaining = total - done
                        elapsed = max(1e-6, time.time() - t0)
                        rate_cps = done / elapsed  # cells per second
                        eta_sec = remaining / max(1e-6, rate_cps)
                        if eta_sec >= 3600:
                            h = int(eta_sec // 3600)
                            m = int((eta_sec % 3600) // 60)
                            s = int(eta_sec % 60)
                            eta_str = f"{h:d}:{m:02d}:{s:02d}"
                        else:
                            m = int(eta_sec // 60)
                            s = int(eta_sec % 60)
                            eta_str = f"{m:d}:{s:02d}"
                        status.markdown(
                            f"<div style='color:#9A9A9A; font-size:12px; text-align:center; width:100%;'>"
                            f"Cell {done:,} / {total:,} • Remaining: {remaining:,} • ETA: {eta_str}"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                        # Global overlay (visible even when scrolled)
                        try:
                            _rbv_global_progress_show(pct, hm_overlay_label, eta_sec=eta_sec)
                            if done >= total:
                                _rbv_global_progress_clear()
                        except Exception:
                            pass

                try:
                    Z, _app, _rent = _compute_heatmap(
                        hm_metric, grid_size, mc_sims,
                        st.session_state.buyer_ret, st.session_state.renter_ret, invest_surplus_input, renter_uses_closing_input,
                        market_corr_input, rate, rent_inf,
                        rent_cap_enabled_local, rent_cap_value_local,
                        progress_cb=_cb
                    )
                finally:
                    try:
                        _rbv_global_progress_clear()
                    except Exception:
                        pass

            # Update heatmap speed estimate for next ETA seed
            try:
                _elapsed = max(1e-6, time.time() - t0)
                _sec_per_cell = _elapsed / max(1, int(total_cells))
                _prev = float(st.session_state.get("_rbv_hm_avg_sec_per_cell", 0.0))
                st.session_state["_rbv_hm_avg_sec_per_cell"] = (0.7 * _prev + 0.3 * _sec_per_cell) if _prev > 0 else _sec_per_cell
            except Exception:
                pass

            # Store heatmap result in a small per-session LRU to prevent session bloat
            try:
                st.session_state["_heatmap_cache"][hm_key] = (Z, _app, _rent)
                order = st.session_state.get("_heatmap_cache_order", [])
                order.append(hm_key)
                MAX_KEEP = 6
                if len(order) > MAX_KEEP:
                    drop = order[:-MAX_KEEP]
                    st.session_state["_heatmap_cache_order"] = order[-MAX_KEEP:]
                    for k in drop:
                        st.session_state["_heatmap_cache"].pop(k, None)
                else:
                    st.session_state["_heatmap_cache_order"] = order
            except Exception:
                st.session_state["_heatmap_cache"][hm_key] = (Z, _app, _rent)
            _t1_longrun_bar.empty()
            _t1_longrun_status.empty()

            # Completed normally -> clear active long-run marker.
            try:
                st.session_state["_rbv_active_longrun"] = None
            except Exception:
                pass

        # --- Phase 3C: Heatmap diagnostics (non-fatal sanity checks) ---
        try:
            if bool(st.session_state.get("_rbv_hm_pause_active", False)):
                raise RuntimeError("Heatmap paused")
            st.session_state["_rbv_last_heatmap"] = {
                "metric": str(hm_metric),
                "Z": Z,
                "app": _app,
                "rent": _rent,
            }

            # Adaptive heatmap refinement info (Phase 4): surfaced in diagnostics for transparency
            try:
                _hm_ad = st.session_state.get("_rbv_last_heatmap_adaptive")
                if isinstance(_hm_ad, dict) and ("Win" in str(_hm_ad.get("metric", ""))):
                    _rbv_diag_add(
                        "OK",
                        "Adaptive heatmap refinement",
                        f"Base {_hm_ad.get('base_sims'):,} sims; refined {_hm_ad.get('refined_cells'):,}/{_hm_ad.get('total_cells'):,} cells at {_hm_ad.get('target_sims'):,} sims",
                    )
            except Exception:
                pass

            valid = np.isfinite(Z)
            if not bool(valid.any()):
                _rbv_diag_add("FAIL", "Heatmap produced no finite cells", str(hm_metric))
            else:
                frac_bad = 1.0 - (float(np.count_nonzero(valid)) / float(Z.size))
                if frac_bad > 0.0:
                    _rbv_diag_add("WARN", "Heatmap contains NaN/Inf cells", f"{frac_bad*100.0:.1f}% invalid")
                else:
                    _rbv_diag_add("OK", "Heatmap finite cells", "100% valid")

                # Win% bounds check
                if "Win %" in str(hm_metric):
                    vv = Z[valid]
                    n_oob = int(np.count_nonzero((vv < 0.0) | (vv > 100.0)))
                    if n_oob:
                        _rbv_diag_add("FAIL", "Heatmap Win% out of bounds", f"{n_oob} cells outside 0..100")
                    else:
                        _rbv_diag_add("OK", "Heatmap Win% in bounds")

                # Diagonal monotonicity sanity: as both appreciation and rent inflation rise together,
                # the buyer advantage should generally increase (small MC noise tolerated).
                if Z.shape[0] == Z.shape[1]:
                    d = np.diag(Z)
                    if np.isfinite(d).all() and (len(d) >= 3):
                        eps = 2.5 if ("Monte Carlo" in str(hm_metric) or "MC" in str(hm_metric) or "Win %" in str(hm_metric)) else 1e-6
                        dv = np.diff(d)
                        n_viol = int(np.count_nonzero(dv < -float(eps)))
                        if n_viol == 0:
                            _rbv_diag_add("OK", "Heatmap diagonal monotonicity", "No decreases detected")
                        else:
                            _rbv_diag_add("WARN", "Heatmap diagonal monotonicity", f"{n_viol} decreases (tolerance={eps})")
        except Exception:
            pass
        # Colors (fixed Fintech theme)
        low_c, mid_c, high_c = RENT_COLOR, SURFACE_CARD, BUY_COLOR
        # rent -> neutral -> buy

        # Colorbar labeling: be explicit about what Z represents.
        if "Win %" in str(hm_metric):
            cb_title = "Buying win probability (%)"
            cb_tickprefix = ""
            cb_tickformat = ".0f"
            hover_value_fmt = "%{z:.0f}%"
        else:
            _m = str(hm_metric)
            if "PV" in _m:
                cb_title = "PV Δ Net Worth (Buyer − Renter)"
            else:
                cb_title = "Δ Net Worth (Buyer − Renter)"
            if "Expected" in _m:
                cb_title = "Expected " + cb_title
            cb_tickprefix = "$"
            cb_tickformat = ","
            hover_value_fmt = "$%{z:,.0f}"

        if "Win %" in hm_metric:
            hm_zmin = 0.0
            hm_zmax = 100.0
            hm_zmid = 50.0
        else:
            # For $ deltas, anchor the neutral color at 0 so the breakeven contour visually matches the midpoint.
            hm_zmid = 0.0
            try:
                _finite = Z[np.isfinite(Z)]
                if _finite.size:
                    _zabs = float(np.nanmax(np.abs(_finite)))
                    if not np.isfinite(_zabs) or _zabs <= 0:
                        _zabs = 1.0
                    hm_zmin = -_zabs
                    hm_zmax = _zabs
                else:
                    hm_zmin = None
                    hm_zmax = None
            except Exception:
                hm_zmin = None
                hm_zmax = None


        # Visual smoothing: MC heatmaps benefit from interpolation for readability.
        # This does NOT change the computed grid values—only how Plotly renders between cells.
        hm_zsmooth = "best" if (("Monte Carlo" in hm_metric) or ("MC mean" in hm_metric)) else False

        fig_hm = go.Figure()

        fig_hm.add_trace(go.Heatmap(
            z=Z,
            x=_app,
            y=_rent,
            colorscale=[[0, low_c], [0.5, mid_c], [1, high_c]],
            zsmooth=hm_zsmooth,
            zmin=hm_zmin,
            zmax=hm_zmax,
            zmid=hm_zmid,
            colorbar=dict(
                title=dict(text=cb_title, font=dict(color="#94a3b8")),
                tickprefix=cb_tickprefix,
                tickformat=cb_tickformat,
                tickfont=dict(color="#94a3b8"),
                outlinewidth=0
            ),
            hovertemplate="Apprec: %{x:.2f}%<br>" + hm_y_hover + ": %{y:.2f}%<br>Value: " + hover_value_fmt + "<extra></extra>"
        ))

        # Breakeven contour (line only) for currency deltas
        if "Win %" not in hm_metric:
            fig_hm.add_trace(go.Contour(
                z=Z,
                x=_app,
                y=_rent,
                contours=dict(start=0, end=0, size=1, coloring="none"),
                line=dict(color="rgba(255,255,255,0.85)", width=2, dash="dot"),
                showscale=False,
                hoverinfo="skip"
            ))

            # Label near closest-to-zero point
            try:
                valid = np.isfinite(Z)
                if valid.any():
                    idx = np.unravel_index(np.nanargmin(np.abs(np.where(valid, Z, np.nan))), Z.shape)
                    y0 = float(_rent[idx[0]])
                    x0 = float(_app[idx[1]])
                    fig_hm.add_annotation(
                        x=x0, y=y0,
                        text="Breakeven",
                        showarrow=True,
                        arrowhead=2,
                        ax=30, ay=-30,
                        bgcolor="rgba(16,16,18,0.90)",
                        bordercolor="rgba(255,255,255,0.35)",
                        borderwidth=1,
                        font=dict(color="#E2E8F0", size=12)
                    )
            except Exception:
                pass


        else:
            # Win% breakeven (50%) contour line for Monte Carlo win-rate views
            try:
                fig_hm.add_trace(go.Contour(
                    z=Z,
                    x=_app,
                    y=_rent,
                    contours=dict(start=50, end=50, size=1, coloring="none"),
                    line=dict(color="rgba(255,255,255,0.75)", width=2, dash="dot"),
                    showscale=False,
                    hoverinfo="skip",
                    name="Win% breakeven"
                ))
            except Exception:
                pass


        # Base-case marker (current inputs) to orient the user on the grid
        try:
            _base_x = float(st.session_state.get("apprec", locals().get("apprec", 0.0)) or locals().get("apprec", 0.0))
            if str(hm_y_axis) == "renter_ret":
                _base_y = float(st.session_state.get("renter_ret", 7.0) or 7.0)
                _base_y_lbl = "Renter return"
            else:
                _base_y = float(st.session_state.get("rent_inf", 3.0) or 3.0)
                _base_y_lbl = "Rent inflation"
            fig_hm.add_trace(go.Scatter(
                x=[_base_x],
                y=[_base_y],
                mode="markers",
                marker=dict(size=10, symbol="x", color="rgba(255,255,255,0.95)"),
                hovertemplate=f"Base case<br>Apprec: {_base_x:.2f}%<br>{_base_y_lbl}: {_base_y:.2f}%<extra></extra>",
                showlegend=False,
            ))
        except Exception:
            pass

        fig_hm.update_layout(
            template=pio.templates.default,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=40, r=20, t=20, b=40),
            font=dict(color="#E2E8F0", family="Manrope, Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif"),
        )

        fig_hm.update_xaxes(title="Home Appreciation (%)", showgrid=False, zeroline=False, mirror=True, ticks="outside")
        fig_hm.update_yaxes(title=hm_y_title, showgrid=False, zeroline=False, mirror=True, ticks="outside")

        st.plotly_chart(_rbv_apply_plotly_theme(fig_hm), use_container_width=True)

        _hm_be_caption = "Breakeven line (dotted) = Win% 50%" if ("Win %" in str(hm_metric)) else "Breakeven line (dotted) = Δ = 0"

        st.markdown(
            f"""<div style="display:flex; gap:18px; align-items:center; margin-top:8px; flex-wrap:wrap;">
                <div style="display:flex; gap:8px; align-items:center;">
                    <span style="width:10px; height:10px; border-radius:3px; background:{high_c}; display:inline-block;"></span>
                    <span style="color:#E2E8F0;">Buying wins</span>
                </div>
                <div style="display:flex; gap:8px; align-items:center;">
                    <span style="width:10px; height:10px; border-radius:3px; background:{low_c}; display:inline-block;"></span>
                    <span style="color:#E2E8F0;">Renting wins</span>
                </div>
                <div style="color:#9A9A9A;">{_hm_be_caption}</div>
            </div>""",
            unsafe_allow_html=True
        )

        st.caption("Tip: Higher grid resolution and Monte Carlo modes can be slower. Results are cached per setting.")

elif tab == _TAB_COSTS:
    st.markdown(
        '<div class=\"note-box\"><b>About these costs:</b> This tab summarizes <b>ongoing non-principal housing costs</b> '
        '(interest, taxes, condo/maintenance, insurance, utilities, rent, etc.). '
        'Some of these costs help maintain the asset (e.g., maintenance) and are partly “offset” by appreciation in the net worth view. '
        'Principal paydown is <b>not</b> shown as a cost because it becomes equity. '
        '<br><b>Note:</b> Buyer total includes upfront closing costs + selling costs at horizon (realtor + legal). Renter total includes all moving costs.</div>',
        unsafe_allow_html=True,
    )
    diff_uc = df.iloc[-1]['Buyer Unrecoverable'] - df.iloc[-1]['Renter Unrecoverable']
    st.markdown(f'<div class="unrec-box"><div style="font-weight:700; color:#9A9A9A;">ONGOING HOUSING COSTS SUMMARY</div>'
                f'<div style="font-size:14px; margin:10px 0;">Buyer Lost: <b>${df.iloc[-1]["Buyer Unrecoverable"]:,.0f}</b> vs Renter Lost: <b>${df.iloc[-1]["Renter Unrecoverable"]:,.0f}</b></div>'
                f'<div style="font-weight:700; font-size:16px; color:#F8FAFC;">The <b>{"Buyer" if diff_uc > 0 else "Renter"}</b> lost <b>${abs(diff_uc):,.0f}</b> more.</div></div>', unsafe_allow_html=True)

    # --- Clarification: opportunity cost (down payment) + principal paydown ---
    try:
        upfront_rent_capital = float(down + (close_cash - down) if renter_uses_closing_input else down)
    except Exception:
        upfront_rent_capital = None

    st.markdown(
        f"""<div class="note-box">
<b>Opportunity cost of the down payment (and optional closing costs)</b><br>
If you rent, the model invests your down payment{"+ closing costs" if renter_uses_closing_input else ""} (<span class="accent-rent">{_fmt_money(upfront_rent_capital) if upfront_rent_capital is not None else "—"}</span>)
in your portfolio instead of locking it into home equity. This capital opportunity cost is often a major driver of outcomes, but it is <b>not</b> a cash “unrecoverable cost”, so it won’t appear inside the unrecoverable totals above.<br><br>
<b>Note on principal:</b> mortgage <b>principal paydown</b> is treated as equity (savings), not a cost, and is included in Buyer Net Worth.
</div>""",
        unsafe_allow_html=True,
    )

    # --- Total cost breakdown (Buyer vs Renter, simplified categories) ---
    st.markdown("##### Total Ongoing Costs (Buyer vs Renter)")

    # We show a small set of aligned categories (two bars per category) so it's easy to compare.
    # This avoids the unreadable stacked legend when many categories exist.
    def _safe_sum(col: str) -> float:
        return float(df[col].sum()) if col in df.columns else 0.0

    buyer_interest = _safe_sum("Interest")
    buyer_tax = _safe_sum("Property Tax")
    buyer_maint_condo = _safe_sum("Maintenance") + _safe_sum("Repairs") + _safe_sum("Condo Fees")
    buyer_insurance = _safe_sum("Home Insurance")
    buyer_utilities = _safe_sum("Utilities")
    buyer_special = _safe_sum("Special Assessment")
    buyer_moving = 0.0  # Moving is modeled for renters (frequency-based), not buyers

    renter_rent = _safe_sum("Rent")
    renter_insurance = _safe_sum("Rent Insurance")
    renter_utilities = _safe_sum("Rent Utilities")
    renter_moving = _safe_sum("Moving")

    # Closing + selling costs are included in Buyer Unrecoverable but not in the monthly columns above
    try:
        buyer_close_sell = max(0.0, float(df.iloc[-1]["Buyer Unrecoverable"]) - (
            buyer_interest + buyer_tax + buyer_maint_condo + buyer_insurance + buyer_utilities + buyer_special + buyer_moving
        ))
    except Exception:
        buyer_close_sell = 0.0

    categories = [
        "Housing payment (Interest / Rent)",
        "Property tax",
        "Maintenance & condo",
        "Insurance",
        "Utilities",
        "Special assessment",
        "Transaction costs",
        "Moving",
    ]

    buyer_vals = [
        buyer_interest,
        buyer_tax,
        buyer_maint_condo,
        buyer_insurance,
        buyer_utilities,
        buyer_special,
        buyer_close_sell,
        buyer_moving,
    ]
    renter_vals = [
        renter_rent,
        0.0,
        0.0,
        renter_insurance,
        renter_utilities,
        0.0,
        0.0,
        renter_moving,
    ]

    # Plot as horizontal grouped bars for readability.
    fig_uc_bar = go.Figure()
    fig_uc_bar.add_trace(go.Bar(
        name="Buyer",
        y=categories,
        x=buyer_vals,
        orientation="h",
        marker=dict(color=BUY_COLOR),
        hovertemplate="%{y}<br>Buyer: $%{x:,.0f}<extra></extra>",
    ))
    fig_uc_bar.add_trace(go.Bar(
        name="Renter",
        y=categories,
        x=renter_vals,
        orientation="h",
        marker=dict(color=RENT_COLOR),
        hovertemplate="%{y}<br>Renter: $%{x:,.0f}<extra></extra>",
    ))

    fig_uc_bar.update_layout(
        template=pio.templates.default,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        barmode="group",
        height=420,
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center", font=dict(color="#FFFFFF")),
        font=dict(family="Manrope, Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif", color="rgba(241,241,243,0.92)"),
    )
    fig_uc_bar.update_xaxes(tickprefix="$", tickformat=",", gridcolor="rgba(255,255,255,0.14)")
    fig_uc_bar.update_yaxes(gridcolor="rgba(255,255,255,0.14)", autorange="reversed")
    st.plotly_chart(_rbv_apply_plotly_theme(fig_uc_bar), use_container_width=True)

    st.caption("Categories are aligned across Buyer/Renter; zeros indicate costs that don’t apply to that side.")

    # --- Monthly unrecoverable series (buyer vs renter) ---
    st.markdown("##### Monthly Unrecoverable Cost Over Time")
    st.caption("Toggle renter series between smooth recurring costs and spiky totals that include moving months.")

    rent_series_mode = st.radio(
        "Renter series mode",
        ["Recurring only (smooth)", "Total incl. moving (spiky)"],
        horizontal=True,
        key="rent_series_mode",
        label_visibility="collapsed",
    )

    try:
        if "Month" in df.columns:
            x_m = (df["Month"].astype(float) - 1.0) / 12.0 + 1.0
        elif "Year" in df.columns:
            x_m = df["Year"].astype(float)
        else:
            x_m = list(range(1, len(df) + 1))
    except Exception:
        x_m = list(range(1, len(df) + 1))

    b_mo_unrec = (
        (df["Interest"] if "Interest" in df.columns else 0.0)
        + (df["Property Tax"] if "Property Tax" in df.columns else 0.0)
        + (df["Maintenance"] if "Maintenance" in df.columns else 0.0)
        + (df["Repairs"] if "Repairs" in df.columns else 0.0)
        + (df["Condo Fees"] if "Condo Fees" in df.columns else 0.0)
        + (df["Home Insurance"] if "Home Insurance" in df.columns else 0.0)
        + (df["Utilities"] if "Utilities" in df.columns else 0.0)
        + (df["Special Assessment"] if "Special Assessment" in df.columns else 0.0)
    )

    if str(rent_series_mode).startswith("Total"):
        r_mo_unrec = df["Rent Payment"] if "Rent Payment" in df.columns else 0.0
    else:
        r_mo_unrec = df["Rent Cost (Recurring)"] if "Rent Cost (Recurring)" in df.columns else (df["Rent"] if "Rent" in df.columns else 0.0)

    fig_mo_uc = go.Figure()
    fig_mo_uc.add_trace(go.Scatter(x=x_m, y=b_mo_unrec, name="Buyer", mode='lines', line=dict(color=BUY_COLOR, width=2)))
    fig_mo_uc.add_trace(go.Scatter(x=x_m, y=r_mo_unrec, name="Renter", mode='lines', line=dict(color=RENT_COLOR, width=2)))

    fig_mo_uc.update_layout(
        template=pio.templates.default,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=330,
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center", font=dict(color="#FFFFFF")),
        font=dict(family="Manrope, Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif", color="rgba(241,241,243,0.92)"),
        hovermode="x unified",
    )
    fig_mo_uc.update_yaxes(tickprefix="$", tickformat=",", gridcolor="rgba(255,255,255,0.14)")
    fig_mo_uc.update_xaxes(gridcolor="rgba(255,255,255,0.14)")
    st.plotly_chart(_rbv_apply_plotly_theme(fig_mo_uc), use_container_width=True)


    with st.expander("Cumulative costs over time", expanded=False):
        fig_uc = go.Figure()
        # X-axis for cumulative plots: prefer continuous years to avoid repeated Year values.
        try:
            if "Month" in df.columns:
                x = (df["Month"].astype(float) - 1.0) / 12.0 + 1.0
            elif "Year" in df.columns:
                x = df["Year"]
            else:
                x = list(range(1, len(df) + 1))
        except Exception:
            x = list(range(1, len(df) + 1))

        fig_uc.add_trace(go.Scatter(x=x, y=df['Buyer Unrecoverable'], name="Buyer", mode='lines', line=dict(color=BUY_COLOR, width=2)))
        fig_uc.add_trace(go.Scatter(x=x, y=df['Renter Unrecoverable'], name="Renter", mode='lines', line=dict(color=RENT_COLOR, width=2)))

        fig_uc.update_layout(
            template=pio.templates.default,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=350,
            margin=dict(l=0,r=0,t=10,b=0),
            legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center", font=dict(color="#FFFFFF")),
            font=dict(family="Manrope, Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif", color="rgba(241,241,243,0.92)")
        )
        fig_uc.update_yaxes(tickprefix="$", tickformat=",", gridcolor="rgba(255,255,255,0.14)")
        fig_uc.update_xaxes(gridcolor="rgba(255,255,255,0.14)")
        st.plotly_chart(_rbv_apply_plotly_theme(fig_uc), use_container_width=True)

    st.markdown("##### Average Monthly Irrecoverable Costs (cost of living)")
    st.caption(
        "These are the monthly costs you pay to live in the property that do **not** build equity (interest, taxes, upkeep, insurance, utilities). "
        "Principal repayment is excluded here because it increases home equity."
    )
    df_avg = df[df['Month'] > 0]
    b_table = pd.DataFrame({
        "Category": ["Interest", "Property Tax", "Maintenance", "Repairs", "Condo Fees", "Special Assessment", "Insurance", "Utilities"],
        "Amount": [
            df_avg['Interest'].mean(),
            df_avg['Property Tax'].mean(),
            df_avg['Maintenance'].mean(),
            df_avg['Repairs'].mean(),
            df_avg['Condo Fees'].mean(),
            (df_avg['Special Assessment'].mean() if 'Special Assessment' in df_avg.columns else 0.0),
            df_avg['Home Insurance'].mean(),
            df_avg['Utilities'].mean(),
        ]
    }).set_index("Category")
    b_table = b_table[b_table['Amount'] > 0]
    b_table.loc['TOTAL'] = b_table['Amount'].sum()

    r_table = pd.DataFrame({
        "Category": ["Rent", "Insurance", "Rent Utilities", "Moving"],
        "Amount": [df_avg['Rent'].mean(), df_avg['Rent Insurance'].mean(), df_avg['Rent Utilities'].mean(), df_avg['Moving'].mean()]
    }).set_index("Category")
    r_table = r_table[r_table['Amount'] > 0]
    r_table.loc['TOTAL'] = r_table['Amount'].sum()

    c_tbl1, c_tbl2 = st.columns(2)
    with c_tbl1:
        st.markdown('<div class="header-buy section-header">BUYER AVG</div>', unsafe_allow_html=True)
        st.markdown(render_fin_table(b_table, index_name="Category", table_key="buyer_avg"), unsafe_allow_html=True)
    with c_tbl2:
        st.markdown('<div class="header-rent section-header">RENTER AVG</div>', unsafe_allow_html=True)
        st.markdown(render_fin_table(r_table, index_name="Category", table_key="renter_avg"), unsafe_allow_html=True)

    # Bridge the "Outflow" KPI vs irrecoverable costs: principal paydown is the main difference.
    try:
        avg_b_out = float(_df_mean(df_avg, ["Buy Payment"], 0.0))
        avg_b_irrec = float(b_table.loc['TOTAL', 'Amount'])
        avg_principal = max(0.0, avg_b_out - avg_b_irrec)
        if avg_principal > 0:
            st.markdown(
                f"<div style='text-align:center; font-size:13px; opacity:0.82; margin-top:6px;'>"
                f"Avg buyer <b>principal paydown</b> (equity build): <span style='color:{BUY_COLOR}; font-weight:700;'>${avg_principal:,.0f}/mo</span>. "
                f"Outflow = irrecoverable costs + principal.</div>",
                unsafe_allow_html=True,
            )
    except Exception:
        pass

    monthly_diff = b_table.loc['TOTAL', 'Amount'] - r_table.loc['TOTAL', 'Amount']
    note_color = BUY_COLOR if monthly_diff > 0 else RENT_COLOR
    note_text = "pays more" if monthly_diff > 0 else "saves"
    st.markdown(f"<div style='text-align:center; font-size:14px; color:{note_color};'>Buyer {note_text} <b>${abs(monthly_diff):,.0f} / month</b> in pure costs.</div>", unsafe_allow_html=True)

    uc_view = st.radio("View Period", ["Yearly", "Monthly"], horizontal=True, key="uc_view", label_visibility="collapsed")

    # Display labels vs underlying simulation column names
    buyer_map = {
        "Interest": "Interest",
        "Property Tax": "Property Tax",
        "Maintenance": "Maintenance",
        "Repairs": "Repairs",
        "Special Assessment": "Special Assessment",
        "Condo Fees": "Condo Fees",
        "Insurance": "Home Insurance",
        "Utilities": "Utilities",
    }
    renter_map = {
        "Rent": "Rent",
        "Insurance": "Rent Insurance",
        "Utilities": "Rent Utilities",
        "Moving": "Moving",
    }

    active_b = [label for label, src in buyer_map.items() if src in df.columns and df[src].sum() > 0]
    active_r = [label for label, src in renter_map.items() if src in df.columns and df[src].sum() > 0]

    if uc_view == "Yearly":
        uc_b = df.groupby("Year")[[buyer_map[l] for l in active_b]].sum().rename(columns={buyer_map[l]: l for l in active_b})
        uc_r = df.groupby("Year")[[renter_map[l] for l in active_r]].sum().rename(columns={renter_map[l]: l for l in active_r})
    else:
        uc_b = df[["Month"] + [buyer_map[l] for l in active_b]].set_index("Month").rename(columns={buyer_map[l]: l for l in active_b})
        uc_r = df[["Month"] + [renter_map[l] for l in active_r]].set_index("Month").rename(columns={renter_map[l]: l for l in active_r})

    uc_b["TOTAL"] = uc_b.sum(axis=1)
    uc_r["TOTAL"] = uc_r.sum(axis=1)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="header-buy section-header">BUYER UNRECOVERABLE</div>', unsafe_allow_html=True)
        st.markdown(render_fin_table(uc_b, index_name=("Year" if uc_view=="Yearly" else "Month"), table_key="buyer_unrec"), unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="header-rent section-header">RENTER UNRECOVERABLE</div>', unsafe_allow_html=True)
        st.markdown(render_fin_table(uc_r, index_name=("Year" if uc_view=="Yearly" else "Month"), table_key="renter_unrec"), unsafe_allow_html=True)

elif tab == _TAB_ASSUM:

    st.markdown('<div class="assumptions-wrap">', unsafe_allow_html=True)
    # Consistent, scannable assumptions + notes (avoid mixed badges/headings).
    with st.expander("📝 Model assumptions & notes", expanded=True):
        st.markdown(
            """<div class="note-box"><b>Educational use only</b><br>
            This simulator is for education and scenario-planning only (not financial, tax, or legal advice). Results are highly sensitive to inputs.</div>
            <div class="note-box"><b>What is being compared</b><br>
            We compare <b>economic net worth</b> over the horizon: the buyer's home equity + any invested surplus vs. the renter's invested portfolio. Principal paydown is treated as wealth transfer (not a cost).</div>
            <div class="note-box"><b>Opportunity cost & bidirectional surplus investing</b><br>
            The renter starts with the down payment invested (and optionally closing costs). Each month, whichever path is cheaper invests the surplus; if buying is cheaper than renting, the buyer invests the surplus too.</div>
            <div class="note-box"><b>Separate inflation channels</b><br>
            Home appreciation, rent inflation, and general CPI are modeled separately. Property taxes/maintenance scale with home value, while some operating costs scale with CPI. Condo/strata fees can use their own inflation rate.</div>
            <div class="note-box"><b>Exit scenarios & liquidation</b><br>
            Optional selling costs (realtor + legal) reduce final home equity if you assume a sale at the end. You can also view a liquidation-style comparison where portfolio capital gains taxes are applied at the end (useful for taxable accounts).</div>
            <div class="note-box"><b>Risk, uncertainty & correlation</b><br>
            Volatility mode runs Monte Carlo paths for both housing and equities, optionally correlated (ρ). This widens outcome ranges and helps stress test “what if both drop together?” scenarios.</div>""",
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""<div class="note-box"><b>Rate compounding convention</b><br>
            Annual rates you enter (returns, inflation, home appreciation) are treated as <i>annual effective</i> rates and converted to monthly compounding internally:
            <code>(1 + r)^(1/12) - 1</code> (equivalently the Monte Carlo engine uses monthly log drift <code>ln(1+r)/12</code>).</div>""",
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""<div class="note-box"><b>Tax schedule date</b><br>
            Transfer-tax schedules are evaluated as of <code>{_tax_asof.isoformat()}</code>. You can change this in the sidebar (<i>Tax rules as of</i>) to control date-dependent rules (e.g., Toronto MLTT luxury brackets for &gt;$3M).</div>""",
            unsafe_allow_html=True,
        )

        st.markdown(
            """<div class="note-box"><b>City presets (optional quick-start)</b><br>
            City presets are convenience starters for common markets. They speed up setup by prefilling city/province context and baseline assumptions, but they are not recommendations and do not lock your inputs. Always review and edit values for your own scenario.</div>""",
            unsafe_allow_html=True,
        )

        st.markdown(
            """<div class="note-box"><b>Insured mortgage rules (simplified)</b><br>
            For default-insured mortgages, this tool enforces a simplified Canadian minimum down-payment rule: 5% on the first $500k + 10% on the remainder up to $1.5M, and 20% at/above $1.5M. LTV is capped at 95% for insured loans.
            (Qualification rules, amortization limits, and insurer-specific policies are not modeled.)</div>""",
            unsafe_allow_html=True,
        )




    # Capital opportunity cost clarity (prevents perceived bias toward buying)
    try:
        upfront_rent_capital = float(down + (close_cash - down) if renter_uses_closing_input else down)
    except Exception:
        upfront_rent_capital = None

    with st.expander("🔎 Key clarifications (read this if results feel surprising)", expanded=True):
        st.markdown(
            f"""<div class="note-box">
<b>Capital opportunity cost (why renting can win)</b><br>
When renting, the simulator keeps your down payment{"+ closing costs" if renter_uses_closing_input else ""} invested (<span class="accent-rent">{_fmt_money(upfront_rent_capital) if upfront_rent_capital is not None else "—"}</span>) instead of tying it up in home equity. That foregone investment growth is the “opportunity cost of the down payment”, and it is accounted for in the Net Worth results (even though it is not an unrecoverable cash expense).
</div>""",
            unsafe_allow_html=True,
        )

        st.markdown(
            """<div class="note-box">
<b>Rent inflation vs. rent control</b><br>
<b>Rent Inflation</b> is your estimate of <i>market</i> rent growth. Enable <b>Rent Control</b> only if your unit is legally capped. When enabled, the model uses the smaller of <b>Rent Inflation</b> and the <b>Rent Control Cap</b>.
</div>""",
            unsafe_allow_html=True,
        )

        st.markdown(
            """<div class="note-box">
<b>Income & budget model </b><br>
If you enable the <b>Income/budget constraints</b> option, both paths must fit within the same monthly income and non-housing spending. Any surplus is invested; deficits are funded via portfolio drawdown (if allowed) or recorded as a <i>shortfall</i>. This can change results by modeling affordability constraints.
</div>""",
            unsafe_allow_html=True,
        )

        st.markdown(
            """<div class="note-box">
<b>Crisis shock (optional stress test)</b><br>
If enabled, a one-time (or short-duration) drawdown is applied to both the portfolio and the home value at the selected year. This is a <i>stress scenario</i> (tail-risk), not a forecast.
</div>""",
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)

    # Province tax assumptions (keeps override as ground-truth option)
    with st.expander("🏛️ Province tax assumptions", expanded=False):
        applied = calc_transfer_tax(province, float(price), first_time, toronto, override_amount=transfer_tax_override, asof_date=_tax_asof, assessed_value=assessed_value, ns_deed_transfer_rate=ns_deed_transfer_rate)
        rule_md = PROV_TAX_RULES_MD.get(province, "- No built-in rule text for this region. Use **Override** if applicable.")
        st.markdown(rule_md)

        st.markdown("**Applied estimate for your current inputs:**")
        c1, c2, c3 = st.columns(3)
        with c1:
            _kpi("Provincial / registration", _fmt_money(applied.get("prov", 0.0)), accent="#9A9A9A")
        with c2:
            _kpi("Municipal (if any)", _fmt_money(applied.get("muni", 0.0)), accent="#9A9A9A")
        with c3:
            _kpi("Total", _fmt_money(applied.get("total", 0.0)), accent="rgba(241,241,243,0.70)")

        if applied.get("note"):
            st.markdown(
                f"""<div class="note-box">{html.escape(str(applied["note"]))}</div>""",
                unsafe_allow_html=True,
            )

        if transfer_tax_override and float(transfer_tax_override) > 0:
            st.markdown(
                """<div class="note-box"><b>Transfer tax override is enabled.</b><br>
This estimate uses your override amount (recommended when your municipality has different rates or exemptions).</div>""",
                unsafe_allow_html=True,
            )


    # ------------------------------
    # Bias & Sensitivity Dashboard (v153)
    # ------------------------------
    # ------------------------------
    # Bias & Sensitivity Dashboard
elif tab == _TAB_BIAS:
    st.markdown(
        """<div class="note-box">
<b>What this tab does:</b>
<ul style="margin:6px 0 0 18px;">
  <li><b>Flip-points</b>: “What would need to change for the winner to switch?” (for example, how high rent would need to be, or how fast home prices would need to grow).</li>
  <li><b>Sensitivity</b>: “Which inputs matter most <i>right now</i>?” It nudges one input at a time by a small amount and measures how much the Buy vs Rent gap changes.</li>
</ul>
<b>How this helps you:</b> It tells you which assumptions are worth double‑checking (rent, appreciation, rates, etc.) because they have the biggest impact on the verdict.
</div>""",
        unsafe_allow_html=True,
    )

    # Mode selection
    bias_mode = st.radio(
        "Mode",
        ["Deterministic", "Monte Carlo"],
        horizontal=True,
        key="bias_dash_mode",
    )

    use_mc = bias_mode.startswith("Monte Carlo")

    mc_metric = None
    mc_sims = None

    if use_mc:
        st.markdown(
            """<div class="note-box">
<b>Monte Carlo mode:</b> Uses your current volatility/correlation settings and runs additional simulations to estimate either Win% or Expected Δ. This can be slow for long horizons or large sim counts.
</div>""",
            unsafe_allow_html=True,
        )

        mc_metric = st.selectbox(
            "Monte Carlo metric",
            ["Win% crossover (50%)", "Expected Δ (mean Buyer − Renter)"],
            index=0,
            key="bias_dash_mc_metric",
        )

        _raw_bias_mc_sims = st.session_state.get("bias_mc_sims", 15_000 if fast_mode else 30_000)
        try:
            mc_sims = int(float(_raw_bias_mc_sims))
        except Exception:
            mc_sims = 15_000 if fast_mode else 30_000
        mc_sims = int(max(100, min(250_000, mc_sims)))
        st.caption(f"Monte Carlo simulations (from Performance mode): **{mc_sims:,}**")

    # PV metric only applies to money-valued deltas (deterministic Δ or MC Expected Δ)
    pv_allowed = (not use_mc) or (mc_metric == "Expected Δ (mean Buyer − Renter)")
    use_pv_metric = False
    if pv_allowed:
        use_pv_metric = st.checkbox(
            "Use PV metric for flip-points/sensitivity (instead of nominal net worth)",
            value=False,
            key="bias_dash_use_pv",
        )
    else:
        st.session_state["bias_dash_use_pv"] = False
        st.caption("PV metric is disabled for Win% mode (Win% is not PV-discounted).")

    # Flip-points included in the 12-card grid (computed on every dashboard run).
    adv_selected = [
        "Down payment (% of price)",
        "Selling cost (% of sale price)",
        "Rent inflation (%/yr)",
        "Property tax rate (% of home value)",
        "Maintenance rate (% of home value)",
        "Repair costs rate (% of home value)",
        "Buyer investment return (%/yr)",
    ]

    st.markdown(
        "<div class='bias-subpill'>This dashboard computes flip-points for the most important drivers (rent, home appreciation, mortgage rate, returns, down payment, selling costs, taxes, maintenance, and repairs). Click <b>Compute Bias Dashboard</b> to refresh.</div>",
        unsafe_allow_html=True,
    )


    # Signature for caching the computed dashboard within this session
    def _bias_signature() -> str:
        # Use Session State (not module globals) so caches are per-user and stable.
        # The keys below are explicitly keyed widgets (v167 hotfix).
        def _ss(k, default=None):
            try:
                return st.session_state.get(k, default)
            except Exception:
                return default

        sig = {
            "bias_cache_version": 2,
            "bias_mode": str(bias_mode),
            "use_mc": bool(use_mc),
            "mc_metric": str(mc_metric) if mc_metric is not None else None,
            "mc_sims": int(mc_sims) if mc_sims is not None else None,
            "use_pv_metric": bool(use_pv_metric),
            "price": float(_ss("price", 0.0)),
            "rent": float(_ss("rent", 0.0)),
            "years": int(_ss("years", 25)),
            "down": float(_ss("down", 0.0)),
            "rate": float(_ss("rate", 0.0)),
            "buyer_ret": float(_ss("buyer_ret", 0.0)),
            "renter_ret": float(_ss("renter_ret", 0.0)),
            "apprec": float(_ss("apprec", 0.0)),
            "rent_inf": float(_ss("rent_inf", 0.0)),
            "canadian_compounding": bool(_ss("canadian_compounding", True)),
            "assume_sale_end": bool(_ss("assume_sale_end", True)),
            "show_liquidation_view": bool(_ss("show_liquidation_view", True)),
            "investment_tax_mode": str(_ss("investment_tax_mode", "")),
            "cg_tax_end": float(_ss("cg_tax_end", 0.0)),
            "home_sale_legal_fee": float(_ss("home_sale_legal_fee", 0.0)),
            "use_volatility": bool(_ss("use_volatility", False)),
            "mc_seed": _ss("mc_seed", None),
            "mc_randomize": bool(_ss("mc_randomize", True)),
            "ret_std_pct": float(_ss("ret_std_pct", 15.0)),
            "apprec_std_pct": float(_ss("apprec_std_pct", 5.0)),
            "market_corr_input": float(_ss("market_corr_input", 0.0)),
            "sell_cost_pct": float(_ss("sell_cost_pct", 0.0)),
            "p_tax_rate_pct": float(_ss("p_tax_rate_pct", 0.0)),
            "maint_rate_pct": float(_ss("maint_rate_pct", 0.0)),
            "repair_rate_pct": float(_ss("repair_rate_pct", 0.0)),
            "renter_uses_closing_input": bool(_ss("renter_uses_closing_input", True)),
            "prop_tax_growth_model": str(_ss("prop_tax_growth_model", "")),
            "prop_tax_hybrid_addon_pct": float(_ss("prop_tax_hybrid_addon_pct", 0.5)),
            "rent_control_enabled": bool(_ss("rent_control_enabled", False)),
            "rent_control_cap_pct": float(_ss("rent_control_cap_pct", 2.5)),
            "rent_control_frequency": str(_ss("rent_control_frequency", "Every year")),
            "invest_surplus_input": bool(_ss("invest_surplus_input", False)),
            "budget_enabled": bool(_ss("budget_enabled", False)),
            "budget_allow_withdraw": bool(_ss("budget_allow_withdraw", False)),
            "tax_deduct_contributions": bool(_ss("tax_deduct_contributions_input", False)),
            "reg_shelter_enabled": bool(_ss("reg_shelter_enabled", False)),
            "reg_initial_room": float(_ss("reg_initial_room", 0.0)),
            "reg_annual_room": float(_ss("reg_annual_room", 0.0)),
        }
        raw = json.dumps(sig, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    # --- Phase 3B: Bias solver acceleration ---
    # We reuse common random numbers across bias evaluations (bisection / sensitivity)
    # and avoid allocating full MC path arrays by requesting summary-only MC output.
    _bias_mc_shocks_cache = _rbv_get_session_cache("_bias_mc_shocks_cache")

    def _bias_effective_mc_seed() -> int | None:
        """Ensure MC bias tools have a stable seed even if the main MC toggle is off."""
        if mc_seed is not None:
            try:
                return int(mc_seed)
            except Exception:
                return None
        # Derive a stable per-input seed for bias tools (common random numbers).
        try:
            base = "bias:" + _bias_signature()
            return int(hashlib.sha256(base.encode("utf-8")).hexdigest()[:8], 16)
        except Exception:
            return None

    def _bias_get_mc_shocks(months: int, sims: int, seed: int | None):
        """Pre-generate standard normal shocks for CRN reuse across evaluations."""
        if seed is None:
            return None
        months_i = int(max(1, months))
        sims_i = int(max(1, sims))
        # Keep memory bounded: float32 arrays, 3 * months*sims
        # ~12MB at (300×5000). If bigger than ~48MB, skip caching.
        try:
            est_bytes = 3 * months_i * sims_i * 4
            if est_bytes > 800_000_000:
                return None
        except Exception:
            return None

        key = (int(seed), months_i, sims_i)
        if key in _bias_mc_shocks_cache:
            return _bias_mc_shocks_cache[key]

        # Soft-LRU: keep only a couple of keys to avoid session bloat
        try:
            if len(_bias_mc_shocks_cache) > 2:
                _bias_mc_shocks_cache.clear()
        except Exception:
            pass

        try:
            rng = np.random.default_rng(int(seed))
            z_sys = np.empty((months_i, sims_i), dtype=np.float32)
            z_stock = np.empty((months_i, sims_i), dtype=np.float32)
            z_house = np.empty((months_i, sims_i), dtype=np.float32)
            for i in range(months_i):
                z_sys[i, :] = rng.standard_normal(sims_i).astype(np.float32, copy=False)
                z_stock[i, :] = rng.standard_normal(sims_i).astype(np.float32, copy=False)
                z_house[i, :] = rng.standard_normal(sims_i).astype(np.float32, copy=False)
            _bias_mc_shocks_cache[key] = (z_sys, z_stock, z_house)
            return _bias_mc_shocks_cache[key]
        except Exception:
            return None

    # --- v2_30: Adaptive Bias Solver (coarse pass + refine near flip) ---
    # We run the bias flip-point solvers in two passes:
    #   1) coarse sims for bracketing + bisection
    #   2) refine only near the flip (full sims), reusing CRN shocks for stability
    _bias_full_sims = int(mc_sims) if (use_mc and mc_sims is not None) else None

    def _bias_coarse_sims_from_full(full):
        if full is None:
            return None
        try:
            full_i = int(full)
            # Use ~20% of target, clipped to 3k..6k (matches the heatmap adaptive philosophy).
            coarse = int(round(max(3000, min(6000, 0.20 * full_i)) / 500.0) * 500)
            return max(500, coarse)
        except Exception:
            return None

    _bias_coarse_sims = _bias_coarse_sims_from_full(_bias_full_sims) if _bias_full_sims is not None else None

    # Bias eval phase: controls default sims used by _eval_metric/_eval_mc_raw when sims_override is None.
    # We keep this as a simple string flag to avoid passing extra args everywhere.
    _bias_eval_phase = "full"
    def _eval_mc_raw(
        metric_use_pv: bool,
        apprec_override_pct=None,
        rent_override=None,
        buyer_ret_override_pct=None,
        renter_ret_override_pct=None,
        rate_override_pct=None,
        rent_inf_override_pct=None,
        param_overrides=None,
        sims_override=None,
    ):
        """Return (mean_delta, win_pct) from MC using the engine (no globals mutation)."""
        _po = dict(param_overrides or {})
        if rent_override is not None:
            _po["rent"] = float(rent_override)

        _mc_seed_use = _bias_effective_mc_seed()
        _months = int(max(1, int(st.session_state.get("years", 25))) * 12)
        # Determine sims for this evaluation (override > phase > full)
        try:
            _sims_use = int(sims_override) if sims_override is not None else (
                int(_bias_coarse_sims) if (_bias_eval_phase == "coarse" and _bias_coarse_sims is not None) else (
                    int(mc_sims) if mc_sims is not None else 0
                )
            )
        except Exception:
            _sims_use = 0
        _sims_use = int(max(1, _sims_use)) if _sims_use is not None else 0
        _shocks = _bias_get_mc_shocks(_months, int(_sims_use), _mc_seed_use)

        cache_key = (            bool(metric_use_pv),
            float(apprec_override_pct) if apprec_override_pct is not None else None,
            float(rent_override) if rent_override is not None else None,
            float(buyer_ret_override_pct) if buyer_ret_override_pct is not None else None,
            float(renter_ret_override_pct) if renter_ret_override_pct is not None else None,
            float(rate_override_pct) if rate_override_pct is not None else None,
            float(rent_inf_override_pct) if rent_inf_override_pct is not None else None,
            tuple(sorted(_po.items())),
            int(_sims_use) if _sims_use is not None else None,
            int(_mc_seed_use) if _mc_seed_use is not None else None,
        )
        if cache_key in _eval_mc_cache:
            return _eval_mc_cache[cache_key]

        a = float(apprec_override_pct) if apprec_override_pct is not None else float(st.session_state.apprec)
        br = float(buyer_ret_override_pct) if buyer_ret_override_pct is not None else float(st.session_state.buyer_ret)
        rr = float(renter_ret_override_pct) if renter_ret_override_pct is not None else float(st.session_state.renter_ret)

        _df, _, _, _win = run_simulation(
            br, rr, a,
            invest_surplus_input, renter_uses_closing_input, market_corr_input,
            force_deterministic=False,
            mc_seed=_mc_seed_use,
            rate_override_pct=rate_override_pct,
            rent_inf_override_pct=rent_inf_override_pct,
            param_overrides=_po,
            force_use_volatility=True,
            num_sims_override=int(_sims_use) if (_sims_use is not None and int(_sims_use) > 0) else None,            mc_summary_only=True,
            mc_precomputed_shocks=_shocks,
            **st.session_state.get('_rbv_extra_engine_kwargs', extra_engine_kwargs)
        )

        win_pct_use = float(_win) if _win is not None else None

        if metric_use_pv:
            bcol = "Buyer PV NW Mean" if "Buyer PV NW Mean" in _df.columns else "Buyer PV NW"
            rcol = "Renter PV NW Mean" if "Renter PV NW Mean" in _df.columns else "Renter PV NW"
        else:
            bcol = "Buyer NW Mean" if "Buyer NW Mean" in _df.columns else "Buyer Net Worth"
            rcol = "Renter NW Mean" if "Renter NW Mean" in _df.columns else "Renter Net Worth"

        mean_delta = float(_df.iloc[-1][bcol] - _df.iloc[-1][rcol])
        _eval_mc_cache[cache_key] = (mean_delta, win_pct_use)
        _rbv_cache_soft_cap(_eval_mc_cache, 6000)
        return mean_delta, win_pct_use

    def _eval_metric(
        metric_use_pv: bool,
        apprec_override_pct=None,
        rent_override=None,
        buyer_ret_override_pct=None,
        renter_ret_override_pct=None,
        rate_override_pct=None,
        rent_inf_override_pct=None,
        param_overrides=None,
        sims_override=None,
    ) -> float:
        """Scalar objective used for flip-points/sensitivity (no globals mutation)."""
        _po = dict(param_overrides or {})
        if rent_override is not None:
            _po["rent"] = float(rent_override)

        _mc_seed_use = _bias_effective_mc_seed() if bool(use_mc) else None

        _sims_key = int(sims_override) if sims_override is not None else (int(_bias_coarse_sims) if (_bias_eval_phase == "coarse" and _bias_coarse_sims is not None) else (int(mc_sims) if mc_sims is not None else None))

        cache_key = (
            bool(metric_use_pv),
            bool(use_mc),
            str(mc_metric),
            int(_sims_key) if _sims_key is not None else None,
            int(_mc_seed_use) if _mc_seed_use is not None else None,
            float(apprec_override_pct) if apprec_override_pct is not None else None,
            float(rent_override) if rent_override is not None else None,
            float(buyer_ret_override_pct) if buyer_ret_override_pct is not None else None,
            float(renter_ret_override_pct) if renter_ret_override_pct is not None else None,
            float(rate_override_pct) if rate_override_pct is not None else None,
            float(rent_inf_override_pct) if rent_inf_override_pct is not None else None,
            tuple(sorted(_po.items())),
        )
        if cache_key in _eval_cache:
            return _eval_cache[cache_key]

        if not use_mc:
            # Deterministic
            a = float(apprec_override_pct) if apprec_override_pct is not None else float(st.session_state.apprec)
            br = float(buyer_ret_override_pct) if buyer_ret_override_pct is not None else float(st.session_state.buyer_ret)
            rr = float(renter_ret_override_pct) if renter_ret_override_pct is not None else float(st.session_state.renter_ret)

            _df, _, _, _ = run_simulation(
                br, rr, a,
                invest_surplus_input, renter_uses_closing_input, market_corr_input,
                force_deterministic=True,
                mc_seed=mc_seed,
                rate_override_pct=rate_override_pct,
                rent_inf_override_pct=rent_inf_override_pct,
                param_overrides=_po,
                force_use_volatility=False,
                **st.session_state.get('_rbv_extra_engine_kwargs', extra_engine_kwargs)
            )

            if metric_use_pv:
                val = float(_df.iloc[-1]["Buyer PV NW"] - _df.iloc[-1]["Renter PV NW"])
            else:
                val = float(_df.iloc[-1]["Buyer Net Worth"] - _df.iloc[-1]["Renter Net Worth"])

            _eval_cache[cache_key] = val
            _rbv_cache_soft_cap(_eval_cache, 8000)
            return val

        # Monte Carlo objective
        mean_delta, win_pct_use = _eval_mc_raw(
            metric_use_pv,
            apprec_override_pct=apprec_override_pct,
            rent_override=rent_override,
            buyer_ret_override_pct=buyer_ret_override_pct,
            renter_ret_override_pct=renter_ret_override_pct,
            rate_override_pct=rate_override_pct,
            rent_inf_override_pct=rent_inf_override_pct,
            param_overrides=_po,
            sims_override=_sims_key,
        )

        if mc_metric == "Win% crossover (50%)":
            if win_pct_use is None:
                val = float("nan")
            else:
                val = (win_pct_use / 100.0) - 0.5
        else:
            val = float(mean_delta)

        _eval_cache[cache_key] = val
        _rbv_cache_soft_cap(_eval_cache, 8000)
        return val


    def _bisection_solve(f, lo, hi, iters=18, tol=1e-3):
        flo = f(lo)
        fhi = f(hi)
        if math.isnan(flo) or math.isnan(fhi):
            return None
        if abs(flo) < tol:
            return lo
        if abs(fhi) < tol:
            return hi
        if flo * fhi > 0:
            return None
        a, b = lo, hi
        fa, fb = flo, fhi
        for _ in range(iters):
            mid = 0.5 * (a + b)
            fm = f(mid)
            if abs(fm) < tol:
                return mid
            if fa * fm <= 0:
                b, fb = mid, fm
            else:
                a, fa = mid, fm
        return 0.5 * (a + b)


    def _bias_eval_with_phase(f, x, phase: str):
        """Evaluate f(x) while forcing bias eval phase (controls sims)."""
        global _bias_eval_phase
        prev = _bias_eval_phase
        _bias_eval_phase = str(phase)
        try:
            return f(x)
        finally:
            _bias_eval_phase = prev

    def _bias_refine_flip(f, x0, lo, hi, iters_full: int = 12, tol: float = 1e-3):
        """Refine a coarse flip-point estimate near x0 using full sims only."""
        if x0 is None:
            return None, False
        try:
            x0f = float(x0)
            lo_f = float(lo)
            hi_f = float(hi)
        except Exception:
            return x0, False

        # Evaluate at full sims (phase="full")
        try:
            f0 = _bias_eval_with_phase(f, x0f, "full")
        except Exception:
            return x0, False
        if not _rbv_diag_isfinite(f0):
            return x0, False
        if abs(float(f0)) < float(tol):
            return x0, True

        # Try to find a small local bracket around x0 (keeps full-eval count low)
        span = abs(hi_f - lo_f)
        step = max(span / 32.0, 1e-9)
        max_expand = 10
        a = b = None

        for _ in range(max_expand):
            left = max(lo_f, x0f - step)
            right = min(hi_f, x0f + step)

            # Prefer bracketing against x0 (one side at a time)
            if left != x0f:
                try:
                    fl = _bias_eval_with_phase(f, left, "full")
                except Exception:
                    fl = float("nan")
                if _rbv_diag_isfinite(fl) and float(fl) * float(f0) <= 0:
                    a, b = left, x0f
                    break

            if right != x0f:
                try:
                    fr = _bias_eval_with_phase(f, right, "full")
                except Exception:
                    fr = float("nan")
                if _rbv_diag_isfinite(fr) and float(fr) * float(f0) <= 0:
                    a, b = x0f, right
                    break

            # Fallback: check if left/right bracket each other
            if left != x0f and right != x0f:
                if _rbv_diag_isfinite(fl) and _rbv_diag_isfinite(fr) and float(fl) * float(fr) <= 0:
                    a, b = left, right
                    break

            step *= 1.8

        # If we couldn't find a local bracket, fall back to the original bounds if they bracket at full sims
        if a is None or b is None:
            try:
                flo = _bias_eval_with_phase(f, lo_f, "full")
                fhi = _bias_eval_with_phase(f, hi_f, "full")
                if _rbv_diag_isfinite(flo) and _rbv_diag_isfinite(fhi) and float(flo) * float(fhi) <= 0:
                    a, b = lo_f, hi_f
            except Exception:
                a = b = None

        if a is None or b is None or float(a) == float(b):
            return x0, False

        # Full-sims bisection on the bracket (phase forced to full for each eval)
        def _ff(x):
            return _bias_eval_with_phase(f, x, "full")

        x1 = _bisection_solve(_ff, float(a), float(b), iters=int(iters_full), tol=float(tol))
        return (x1 if x1 is not None else x0), True

    def _bias_solve_flip(f, lo, hi, iters_coarse: int = 12, iters_full: int = 12, tol: float = 1e-3):
        """Adaptive flip solve: coarse bisection + full refinement near the flip."""
        # Track diagnostics counters (per compute run)
        try:
            st.session_state["_rbv_bias_total_flips"] = int(st.session_state.get("_rbv_bias_total_flips", 0)) + 1
        except Exception:
            pass

        adaptive_ok = bool(use_mc) and (_bias_full_sims is not None) and (_bias_coarse_sims is not None) and int(_bias_coarse_sims) < int(_bias_full_sims)

        if not adaptive_ok:
            # Deterministic or no coarse benefit
            return _bisection_solve(f, lo, hi, iters=18, tol=float(tol))

        # Coarse phase bisection (bracketing scans outside already use coarse)
        x0 = _bisection_solve(f, lo, hi, iters=int(iters_coarse), tol=float(tol))
        x1, refined = _bias_refine_flip(f, x0, lo, hi, iters_full=int(iters_full), tol=float(tol))
        if refined:
            try:
                st.session_state["_rbv_bias_refined_flips"] = int(st.session_state.get("_rbv_bias_refined_flips", 0)) + 1
            except Exception:
                pass
        return x1
    sig_now = _bias_signature()

    # Session cache (Phase 3D): keep computed dashboards per-signature so users can toggle around
    # without re-running bisection/MC.
    if "_bias_dash_sig" not in st.session_state:
        st.session_state["_bias_dash_sig"] = None
    if "_bias_dash_result" not in st.session_state:
        st.session_state["_bias_dash_result"] = None
    if "_bias_dash_cache" not in st.session_state:
        st.session_state["_bias_dash_cache"] = {}
    if "_bias_dash_cache_order" not in st.session_state:
        st.session_state["_bias_dash_cache_order"] = []

    # Button triggers compute
    try:
        compute_now = st.button(
            "Compute Bias Dashboard",
            use_container_width=True,
            key="bias_dash_compute",
            type="primary",
        )
    except TypeError:
        compute_now = st.button(
            "Compute Bias Dashboard",
            use_container_width=True,
            key="bias_dash_compute",
        )

    # Validation: avoid long MC runs / confusing tracebacks on invalid scenarios
    if compute_now:
        _errs_bias = _rbv_basic_validation_errors()
        if _errs_bias:
            st.error("Cannot compute Bias Dashboard until these are fixed:\n\n- " + "\n- ".join(_errs_bias))
            compute_now = False


    # Load cached result for this input signature (unless user explicitly re-computes)
    if st.session_state.get("_bias_dash_sig") != sig_now:
        st.session_state["_bias_dash_sig"] = sig_now
        st.session_state["_bias_dash_result"] = st.session_state["_bias_dash_cache"].get(sig_now)

    if (st.session_state.get("_bias_dash_result") is None) and (sig_now in st.session_state["_bias_dash_cache"]) and (not compute_now):
        st.session_state["_bias_dash_result"] = st.session_state["_bias_dash_cache"].get(sig_now)

    if compute_now:

        # Mark this as an active long run so a Stop can deterministically freeze any immediate rerun.
        try:
            st.session_state["_rbv_active_longrun"] = {"kind": "bias", "sig": str(sig_now)}
        except Exception:
            pass

        # Reset per-run adaptive bias stats
        try:
            st.session_state["_rbv_bias_refined_flips"] = 0
            st.session_state["_rbv_bias_total_flips"] = 0
        except Exception:
            pass

        _prev_bias_phase = _bias_eval_phase
        _adaptive_bias_active = bool(use_mc) and (_bias_full_sims is not None) and (_bias_coarse_sims is not None) and int(_bias_coarse_sims) < int(_bias_full_sims)
        _bias_eval_phase = "full"
        _flip_n = 4 + len(adv_selected)  # rent, home appreciation, mortgage rate, renter return + advanced flips
        _total_steps = 1 + (1 if use_mc else 0) + _flip_n + 9

        _eta0 = None
        try:
            _avg_step = float(st.session_state.get("_rbv_bias_avg_step_sec", 0.0))
            if _avg_step > 0:
                _eta0 = _avg_step * float(_total_steps)
        except Exception:
            _eta0 = None

        try:
            _rbv_global_progress_show(0, "Bias & Sensitivity", eta_sec=_eta0)
        except Exception:
            pass
        with st.spinner("Computing flip-points and sensitivities..."):
            _status = st.empty()
            _steps_done = [0]
            _bias_t0 = time.time()
            def _bump(msg: str):
                _steps_done[0] += 1
                pct = int(min(100, (_steps_done[0] / max(1, _total_steps)) * 100))
                try:
                    # ETA estimate (best-effort)
                    eta_str = ""
                    try:
                        elapsed = max(1e-6, time.time() - _bias_t0)
                        rate = _steps_done[0] / elapsed
                        remaining = max(_total_steps - _steps_done[0], 0)
                        eta_sec = remaining / max(1e-6, rate)
                        eta_str = _rbv_eta_str_from_seconds(eta_sec)
                    except Exception:
                        eta_sec = None
                    try:
                        eta_html = f" • ETA: {html.escape(eta_str)}" if eta_str else ""
                        _status.markdown(
                            f"<div style='color:rgba(148,163,184,0.95); font-size:12px; margin-top:4px; text-align:center; width:100%;'>"
                            f"{html.escape(msg)}{eta_html}"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                    except Exception:
                        pass
                    # Global overlay (visible even when scrolled)
                    try:
                        _rbv_global_progress_show(pct, "Bias & Sensitivity", eta_sec=eta_sec if 'eta_sec' in locals() else None)
                        if pct >= 100:
                            _rbv_global_progress_clear()
                    except Exception:
                        pass
                except Exception:
                    pass

            try:
                _status.markdown(
                    "<div style='color:rgba(148,163,184,0.95); font-size:12px; margin-top:4px; text-align:center; width:100%;'>Running baseline (current inputs)...</div>",
                    unsafe_allow_html=True,
                )
            except Exception:
                pass
            base_val = _eval_metric(use_pv_metric)
            _bump("Baseline computed")

            # Also compute MC headline (if applicable) for display
            base_win_pct = None
            if use_mc:
                try:
                    _status.markdown(
                        "<div style='color:rgba(148,163,184,0.95); font-size:12px; margin-top:4px; text-align:center; width:100%;'>Running Monte Carlo baseline...</div>",
                        unsafe_allow_html=True,
                    )
                except Exception:
                    pass
                _, base_win_pct = _eval_mc_raw(use_pv_metric)
                _bump("Monte Carlo baseline computed")

            # Flip-point: RENT ($/mo)
            # Adaptive Bias: run flip-point solvers with coarse sims for bracketing/bisection
            if _adaptive_bias_active:
                _bias_eval_phase = "coarse"

            base_r = float(rent)

            def f_r(x):
                return _eval_metric(use_pv_metric, rent_override=x)

            flip_rent = None
            if base_r > 0:
                f0 = base_val
                if f0 < 0:
                    lo, hi = base_r, max(base_r * 2.0, base_r + 500.0)
                    while hi <= 30000 and f_r(hi) < 0:
                        hi *= 1.5
                    if hi <= 30000:
                        flip_rent = _bias_solve_flip(f_r, lo, hi)
                else:
                    hi, lo = base_r, max(0.0, base_r * 0.5)
                    while lo > 0 and f_r(lo) > 0:
                        lo *= 0.5
                    flip_rent = _bias_solve_flip(f_r, lo, hi)

            _bump("Flip rent computed")

            # Flip-point: HOME APPRECIATION (%)
            base_a = float(st.session_state.apprec)
            def f_a(x):
                return _eval_metric(use_pv_metric, apprec_override_pct=x)

            flip_app = None
            f0a = base_val
            if f0a < 0:
                lo, hi = base_a, max(base_a + 2.0, base_a * 1.5 + 0.5)
                while hi <= 25.0 and f_a(hi) < 0:
                    hi += 2.0
                if hi <= 25.0:
                    flip_app = _bias_solve_flip(f_a, lo, hi)
            else:
                hi, lo = base_a, base_a - 2.0
                while lo >= -10.0 and f_a(lo) > 0:
                    lo -= 2.0
                if lo >= -10.0:
                    flip_app = _bias_solve_flip(f_a, lo, hi)


            _bump("Flip appreciation computed")

            # Flip-point: MORTGAGE RATE (%)
            base_m = float(rate)
            def f_m(x):
                return _eval_metric(use_pv_metric, rate_override_pct=x)

            flip_rate = None
            try:
                if base_val < 0:
                    # Renting is ahead: lower rates can help buying
                    hi = base_m
                    lo = max(0.0, base_m - 1.0)
                    vlo = f_m(lo)
                    while lo > 0.0 and vlo < 0:
                        lo = max(0.0, lo - 1.0)
                        vlo = f_m(lo)
                    if (not math.isnan(vlo)) and vlo >= 0 and lo < hi:
                        flip_rate = _bias_solve_flip(f_m, lo, hi)
                else:
                    # Buying is ahead: higher rates can erode buying advantage
                    lo = base_m
                    hi = min(25.0, base_m + 1.0)
                    vhi = f_m(hi)
                    while hi < 25.0 and vhi > 0:
                        hi = min(25.0, hi + 1.0)
                        vhi = f_m(hi)
                    if (not math.isnan(vhi)) and vhi <= 0 and lo < hi:
                        flip_rate = _bias_solve_flip(f_m, lo, hi)
            except Exception:
                flip_rate = None

            _bump("Flip mortgage rate computed")


            # Flip: Renter investment return (%/yr)  (core flip-point; enabled by default)
            flip_renter_ret = None
            try:
                base_rr = float(st.session_state.get("renter_ret", 0.0))
                def f_rr(x):
                    return _eval_metric(use_pv_metric, renter_ret_override_pct=float(x))
                if base_val < 0:
                    # Renting ahead: lower renter return can reduce renting advantage
                    hi, lo = base_rr, max(-10.0, base_rr - 1.0)
                    vlo = f_rr(lo)
                    while lo > -10.0 and vlo < 0:
                        lo -= 1.0
                        vlo = f_rr(lo)
                    if hi > lo and vlo >= 0:
                        flip_renter_ret = _bias_solve_flip(f_rr, lo, hi)
                else:
                    # Buying ahead: higher renter return can tilt toward renting
                    lo, hi = base_rr, min(25.0, base_rr + 1.0)
                    vhi = f_rr(hi)
                    while hi < 25.0 and vhi > 0:
                        hi += 1.0
                        vhi = f_rr(hi)
                    if hi > lo and vhi <= 0:
                        flip_renter_ret = _bias_solve_flip(f_rr, lo, hi)
            except Exception:
                flip_renter_ret = None

            _bump("Flip renter return computed")


            # Optional advanced flip-points (computed only if selected)
            adv_flips = {}
            _price_f = float(price)

            def _store_adv(name: str, value, fmt: str, tooltip: str, sub: str | None = None):
                if value is None:
                    adv_flips[name] = {"value": None, "fmt": fmt, "tooltip": tooltip, "sub": sub}
                else:
                    adv_flips[name] = {"value": float(value), "fmt": fmt, "tooltip": tooltip, "sub": sub}
            # Advanced flips are always computed (no selection UI).
            if True:
                # Flip: Down payment (as % of price; solved in $ then displayed as %)
                if "Down payment (% of price)" in adv_selected and _price_f > 0:
                    try:
                        base_d = float(down)
                        def f_d(x):
                            return _eval_metric(use_pv_metric, param_overrides={"down": float(x)})
                        flip_down = None
                        if base_val < 0:
                            lo = base_d
                            hi = min(_price_f, max(base_d + 10000.0, base_d * 1.5))
                            vhi = f_d(hi)
                            while hi < _price_f and vhi < 0:
                                hi = min(_price_f, hi + max(20000.0, 0.10 * _price_f))
                                vhi = f_d(hi)
                            if hi > lo and vhi >= 0:
                                flip_down = _bias_solve_flip(f_d, lo, hi)
                        else:
                            lo, hi = 0.0, base_d
                            vlo = f_d(lo)
                            if hi > lo and vlo <= 0:
                                flip_down = _bias_solve_flip(f_d, lo, hi)
                        dpct = None if flip_down is None else (float(flip_down) / _price_f * 100.0)
                        sub = None if flip_down is None else f"${float(flip_down):,.0f}"
                        _store_adv(
                            "Flip down payment",
                            dpct,
                            "pct",
                            "Approximate down payment percentage (of purchase price) that would make the result a tie, holding everything else constant.",
                            sub=sub,
                        )
                    except Exception:
                        _store_adv("Flip down payment", None, "pct", "Down payment flip could not be computed.")
                    _bump("Flip down payment computed")

                # Flip: Selling cost (% of sale price)
                if "Selling cost (% of sale price)" in adv_selected:
                    try:
                        base_sc = float(sell_cost)
                        def f_sc(x):
                            return _eval_metric(use_pv_metric, param_overrides={"sell_cost": float(x)})
                        flip_sc = None
                        lo, hi = 0.0, min(0.25, max(base_sc + 0.02, 0.08))
                        # If buying is ahead, higher selling costs can push it to tie; if renting ahead, lower costs can help buying.
                        if base_val < 0:
                            hi, lo = base_sc, 0.0
                            vlo = f_sc(lo)
                            if hi > lo and vlo >= 0:
                                flip_sc = _bias_solve_flip(f_sc, lo, hi)
                        else:
                            lo, hi = base_sc, min(0.25, max(base_sc + 0.02, base_sc * 1.5 + 0.01))
                            vhi = f_sc(hi)
                            while hi < 0.25 and vhi > 0:
                                hi = min(0.25, hi + 0.02)
                                vhi = f_sc(hi)
                            if hi > lo and vhi <= 0:
                                flip_sc = _bias_solve_flip(f_sc, lo, hi)
                        _store_adv(
                            "Flip selling cost",
                            None if flip_sc is None else float(flip_sc) * 100.0,
                            "pct",
                            "Approximate total selling cost rate (as % of sale price) that would make the result a tie.",
                        )
                    except Exception:
                        _store_adv("Flip selling cost", None, "pct", "Selling cost flip could not be computed.")
                    _bump("Flip selling cost computed")

                # Flip: Rent inflation (%/yr)
                if "Rent inflation (%/yr)" in adv_selected:
                    try:
                        base_ri = float(st.session_state.get("rent_inf", 0.0))
                        def f_ri(x):
                            return _eval_metric(use_pv_metric, rent_inf_override_pct=float(x))
                        flip_ri = None
                        if base_val < 0:
                            lo, hi = base_ri, max(base_ri + 1.0, base_ri * 1.5 + 0.5)
                            vhi = f_ri(hi)
                            while hi < 25.0 and vhi < 0:
                                hi += 1.0
                                vhi = f_ri(hi)
                            if hi > lo and vhi >= 0:
                                flip_ri = _bias_solve_flip(f_ri, lo, hi)
                        else:
                            hi, lo = base_ri, base_ri - 1.0
                            vlo = f_ri(lo)
                            while lo > -10.0 and vlo > 0:
                                lo -= 1.0
                                vlo = f_ri(lo)
                            if hi > lo and vlo <= 0:
                                flip_ri = _bias_solve_flip(f_ri, lo, hi)
                        _store_adv(
                            "Flip rent inflation",
                            flip_ri,
                            "pctyr",
                            "Approximate annual rent inflation rate that would make the result a tie. If rent control is enabled, the effective inflation may be capped.",
                        )
                    except Exception:
                        _store_adv("Flip rent inflation", None, "pctyr", "Rent inflation flip could not be computed.")
                    _bump("Flip rent inflation computed")

                # Flip: Property tax rate (% of home value)
                if "Property tax rate (% of home value)" in adv_selected:
                    try:
                        base_pt = float(p_tax_rate)
                        def f_pt(x):
                            return _eval_metric(use_pv_metric, param_overrides={"p_tax_rate": float(x)})
                        flip_pt = None
                        if base_val < 0:
                            hi, lo = base_pt, 0.0
                            vlo = f_pt(lo)
                            if hi > lo and vlo >= 0:
                                flip_pt = _bias_solve_flip(f_pt, lo, hi)
                        else:
                            lo, hi = base_pt, min(0.05, max(base_pt + 0.002, base_pt * 1.5 + 0.001))
                            vhi = f_pt(hi)
                            while hi < 0.05 and vhi > 0:
                                hi = min(0.05, hi + 0.002)
                                vhi = f_pt(hi)
                            if hi > lo and vhi <= 0:
                                flip_pt = _bias_solve_flip(f_pt, lo, hi)
                        _store_adv(
                            "Flip property tax rate",
                            None if flip_pt is None else float(flip_pt) * 100.0,
                            "pctyr",
                            "Approximate property tax rate (as % of home value per year) that would make the result a tie.",
                        )
                    except Exception:
                        _store_adv("Flip property tax rate", None, "pctyr", "Property tax flip could not be computed.")
                    _bump("Flip property tax computed")

                # Flip: Maintenance rate (% of home value)
                if "Maintenance rate (% of home value)" in adv_selected:
                    try:
                        base_mr = float(maint_rate)
                        def f_mr(x):
                            return _eval_metric(use_pv_metric, param_overrides={"maint_rate": float(x)})
                        flip_mr = None
                        if base_val < 0:
                            hi, lo = base_mr, 0.0
                            vlo = f_mr(lo)
                            if hi > lo and vlo >= 0:
                                flip_mr = _bias_solve_flip(f_mr, lo, hi)
                        else:
                            lo, hi = base_mr, min(0.08, max(base_mr + 0.002, base_mr * 1.5 + 0.001))
                            vhi = f_mr(hi)
                            while hi < 0.08 and vhi > 0:
                                hi = min(0.08, hi + 0.002)
                                vhi = f_mr(hi)
                            if hi > lo and vhi <= 0:
                                flip_mr = _bias_solve_flip(f_mr, lo, hi)
                        _store_adv(
                            "Flip maintenance rate",
                            None if flip_mr is None else float(flip_mr) * 100.0,
                            "pctyr",
                            "Approximate maintenance rate (as % of home value per year) that would make the result a tie.",
                        )
                    except Exception:
                        _store_adv("Flip maintenance rate", None, "pctyr", "Maintenance flip could not be computed.")
                    _bump("Flip maintenance computed")



                # Flip: Repair costs rate (% of home value)
                if "Repair costs rate (% of home value)" in adv_selected:
                    try:
                        base_rrate = float(repair_rate)
                        def f_rrate(x):
                            return _eval_metric(use_pv_metric, param_overrides={"repair_rate": float(x)})
                        flip_rrate = None
                        if base_val < 0:
                            hi, lo = base_rrate, 0.0
                            vlo = f_rrate(lo)
                            if hi > lo and vlo >= 0:
                                flip_rrate = _bias_solve_flip(f_rrate, lo, hi)
                        else:
                            lo, hi = base_rrate, min(0.10, max(base_rrate + 0.002, base_rrate * 1.5 + 0.001))
                            vhi = f_rrate(hi)
                            while hi < 0.10 and vhi > 0:
                                hi = min(0.10, hi + 0.002)
                                vhi = f_rrate(hi)
                            if hi > lo and vhi <= 0:
                                flip_rrate = _bias_solve_flip(f_rrate, lo, hi)
                        _store_adv(
                            "Flip repair costs rate",
                            None if flip_rrate is None else float(flip_rrate) * 100.0,
                            "pctyr",
                            "Approximate annual repair costs rate (as % of home value per year) that would make the result a tie.",
                        )
                    except Exception:
                        _store_adv("Flip repair costs rate", None, "pctyr", "Repair costs flip could not be computed.")
                    _bump("Flip repair costs computed")
                # Flip: Buyer investment return (%/yr)
                if "Buyer investment return (%/yr)" in adv_selected:
                    try:
                        base_br = float(st.session_state.get("buyer_ret", 0.0))
                        def f_br(x):
                            return _eval_metric(use_pv_metric, buyer_ret_override_pct=float(x))
                        flip_br = None
                        if base_val < 0:
                            # Renting ahead: higher buyer return can help buying
                            lo, hi = base_br, min(25.0, max(base_br + 1.0, base_br * 1.5 + 0.5))
                            vhi = f_br(hi)
                            while hi < 25.0 and vhi < 0:
                                hi += 1.0
                                vhi = f_br(hi)
                            if hi > lo and vhi >= 0:
                                flip_br = _bias_solve_flip(f_br, lo, hi)
                        else:
                            # Buying ahead: lower buyer return can reduce buying advantage
                            hi, lo = base_br, max(-10.0, base_br - 1.0)
                            vlo = f_br(lo)
                            while lo > -10.0 and vlo > 0:
                                lo -= 1.0
                                vlo = f_br(lo)
                            if hi > lo and vlo <= 0:
                                flip_br = _bias_solve_flip(f_br, lo, hi)
                        _store_adv(
                            "Flip buyer return",
                            flip_br,
                            "pctyr",
                            "Approximate buyer investment return that would make the result a tie (holding other inputs constant).",
                        )
                    except Exception:
                        _store_adv("Flip buyer return", None, "pctyr", "Buyer return flip could not be computed.")
                    _bump("Flip buyer return computed")

            # Local sensitivities: impact on objective if we INCREASE each input by a small step
            # After flip-point solving, switch back to full sims for sensitivity evaluations
            if _adaptive_bias_active:
                _bias_eval_phase = "full"

            sens_specs = [
                ("Monthly Rent ($)", max(200.0, 0.07 * max(1.0, base_r)), "rent"),
                ("Home appreciation (+0.5%/yr)", 0.50, "apprec"),
                ("Renter portfolio return (+0.5%/yr)", 0.50, "renter_ret"),
                ("Buyer portfolio return (+0.5%/yr)", 0.50, "buyer_ret"),
                ("Mortgage rate (+0.5%/yr)", 0.50, "mort_rate"),
                ("Rent inflation (+0.5%/yr)", 0.50, "rent_inf"),
                ("Property tax rate (+0.10% of home value)", 0.10, "p_tax_rate"),
                ("Maintenance rate (+0.10% of home value)", 0.10, "maint_rate"),
                ("Selling cost (+0.5% of sale price)", 0.50, "sell_cost"),
            ]

            # Use the explicit user-entered percent-point value for rent inflation in sensitivity
            # (not the already-capped effective decimal), then let engine rules apply caps consistently.
            try:
                _base_rent_inf_pct = float(st.session_state.get("rent_inf", 0.0))
            except Exception:
                _base_rent_inf_pct = float(rent_inf_eff * 100.0)

            sens_rows = []
            for label, step, key in sens_specs:
                try:
                    if key == "rent":
                        d_plus = _eval_metric(use_pv_metric, rent_override=base_r + step) - base_val
                    elif key == "apprec":
                        d_plus = _eval_metric(use_pv_metric, apprec_override_pct=base_a + step) - base_val
                    elif key == "renter_ret":
                        d_plus = _eval_metric(use_pv_metric, renter_ret_override_pct=float(st.session_state.renter_ret) + step) - base_val
                    elif key == "buyer_ret":
                        d_plus = _eval_metric(use_pv_metric, buyer_ret_override_pct=float(st.session_state.buyer_ret) + step) - base_val
                    elif key == "mort_rate":
                        d_plus = _eval_metric(use_pv_metric, rate_override_pct=float(rate) + step) - base_val
                    elif key == "rent_inf":
                        _ri_plus = float(_base_rent_inf_pct) + float(step)
                        _ri_plus = min(100.0, max(-99.0, _ri_plus))
                        d_plus = _eval_metric(use_pv_metric, rent_inf_override_pct=_ri_plus) - base_val
                    elif key in ("p_tax_rate", "maint_rate"):
                        cur = float(p_tax_rate) if key == "p_tax_rate" else float(maint_rate)
                        d_plus = _eval_metric(use_pv_metric, param_overrides={key: cur + 0.01 * step}) - base_val
                    elif key == "sell_cost":
                        cur = float(sell_cost)
                        d_plus = _eval_metric(use_pv_metric, param_overrides={"sell_cost": cur + 0.01 * step}) - base_val
                    else:
                        continue

                    sens_rows.append({
                        "Input": label,
                        "Increase By": f"+{step:.2f}" if isinstance(step, (int, float)) else str(step),
                        "Impact": float(d_plus),
                    })
                except Exception:
                    sens_rows.append({
                        "Input": label,
                        "Increase By": f"+{step:.2f}" if isinstance(step, (int, float)) else str(step),
                        "Impact": np.nan,
                    })
                _bump(f"Sensitivity computed: {label}")

            sens_df = pd.DataFrame(sens_rows)
            sens_df["Abs Impact"] = sens_df["Impact"].abs()
            sens_df = sens_df.sort_values("Abs Impact", ascending=False)

            # Presentation labels
            if not use_mc:
                metric_label = "PV Δ (Buyer − Renter)" if use_pv_metric else "Δ Net Worth (Buyer − Renter)"
                value_kind = "money"
            else:
                if mc_metric == "Win% crossover (50%)":
                    metric_label = "MC Win% (Buyer beats Renter)"
                    value_kind = "pct"
                else:
                    metric_label = "MC Expected Δ (mean Buyer − Renter), PV" if use_pv_metric else "MC Expected Δ (mean Buyer − Renter)"
                    value_kind = "money"


            # Restore bias eval phase flag
            try:
                _bias_eval_phase = _prev_bias_phase
            except Exception:
                pass

            # Record adaptive bias stats in diagnostics stream
            if _adaptive_bias_active:
                try:
                    _rbv_diag_add(
                        "OK",
                        "Adaptive Bias refinement",
                        f"{int(st.session_state.get('_rbv_bias_refined_flips', 0))}/{int(st.session_state.get('_rbv_bias_total_flips', 0))} flip solves refined at full sims (coarse={_bias_coarse_sims}, full={_bias_full_sims})",
                    )
                except Exception:
                    pass

            st.session_state["_bias_dash_result"] = {
                "metric_label": metric_label,
                "value_kind": value_kind,
                "use_mc": bool(use_mc),
                "mc_metric": str(mc_metric) if mc_metric is not None else None,
                "mc_sims": int(mc_sims) if mc_sims is not None else None,
                "base_val": float(base_val),
                "base_win_pct": None if base_win_pct is None else float(base_win_pct),
                "flip_rent": None if flip_rent is None else float(flip_rent),
                "flip_app": None if flip_app is None else float(flip_app),
                "flip_rate": None if flip_rate is None else float(flip_rate),
                "flip_renter_ret": None if flip_renter_ret is None else float(flip_renter_ret),
                "adv_selected": list(adv_selected) if isinstance(adv_selected, (list, tuple)) else [],
                "adv_flips": adv_flips if isinstance(adv_flips, dict) else {},
                "sens_df": sens_df.drop(columns=["Abs Impact"]).head(8),
            }
            # Store per-signature cache (Phase 3D)
            try:
                st.session_state["_bias_dash_cache"][sig_now] = st.session_state["_bias_dash_result"]
                order = st.session_state.get("_bias_dash_cache_order", [])
                order.append(sig_now)
                MAX_KEEP = 6
                if len(order) > MAX_KEEP:
                    drop = order[:-MAX_KEEP]
                    st.session_state["_bias_dash_cache_order"] = order[-MAX_KEEP:]
                    for k in drop:
                        st.session_state["_bias_dash_cache"].pop(k, None)
                else:
                    st.session_state["_bias_dash_cache_order"] = order
            except Exception:
                pass

            # Update average seconds-per-step for seeding ETAs on future runs
            try:
                _elapsed_total = max(1e-6, time.time() - _bias_t0)
                _sec_per_step = _elapsed_total / max(1, int(_steps_done[0]))
                _prev = float(st.session_state.get("_rbv_bias_avg_step_sec", 0.0))
                st.session_state["_rbv_bias_avg_step_sec"] = (0.7 * _prev + 0.3 * _sec_per_step) if _prev > 0 else _sec_per_step
            except Exception:
                pass
            try:
                _status.markdown("<div style='color:rgba(148,163,184,0.95); font-size:12px; margin-top:4px; text-align:center; width:100%;'>Done.</div>", unsafe_allow_html=True)
            except Exception:
                pass
            try:
                _status.empty()
            except Exception:
                pass

        # Completed normally -> clear active long-run marker.
        try:
            st.session_state["_rbv_active_longrun"] = None
        except Exception:
            pass


    # --- Render results (simplified + dark-theme friendly) ---
    res = st.session_state.get("_bias_dash_result")
    if res is None:
        st.info("Click **Compute Bias Dashboard** to generate flip-points and sensitivities for your current inputs.")
    else:
        # Small pill/badge row (avoid st.metric truncation)
        try:
            _metric = str(res.get("metric_label",""))
            _kind = str(res.get("value_kind","money"))
            _use_mc = bool(res.get("use_mc", False))
            _mc_metric = res.get("mc_metric")
            _mc_sims = res.get("mc_sims")

            # Determine current banner and who is ahead
            if _kind == "money":
                base_val_f = float(res.get("base_val", 0.0))
                current_label = "Current gap"
                current_value = _fmt_money(abs(base_val_f))
                cur_class = "buy" if base_val_f >= 0 else "rent"
                current_sub = "Buying ahead" if base_val_f >= 0 else "Renting ahead"
                current_tip = (
                    "Magnitude of the current gap for your chosen metric. We display the absolute value; the border/color tells you who is ahead."
                )
            else:
                win = res.get("base_win_pct")
                current_label = "Buyer win chance"
                cur_class = "buy"
                current_value = "n/a"
                current_sub = ""
                if win is not None:
                    winf = float(win)
                    current_value = f"{winf:.1f}%"
                    cur_class = "buy" if winf >= 50.0 else "rent"
                    try:
                        n_sims = int(_mc_sims) if _mc_sims is not None else 0
                    except Exception:
                        n_sims = 0
                    if n_sims > 0:
                        wins_est = int(round((winf / 100.0) * n_sims))
                        current_sub = f"Buy wins ~{wins_est}/{n_sims} sims"
                current_tip = (
                    "Across the dashboard simulations, this is the percent of futures where Buying ends with higher ending net worth than Renting."
                )

            def _fmt_crossover(v, kind: str) -> str:
                if v is None:
                    return "No crossover"
                try:
                    if kind == "money_mo":
                        return _fmt_money(float(v)) + " /mo"
                    if kind == "pctyr":
                        return f"{float(v):.2f}%/yr"
                    if kind == "pct":
                        return f"{float(v):.2f}%"
                    return str(v)
                except Exception:
                    return "No crossover"

            adv = res.get("adv_flips", {}) if isinstance(res, dict) else {}

            def _adv_text(name: str):
                info = adv.get(name, {}) if isinstance(adv, dict) else {}
                val = info.get("value", None) if isinstance(info, dict) else None
                fmt = info.get("fmt", "") if isinstance(info, dict) else ""
                sub = info.get("sub", None) if isinstance(info, dict) else None
                tip = info.get("tooltip", "") if isinstance(info, dict) else ""
                if val is None:
                    txt = "No crossover"
                else:
                    if fmt == "pct":
                        txt = f"{float(val):.2f}%"
                    elif fmt == "pctyr":
                        txt = f"{float(val):.2f}%/yr"
                    else:
                        txt = f"{float(val):.2f}"
                return txt, sub, tip

            fr = res.get("flip_rent")
            fa = res.get("flip_app")
            fm = res.get("flip_rate")
            frr = res.get("flip_renter_ret")

            flip_rent_txt = _fmt_crossover(fr, "money_mo")
            flip_app_txt = _fmt_crossover(fa, "pctyr")
            flip_rate_txt = _fmt_crossover(fm, "pct")  # mortgage rate is nominal annual % (not “%/yr”)
            flip_renter_txt = _fmt_crossover(frr, "pctyr")

            flip_buyer_txt, flip_buyer_sub, flip_buyer_tip = _adv_text("Flip buyer return")
            flip_down_txt, flip_down_sub, flip_down_tip = _adv_text("Flip down payment")
            flip_sell_txt, flip_sell_sub, flip_sell_tip = _adv_text("Flip selling cost")
            flip_rinf_txt, flip_rinf_sub, flip_rinf_tip = _adv_text("Flip rent inflation")
            flip_ptax_txt, flip_ptax_sub, flip_ptax_tip = _adv_text("Flip property tax rate")
            flip_maint_txt, flip_maint_sub, flip_maint_tip = _adv_text("Flip maintenance rate")
            flip_repair_txt, flip_repair_sub, flip_repair_tip = _adv_text("Flip repair costs rate")

            _mode_txt = "Monte Carlo" if _use_mc else "Deterministic"
            _mc_txt = ""
            if _use_mc:
                try:
                    _mc_txt = f"{_mc_metric} • {int(_mc_sims)} sims" if (_mc_metric and _mc_sims) else "Monte Carlo"
                except Exception:
                    _mc_txt = "Monte Carlo"

            mode_row = f"""
            <div class="bias-pill-row">
              <div class="bias-pill">
                <div class="k">Mode {rbv_help_html("Choose how the dashboard measures who wins. Deterministic is fast and uses one run. Monte Carlo uses many simulated futures.", small=True)}</div>
                <div class="v">{html.escape(_mode_txt)}</div>
                {f"<div class='s' style='color:rgba(148,163,184,0.92); font-weight:650;'>{html.escape(_mc_txt)}</div>" if _mc_txt else ""}
              </div>
              <div class="bias-pill">
                <div class="k">Metric {rbv_help_html("For dollar metrics, Δ means Buyer net worth minus Renter net worth at the horizon. In Win% mode, the flip-point targets a 50/50 win chance.", small=True)}</div>
                <div class="v">{html.escape(_metric)}</div>
              </div>
            </div>
            """

            current_pill = f"""
              <div class="bias-pill bias-current {cur_class}">
                <div class="k">{html.escape(current_label)} {rbv_help_html(current_tip, small=True)}</div>
                <div class="v">{html.escape(current_value)}</div>
                <div class="s">{html.escape(current_sub)}</div>
              </div>
            """

            def _pill(label: str, value: str, tip: str = "", sub=None) -> str:
                tip_html = rbv_help_html(tip, small=True) if tip else ""
                sub_html = (
                    f"<div class='s' style='color:rgba(148,163,184,0.92); font-weight:650;'>{html.escape(str(sub))}</div>"
                    if sub
                    else ""
                )
                return (
                    f"<div class='bias-pill'><div class='k'>{html.escape(label)} {tip_html}</div><div class='v'>{html.escape(value)}</div>{sub_html}</div>"
                )

            _flip_cards = [
                _pill(
                    "Flip rent",
                    flip_rent_txt,
                    "Approximate monthly rent that would make the result a tie. If it says ‘No crossover’, the tie wasn’t found within the search range.",
                ),
                _pill(
                    "Flip home appreciation",
                    flip_app_txt,
                    "Approximate annual home appreciation rate that would make the result a tie for the chosen metric.",
                ),
                _pill(
                    "Flip mortgage rate",
                    flip_rate_txt,
                    "Approximate mortgage rate that would make the result a tie (holding other inputs constant).",
                ),
                _pill(
                    "Flip renter return",
                    flip_renter_txt,
                    "Approximate renter investment return that would make the result a tie (holding other inputs constant).",
                ),
            ]

            _adv_specs = [
                ("Flip buyer return", flip_buyer_txt, flip_buyer_tip or "Approximate buyer investment return that would make the result a tie (holding other inputs constant).", flip_buyer_sub),
                ("Flip down payment", flip_down_txt, flip_down_tip or "Approximate down payment percentage (of purchase price) that would make the result a tie.", flip_down_sub),
                ("Flip selling cost", flip_sell_txt, flip_sell_tip or "Approximate total selling cost rate (as % of sale price) that would make the result a tie.", flip_sell_sub),
                ("Flip rent inflation", flip_rinf_txt, flip_rinf_tip or "Approximate annual rent inflation rate that would make the result a tie.", flip_rinf_sub),
                ("Flip property tax rate", flip_ptax_txt, flip_ptax_tip or "Approximate property tax rate (as % of home value per year) that would make the result a tie.", flip_ptax_sub),
                ("Flip maintenance rate", flip_maint_txt, flip_maint_tip or "Approximate maintenance rate (as % of home value per year) that would make the result a tie.", flip_maint_sub),
                ("Flip repairs rate", flip_repair_txt, flip_repair_tip or "Approximate annual repair costs rate (as % of home value per year) that would make the result a tie.", flip_repair_sub),
            ]

            _hidden_adv_no_x = 0
            for _label, _val_txt, _tip, _sub in _adv_specs:
                # Keep the panel focused on actionable flips by hiding advanced cards with no found crossover.
                # Core flips remain always visible above.
                if str(_val_txt).strip().lower() == "no crossover":
                    _hidden_adv_no_x += 1
                    continue
                _flip_cards.append(_pill(_label, _val_txt, _tip, sub=_sub))

            flips_grid = "<div class='bias-flip-grid'>" + current_pill + "".join(_flip_cards) + "</div>"
            st.markdown(mode_row + flips_grid, unsafe_allow_html=True)
            if _hidden_adv_no_x > 0:
                st.caption(f"Showing actionable flip-points. Hidden advanced flips with no crossover in current range: {_hidden_adv_no_x}.")
        except Exception:
            pass

        # Context: rent yield + return spread
        try:
            _price = float(price)
            _rent = float(rent)
            rent_yield = (_rent * 12.0 / _price * 100.0) if _price > 0 else 0.0
        except Exception:
            rent_yield = 0.0
        try:
            spread = float(st.session_state.renter_ret) - float(st.session_state.apprec)
        except Exception:
            spread = 0.0

        st.markdown(
                f"""<div class="note-box">
    <b>What this tab tells you</b>
    <ul style="margin:6px 0 6px 18px;">
      <li><b>Flip-points</b>: the value where Buying and Renting would be tied (for the selected metric).</li>
      <li><b>Sensitivity</b>: which inputs move the result the most near your current settings.</li>
    </ul>
    <b>Quick context:</b> With your inputs, annual rent is about <b>{rent_yield:.2f}%</b> of the home price. Also, your portfolio is assumed to grow about <b>{spread:.2f}%/yr</b> faster than the home price. Those gaps often explain why one side is ahead.
    </div>""",
                unsafe_allow_html=True,
            )


        st.markdown(f"""### Sensitivity chart {rbv_help_html("Each bar shows how the Buy vs Rent gap changes when we slightly increase ONE input, holding everything else constant. Bigger bars = that input matters more around your current settings.", small=True)}""", unsafe_allow_html=True)
        st.markdown(
                """<div class="note-box">
    <b>How to read the chart:</b>
    <ul style="margin:6px 0 0 18px;">
      <li>Bars to the <b>right</b> mean the change makes <b>Buying</b> look better vs renting.</li>
      <li>Bars to the <b>left</b> mean the change makes <b>Renting</b> look better vs buying.</li>
      <li>To see what matters most, the dashboard makes a small “what-if” change to each input. For rates/returns/inflation we nudge it by <b>0.5% per year</b> (example: 5.0% → 5.5%).</li>
    </ul>
    </div>""",
                unsafe_allow_html=True,
            )



        # Single graph: tornado bar chart + readable details table (top 8)
        try:
            sens_num = res.get("sens_df")
            if sens_num is not None:
                sens_num = sens_num.copy()
                sens_num = sens_num.dropna(subset=["Impact"])
                if not sens_num.empty:
                    _is_money = str(res.get("value_kind", "money")) == "money"
                    chart_title = "What matters most (near your current inputs)"

                    if _is_money:
                        x_axis_title = "Change in result ($, Buyer − Renter)"
                        x_vals = sens_num["Impact"]
                        tick_fmt = ",.0f"
                        bar_text = [f"${v:,.0f}" for v in x_vals]
                    else:
                        x_axis_title = "Change in win chance (% out of 100)"
                        x_vals = sens_num["Impact"] * 100.0
                        tick_fmt = ",.1f"
                        bar_text = [f"{v:+.2f} pp" for v in x_vals]

                    fig = go.Figure()
                    colors = [(BUY_COLOR if float(v) >= 0 else RENT_COLOR) for v in sens_num['Impact'].tolist()]
                    fig.add_bar(
                        x=x_vals,
                        y=sens_num["Input"],
                        orientation="h",
                        marker=dict(color=colors),
                        text=bar_text,
                        textposition="outside",
                        cliponaxis=False,
                    )
                    fig.update_layout(
                        template=pio.templates.default,
                        height=440,
                        margin=dict(l=10, r=30, t=50, b=10),
                        title=chart_title,
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#E6EDF7"),
                    )
                    fig.update_xaxes(title_text=x_axis_title, gridcolor="rgba(255,255,255,0.10)", tickformat=tick_fmt)
                    fig.update_yaxes(gridcolor="rgba(255,255,255,0.06)", autorange="reversed")
                    fig.add_vline(x=0, line_width=1, line_dash='dash', line_color='rgba(255,255,255,0.25)')
                    st.plotly_chart(_rbv_apply_plotly_theme(fig, height=420), use_container_width=True)

                    with st.expander("Sensitivity details", expanded=False):
                        _tbl = sens_num.copy()
                        if _is_money:
                            _tbl["Impact"] = _tbl["Impact"].map(lambda v: f"${float(v):,.0f}")
                        else:
                            _tbl["Impact"] = (_tbl["Impact"] * 100.0).map(lambda v: f"{float(v):+.2f} pp")
                        _tbl = _tbl[["Input", "Increase By", "Impact"]]
                        st.dataframe(_tbl, use_container_width=True, hide_index=True)
                else:
                    st.info("Sensitivity results are empty for this scenario.")
        except Exception:
            pass
# ------------------------------
# Self-tests
# ------------------------------
def _run_transfer_tax_self_tests() -> list[str]:
    errs = []
    def _assert_close(name, got, exp, tol=1e-6):
        if abs(got-exp) > tol:
            errs.append(f"{name}: got {got:.2f}, expected {exp:.2f}")

    # Ontario example: $500k, first-time (rebate 4k), non-Toronto
    # LTT: 55k*0.005=275; 195k*0.01=1950; 150k*0.015=2250; 100k*0.02=2000 => 6475 - 4000 = 2475
    _assert_close("ON 500k FTHB", calc_transfer_tax("Ontario", 500_000, True, False)["total"], 2475.0)

    # BC example: $500k => 200k*1% + 300k*2% = 8000
    _assert_close("BC 500k", calc_transfer_tax("British Columbia", 500_000, False, False)["total"], 8000.0)

    # MB example: $250k => 0 on 30k; 60k*0.5%=300; 60k*1%=600; 50k*1.5%=750; 50k*2%=1000 => 2650
    _assert_close("MB 250k", calc_transfer_tax("Manitoba", 250_000, False, False)["total"], 2650.0)

    # AB example: $400k => base 50 + 5*ceil(400k/5000)=50+5*80=450
    _assert_close("AB 400k", calc_transfer_tax("Alberta", 400_000, False, False)["total"], 450.0)

    # SK example: $400k => 25 + (400k-6300)*0.4% = 25 + 393700*0.004 = 1599.8
    _assert_close("SK 400k", calc_transfer_tax("Saskatchewan", 400_000, False, False)["total"], 1599.8)

    # NB example: 1% of 300k => 3000
    _assert_close("NB 300k", calc_transfer_tax("New Brunswick", 300_000, False, False)["total"], 3000.0)

    return errs

if __name__ == "__main__":
    import os
    if os.environ.get("RUN_SELF_TESTS", "0") == "1":
        errors = _run_transfer_tax_self_tests()
        if errors:
            raise SystemExit("Self-tests failed:\n" + "\n".join(errors))
        print("All self-tests passed.")

# --- Tooltip hotfix override (v138) ---
# Ensures sidebar help tooltips are fully opaque, padded, and above other UI layers.
try:
    import streamlit as st  # already imported in Streamlit runtime
except Exception:
    pass


# --- Phase 3C: Simulation Diagnostics (collapsed; correctness-first) ---
try:
    diag = st.session_state.get("_rbv_diag", [])
    with st.expander("Simulation Diagnostics", expanded=False):
        if not diag:
            st.caption("No diagnostics recorded for this run.")
        else:
            for item in diag:
                lvl = str(item.get("level", "INFO")).upper()
                title = str(item.get("title", "")).strip()
                detail = str(item.get("detail", "")).strip()
                pill_bg = _rbv_rgba(BUY_COLOR, 0.16) if lvl == "OK" else (_rbv_rgba(RENT_COLOR, 0.16) if lvl == "WARN" else "rgba(255,255,255,0.10)")
                pill_bd = _rbv_rgba(BUY_COLOR, 0.35) if lvl == "OK" else (_rbv_rgba(RENT_COLOR, 0.35) if lvl == "WARN" else "rgba(255,255,255,0.18)")
                pill_tx = BUY_COLOR if lvl == "OK" else (RENT_COLOR if lvl == "WARN" else "#F8FAFC")
                st.markdown(
                    f"""
<div style="display:flex; gap:10px; align-items:flex-start; margin: 6px 0;">
  <div style="min-width:54px; text-align:center; font-weight:800; font-size:12px; letter-spacing:0.4px;\
              color:{pill_tx}; background:{pill_bg}; border:1px solid {pill_bd}; border-radius:999px; padding:4px 10px;">
    {html.escape(lvl)}
  </div>
  <div style="flex:1;">
    <div style="color:#E6EDF7; font-weight:700;">{html.escape(title)}</div>
    {f'<div style="color:#9A9A9A; font-size:12px; margin-top:2px;">{html.escape(detail)}</div>' if detail else ''}
  </div>
</div>
""",
                    unsafe_allow_html=True,
                )

        hm = st.session_state.get("_rbv_last_heatmap", None)
        if isinstance(hm, dict) and hm.get("metric"):
            st.caption(f"Last heatmap metric: {hm.get('metric')}")
except Exception:
    pass


# --- Public release: Export / Share ---
try:
    with st.expander("Export / Share", expanded=False):
        try:
            _payload = _rbv_make_scenario_payload()
            _json = json.dumps(_payload, indent=2, default=str)
            try:
                st.download_button(
                    "Download active snapshot (.json)",
                    data=_json,
                    file_name="rbv_scenario_active.json",
                    mime="application/json",
                    use_container_width=True,
                    type="primary",
                )
            except TypeError:
                st.download_button(
                    "Download active snapshot (.json)",
                    data=_json,
                    file_name="rbv_scenario_active.json",
                    mime="application/json",
                    use_container_width=True,
                )

            # PR11: explicit JSON snapshot exports for compare slots (A/B), if present.
            for _slot in ("A", "B"):
                _slot_payload = st.session_state.get(_rbv_compare_slot_key(_slot))
                if not isinstance(_slot_payload, dict):
                    continue
                _slot_json = json.dumps(_slot_payload, indent=2, default=str)
                st.download_button(
                    f"Download Scenario {_slot} snapshot (.json)",
                    data=_slot_json,
                    file_name=f"rbv_scenario_{_slot}.json",
                    mime="application/json",
                    use_container_width=True,
                )
        except Exception:
            pass

        # PR11: explicit CSV outputs export (not only inside the ZIP bundle).
        try:
            if isinstance(df, pd.DataFrame) and len(df) > 0:
                st.download_button(
                    "Download core outputs (.csv)",
                    data=df.to_csv(index=False),
                    file_name="rbv_core_outputs.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
        except Exception:
            pass

        # PR11: compare export bundle + CSVs (available after rendering the A/B compare preview once).
        try:
            _cmp = st.session_state.get("_rbv_compare_last_export")
            if isinstance(_cmp, dict):
                _metrics_rows = list(_cmp.get("metrics_rows") or [])
                _diff_rows = list(_cmp.get("state_diff_rows") or [])
                _payload_a = _cmp.get("payload_a") if isinstance(_cmp.get("payload_a"), dict) else None
                _payload_b = _cmp.get("payload_b") if isinstance(_cmp.get("payload_b"), dict) else None
                _cmp_meta = dict(_cmp.get("meta") or {})

                _cmp_json = json.dumps(
                    build_compare_export_payload(
                        payload_a=_payload_a,
                        payload_b=_payload_b,
                        metric_rows=_metrics_rows,
                        state_diff_rows=_diff_rows,
                        meta=_cmp_meta,
                    ),
                    indent=2,
                    default=str,
                )
                st.download_button(
                    "Download compare export (.json)",
                    data=_cmp_json,
                    file_name="rbv_compare_export.json",
                    mime="application/json",
                    use_container_width=True,
                )
                st.download_button(
                    "Download compare terminal metrics (.csv)",
                    data=compare_metric_rows_to_csv_text(_metrics_rows),
                    file_name="rbv_compare_terminal_metrics.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
                st.download_button(
                    "Download compare changed inputs (.csv)",
                    data=scenario_state_diff_rows_to_csv_text(_diff_rows),
                    file_name="rbv_compare_changed_inputs.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
                if isinstance(_cmp.get("a_timeseries_csv"), str):
                    st.download_button(
                        "Download Scenario A compare timeseries (.csv)",
                        data=_cmp.get("a_timeseries_csv"),
                        file_name="rbv_compare_A_timeseries.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
                if isinstance(_cmp.get("b_timeseries_csv"), str):
                    st.download_button(
                        "Download Scenario B compare timeseries (.csv)",
                        data=_cmp.get("b_timeseries_csv"),
                        file_name="rbv_compare_B_timeseries.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
                st.caption("Compare exports are generated from the latest rendered A/B preview on this session.")
        except Exception:
            pass

        try:
            _bundle = _rbv_build_results_bundle_bytes(df, close_cash=close_cash, m_pmt=m_pmt, win_pct=win_pct)
            _ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            try:
                st.download_button(
                    "Download results bundle (.zip)",
                    data=_bundle,
                    file_name=f"rbv_results_{_ts}.zip",
                    mime="application/zip",
                    use_container_width=True,
                    type="primary",
                )
            except TypeError:
                st.download_button(
                    "Download results bundle (.zip)",
                    data=_bundle,
                    file_name=f"rbv_results_{_ts}.zip",
                    mime="application/zip",
                    use_container_width=True,
                )
            st.caption("Includes scenario JSON, core timeseries, last heatmap matrix (if computed), last bias dashboard outputs (if computed), and diagnostics snapshot.")
        except Exception:
            st.caption("Run a simulation first to enable exports.")
except Exception:
    pass

# --- FINAL THEME OVERRIDE (Azure B) ---
# Last-write-wins to prevent silent regressions across Streamlit/BaseWeb versions.
try:
    import streamlit as st  # already imported in Streamlit runtime
except Exception:
    pass
