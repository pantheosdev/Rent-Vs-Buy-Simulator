"""UI defaults and economic scenario presets.

This module is intentionally free of Streamlit imports so QA can validate that
first-load defaults match the selected preset (single source of truth).
"""

from __future__ import annotations

from typing import Dict, Any, MutableMapping, List

# Economic scenario presets (only includes parameters that should shift with the scenario).
PRESETS: Dict[str, Dict[str, float]] = {
    "Baseline": {
        "rate": 4.75,
        "apprec": 3.5,
        "general_inf": 2.5,
        "rent_inf": 2.5,
        "buyer_ret": 7.0,
        "renter_ret": 7.0,
    },
    "High Inflation": {
        "rate": 7.5,
        "apprec": 5.0,
        "general_inf": 4.5,
        "rent_inf": 5.0,
        "buyer_ret": 8.0,
        "renter_ret": 8.0,
    },
    "Stagnation": {
        "rate": 3.5,
        "apprec": 1.0,
        "general_inf": 1.5,
        "rent_inf": 1.5,
        "buyer_ret": 4.0,
        "renter_ret": 4.0,
    },
}


CITY_PRESET_CUSTOM = "Custom"

# City presets (R3 preview): optional starting values for location-specific scenarios.
# These are intentionally conservative starter defaults and are fully user-editable after apply.
CITY_PRESETS: Dict[str, Dict[str, Any]] = {
    "Toronto (ON) · Condo": {
        "province": "Ontario",
        "toronto": True,
        "price": 850000.0,
        "down": 170000.0,
        "rent": 3200.0,
        "p_tax_rate_pct": 0.66,
        "condo": 650.0,
        "o_util": 150.0,
        "r_util": 120.0,
    },
    "Toronto (ON) · Detached": {
        "province": "Ontario",
        "toronto": True,
        "price": 1250000.0,
        "down": 250000.0,
        "rent": 4100.0,
        "p_tax_rate_pct": 0.66,
        "condo": 0.0,
        "o_util": 260.0,
        "r_util": 150.0,
    },
    "Vancouver (BC) · Condo": {
        "province": "British Columbia",
        "toronto": False,
        "price": 900000.0,
        "down": 180000.0,
        "rent": 3100.0,
        "p_tax_rate_pct": 0.30,
        "condo": 575.0,
        "o_util": 140.0,
        "r_util": 110.0,
    },
    "Calgary (AB) · Detached": {
        "province": "Alberta",
        "toronto": False,
        "price": 650000.0,
        "down": 130000.0,
        "rent": 2550.0,
        "p_tax_rate_pct": 0.75,
        "condo": 0.0,
        "o_util": 240.0,
        "r_util": 130.0,
    },
    "Montreal (QC) · Condo": {
        "province": "Quebec",
        "toronto": False,
        "price": 600000.0,
        "down": 120000.0,
        "rent": 2350.0,
        "p_tax_rate_pct": 0.70,
        "condo": 400.0,
        "o_util": 140.0,
        "r_util": 110.0,
    },
}


def city_preset_options() -> List[str]:
    return [CITY_PRESET_CUSTOM, *list(CITY_PRESETS.keys())]


def city_preset_metadata(name: str | None) -> Dict[str, Any]:
    """Parse a preset display name into metadata for filtering/polish UI."""
    k = str(name or "").strip()
    vals = city_preset_values(k) or {}
    left, sep, right = k.partition("·")
    left = left.strip()
    right = right.strip()
    city = left
    prov_code = ""
    prov_long = str(vals.get("province", "") or "")
    if "(" in left and ")" in left:
        try:
            city = left.split("(", 1)[0].strip()
            prov_code = left.split("(", 1)[1].split(")", 1)[0].strip().upper()
        except Exception:
            pass
    if not prov_code:
        _map = {
            "Ontario": "ON",
            "British Columbia": "BC",
            "Alberta": "AB",
            "Quebec": "QC",
            "Nova Scotia": "NS",
            "New Brunswick": "NB",
            "Prince Edward Island": "PE",
            "Manitoba": "MB",
            "Saskatchewan": "SK",
            "Newfoundland and Labrador": "NL",
        }
        prov_code = _map.get(prov_long, "")
    housing_type = right or ("Condo" if float(vals.get("condo", 0.0) or 0.0) > 0 else "Detached")
    return {
        "name": k,
        "city": city,
        "province": prov_long,
        "province_code": prov_code,
        "housing_type": housing_type,
        "is_toronto": bool(vals.get("toronto", False)) or city.lower() == "toronto",
    }


def city_preset_filter_region_options() -> List[str]:
    return ["All regions", "Ontario", "West (BC/AB)", "Quebec", "Toronto only"]


def city_preset_filter_type_options() -> List[str]:
    return ["All homes", "Condo", "Detached"]


def city_preset_filtered_options(*, region: str | None = None, home_type: str | None = None, query: str | None = None) -> List[str]:
    """Return filtered preset options with Custom always first."""
    region = str(region or "All regions")
    home_type = str(home_type or "All homes")
    q = str(query or "").strip().lower()
    out: List[str] = [CITY_PRESET_CUSTOM]
    for name in CITY_PRESETS.keys():
        meta = city_preset_metadata(name)
        if region == "Ontario" and str(meta.get("province")) != "Ontario":
            continue
        if region == "West (BC/AB)" and str(meta.get("province")) not in {"British Columbia", "Alberta"}:
            continue
        if region == "Quebec" and str(meta.get("province")) != "Quebec":
            continue
        if region == "Toronto only" and not bool(meta.get("is_toronto")):
            continue
        if home_type == "Condo" and str(meta.get("housing_type")) != "Condo":
            continue
        if home_type == "Detached" and str(meta.get("housing_type")) != "Detached":
            continue
        if q:
            hay = " ".join([
                str(name),
                str(meta.get("city", "")),
                str(meta.get("province", "")),
                str(meta.get("province_code", "")),
                str(meta.get("housing_type", "")),
            ]).lower()
            if q not in hay:
                continue
        out.append(str(name))
    return out


def city_preset_preview_summary_lines(name: str | None, *, max_items: int = 5) -> List[str]:
    vals = city_preset_values(name)
    if not vals:
        return []
    meta = city_preset_metadata(name)
    items = [
        f"Region: {meta.get('city')} ({meta.get('province_code') or meta.get('province')})",
        f"Type: {meta.get('housing_type')}",
        f"Toronto MLTT: {'ON' if bool(vals.get('toronto', False)) else 'OFF'}",
        f"Price: ${float(vals.get('price', 0.0) or 0.0):,.0f}",
        f"Rent: ${float(vals.get('rent', 0.0) or 0.0):,.0f}/mo",
        f"Property tax: {float(vals.get('p_tax_rate_pct', 0.0) or 0.0):.2f}%",
        f"Condo fee: ${float(vals.get('condo', 0.0) or 0.0):,.0f}/mo",
    ]
    return items[: max(1, int(max_items))]


def city_preset_values(name: str | None) -> Dict[str, Any] | None:
    k = str(name or CITY_PRESET_CUSTOM)
    if k == CITY_PRESET_CUSTOM:
        return None
    vals = CITY_PRESETS.get(k)
    return dict(vals) if isinstance(vals, dict) else None


def _city_preset_values_equal(a: Any, b: Any) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return bool(a) is bool(b)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        try:
            return abs(float(a) - float(b)) <= 1e-12
        except Exception:
            return False
    return a == b


def apply_city_preset_values(state: MutableMapping[str, Any], preset_name: str | None) -> List[Dict[str, Any]]:
    """Mutate a mapping with a city preset and return changed fields.

    Returns a list of dict rows: {key, before, after}. If preset is Custom/unknown,
    only the `city_preset` marker is normalized and no field overrides are applied.
    """
    if state is None:
        return []
    name = str(preset_name or CITY_PRESET_CUSTOM)
    vals = city_preset_values(name)
    if not vals:
        try:
            state["city_preset"] = CITY_PRESET_CUSTOM
        except Exception:
            pass
        return []

    patch = dict(vals)
    patch["city_preset"] = name
    # Guardrail: Toronto MLTT toggle is Ontario-only.
    if str(patch.get("province", "") or "") != "Ontario":
        patch["toronto"] = False

    changes: List[Dict[str, Any]] = []
    for k, v_new in patch.items():
        try:
            v_old = state.get(k)
        except Exception:
            v_old = None
        if not _city_preset_values_equal(v_old, v_new):
            changes.append({"key": str(k), "before": v_old, "after": v_new})
        state[k] = v_new
    return changes


def build_city_preset_change_summary(changes: List[Dict[str, Any]], *, max_items: int = 8) -> List[str]:
    """Return compact human-readable summary lines for applied city preset changes."""
    if not isinstance(changes, list) or not changes:
        return []
    labels = {
        "province": "Province",
        "toronto": "Toronto property (MLTT)",
        "price": "Home price",
        "down": "Down payment",
        "rent": "Rent",
        "p_tax_rate_pct": "Property tax (%)",
        "condo": "Condo fee ($/mo)",
        "o_util": "Owner utilities ($/mo)",
        "r_util": "Renter utilities ($/mo)",
        "city_preset": "City preset",
    }

    def _fmt(v: Any) -> str:
        if isinstance(v, bool):
            return "ON" if v else "OFF"
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            x = float(v)
            if abs(x) >= 1000.0 or abs(x).is_integer():
                return f"{x:,.0f}" if abs(x) >= 1000 else f"{x:.0f}"
            if abs(x) < 10.0:
                return f"{x:.2f}".rstrip("0").rstrip(".")
            return f"{x:.1f}".rstrip("0").rstrip(".")
        return str(v)

    out: List[str] = []
    for row in changes[: max(1, int(max_items))]:
        k = str((row or {}).get("key", ""))
        out.append(f"{labels.get(k, k)}: {_fmt((row or {}).get('before'))} → {_fmt((row or {}).get('after'))}")
    if len(changes) > max_items:
        out.append(f"+{len(changes) - int(max_items)} more")
    return out


def build_session_defaults(scenario: str = "Baseline") -> Dict[str, Any]:
    """Return first-load session_state defaults.

    Single source of truth rule:
      - scenario-driven fields must come from PRESETS[scenario]
      - everything else is a stable baseline default

    Notes:
      - This function is used by app.py to seed st.session_state on first load.
      - Keep values JSON-serializable to support scenario export/import.
    """
    if scenario not in PRESETS:
        scenario = "Baseline"

    defaults: Dict[str, Any] = {
        # Core scenario selector
        "scenario_select": scenario,
        "city_preset": CITY_PRESET_CUSTOM,

        # Core horizon + anchors
        "years": 25,
        "price": 800000.0,
        "down": 160000.0,
        "rent": 3000.0,

        # Region / eligibility (must be explicit so scenario export/import is location-correct)
        "province": "Ontario",
        "first_time": True,
        "toronto": False,

        # Mortgage
        "amort": 25,

        # One-time purchase closing costs (editable; do not hardcode in app logic)
        "purchase_legal_fee": 1800.0,
        "home_inspection": 500.0,
        "other_closing_costs": 0.0,

        # Pro realism defaults (additive; do not affect presets)
        "condo_inf": None,                 # Condo fees often outpace CPI; default = CPI + spread
        "condo_inf_mode": "CPI + spread",
        "condo_inf_spread": 1.5,
        "condo_inf_custom": 4.0,
        "canadian_compounding": True,
        "assume_sale_end": True,
        "is_principal_residence": True,
        "investment_tax_mode": "Pre-tax (no investment taxes)",
        "cg_tax_end": 22.5,
        "show_liquidation_view": True,
        "home_sale_legal_fee": 2000.0,

        # Keyed inputs added in v167 hotfix (improves cache correctness + avoids globals() reads)
        "use_volatility": False,
        "ret_std_pct": 15.0,
        "apprec_std_pct": 5.0,
        "ret_std_pct_ui": 15.0,
        "apprec_std_pct_ui": 5.0,
        "market_corr_input": 0.8,
        "sell_cost_pct": 5.0,
        "p_tax_rate_pct": 1.00,
        "maint_rate_pct": 1.0,
        "repair_rate_pct": 0.5,

        # Optional buyer - special assessment shock
        "special_assessment_amount": 0.0,
        "special_assessment_year": 0,
        "special_assessment_month_in_year": 1,

        # Tax sensitivity (Phase 4, opt-in)
        "expert_mode": False,
        "cg_inclusion_policy": "Current (50% inclusion)",
        "cg_inclusion_threshold": 250000.0,
        "reg_shelter_enabled": False,
        "reg_initial_room": 0.0,
        "reg_annual_room": 0.0,
    }

    # Apply the chosen preset last so it *always* wins for scenario-driven keys.
    defaults.update(PRESETS[scenario])

    return defaults
