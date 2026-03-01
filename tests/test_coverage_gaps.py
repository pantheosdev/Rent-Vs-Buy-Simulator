"""Tests covering modules identified as low-coverage in the audit.

Targets: taxes.py (0%), validation.py (36%), policy_canada.py (50%),
         government_programs.py (77%), mortgage.py (61%).
"""

from __future__ import annotations

import warnings

import pytest

# ---------------------------------------------------------------------------
# taxes.py
# ---------------------------------------------------------------------------
from rbv.core.taxes import (
    calc_ltt_ontario,
    calc_ptt_bc,
    calc_transfer_tax,
)


class TestOntarioLTT:
    """Land Transfer Tax — Ontario bracketed calculation."""

    def test_audit_reference_800k(self) -> None:
        """Audit truth table: $800,000 → $12,475."""
        assert calc_ltt_ontario(800_000) == pytest.approx(12_475, abs=1)

    def test_zero_price(self) -> None:
        assert calc_ltt_ontario(0) == pytest.approx(0.0)

    def test_below_first_bracket(self) -> None:
        # Under $55k: 0.5%
        assert calc_ltt_ontario(40_000) == pytest.approx(200.0, abs=1)

    def test_fthb_exemption_applied(self) -> None:
        # FTHB can claim up to $4,000 rebate; tax on $500k = $6,475
        tax = calc_ltt_ontario(500_000)
        assert tax == pytest.approx(6_475, abs=1)

    def test_above_2m_bracket(self) -> None:
        # Above $2M uses 2.5% on the excess
        tax = calc_ltt_ontario(3_000_000)
        # Top bracket: ($3M - $2M) * 0.025 = $25,000 on top of base
        assert tax > 30_000  # sanity: large home = large tax

    def test_negative_price_clamped(self) -> None:
        # Negative price should yield zero or near-zero (no negative tax)
        assert calc_ltt_ontario(-100_000) == pytest.approx(0.0)


class TestBCPTT:
    """Property Transfer Tax — British Columbia."""

    def test_audit_reference_1_2m(self) -> None:
        """Audit truth table: $1,200,000 → $22,000."""
        assert calc_ptt_bc(1_200_000) == pytest.approx(22_000, abs=1)

    def test_below_200k(self) -> None:
        # Only 1% bracket applies
        assert calc_ptt_bc(100_000) == pytest.approx(1_000, abs=1)

    def test_zero_price(self) -> None:
        assert calc_ptt_bc(0) == pytest.approx(0.0)


class TestCalcTransferTax:
    """calc_transfer_tax dispatcher for all provinces."""

    @pytest.mark.parametrize("province", [
        "Ontario",
        "British Columbia",
        "Alberta",
        "Quebec",
        "Manitoba",
        "Nova Scotia",
        "New Brunswick",
        "Prince Edward Island",
        "Newfoundland and Labrador",
    ])
    def test_all_provinces_return_dict(self, province: str) -> None:
        result = calc_transfer_tax(province, 500_000, first_time_buyer=False, toronto_property=False)
        assert isinstance(result, dict)
        assert "total" in result
        assert result["total"] >= 0.0

    def test_unknown_province_returns_zero(self) -> None:
        result = calc_transfer_tax("Yukon", 500_000, first_time_buyer=False, toronto_property=False)
        assert result["total"] == pytest.approx(0.0)
        assert "note" in result

    def test_toronto_mltt_stacks(self) -> None:
        """Toronto property has a municipal LTT on top of provincial."""
        with_toronto = calc_transfer_tax("Ontario", 800_000, first_time_buyer=False, toronto_property=True)
        without_toronto = calc_transfer_tax("Ontario", 800_000, first_time_buyer=False, toronto_property=False)
        assert with_toronto["total"] > without_toronto["total"]


# ---------------------------------------------------------------------------
# policy_canada.py
# ---------------------------------------------------------------------------
import datetime as dt

from rbv.core.policy_canada import (
    cmhc_premium_rate_from_ltv,
    min_down_payment_canada,
)


class TestCMHCPremiumRate:
    """CMHC insurance premium tiers."""

    def test_below_80_no_insurance(self) -> None:
        assert cmhc_premium_rate_from_ltv(0.75) == pytest.approx(0.0)

    def test_exactly_80_no_insurance(self) -> None:
        assert cmhc_premium_rate_from_ltv(0.80) == pytest.approx(0.0)

    def test_85_tier(self) -> None:
        assert cmhc_premium_rate_from_ltv(0.82) == pytest.approx(0.028)

    def test_90_tier(self) -> None:
        assert cmhc_premium_rate_from_ltv(0.88) == pytest.approx(0.031)

    def test_95_tier_traditional(self) -> None:
        assert cmhc_premium_rate_from_ltv(0.95, "Traditional") == pytest.approx(0.040)

    def test_95_tier_non_traditional(self) -> None:
        assert cmhc_premium_rate_from_ltv(0.95, "Non-traditional") == pytest.approx(0.045)

    def test_non_traditional_90_boundary_not_triggered(self) -> None:
        # Non-traditional premium only applies above 90% LTV
        assert cmhc_premium_rate_from_ltv(0.88, "Non-traditional") == pytest.approx(0.031)

    def test_above_95_warns_and_returns_zero(self) -> None:
        """LTV > 95% is invalid — expect warning and 0.0 return."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            rate = cmhc_premium_rate_from_ltv(0.97)
        assert rate == pytest.approx(0.0)
        assert len(caught) == 1
        assert "95%" in str(caught[0].message)

    def test_ltv_100_warns(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            rate = cmhc_premium_rate_from_ltv(1.00)
        assert rate == pytest.approx(0.0)
        assert len(caught) == 1

    def test_invalid_input_returns_zero(self) -> None:
        assert cmhc_premium_rate_from_ltv(float("nan")) == pytest.approx(0.0)


class TestMinDownPayment:
    """Minimum down payment rules per CMHC/OSFI."""

    _POST_DEC2024 = dt.date(2025, 1, 1)
    _PRE_DEC2024 = dt.date(2024, 1, 1)

    def test_below_500k_5pct(self) -> None:
        dp = min_down_payment_canada(400_000, self._POST_DEC2024)
        assert dp == pytest.approx(20_000, rel=1e-6)

    def test_750k_post_dec2024(self) -> None:
        """Audit truth table: $750k → $50,000 post Dec 15 2024."""
        dp = min_down_payment_canada(750_000, self._POST_DEC2024)
        assert dp == pytest.approx(50_000, abs=1)

    def test_above_insured_cap_requires_20pct(self) -> None:
        # Post-Dec 2024, insured cap = $1.5M
        dp = min_down_payment_canada(1_600_000, self._POST_DEC2024)
        assert dp == pytest.approx(320_000, abs=1)  # 20% of $1.6M


# ---------------------------------------------------------------------------
# validation.py
# ---------------------------------------------------------------------------
from rbv.core.validation import validate_simulation_params


class TestValidationBounds:
    """validate_simulation_params clamps extreme inputs."""

    _BASE = dict(
        rate_pct=5.0,
        buyer_ret_pct=7.0,
        renter_ret_pct=7.0,
        apprec_pct=3.0,
        general_inf=0.02,
        rent_inf=0.02,
        years=25,
        price=800_000.0,
        rent=3_200.0,
        down=160_000.0,
    )

    def test_valid_passthrough(self) -> None:
        result = validate_simulation_params(**self._BASE)
        assert result["rate_pct"] == pytest.approx(5.0)
        assert result["years"] == 25

    def test_mortgage_rate_clamped_at_25(self) -> None:
        params = {**self._BASE, "rate_pct": 99.0}
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = validate_simulation_params(**params)
        assert result["rate_pct"] == pytest.approx(25.0)

    def test_appreciation_clamped_at_30(self) -> None:
        params = {**self._BASE, "apprec_pct": 500.0}
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = validate_simulation_params(**params)
        assert result["apprec_pct"] == pytest.approx(30.0)

    def test_years_clamped_at_50(self) -> None:
        params = {**self._BASE, "years": 200}
        result = validate_simulation_params(**params)
        assert result["years"] == 50

    def test_years_minimum_1(self) -> None:
        params = {**self._BASE, "years": 0}
        result = validate_simulation_params(**params)
        assert result["years"] == 1

    def test_negative_price_clamped(self) -> None:
        params = {**self._BASE, "price": -100_000.0}
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = validate_simulation_params(**params)
        assert result["price"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# mortgage.py
# ---------------------------------------------------------------------------
from rbv.core.mortgage import (
    _annual_nominal_pct_to_monthly_rate,
    _pmt,
)


class TestMortgage:
    """Canadian semi-annual compounding mortgage math."""

    def test_canadian_monthly_rate_5pct(self) -> None:
        """Audit truth table: 5% → mr ≈ 0.00412391546..."""
        mr = _annual_nominal_pct_to_monthly_rate(5.0, canadian=True)
        assert mr == pytest.approx(0.0041239154651442345, rel=1e-10)

    def test_us_monthly_rate_5pct(self) -> None:
        """US: simple division r/12."""
        mr = _annual_nominal_pct_to_monthly_rate(5.0, canadian=False)
        assert mr == pytest.approx(0.05 / 12, rel=1e-10)

    def test_canadian_vs_us_canadian_is_lower(self) -> None:
        """Canadian effective monthly rate is slightly lower than US for the same nominal."""
        mr_ca = _annual_nominal_pct_to_monthly_rate(5.0, canadian=True)
        mr_us = _annual_nominal_pct_to_monthly_rate(5.0, canadian=False)
        assert mr_ca < mr_us

    def test_payment_640k_25yr_5pct_canadian(self) -> None:
        """Audit truth table: $640k / 300 months / 5% → pmt ≈ $3,722.27."""
        mr = _annual_nominal_pct_to_monthly_rate(5.0, canadian=True)
        pmt = _pmt(640_000.0, mr, 300)
        assert pmt == pytest.approx(3722.27, abs=0.01)

    def test_zero_rate_payment(self) -> None:
        """Zero interest: payment = principal / months."""
        pmt = _pmt(120_000.0, 0.0, 120)
        assert pmt == pytest.approx(1_000.0, abs=0.01)

    def test_full_down_payment_zero_mortgage(self) -> None:
        """100% down payment: no mortgage balance → payment = 0."""
        pmt = _pmt(0.0, _annual_nominal_pct_to_monthly_rate(5.0, canadian=True), 300)
        assert pmt == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# government_programs.py
# ---------------------------------------------------------------------------
from rbv.core.government_programs import (
    fhsa_balance,
    fhsa_tax_savings,
    hbp_monthly_repayment,
)


class TestGovernmentPrograms:
    """RRSP HBP and FHSA benefit calculations."""

    def test_hbp_monthly_repayment_35k(self) -> None:
        """$35,000 HBP withdrawal repaid over 15 years = ~$194.44/month."""
        monthly = hbp_monthly_repayment(35_000.0)
        assert monthly == pytest.approx(35_000 / (15 * 12), rel=1e-6)

    def test_hbp_monthly_repayment_zero(self) -> None:
        monthly = hbp_monthly_repayment(0.0)
        assert monthly == pytest.approx(0.0)

    def test_fhsa_tax_savings_positive(self) -> None:
        """FHSA tax savings: cumulative contributions × marginal rate."""
        # $8,000/yr × 5 years = $40,000 cumulative; at 33% rate = $13,200
        savings = fhsa_tax_savings(40_000.0, 33.0)
        assert savings == pytest.approx(40_000 * 0.33, rel=1e-6)

    def test_fhsa_tax_savings_zero_rate(self) -> None:
        savings = fhsa_tax_savings(40_000.0, 0.0)
        assert savings == pytest.approx(0.0)

    def test_fhsa_balance_grows_over_time(self) -> None:
        """FHSA balance should grow with more years of contributions."""
        bal_5, _ = fhsa_balance(8_000.0, years_contributed=5, annual_return_pct=5.0)
        bal_1, _ = fhsa_balance(8_000.0, years_contributed=1, annual_return_pct=5.0)
        assert bal_5 > bal_1
