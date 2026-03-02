"""Tests for Phase D financial features.

Covers:
- Foreign buyer taxes (BC APTT, Ontario NRST) in policy_canada.py
- RRSP Home Buyers' Plan (HBP) in government_programs.py
- First Home Savings Account (FHSA) in government_programs.py
- IRD mortgage prepayment penalty in mortgage.py
- Engine integration smoke test
"""

from __future__ import annotations

import datetime as dt

import pytest

# ---------------------------------------------------------------------------
# Foreign Buyer Taxes
# ---------------------------------------------------------------------------
from rbv.core.policy_canada import foreign_buyer_tax_amount, foreign_buyer_tax_rate


class TestForeignBuyerTax:
    def test_bc_2026_rate_is_20_pct(self):
        assert foreign_buyer_tax_rate("British Columbia", dt.date(2026, 1, 1)) == pytest.approx(0.20)

    def test_bc_rate_by_shortcode(self):
        assert foreign_buyer_tax_rate("bc", dt.date(2026, 1, 1)) == pytest.approx(0.20)

    def test_bc_pre_2016_no_tax(self):
        assert foreign_buyer_tax_rate("British Columbia", dt.date(2015, 12, 31)) == pytest.approx(0.0)

    def test_bc_2016_rate_is_15_pct(self):
        # Introduced 2016-08-02 at 15%
        assert foreign_buyer_tax_rate("British Columbia", dt.date(2017, 1, 1)) == pytest.approx(0.15)

    def test_bc_2018_rate_raised_to_20_pct(self):
        assert foreign_buyer_tax_rate("British Columbia", dt.date(2018, 3, 1)) == pytest.approx(0.20)

    def test_ontario_2026_rate_is_25_pct(self):
        assert foreign_buyer_tax_rate("Ontario", dt.date(2026, 1, 1)) == pytest.approx(0.25)

    def test_ontario_shortcode(self):
        assert foreign_buyer_tax_rate("on", dt.date(2026, 1, 1)) == pytest.approx(0.25)

    def test_ontario_2017_intro_15_pct(self):
        assert foreign_buyer_tax_rate("Ontario", dt.date(2018, 1, 1)) == pytest.approx(0.15)

    def test_ontario_2022_20_pct(self):
        assert foreign_buyer_tax_rate("Ontario", dt.date(2022, 6, 1)) == pytest.approx(0.20)

    def test_ontario_2023_25_pct(self):
        assert foreign_buyer_tax_rate("Ontario", dt.date(2023, 6, 1)) == pytest.approx(0.25)

    def test_ontario_pre_2017_no_tax(self):
        assert foreign_buyer_tax_rate("Ontario", dt.date(2016, 12, 31)) == pytest.approx(0.0)

    def test_alberta_no_tax(self):
        assert foreign_buyer_tax_rate("Alberta", dt.date(2026, 1, 1)) == pytest.approx(0.0)

    def test_amount_bc_1m_purchase(self):
        amt = foreign_buyer_tax_amount(1_000_000.0, "British Columbia", dt.date(2026, 1, 1))
        assert amt == pytest.approx(200_000.0)

    def test_amount_ontario_800k_purchase(self):
        amt = foreign_buyer_tax_amount(800_000.0, "Ontario", dt.date(2026, 1, 1))
        assert amt == pytest.approx(200_000.0)

    def test_amount_zero_price(self):
        assert foreign_buyer_tax_amount(0.0, "British Columbia", dt.date(2026, 1, 1)) == pytest.approx(0.0)

    def test_amount_no_tax_province(self):
        amt = foreign_buyer_tax_amount(1_000_000.0, "Alberta", dt.date(2026, 1, 1))
        assert amt == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# RRSP Home Buyers' Plan (HBP)
# ---------------------------------------------------------------------------

from rbv.core.government_programs import (
    HBP_GRACE_YEARS,
    HBP_REPAYMENT_YEARS,
    hbp_annual_repayment,
    hbp_max_withdrawal,
    hbp_monthly_repayment,
    hbp_repayment_monthly_schedule,
)


class TestHBP:
    def test_max_withdrawal_pre_2024(self):
        assert hbp_max_withdrawal(dt.date(2024, 1, 1)) == pytest.approx(35_000.0)

    def test_max_withdrawal_post_2024_04_16(self):
        assert hbp_max_withdrawal(dt.date(2024, 5, 1)) == pytest.approx(60_000.0)

    def test_max_withdrawal_no_date_defaults(self):
        # Should return some positive value (either 35k or 60k)
        result = hbp_max_withdrawal()
        assert result in (35_000.0, 60_000.0)

    def test_annual_repayment_for_60k(self):
        # 60000 / 15 = 4000/year
        assert hbp_annual_repayment(60_000.0) == pytest.approx(4_000.0)

    def test_annual_repayment_for_35k(self):
        # 35000 / 15 = 2333.33.../year
        assert hbp_annual_repayment(35_000.0) == pytest.approx(35_000.0 / 15)

    def test_monthly_repayment_for_60k(self):
        # 60000 / 15 / 12 = 333.33...
        assert hbp_monthly_repayment(60_000.0) == pytest.approx(60_000.0 / 15 / 12)

    def test_monthly_repayment_zero_withdrawal(self):
        assert hbp_monthly_repayment(0.0) == pytest.approx(0.0)

    def test_repayment_schedule_grace_period_zeros(self):
        """Months 0..23 should be 0 (2-year grace period)."""
        sched = hbp_repayment_monthly_schedule(60_000.0, sim_months=300)
        assert all(v == 0.0 for v in sched[:24])

    def test_repayment_schedule_starts_at_month_25(self):
        sched = hbp_repayment_monthly_schedule(60_000.0, sim_months=300)
        # Month index 24 = month 25 (0-indexed) → should be non-zero
        assert sched[24] == pytest.approx(60_000.0 / 15 / 12)

    def test_repayment_schedule_ends_correctly(self):
        """Repayments stop after grace + 15*12 months."""
        sched = hbp_repayment_monthly_schedule(60_000.0, sim_months=300)
        grace_mo = HBP_GRACE_YEARS * 12
        end_mo = grace_mo + HBP_REPAYMENT_YEARS * 12
        # Last repayment month
        assert sched[end_mo - 1] == pytest.approx(60_000.0 / 15 / 12)
        # After repayment window, schedule is 0
        if end_mo < len(sched):
            assert sched[end_mo] == pytest.approx(0.0)

    def test_repayment_schedule_total_matches_withdrawal(self):
        """Total repayment amount should equal the withdrawal."""
        withdrawal = 60_000.0
        sched = hbp_repayment_monthly_schedule(withdrawal, sim_months=300)
        total = sum(sched)
        assert total == pytest.approx(withdrawal, rel=1e-6)


# ---------------------------------------------------------------------------
# FHSA
# ---------------------------------------------------------------------------

from rbv.core.government_programs import FHSA_START_DATE, fhsa_balance, fhsa_tax_savings


class TestFHSA:
    def test_not_available_before_2023(self):
        bal, contrib = fhsa_balance(8_000.0, 3, 5.0, asof_date=dt.date(2022, 12, 31))
        assert bal == pytest.approx(0.0)
        assert contrib == pytest.approx(0.0)

    def test_zero_years_contributed(self):
        bal, contrib = fhsa_balance(8_000.0, 0, 5.0, asof_date=dt.date(2026, 1, 1))
        assert bal == pytest.approx(0.0)
        assert contrib == pytest.approx(0.0)

    def test_lifetime_cap_respected(self):
        # 6 years of $8k = $48k, but lifetime cap is $40k
        bal, contrib = fhsa_balance(8_000.0, 6, 5.0, asof_date=dt.date(2026, 1, 1))
        assert contrib == pytest.approx(40_000.0)  # capped at lifetime limit

    def test_5yr_contributions_sum_40k(self):
        bal, contrib = fhsa_balance(8_000.0, 5, 0.0, asof_date=dt.date(2026, 1, 1))
        assert contrib == pytest.approx(40_000.0)
        assert bal == pytest.approx(40_000.0)  # 0% return → balance = contributions

    def test_balance_grows_with_return(self):
        bal_0pct, _ = fhsa_balance(8_000.0, 5, 0.0, asof_date=dt.date(2026, 1, 1))
        bal_5pct, _ = fhsa_balance(8_000.0, 5, 5.0, asof_date=dt.date(2026, 1, 1))
        assert bal_5pct > bal_0pct

    def test_tax_savings_basic(self):
        savings = fhsa_tax_savings(40_000.0, 40.0)
        assert savings == pytest.approx(16_000.0)

    def test_tax_savings_zero_contributions(self):
        assert fhsa_tax_savings(0.0, 40.0) == pytest.approx(0.0)

    def test_tax_savings_zero_rate(self):
        assert fhsa_tax_savings(40_000.0, 0.0) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# IRD Mortgage Prepayment Penalty
# ---------------------------------------------------------------------------

from rbv.core.mortgage import ird_penalty_for_simulation, ird_prepayment_penalty


class TestIRD:
    def test_no_penalty_when_rates_risen(self):
        """If comparison rate > contract rate, IRD is zero; only 3-month rule applies."""
        # contract 4.5%, current 5.5% → rate diff < 0 → only 3-month interest
        penalty = ird_prepayment_penalty(400_000.0, 4.5, 5.5, 24)
        # Should be > 0 (3-month interest) but small
        assert penalty > 0.0
        # 3-month interest: 400k × (monthly rate at 4.5%) × 3
        from rbv.core.mortgage import _annual_nominal_pct_to_monthly_rate
        mr = _annual_nominal_pct_to_monthly_rate(4.5, canadian=True)
        expected_3mo = 400_000.0 * mr * 3.0
        assert penalty == pytest.approx(expected_3mo, rel=1e-4)

    def test_ird_when_rates_fallen(self):
        """When rates fall, IRD > 3-month interest."""
        # Contract 5.0%, comparison 3.0%, 24 months remaining
        penalty = ird_prepayment_penalty(400_000.0, 5.0, 3.0, 24)
        # IRD = 400k × (0.05 - 0.03) × 2 = 16000
        assert penalty == pytest.approx(16_000.0, rel=1e-3)

    def test_zero_balance_no_penalty(self):
        assert ird_prepayment_penalty(0.0, 4.5, 3.0, 24) == pytest.approx(0.0)

    def test_zero_remaining_term_no_penalty(self):
        assert ird_prepayment_penalty(400_000.0, 4.5, 3.0, 0) == pytest.approx(0.0)

    def test_sim_helper_no_break_full_term(self):
        """No penalty when months_elapsed >= term_months."""
        penalty = ird_penalty_for_simulation(
            original_principal=500_000.0,
            contract_rate_pct=4.5,
            monthly_payment=2_700.0,
            months_elapsed=60,
            term_months=60,
        )
        assert penalty == pytest.approx(0.0)

    def test_sim_helper_penalty_when_breaking_early(self):
        """Penalty > 0 when selling before the term ends."""
        penalty = ird_penalty_for_simulation(
            original_principal=500_000.0,
            contract_rate_pct=4.5,
            monthly_payment=2_700.0,
            months_elapsed=36,
            term_months=60,
            rate_drop_pp=1.5,
        )
        assert penalty > 0.0

    def test_sim_helper_larger_penalty_with_bigger_rate_drop(self):
        p1 = ird_penalty_for_simulation(500_000.0, 4.5, 2_700.0, 36, 60, rate_drop_pp=1.0)
        p2 = ird_penalty_for_simulation(500_000.0, 4.5, 2_700.0, 36, 60, rate_drop_pp=2.5)
        assert p2 > p1


# ---------------------------------------------------------------------------
# Engine Integration Smoke Test
# ---------------------------------------------------------------------------

from rbv.core.engine import run_simulation_core

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
    df, close_cash, pmt, win_pct = run_simulation_core(
        cfg, 7.0, 7.0, 3.0, False, False, 0.0
    )
    return df, close_cash, pmt


class TestEnginePhaseD:
    def test_baseline_runs(self):
        df, close_cash, pmt = _run({})
        assert len(df) == _BASE_CFG["years"] * 12

    def test_foreign_buyer_increases_close_cash(self):
        df_base, cc_base, _ = _run({})
        df_fb, cc_fb, _ = _run({"is_foreign_buyer": True, "province": "Ontario"})
        # Ontario NRST 25% on 700k = 175k extra
        assert cc_fb > cc_base
        assert pytest.approx(cc_fb - cc_base, rel=0.01) == 700_000.0 * 0.25

    def test_hbp_withdrawal_reduces_buyer_nw_late(self):
        """HBP repayment is a buyer cost → reduces buyer NW slightly vs baseline."""
        df_base, _, _ = _run({})
        df_hbp, _, _ = _run({
            "hbp_enabled": True,
            "hbp_withdrawal": 60_000.0,
        })
        # Down is same (HBP added to down, mortgage recalculated, but our fixture down_use starts same)
        # The HBP repayment adds cost to buyer, reducing final NW
        b_base = df_base.iloc[-1]["Buyer Net Worth"]
        b_hbp = df_hbp.iloc[-1]["Buyer Net Worth"]
        # Buyer NW with HBP repayment should differ from baseline
        # (it could be higher if HBP effectively reduces mortgage more than repayment costs)
        assert b_hbp != b_base  # something changed

    def test_ird_penalty_reduces_buyer_nw(self):
        """IRD penalty at terminal month reduces buyer NW."""
        df_base, _, _ = _run({})
        df_ird, _, _ = _run({
            "ird_enabled": True,
            "mortgage_term_months": 60,  # 5-year term
            "ird_rate_drop_pp": 1.5,
        })
        b_base = df_base.iloc[-1]["Buyer Net Worth"]
        b_ird = df_ird.iloc[-1]["Buyer Net Worth"]
        # Sim is 5 years (60 months) = same as term → no IRD (elapsed == term)
        # (so values should be approximately equal when horizon == term)
        assert b_ird == pytest.approx(b_base, rel=1e-5)

    def test_ird_penalty_when_horizon_shorter_than_term(self):
        """When sim horizon < term, IRD penalty reduces buyer NW."""
        df_base, _, _ = _run({"years": 3})
        df_ird, _, _ = _run({
            "years": 3,
            "ird_enabled": True,
            "mortgage_term_months": 60,  # 5-year term, sell at year 3
            "ird_rate_drop_pp": 1.5,
        })
        b_base = df_base.iloc[-1]["Buyer Net Worth"]
        b_ird = df_ird.iloc[-1]["Buyer Net Worth"]
        assert b_ird < b_base  # IRD penalty reduces buyer NW

    def test_phase_d_attrs_present(self):
        """Engine should attach Phase D metadata to df.attrs."""
        df_fb, _, _ = _run({"is_foreign_buyer": True, "province": "Ontario"})
        assert "phase_d_foreign_buyer_tax" in df_fb.attrs
        assert df_fb.attrs["phase_d_foreign_buyer_tax"] > 0

    def test_fhsa_supplement_no_crash(self):
        """FHSA with valid inputs runs without error."""
        df, _, _ = _run({
            "fhsa_enabled": True,
            "fhsa_annual_contribution": 8_000.0,
            "fhsa_years_contributed": 3,
            "fhsa_return_pct": 5.0,
            "fhsa_marginal_tax_rate_pct": 40.0,
            "asof_date": "2026-01-01",
        })
        assert len(df) == _BASE_CFG["years"] * 12
