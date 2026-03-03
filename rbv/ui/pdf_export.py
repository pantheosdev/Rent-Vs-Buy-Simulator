"""Helpers for orchestrating rich PDF export attempts."""

from __future__ import annotations

from typing import Any, Callable

import pandas as pd


def build_report_context(
    state: dict[str, Any],
    meta: dict[str, Any],
    *,
    compare_export: dict[str, Any] | None,
    version_line: str,
    generated_at: str,
) -> dict[str, list[tuple[str, str]]]:
    ctx: dict[str, list[tuple[str, str]]] = {
        "meta": [
            ("Generated", str(generated_at)),
            ("Version", str(version_line)),
            ("Scenario hash", str(meta.get("scenario_hash", "n/a"))),
        ],
        "assumptions": [
            ("First-time buyer", "Yes" if bool(state.get("first_time", False)) else "No"),
            ("Toronto municipal tax", "Yes" if bool(state.get("toronto", False)) else "No"),
            ("Simulation mode", str(state.get("sim_mode", "—"))),
            ("Monte Carlo sims", str(state.get("num_sims", "—"))),
            ("Budget mode", "Enabled" if bool(state.get("budget_enabled", False)) else "Disabled"),
            ("Crisis mode", "Enabled" if bool(state.get("crisis_enabled", False)) else "Disabled"),
        ],
    }
    if isinstance(compare_export, dict):
        metrics_rows = list(compare_export.get("metrics_rows") or [])
        diff_rows = list(compare_export.get("state_diff_rows") or [])
        meta_cmp = dict(compare_export.get("meta") or {})
        ctx["compare"] = [
            ("Compare metrics rows", str(len(metrics_rows))),
            ("Compare changed-input rows", str(len(diff_rows))),
            ("Scenario A hash", str(meta_cmp.get("a_hash", ""))),
            ("Scenario B hash", str(meta_cmp.get("b_hash", ""))),
        ]
    return ctx


def try_build_rich_pdf(
    df: pd.DataFrame,
    state: dict[str, Any],
    meta: dict[str, Any],
    *,
    compare_export: dict[str, Any] | None,
    version_line: str,
    generated_at: str,
    bias_result: dict[str, Any] | None,
    close_cash: float | None,
    monthly_pmt: float | None,
    win_pct: float | None,
    build_pdf_report: Callable[..., bytes],
) -> tuple[bytes | None, str | None]:
    def _pick(*keys: str, default: Any = None) -> Any:
        for k in keys:
            if k in state and state.get(k) is not None:
                return state.get(k)
        return default

    try:
        context = build_report_context(
            state,
            meta,
            compare_export=compare_export,
            version_line=version_line,
            generated_at=generated_at,
        )
    except (TypeError, ValueError, KeyError, AttributeError):
        context = {}

    rich_cfg = {
        "years": _pick("years", default=25),
        "province": _pick("province", default="Ontario"),
        "price": _pick("price", default=0.0),
        "down": _pick("down", default=0.0),
        "rent": _pick("rent", default=0.0),
        "rate": _pick("rate", default=0.0),
        "amort": _pick("amort", default=25),
        "p_tax_rate_pct": _pick("p_tax_rate_pct", "property_tax_rate_annual", default=0.0),
        "maint_rate_pct": _pick("maint_rate_pct", "maintenance_rate_annual", default=0.0),
        "repair_rate_pct": _pick("repair_rate_pct", "repair_rate_annual", default=0.0),
        "sell_cost_pct": _pick("sell_cost_pct", "selling_cost_pct", default=0.0),
        "condo": _pick("condo", "condo_fees", "condo_fee_monthly", default=0.0),
        "h_ins": _pick("h_ins", "home_ins", "home_insurance_monthly", default=0.0),
        "r_ins": _pick("r_ins", "renter_ins", "rent_insurance_monthly", default=0.0),
        "rent_inf": _pick("rent_inf", "rent_inflation_rate_annual", default=0.0),
        "general_inf": _pick("general_inf", "general_inflation_rate_annual", default=0.0),
        "moving_cost": _pick("moving_cost", default=0.0),
        "moving_freq": _pick("moving_freq", default=None),
        "r_util": _pick("r_util", default=0.0),
        "o_util": _pick("o_util", default=0.0),
    }

    try:
        pdf_bytes = build_pdf_report(
            df,
            rich_cfg,
            buyer_ret_pct=float(_pick("buyer_ret", default=7.0) or 7.0),
            renter_ret_pct=float(_pick("renter_ret", default=7.0) or 7.0),
            apprec_pct=float(_pick("apprec", default=3.0) or 3.0),
            close_cash=close_cash,
            monthly_pmt=monthly_pmt,
            win_pct=win_pct,
            scenario_name=str(_pick("scenario_select", default="Custom Scenario") or "Custom Scenario"),
            bias_result=bias_result,
            report_context=context,
        )
        if isinstance(pdf_bytes, (bytes, bytearray)) and len(pdf_bytes) > 0:
            return bytes(pdf_bytes), None
        return None, "Rich PDF renderer returned no data."
    except (ImportError, RuntimeError, TypeError, ValueError) as exc:
        return None, f"Rich PDF renderer failed: {exc}"
