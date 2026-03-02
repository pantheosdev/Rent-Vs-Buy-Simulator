"""Canadian transfer tax and closing-cost utilities."""

import datetime
import math

# Policy freshness marker (used by CI reminder workflows)
TAX_RULES_LAST_REVIEWED = datetime.date(2026, 2, 22)
PROVINCES = [
    "Ontario",
    "British Columbia",
    "Alberta",
    "Quebec",
    "Manitoba",
    "Saskatchewan",
    "Nova Scotia",
    "New Brunswick",
    "Newfoundland and Labrador",
    "Prince Edward Island",
    "Northwest Territories",
    "Yukon",
    "Nunavut",
]


# Province transfer tax / land-title fee assumptions (high-level).
# These are shown in the Model Assumptions tab to help users understand what's being applied.


PROV_TAX_RULES_MD = {
    "Ontario": "- **Ontario LTT (provincial):** progressive brackets. **First-time buyer (FTHB)** rebate up to **$4,000** (simplified).\n- **Toronto (optional):** additional **Municipal LTT** with simplified FTHB rebate up to **$4,475**.",
    "British Columbia": "- **BC PTT:** 1% on first $200k, 2% on $200k–$2M, 3% on $2M–$3M, 5% above $3M.\n- **FTHB exemption (simplified):** reduces PTT by up to **$8,000** (full up to **$835k**, phases out to **$860k**, as-of **Apr 1, 2024**+). Assumes you qualify; does not model all eligibility rules.\n- Excludes additional taxes (e.g., foreign buyer/speculation).",
    "Alberta": "- **AB:** no land transfer tax; **land title registration fee** estimated (transfer-of-land only; mortgage registration not included).",
    "Saskatchewan": "- **SK:** **land title transfer fee** estimated (mortgage registration not included).",
    "Manitoba": "- **MB land transfer tax:** progressive brackets (0% to $30k; then 0.5%, 1.0%, 1.5%, 2.0% tiers).",
    "Quebec": "- **QC welcome tax (standard):** 0.5% to $55,200; 1.0% to $276,200; 1.5% above.\n- Many municipalities apply higher top rates; use **Override** for precision.",
    "New Brunswick": "- **NB property transfer tax:** simplified as **1%** of the **higher of purchase price and assessed value**. Provide assessed value (defaults to purchase price).",
    "Nova Scotia": "- **NS deed transfer tax:** municipal; rates vary. Default **1.5%**. Adjust the rate input (or override) for your municipality.",
    "Prince Edward Island": "- **PEI real property transfer tax:** simplified bracketed schedule. Uses the **higher of purchase price and assessed value**; some exemptions not modeled (use override if applicable).",
    "Newfoundland and Labrador": "- **NL:** estimates deed **registration fee** portion only (simplified; may vary by local rules).",
    "Northwest Territories": "- **Territories:** fees vary; defaulting to **$0**. Use **Override** if applicable.",
    "Yukon": "- **Territories:** fees vary; defaulting to **$0**. Use **Override** if applicable.",
    "Nunavut": "- **Territories:** fees vary; defaulting to **$0**. Use **Override** if applicable.",
}


def _safe_float(value: float | int | str | None, default: float = 0.0) -> float:
    """Return a finite float, otherwise ``default``.

    Tax helpers are used from both UI and scripts; this prevents NaN/inf inputs from
    contaminating downstream totals with NaN.
    """
    try:
        x = float(value)  # type: ignore[arg-type]
    except Exception:
        return float(default)
    return x if math.isfinite(x) else float(default)


def _as_bool(value: object) -> bool:
    """Parse booleans from UI/session-friendly values.

    Without this, strings like "False" are truthy and accidentally trigger rebates/toggles.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    s = str(value or "").strip().lower()
    if s in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if s in {"0", "false", "f", "no", "n", "off", "", "none", "null"}:
        return False
    return bool(value)


def _normalize_province_key(province: str | None) -> str:
    """Normalize province names/abbreviations to a canonical key."""
    raw = " ".join(str(province or "").strip().lower().replace("&", " and ").split())
    aliases = {
        "on": "ontario",
        "ont": "ontario",
        "bc": "british columbia",
        "b.c.": "british columbia",
        "ab": "alberta",
        "alta": "alberta",
        "sk": "saskatchewan",
        "mb": "manitoba",
        "qc": "quebec",
        "pq": "quebec",
        "ns": "nova scotia",
        "nb": "new brunswick",
        "pei": "prince edward island",
        "pe": "prince edward island",
        "p.e.i.": "prince edward island",
        "nl": "newfoundland and labrador",
        "newfoundland": "newfoundland and labrador",
        "nwt": "northwest territories",
        "nt": "northwest territories",
        "yt": "yukon",
        "nu": "nunavut",
    }
    return aliases.get(raw, raw)


def calc_ltt_ontario(p: float) -> float:
    """Ontario Land Transfer Tax (provincial portion), excluding rebates."""
    p = round(max(0.0, _safe_float(p)), 2)
    if p <= 0.0:
        return 0.0
    ltt = 0.0
    orig_p = p
    if p > 2000000:
        ltt += (p - 2000000) * 0.025
        p = 2000000
    if p > 400000:
        ltt += (p - 400000) * 0.02
        p = 400000
    if p > 250000:
        ltt += (p - 250000) * 0.015
        p = 250000
    if p > 55000:
        ltt += (p - 55000) * 0.01
    ltt += min(orig_p, 55000) * 0.005
    return ltt


def calc_ltt_toronto_municipal(p: float, asof_date: datetime.date | None = None) -> float:
    """Toronto Municipal Land Transfer Tax (MLTT) for residential properties.

    - Mirrors Ontario brackets up to $3,000,000.
    - Applies luxury brackets on the portion above $3,000,000.
    - Uses the April 1, 2026 schedule automatically once that date has passed.
      (Schedule selection can be controlled via asof_date; defaults to today's date.)
    """
    p = round(max(0.0, _safe_float(p)), 2)
    if p <= 0:
        return 0.0

    base_cap = 3_000_000.0
    base = calc_ltt_ontario(min(p, base_cap))
    if p <= base_cap:
        return base

    try:
        today = asof_date if isinstance(asof_date, datetime.date) else datetime.date.today()
    except Exception:
        today = datetime.date(2026, 1, 1)
    cutoff = datetime.date(2026, 4, 1)

    # Marginal rates for the portion above $3M.
    if today >= cutoff:
        brackets = [
            (4_000_000.0, 0.0440),
            (5_000_000.0, 0.0545),
            (10_000_000.0, 0.0650),
            (20_000_000.0, 0.0755),
            (float("inf"), 0.0860),
        ]
    else:
        brackets = [
            (4_000_000.0, 0.0350),
            (5_000_000.0, 0.0450),
            (10_000_000.0, 0.0550),
            (20_000_000.0, 0.0650),
            (float("inf"), 0.0750),
        ]

    extra = 0.0
    prev = base_cap
    x = p
    for upper, rate in brackets:
        if x <= prev:
            break
        taxable = min(x, upper) - prev
        if taxable > 0:
            extra += taxable * rate
        prev = upper

    return base + extra


def calc_ptt_bc(p: float) -> float:
    """BC Property Transfer Tax (base, excluding additional foreign buyer/speculation taxes)."""
    p = round(max(0.0, _safe_float(p)), 2)
    if p <= 0.0:
        return 0.0
    tax = 0.0
    # 1% on first 200k
    tax += min(p, 200_000.0) * 0.01
    # 2% on 200k-2M
    if p > 200_000.0:
        tax += (min(p, 2_000_000.0) - 200_000.0) * 0.02
    # 3% on 2M-3M
    if p > 2_000_000.0:
        tax += (min(p, 3_000_000.0) - 2_000_000.0) * 0.03
    # 5% on 3M+
    if p > 3_000_000.0:
        tax += (p - 3_000_000.0) * 0.05
    return tax


def bc_fthb_exemption_amount(price: float, asof_date: datetime.date | None = None) -> float:
    """BC First Time Home Buyers (FTHB) exemption amount (simplified).

    This models the *max* exemption value (i.e., the amount that reduces the base PTT), not the
    full set of eligibility criteria (principal residence, citizenship, prior ownership, etc.).

    Approximation:
    - For properties <= $500k: fully exempt the base PTT (which is <= $8,000)
    - Post Apr 1, 2024: max exemption is $8,000 for FMV <= $835k; then phases out to $0 at $860k
    - Pre Apr 1, 2024: legacy schedule: phases out from $500k to $525k

    Notes:
    - The max exemption of $8,000 corresponds to the base PTT on the first $500k.
    - We treat purchase price as a proxy for fair market value.
    """
    p = round(max(0.0, _safe_float(price)), 2)
    if p <= 0:
        return 0.0

    d = asof_date if isinstance(asof_date, datetime.date) else datetime.date.today()
    cutoff = datetime.date(2024, 4, 1)

    # Fully exempt under $500k in both regimes
    if p <= 500_000.0:
        return calc_ptt_bc(p)

    max_ex = 8_000.0

    if d >= cutoff:
        full_to = 835_000.0
        phaseout_to = 860_000.0
    else:
        # Legacy program thresholds (pre-Apr 1, 2024)
        full_to = 500_000.0
        phaseout_to = 525_000.0

    if p <= full_to:
        return max_ex
    if p >= phaseout_to:
        return 0.0

    # Linear phaseout between (full_to, phaseout_to)
    span = float(phaseout_to - full_to)
    if span <= 0:
        return 0.0
    frac = (float(phaseout_to) - p) / span
    return max(0.0, min(max_ex, max_ex * frac))


def _calc_bracket_tax(amount: float, brackets: list[tuple[float, float]]) -> float:
    """Generic marginal tax calculator.
    brackets: list of (upper_limit, rate) in ascending order; last upper_limit can be float('inf').
    """
    x = max(0.0, _safe_float(amount))
    tax = 0.0
    prev = 0.0
    for upper, rate in brackets:
        if x <= prev:
            break
        taxable = min(x, upper) - prev
        if taxable > 0:
            tax += taxable * rate
        prev = upper
    return tax


def calc_land_title_fee_alberta(price: float) -> float:
    """Alberta Transfer of Land registration fee (Land Titles Registration Levy, Oct 2024+).
    Simplified: $50 base + $5 per $5,000 (or part thereof) of property value.
    """
    p = max(0.0, _safe_float(price))
    if p <= 0:
        return 0.0
    portions = math.ceil(p / 5000.0)
    return 50.0 + 5.0 * portions


def calc_land_title_fee_saskatchewan(price: float) -> float:
    """Saskatchewan land title transfer fee (simplified).
    First $500: $0
    $500 to $6,300: $25 flat
    Over $6,300: $25 + 0.4% of amount over $6,300
    """
    p = max(0.0, _safe_float(price))
    if p <= 500:
        return 0.0
    if p <= 6300:
        return 25.0
    return 25.0 + (p - 6300.0) * 0.004


def calc_land_transfer_tax_manitoba(price: float) -> float:
    """Manitoba land transfer tax (provincial schedule)."""
    p = max(0.0, _safe_float(price))
    brackets = [
        (30000.0, 0.0),
        (90000.0, 0.005),
        (150000.0, 0.01),
        (200000.0, 0.015),
        (float("inf"), 0.02),
    ]
    return _calc_bracket_tax(p, brackets)


def calc_transfer_duty_quebec_baseline(price: float, asof_date: 'datetime.date | None' = None) -> float:
    """Quebec 'welcome tax' baseline schedule (Droits sur les mutations immobilières).

    Quebec municipalities can adopt higher rates in upper brackets. This function implements the *baseline*
    schedule (0.5% / 1% / 1.5%) with annually indexed thresholds.
    """
    p = round(max(0.0, _safe_float(price)), 2)
    d = asof_date if isinstance(asof_date, datetime.date) else datetime.date.today()
    y = int(getattr(d, "year", datetime.date.today().year))

    # Indexed thresholds (CAD). Keep a small table to avoid silent drift.
    if y <= 2024:
        b1, b2 = 58_900.0, 294_600.0
    elif y == 2025:
        b1, b2 = 61_500.0, 307_800.0
    else:
        # 2026+ (use latest known indexation; update annually).
        b1, b2 = 62_900.0, 315_000.0

    brackets = [
        (b1, 0.005),
        (b2, 0.01),
        (float("inf"), 0.015),
    ]
    return _calc_bracket_tax(p, brackets)


# Backwards-compatible alias (older app.py imports)
def calc_transfer_duty_quebec_standard(price: float, asof_date: "datetime.date | None" = None) -> float:
    """Alias for the baseline Quebec transfer duty schedule (municipal surcharges excluded)."""
    return calc_transfer_duty_quebec_baseline(price, asof_date=asof_date)


def calc_transfer_duty_quebec_big_city(price: float, asof_date: 'datetime.date | None' = None) -> float:
    """Example of a higher-bracket Quebec municipality schedule (e.g., Montréal-like tiers).

    Not used by default; kept for future municipality selectors.
    """
    p = round(max(0.0, _safe_float(price)), 2)

    brackets = [
        (62_900.0, 0.005),
        (315_000.0, 0.01),
        (552_300.0, 0.015),
        (1_104_700.0, 0.02),
        (2_136_500.0, 0.025),
        (3_113_000.0, 0.035),
        (float("inf"), 0.04),
    ]
    return _calc_bracket_tax(p, brackets)


def calc_property_transfer_tax_new_brunswick(price: float) -> float:
    """New Brunswick property transfer tax (simplified): 1% of assessed value.
    We use purchase price as proxy.
    """
    p = max(0.0, _safe_float(price))
    return max(0.0, p) * 0.01


def calc_deed_transfer_tax_nova_scotia_default(price: float, rate: float = 0.015) -> float:
    """Nova Scotia deed transfer tax is municipal. Default 1.5% (common, e.g. HRM).
    Use override for a precise local rate.
    """
    p = max(0.0, _safe_float(price))
    r = max(0.0, _safe_float(rate, default=0.0))
    return p * r


def calc_real_property_transfer_tax_pei(price: float) -> float:
    """Prince Edward Island real property transfer tax (simplified).
    Historically 1% on the portion above $30,000. Recent budgets introduced a higher rate above $1,000,000.
    Implemented here as: 1% on (min(price, 1M) - 30k) + 2% on amount above 1M.
    Use override for edge cases / exemptions.
    """
    p = max(0.0, _safe_float(price))
    if p <= 30000:
        return 0.0
    base = (min(p, 1_000_000.0) - 30000.0) * 0.01
    extra = (p - 1_000_000.0) * 0.02 if p > 1_000_000.0 else 0.0
    return max(0.0, base + extra)


def calc_registration_fee_newfoundland(price: float) -> float:
    """Newfoundland & Labrador registration of deeds fee (simplified).
    Base $100 covers first $500; then $0.40 per $100 over $500 (rounded down). Capped at $5,000.
    """
    p = max(0.0, _safe_float(price))
    if p <= 0:
        return 0.0
    fee = 100.0
    if p > 500.0:
        increments = math.floor((p - 500.0) / 100.0)
        fee += increments * 0.40
    return min(5000.0, fee)


def calc_transfer_tax(
    province: str,
    price: float,
    first_time_buyer: bool,
    toronto_property: bool,
    override_amount: float = 0.0,
    asof_date: datetime.date | None = None,
    assessed_value: float | None = None,
    ns_deed_transfer_rate: float | None = None,
) -> dict:
    """Return dict with total and components: {'prov': x, 'muni': y, 'total': z, 'note': str}.

    If override_amount > 0, it is used as the provincial component (and a note is added).
    """
    province = (province or "Ontario").strip()
    province_key = _normalize_province_key(province)
    price = round(max(0.0, _safe_float(price)), 2)
    prov = 0.0
    assessed_value = None if assessed_value is None else round(max(0.0, _safe_float(assessed_value)), 2)
    first_time_buyer = _as_bool(first_time_buyer)
    toronto_property = _as_bool(toronto_property)

    muni = 0.0
    note = ""

    # User override always wins (keeps behavior predictable)
    override = _safe_float(override_amount, default=0.0)
    if override > 0:
        prov = override
        note = "Using your 'Transfer Tax Override' amount for this province/municipality."
        return {"prov": prov, "muni": 0.0, "total": prov, "note": note}

    if province_key == "ontario":
        raw = calc_ltt_ontario(price)
        # Ontario first-time buyer rebate up to $4,000 (simplified; eligibility not fully modeled)
        rebate = 4000.0 if first_time_buyer else 0.0
        prov = max(0.0, raw - rebate)
        if toronto_property:
            raw_m = calc_ltt_toronto_municipal(price, asof_date=asof_date)
            # Toronto first-time buyer rebate up to $4,475 (simplified)
            rebate_m = 4475.0 if first_time_buyer else 0.0
            muni = max(0.0, raw_m - rebate_m)

            # Date-dependent Toronto luxury MLTT schedule (>$3M) is selected using asof_date (defaults to today).
            if price > 3_000_000:
                try:
                    _d = asof_date if isinstance(asof_date, datetime.date) else datetime.date.today()
                except Exception:
                    _d = datetime.date(2026, 1, 1)
                _cut = datetime.date(2026, 4, 1)
                _sched = "post-Apr 1, 2026" if _d >= _cut else "pre-Apr 1, 2026"
                note = f"Toronto MLTT luxury brackets (>$3M) use the {_sched} schedule as of {_d.isoformat()}."

    elif province_key == "british columbia":
        raw = calc_ptt_bc(price)
        prov = raw
        note = "BC PTT excludes additional taxes (e.g., foreign buyer/speculation)."

        if first_time_buyer:
            ex = bc_fthb_exemption_amount(price, asof_date=asof_date)
            if ex > 0:
                prov = max(0.0, raw - ex)
                try:
                    _d = asof_date if isinstance(asof_date, datetime.date) else datetime.date.today()
                except Exception:
                    _d = datetime.date.today()
                _cut = datetime.date(2024, 4, 1)
                _sched = "post-Apr 1, 2024" if _d >= _cut else "pre-Apr 1, 2024"
                note = (
                    f"BC FTHB exemption applied (simplified; assumes eligible). "
                    f"Max $8,000; {_sched} schedule as of {_d.isoformat()}. "
                    "Excludes additional taxes (e.g., foreign buyer/speculation)."
                )

    elif province_key == "alberta":
        # Alberta has registration fees rather than a transfer tax; we estimate the transfer-of-land fee only.
        prov = calc_land_title_fee_alberta(price)
        note = "Alberta uses land title registration fees (transfer-of-land). Mortgage registration fees not included."

    elif province_key == "saskatchewan":
        prov = calc_land_title_fee_saskatchewan(price)
        note = "Saskatchewan uses land title transfer fees (simplified). Mortgage registration fees not included."

    elif province_key == "manitoba":
        prov = calc_land_transfer_tax_manitoba(price)

    elif province_key == "quebec":
        prov = calc_transfer_duty_quebec_baseline(price, asof_date=asof_date)
        note = "Quebec duties can vary by municipality (some apply higher rates in top brackets). Use override for precision."

    elif province_key == "new brunswick":
        basis = max(price, assessed_value) if assessed_value is not None else price
        prov = calc_property_transfer_tax_new_brunswick(basis)
        note = (
            "NB property transfer tax is based on assessed value; using max(purchase price, assessed value)."
            if assessed_value is not None
            else "NB property transfer tax is based on assessed value; using purchase price as proxy. Provide assessed value for precision."
        )

    elif province_key == "nova scotia":
        _input_rate = _safe_float(ns_deed_transfer_rate, default=0.0) if ns_deed_transfer_rate is not None else 0.0
        _rate = _input_rate if _input_rate > 0 else 0.015
        prov = calc_deed_transfer_tax_nova_scotia_default(price, rate=_rate)
        if ns_deed_transfer_rate is not None and _input_rate > 0:
            note = f"Nova Scotia deed transfer tax is municipal; using your selected rate of {_rate * 100:.3g}%."
        else:
            note = "Nova Scotia deed transfer tax is municipal; defaulting to 1.5%. Use the rate input or override for your municipality."

    elif province_key == "prince edward island":
        basis = max(price, assessed_value) if assessed_value is not None else price
        prov = calc_real_property_transfer_tax_pei(basis)
        note = "PEI transfer tax can include exemptions/eligibility rules; using max(purchase price, assessed value). Override if you have a local exemption."
    elif province_key == "newfoundland and labrador":
        prov = calc_registration_fee_newfoundland(price)
        note = "NL uses registration fees; this estimates the deed registration portion only."

    else:
        prov = 0.0
        note = "No built-in transfer tax rule for this region. Use 'Transfer Tax Override' if applicable."

    total = prov + muni
    return {"prov": prov, "muni": muni, "total": total, "note": note}
