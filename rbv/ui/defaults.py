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
    # Ontario
    "Toronto (ON) · Condo": {
        "id": "toronto_on_condo",
        "version": 1,
        "region": "Ontario",
        "home_type": "Condo",
        "province": "Ontario",
        "province_code": "ON",
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
        "id": "toronto_on_detached",
        "version": 1,
        "region": "Ontario",
        "home_type": "Detached",
        "province": "Ontario",
        "province_code": "ON",
        "toronto": True,
        "price": 1250000.0,
        "down": 250000.0,
        "rent": 4100.0,
        "p_tax_rate_pct": 0.66,
        "condo": 0.0,
        "o_util": 260.0,
        "r_util": 150.0,
    },
    "Ottawa (ON) · Condo": {
        "id": "ottawa_on_condo",
        "version": 1,
        "region": "Ontario",
        "home_type": "Condo",
        "province": "Ontario",
        "province_code": "ON",
        "toronto": False,
        "price": 550000.0,
        "down": 110000.0,
        "rent": 2200.0,
        "p_tax_rate_pct": 1.05,
        "condo": 480.0,
        "o_util": 150.0,
        "r_util": 120.0,
    },
    "Ottawa (ON) · Detached": {
        "id": "ottawa_on_detached",
        "version": 1,
        "region": "Ontario",
        "home_type": "Detached",
        "province": "Ontario",
        "province_code": "ON",
        "toronto": False,
        "price": 825000.0,
        "down": 165000.0,
        "rent": 3000.0,
        "p_tax_rate_pct": 1.05,
        "condo": 0.0,
        "o_util": 240.0,
        "r_util": 140.0,
    },
    "Mississauga (ON) · Condo": {
        "id": "mississauga_on_condo",
        "version": 1,
        "region": "Ontario",
        "home_type": "Condo",
        "province": "Ontario",
        "province_code": "ON",
        "toronto": False,
        "price": 750000.0,
        "down": 150000.0,
        "rent": 2800.0,
        "p_tax_rate_pct": 0.75,
        "condo": 600.0,
        "o_util": 150.0,
        "r_util": 120.0,
    },
    "Hamilton (ON) · Detached": {
        "id": "hamilton_on_detached",
        "version": 1,
        "region": "Ontario",
        "home_type": "Detached",
        "province": "Ontario",
        "province_code": "ON",
        "toronto": False,
        "price": 900000.0,
        "down": 180000.0,
        "rent": 3200.0,
        "p_tax_rate_pct": 1.05,
        "condo": 0.0,
        "o_util": 250.0,
        "r_util": 145.0,
    },
    # West (BC/AB)
    "Vancouver (BC) · Condo": {
        "id": "vancouver_bc_condo",
        "version": 1,
        "region": "West (BC/AB)",
        "home_type": "Condo",
        "province": "British Columbia",
        "province_code": "BC",
        "toronto": False,
        "price": 900000.0,
        "down": 180000.0,
        "rent": 3100.0,
        "p_tax_rate_pct": 0.30,
        "condo": 575.0,
        "o_util": 140.0,
        "r_util": 110.0,
    },
    "Vancouver (BC) · Detached": {
        "id": "vancouver_bc_detached",
        "version": 1,
        "region": "West (BC/AB)",
        "home_type": "Detached",
        "province": "British Columbia",
        "province_code": "BC",
        "toronto": False,
        "price": 1650000.0,
        "down": 330000.0,
        "rent": 5200.0,
        "p_tax_rate_pct": 0.30,
        "condo": 0.0,
        "o_util": 260.0,
        "r_util": 150.0,
    },
    "Victoria (BC) · Condo": {
        "id": "victoria_bc_condo",
        "version": 1,
        "region": "West (BC/AB)",
        "home_type": "Condo",
        "province": "British Columbia",
        "province_code": "BC",
        "toronto": False,
        "price": 700000.0,
        "down": 140000.0,
        "rent": 2600.0,
        "p_tax_rate_pct": 0.35,
        "condo": 520.0,
        "o_util": 140.0,
        "r_util": 110.0,
    },
    "Calgary (AB) · Detached": {
        "id": "calgary_ab_detached",
        "version": 1,
        "region": "West (BC/AB)",
        "home_type": "Detached",
        "province": "Alberta",
        "province_code": "AB",
        "toronto": False,
        "price": 650000.0,
        "down": 130000.0,
        "rent": 2550.0,
        "p_tax_rate_pct": 0.75,
        "condo": 0.0,
        "o_util": 240.0,
        "r_util": 130.0,
    },
    "Calgary (AB) · Condo": {
        "id": "calgary_ab_condo",
        "version": 1,
        "region": "West (BC/AB)",
        "home_type": "Condo",
        "province": "Alberta",
        "province_code": "AB",
        "toronto": False,
        "price": 380000.0,
        "down": 76000.0,
        "rent": 1900.0,
        "p_tax_rate_pct": 0.75,
        "condo": 420.0,
        "o_util": 170.0,
        "r_util": 125.0,
    },
    "Edmonton (AB) · Detached": {
        "id": "edmonton_ab_detached",
        "version": 1,
        "region": "West (BC/AB)",
        "home_type": "Detached",
        "province": "Alberta",
        "province_code": "AB",
        "toronto": False,
        "price": 500000.0,
        "down": 100000.0,
        "rent": 2200.0,
        "p_tax_rate_pct": 0.90,
        "condo": 0.0,
        "o_util": 230.0,
        "r_util": 135.0,
    },
    # Quebec
    "Montreal (QC) · Condo": {
        "id": "montreal_qc_condo",
        "version": 1,
        "region": "Quebec",
        "home_type": "Condo",
        "province": "Quebec",
        "province_code": "QC",
        "toronto": False,
        "price": 600000.0,
        "down": 120000.0,
        "rent": 2350.0,
        "p_tax_rate_pct": 0.70,
        "condo": 400.0,
        "o_util": 140.0,
        "r_util": 110.0,
    },
    "Montreal (QC) · Detached": {
        "id": "montreal_qc_detached",
        "version": 1,
        "region": "Quebec",
        "home_type": "Detached",
        "province": "Quebec",
        "province_code": "QC",
        "toronto": False,
        "price": 850000.0,
        "down": 170000.0,
        "rent": 3300.0,
        "p_tax_rate_pct": 0.70,
        "condo": 0.0,
        "o_util": 240.0,
        "r_util": 140.0,
    },
    # Atlantic
    "Halifax (NS) · Condo": {
        "id": "halifax_ns_condo",
        "version": 1,
        "region": "Atlantic (NS/NB/PE/NL)",
        "home_type": "Condo",
        "province": "Nova Scotia",
        "province_code": "NS",
        "toronto": False,
        "price": 450000.0,
        "down": 90000.0,
        "rent": 2100.0,
        "p_tax_rate_pct": 1.20,
        "condo": 420.0,
        "o_util": 170.0,
        "r_util": 125.0,
    },
    "Halifax (NS) · Detached": {
        "id": "halifax_ns_detached",
        "version": 1,
        "region": "Atlantic (NS/NB/PE/NL)",
        "home_type": "Detached",
        "province": "Nova Scotia",
        "province_code": "NS",
        "toronto": False,
        "price": 650000.0,
        "down": 130000.0,
        "rent": 2800.0,
        "p_tax_rate_pct": 1.20,
        "condo": 0.0,
        "o_util": 240.0,
        "r_util": 140.0,
    },
    "Fredericton (NB) · Detached": {
        "id": "fredericton_nb_detached",
        "version": 1,
        "region": "Atlantic (NS/NB/PE/NL)",
        "home_type": "Detached",
        "province": "New Brunswick",
        "province_code": "NB",
        "toronto": False,
        "price": 350000.0,
        "down": 70000.0,
        "rent": 1800.0,
        "p_tax_rate_pct": 1.10,
        "condo": 0.0,
        "o_util": 230.0,
        "r_util": 135.0,
    },
}


_CITY_PRESET_META_KEYS = {"id", "version", "region", "home_type", "province_code"}


def city_preset_options() -> List[str]:
    return [CITY_PRESET_CUSTOM, *list(CITY_PRESETS.keys())]


def city_preset_metadata(name: str | None) -> Dict[str, Any]:
    """Return metadata used for filtering and UI polish.

    Prefer explicit preset metadata (id/version/region/home_type) when present,
    but keep best-effort parsing for backwards compatibility with older presets.
    """
    k = str(name or "").strip()
    vals = city_preset_values(k) or {}

    left, _, right = k.partition("·")
    left = left.strip()
    right = right.strip()

    city = left
    prov_code_from_name = ""
    if "(" in left and ")" in left:
        try:
            city = left.split("(", 1)[0].strip()
            prov_code_from_name = left.split("(", 1)[1].split(")", 1)[0].strip().upper()
        except Exception:
            pass

    prov_long = str(vals.get("province", "") or "").strip()
    prov_code = str(vals.get("province_code", "") or "").strip().upper() or prov_code_from_name

    if not prov_code and prov_long:
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

    home_type = str(vals.get("home_type", "") or "").strip()
    if not home_type:
        home_type = right or ("Condo" if float(vals.get("condo", 0.0) or 0.0) > 0 else "Detached")

    region = str(vals.get("region", "") or "").strip()
    if not region:
        # Back-compat inference if a preset doesn't declare region.
        if prov_long == "Ontario":
            region = "Ontario"
        elif prov_long in {"British Columbia", "Alberta"}:
            region = "West (BC/AB)"
        elif prov_long == "Quebec":
            region = "Quebec"
        elif prov_long in {"Nova Scotia", "New Brunswick", "Prince Edward Island", "Newfoundland and Labrador"}:
            region = "Atlantic (NS/NB/PE/NL)"

    preset_id = str(vals.get("id", "") or "").strip()
    try:
        version = int(vals.get("version")) if vals.get("version") is not None else None
    except Exception:
        version = None

    return {
        "name": k,
        "id": preset_id or None,
        "version": version,
        "region": region or None,
        "city": city,
        "province": prov_long,
        "province_code": prov_code,
        "home_type": home_type,
        # Back-compat key used by some UI callsites
        "housing_type": home_type,
        "is_toronto": bool(vals.get("toronto", False)) or city.lower() == "toronto",
    }


def city_preset_filter_region_options() -> List[str]:
    return [
        "All regions",
        "Ontario",
        "West (BC/AB)",
        "Quebec",
        "Atlantic (NS/NB/PE/NL)",
        "Toronto only",
    ]


def city_preset_filter_type_options() -> List[str]:
    return ["All homes", "Condo", "Detached"]


def city_preset_filtered_options(
    *, region: str | None = None, home_type: str | None = None, query: str | None = None
) -> List[str]:
    """Return filtered preset options with Custom always first."""
    region = str(region or "All regions")
    home_type = str(home_type or "All homes")
    q = str(query or "").strip().lower()
    out: List[str] = [CITY_PRESET_CUSTOM]
    for name in CITY_PRESETS.keys():
        meta = city_preset_metadata(name)

        if region != "All regions":
            if region == "Toronto only":
                if not bool(meta.get("is_toronto")):
                    continue
            else:
                if str(meta.get("region") or "") != region:
                    continue

        if home_type != "All homes" and str(meta.get("housing_type")) != home_type:
            continue

        if q:
            hay = " ".join(
                [
                    str(name),
                    str(meta.get("id", "") or ""),
                    str(meta.get("city", "")),
                    str(meta.get("province", "")),
                    str(meta.get("province_code", "")),
                    str(meta.get("region", "") or ""),
                    str(meta.get("housing_type", "")),
                ]
            ).lower()
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

    patch = {k: v for k, v in dict(vals).items() if str(k) not in _CITY_PRESET_META_KEYS}
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


def city_preset_identity(name: str | None) -> Dict[str, Any] | None:
    """Return stable identity metadata for a preset (or None for Custom/unknown)."""
    vals = city_preset_values(name)
    if not vals:
        return None
    meta = city_preset_metadata(name)
    return {
        "id": meta.get("id"),
        "name": meta.get("name"),
        "version": meta.get("version"),
        "region": meta.get("region"),
        "province": meta.get("province"),
        "province_code": meta.get("province_code"),
        "home_type": meta.get("home_type") or meta.get("housing_type"),
        "is_toronto": bool(meta.get("is_toronto")),
    }


def city_preset_patch_values(name: str | None) -> Dict[str, Any] | None:
    """Return the values that a preset would apply (excluding catalog metadata keys)."""
    vals = city_preset_values(name)
    if not vals:
        return None
    patch = {k: v for k, v in dict(vals).items() if str(k) not in _CITY_PRESET_META_KEYS}
    patch["city_preset"] = str(name or CITY_PRESET_CUSTOM)
    # Guardrail: Toronto MLTT is Ontario-only.
    if str(patch.get("province", "") or "") != "Ontario":
        patch["toronto"] = False
    return patch


def city_preset_overrides_from_state(state: MutableMapping[str, Any] | None, preset_name: str | None) -> Dict[str, Any]:
    """Return {key: current_value} for preset-controlled keys that differ from the preset."""
    if not isinstance(state, dict):
        try:
            state = dict(state or {})
        except Exception:
            return {}
    patch = city_preset_patch_values(preset_name)
    if not patch:
        return {}
    overrides: Dict[str, Any] = {}
    for k, v_preset in patch.items():
        if str(k) == "city_preset":
            continue
        try:
            v_cur = state.get(k)
        except Exception:
            v_cur = None
        if not _city_preset_values_equal(v_cur, v_preset):
            overrides[str(k)] = v_cur
    return overrides


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
        "condo_inf": None,  # Condo fees often outpace CPI; default = CPI + spread
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
