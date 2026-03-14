from __future__ import annotations

import datetime as dt

import pytest

from rbv.core.engine import run_simulation_core
from rbv.core.government_programs import hbp_grace_years
from rbv.core.policy_canada import (
    foreign_buyer_tax_amount,
    foreign_buyer_tax_rate,
    toronto_municipal_non_resident_tax_rate,
)

_BASE_CFG = {
    "years": 5,
    "price": 700_000.0,
    "rent": 2_500.0,
    "down": 140_000.0,
    "rate": 5.0,
    "rent_inf": 0.03,
    "sell_cost": 0.05,
    "p_tax_rate": 0.008,
    "maint_rate": 0.01,
    "repair_rate": 0.005,
    "condo": 0.0,
    "h_ins": 150.0,
    "o_util": 200.0,
    "r_ins": 30.0,
    "r_util": 100.0,
    "moving_cost": 3_000.0,
    "moving_freq": 5,
    "mort": 560_000.0,
    "close": 15_000.0,
    "pst": 0.0,
    "nm": 300,
    "discount_rate": 0.0,
    "tax_r": 0.0,
    "province": "Ontario",
    "first_time": True,
    "new_construction": False,
    "toronto": False,
    "use_volatility": False,
    "num_sims": 1,
    "ret_std": 0.0,
    "apprec_std": 0.0,
    "general_inf": 0.025,
    "condo_inf": 0.0,
    "rate_mode": "Fixed",
    "rate_reset_years_eff": None,
    "rate_reset_to_eff": None,
    "rate_reset_step_pp_eff": 0.0,
    "rate_shock_enabled_eff": False,
    "rate_shock_start_year_eff": 5,
    "rate_shock_duration_years_eff": 5,
    "rate_shock_pp_eff": 0.0,
    "rent_control_enabled": False,
    "rent_control_cap": None,
    "rent_control_frequency_years": 1,
    "assume_sale_end": False,
    "is_principal_residence": True,
    "show_liquidation_view": False,
    "cg_tax_end": 0.0,
    "home_sale_legal_fee": 0.0,
    "special_assessment_amount": 0.0,
    "special_assessment_month": 0,
    "cg_inclusion_policy": "current",
    "cg_inclusion_threshold": 250_000.0,
    "reg_shelter_enabled": False,
    "reg_initial_room": 0.0,
    "reg_annual_room": 0.0,
    "canadian_compounding": True,
    "prop_tax_growth_model": "Hybrid (recommended for Toronto)",
    "prop_tax_hybrid_addon_pct": 0.5,
    "investment_tax_mode": "Pre-tax (no investment taxes)",
}


def _run(extra: dict):
    cfg = {**_BASE_CFG, **extra}
    df, close_cash, pmt, win_pct = run_simulation_core(cfg, 7.0, 7.0, 3.0, False, False, 0.0)
    return df, close_cash, pmt, win_pct


def test_ontario_nrst_rate_changes_on_2022_10_25() -> None:
    assert foreign_buyer_tax_rate("Ontario", dt.date(2022, 10, 24)) == pytest.approx(0.20)
    assert foreign_buyer_tax_rate("Ontario", dt.date(2022, 10, 25)) == pytest.approx(0.25)


def test_toronto_mnrst_applies_from_2025_01_01() -> None:
    assert toronto_municipal_non_resident_tax_rate(
        "Ontario", toronto_property=True, asof_date=dt.date(2024, 12, 31)
    ) == pytest.approx(0.0)
    assert toronto_municipal_non_resident_tax_rate(
        "Ontario", toronto_property=True, asof_date=dt.date(2025, 1, 1)
    ) == pytest.approx(0.10)
    assert foreign_buyer_tax_amount(
        1_000_000.0, "Ontario", dt.date(2025, 1, 15), toronto_property=True
    ) == pytest.approx(350_000.0)


def test_hbp_grace_years_temp_relief_window() -> None:
    assert hbp_grace_years(dt.date(2021, 12, 31)) == 2
    assert hbp_grace_years(dt.date(2022, 1, 1)) == 5
    assert hbp_grace_years(dt.date(2025, 12, 31)) == 5
    assert hbp_grace_years(dt.date(2026, 1, 1)) == 2


def test_engine_hbp_limit_and_repayment_start_are_asof_date_aware() -> None:
    df_old, _, _, _ = _run(
        {
            "asof_date": "2024-01-01",
            "hbp_enabled": True,
            "hbp_withdrawal": 60_000.0,
            "first_time": True,
        }
    )
    assert df_old.attrs["phase_d_hbp_withdrawal"] == pytest.approx(35_000.0)
    assert df_old.attrs["phase_d_hbp_repayment_start_month"] == 61

    df_new, _, _, _ = _run(
        {
            "asof_date": "2026-01-01",
            "hbp_enabled": True,
            "hbp_withdrawal": 60_000.0,
            "first_time": True,
        }
    )
    assert df_new.attrs["phase_d_hbp_withdrawal"] == pytest.approx(60_000.0)
    assert df_new.attrs["phase_d_hbp_repayment_start_month"] == 25


def test_engine_hbp_and_fhsa_require_first_time_buyer_flag() -> None:
    df, _, _, _ = _run(
        {
            "asof_date": "2026-01-01",
            "first_time": False,
            "hbp_enabled": True,
            "hbp_withdrawal": 60_000.0,
            "fhsa_enabled": True,
            "fhsa_annual_contribution": 8_000.0,
            "fhsa_years_contributed": 5,
            "fhsa_return_pct": 5.0,
            "fhsa_marginal_tax_rate_pct": 40.0,
        }
    )
    assert df.attrs["phase_d_hbp_eligible"] is False
    assert df.attrs["phase_d_hbp_withdrawal"] == pytest.approx(0.0)
    assert df.attrs["phase_d_fhsa_eligible"] is False
    assert df.attrs["phase_d_fhsa_supplement"] == pytest.approx(0.0)
    assert df.attrs["phase_d_fhsa_tax_saving"] == pytest.approx(0.0)


def test_engine_foreign_buyer_tax_attrs_include_toronto_municipal_component() -> None:
    df, close_cash, _, _ = _run(
        {
            "price": 1_000_000.0,
            "down": 200_000.0,
            "mort": 800_000.0,
            "province": "Ontario",
            "toronto": True,
            "is_foreign_buyer": True,
            "asof_date": "2025-01-15",
        }
    )
    assert df.attrs["phase_d_foreign_buyer_tax_provincial"] == pytest.approx(250_000.0)
    assert df.attrs["phase_d_foreign_buyer_tax_municipal"] == pytest.approx(100_000.0)
    assert df.attrs["phase_d_foreign_buyer_tax"] == pytest.approx(350_000.0)


def test_engine_string_false_does_not_enable_first_time_programs() -> None:
    df, _, _, _ = _run(
        {
            "asof_date": "2026-01-01",
            "first_time": "false",
            "hbp_enabled": True,
            "hbp_withdrawal": 60_000.0,
            "fhsa_enabled": True,
            "fhsa_annual_contribution": 8_000.0,
            "fhsa_years_contributed": 5,
            "fhsa_return_pct": 5.0,
            "fhsa_marginal_tax_rate_pct": 40.0,
        }
    )
    assert df.attrs["phase_d_hbp_eligible"] is False
    assert df.attrs["phase_d_hbp_withdrawal"] == pytest.approx(0.0)
    assert df.attrs["phase_d_fhsa_eligible"] is False
    assert df.attrs["phase_d_fhsa_supplement"] == pytest.approx(0.0)


def test_engine_string_false_does_not_enable_foreign_buyer_tax() -> None:
    df, _, _, _ = _run(
        {
            "price": 1_000_000.0,
            "down": 200_000.0,
            "mort": 800_000.0,
            "province": "Ontario",
            "toronto": True,
            "is_foreign_buyer": "false",
            "asof_date": "2025-01-15",
        }
    )
    assert df.attrs["phase_d_foreign_buyer_tax_provincial"] == pytest.approx(0.0)
    assert df.attrs["phase_d_foreign_buyer_tax_municipal"] == pytest.approx(0.0)
    assert df.attrs["phase_d_foreign_buyer_tax"] == pytest.approx(0.0)


def test_engine_first_time_key_takes_precedence_over_fallback_key() -> None:
    """Explicit first_time=False should not be overridden by first_time_buyer=True."""
    df, _, _, _ = _run(
        {
            "asof_date": "2026-01-01",
            "first_time": False,
            "first_time_buyer": True,
            "hbp_enabled": True,
            "hbp_withdrawal": 60_000.0,
            "fhsa_enabled": True,
            "fhsa_annual_contribution": 8_000.0,
            "fhsa_years_contributed": 5,
            "fhsa_return_pct": 5.0,
            "fhsa_marginal_tax_rate_pct": 40.0,
        }
    )
    assert df.attrs["phase_d_hbp_eligible"] is False
    assert df.attrs["phase_d_hbp_withdrawal"] == pytest.approx(0.0)
    assert df.attrs["phase_d_fhsa_eligible"] is False
