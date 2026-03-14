from __future__ import annotations

from rbv.core.purchase_derivations import derive_purchase_fields, enrich_cfg_with_purchase_derivations


def test_string_false_flags_do_not_trigger_first_time_or_toronto_rebates() -> None:
    cfg_bool = {
        "price": 1_000_000.0,
        "down": 200_000.0,
        "province": "Ontario",
        "first_time": False,
        "toronto": False,
    }
    cfg_str = {
        "price": 1_000_000.0,
        "down": 200_000.0,
        "province": "Ontario",
        "first_time": "false",
        "toronto": "false",
    }

    d_bool = derive_purchase_fields(cfg_bool)
    d_str = derive_purchase_fields(cfg_str)
    assert d_str.transfer_tax_total == d_bool.transfer_tax_total


def test_recompute_sets_zero_mortgage_when_home_is_fully_paid() -> None:
    cfg = {
        "price": 500_000.0,
        "down": 500_000.0,
    }
    enriched = enrich_cfg_with_purchase_derivations(cfg, force_recompute=True)
    assert "mort" in enriched
    assert enriched["mort"] == 0.0

