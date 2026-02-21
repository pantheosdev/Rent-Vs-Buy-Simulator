"""UI defaults and economic scenario presets.

This module is intentionally free of Streamlit imports so QA can validate that
first-load defaults match the selected preset (single source of truth).
"""

from __future__ import annotations

from typing import Dict, Any

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

        # Core horizon + anchors
        "years": 25,
        "price": 800000.0,
        "down": 160000.0,
        "rent": 3000.0,

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
