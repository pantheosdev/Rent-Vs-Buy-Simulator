# Auto-extracted from v167_public_baseline_hotfix4.py

import math
import datetime



PROVINCES = [
    "Ontario", "British Columbia", "Alberta", "Quebec", "Manitoba", "Saskatchewan",
    "Nova Scotia", "New Brunswick", "Newfoundland and Labrador", "Prince Edward Island",
    "Northwest Territories", "Yukon", "Nunavut"
]


# Province transfer tax / land-title fee assumptions (high-level).
# These are shown in the Model Assumptions tab to help users understand what's being applied.


PROV_TAX_RULES_MD = {
    "Ontario": "- **Ontario LTT (provincial):** progressive brackets. **First-time buyer (FTHB)** rebate up to **$4,000** (simplified).\n- **Toronto (optional):** additional **Municipal LTT** with simplified FTHB rebate up to **$4,475**.",
    "British Columbia": "- **BC PTT:** 1% on first $200k, 2% on $200k–$2M, 3% on $2M–$3M, 5% above $3M.\n- Excludes additional taxes (e.g., foreign buyer/speculation) and exemptions.",
    "Alberta": "- **AB:** no land transfer tax; **land title registration fee** estimated (transfer-of-land only; mortgage registration not included).",
    "Saskatchewan": "- **SK:** **land title transfer fee** estimated (mortgage registration not included).",
    "Manitoba": "- **MB land transfer tax:** progressive brackets (0% to $30k; then 0.5%, 1.0%, 1.5%, 2.0% tiers).",
    "Quebec": "- **QC welcome tax (standard):** 0.5% to $55,200; 1.0% to $276,200; 1.5% above.\n- Many municipalities apply higher top rates; use **Override** for precision.",
    "New Brunswick": "- **NB:** simplified **1%** of purchase price (proxy for assessed value).",
    "Nova Scotia": "- **NS:** deed transfer tax is municipal; defaulting to **1.5%**. Use **Override** for your municipality.",
    "Prince Edward Island": "- **PEI:** 1% on portion above $30k; **2% on portion above $1M** (simplified). Exemptions not modeled; use **Override** if applicable.",
    "Newfoundland and Labrador": "- **NL:** estimates deed **registration fee** portion only (simplified; may vary by local rules).",
    "Northwest Territories": "- **Territories:** fees vary; defaulting to **$0**. Use **Override** if applicable.",
    "Yukon": "- **Territories:** fees vary; defaulting to **$0**. Use **Override** if applicable.",
    "Nunavut": "- **Territories:** fees vary; defaulting to **$0**. Use **Override** if applicable.",
}
def calc_ltt_ontario(p: float) -> float:
    """Ontario Land Transfer Tax (provincial portion), excluding rebates."""
    p = round(float(p), 2)
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
    p = round(float(p), 2)
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
    p = round(float(p), 2)
    tax = 0.0
    # 1% on first 200k
    tax += min(p, 200000) * 0.01
    # 2% on 200k-2M
    if p > 200000:
        tax += min(p, 2000000) - 200000
        tax *= 1.0  # keep readable; actual rate applied below
    # re-compute cleanly to avoid confusion:
    tax = min(p, 200000) * 0.01
    if p > 200000:
        tax += (min(p, 2000000) - 200000) * 0.02
    # 3% on 2M-3M
    if p > 2000000:
        tax += (min(p, 3000000) - 2000000) * 0.03
    # 5% on 3M+
    if p > 3000000:
        tax += (p - 3000000) * 0.05
    return tax

def _calc_bracket_tax(amount: float, brackets: list[tuple[float, float]]) -> float:
    """Generic marginal tax calculator.
    brackets: list of (upper_limit, rate) in ascending order; last upper_limit can be float('inf').
    """
    x = float(amount)
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
    p = float(price)
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
    p = float(price)
    if p <= 500:
        return 0.0
    if p <= 6300:
        return 25.0
    return 25.0 + (p - 6300.0) * 0.004

def calc_land_transfer_tax_manitoba(price: float) -> float:
    """Manitoba land transfer tax (provincial schedule)."""
    p = float(price)
    brackets = [
        (30000.0, 0.0),
        (90000.0, 0.005),
        (150000.0, 0.01),
        (200000.0, 0.015),
        (float("inf"), 0.02),
    ]
    return _calc_bracket_tax(p, brackets)

def calc_transfer_duty_quebec_standard(price: float) -> float:
    """Quebec 'Welcome tax' style duties (standard schedule used by many municipalities).
    Note: Municipalities may apply additional rates in higher brackets; use override if needed.
    Thresholds change periodically; these reflect commonly used thresholds in recent guidance.
    """
    p = float(price)
    brackets = [
        (62900.0, 0.005),
        (315000.0, 0.01),
        (552300.0, 0.015),
        (1104700.0, 0.02),
        (2136500.0, 0.025),
        (3113000.0, 0.035),
        (float("inf"), 0.04),
    ]
    return _calc_bracket_tax(p, brackets)

def calc_property_transfer_tax_new_brunswick(price: float) -> float:
    """New Brunswick property transfer tax (simplified): 1% of assessed value.
    We use purchase price as proxy.
    """
    p = float(price)
    return max(0.0, p) * 0.01

def calc_deed_transfer_tax_nova_scotia_default(price: float, rate: float = 0.015) -> float:
    """Nova Scotia deed transfer tax is municipal. Default 1.5% (common, e.g. HRM).
    Use override for a precise local rate.
    """
    p = float(price)
    return max(0.0, p) * float(rate)

def calc_real_property_transfer_tax_pei(price: float) -> float:
    """Prince Edward Island real property transfer tax (simplified).
    Historically 1% on the portion above $30,000. Recent budgets introduced a higher rate above $1,000,000.
    Implemented here as: 1% on (min(price, 1M) - 30k) + 2% on amount above 1M.
    Use override for edge cases / exemptions.
    """
    p = float(price)
    if p <= 30000:
        return 0.0
    base = (min(p, 1_000_000.0) - 30000.0) * 0.01
    extra = (p - 1_000_000.0) * 0.02 if p > 1_000_000.0 else 0.0
    return max(0.0, base + extra)

def calc_registration_fee_newfoundland(price: float) -> float:
    """Newfoundland & Labrador registration of deeds fee (simplified).
    Base $100 covers first $500; then $0.40 per $100 over $500 (rounded down). Capped at $5,000.
    """
    p = float(price)
    if p <= 0:
        return 0.0
    fee = 100.0
    if p > 500.0:
        increments = math.floor((p - 500.0) / 100.0)
        fee += increments * 0.40
    return min(5000.0, fee)

def calc_transfer_tax(province: str, price: float, first_time_buyer: bool, toronto_property: bool, override_amount: float = 0.0, asof_date: datetime.date | None = None) -> dict:
    """Return dict with total and components: {'prov': x, 'muni': y, 'total': z, 'note': str}.

    If override_amount > 0, it is used as the provincial component (and a note is added).
    """
    province = (province or "Ontario").strip()
    price = round(float(price), 2)
    prov = 0.0
    muni = 0.0
    note = ""

    # User override always wins (keeps behavior predictable)
    if override_amount and float(override_amount) > 0:
        prov = float(override_amount)
        note = "Using your 'Transfer Tax Override' amount for this province/municipality."
        return {"prov": prov, "muni": 0.0, "total": prov, "note": note}

    if province == "Ontario":
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


    elif province == "British Columbia":
        prov = calc_ptt_bc(price)
        note = "BC PTT excludes additional taxes (e.g., foreign buyer/speculation) and local exemptions."

    elif province == "Alberta":
        # Alberta has registration fees rather than a transfer tax; we estimate the transfer-of-land fee only.
        prov = calc_land_title_fee_alberta(price)
        note = "Alberta uses land title registration fees (transfer-of-land). Mortgage registration fees not included."

    elif province == "Saskatchewan":
        prov = calc_land_title_fee_saskatchewan(price)
        note = "Saskatchewan uses land title transfer fees (simplified). Mortgage registration fees not included."

    elif province == "Manitoba":
        prov = calc_land_transfer_tax_manitoba(price)

    elif province == "Quebec":
        prov = calc_transfer_duty_quebec_standard(price)
        note = "Quebec duties can vary by municipality (some apply higher rates in top brackets). Use override for precision."

    elif province == "New Brunswick":
        prov = calc_property_transfer_tax_new_brunswick(price)

    elif province == "Nova Scotia":
        prov = calc_deed_transfer_tax_nova_scotia_default(price, rate=0.015)
        note = "Nova Scotia deed transfer tax is municipal; defaulting to 1.5%. Use override for your municipality."

    elif province == "Prince Edward Island":
        prov = calc_real_property_transfer_tax_pei(price)
        note = "PEI transfer tax can include exemptions/eligibility rules; override if you have a local exemption."

    elif province == "Newfoundland and Labrador":
        prov = calc_registration_fee_newfoundland(price)
        note = "NL uses registration fees; this estimates the deed registration portion only."

    else:
        prov = 0.0
        note = "No built-in transfer tax rule for this region. Use 'Transfer Tax Override' if applicable."

    total = prov + muni
    return {"prov": prov, "muni": muni, "total": total, "note": note}

# --- v113: RESTORE DARK INPUTS (surgical; does not touch tooltips) ---
