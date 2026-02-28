import math
import re
import numpy as np
import pandas as pd

from .mortgage import _annual_nominal_pct_to_monthly_rate, _monthly_rate_to_annual_nominal_pct
from .policy_canada import (
    insured_mortgage_price_cap,
    min_down_payment_canada,
    cmhc_premium_rate_from_ltv,
    mortgage_default_insurance_sales_tax_rate,
)


def _f(x, default=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return float(default)


def _i(x, default=0):
    try:
        return int(x)
    except (TypeError, ValueError):
        return int(default)


def _clamp_monthly_rate(mr: float) -> float:
    """Clamp an effective monthly rate to a mathematically safe range for amortization math."""
    try:
        x = float(mr)
    except (TypeError, ValueError):
        x = 0.0
    # Prevent (1+mr) <= 0 from breaking pow() / division in payment math.
    return max(x, -0.999999)


def _mortgage_payment(principal: float, mr: float, rem_months: int) -> float:
    """Fixed payment for remaining balance `principal` at monthly rate `mr` over `rem_months`.

    Supports negative rates (hypothetical) as long as (1+mr) > 0. For mr≈0, falls back to principal/rem_months.
    """
    try:
        p = float(principal)
    except Exception:
        p = 0.0
    try:
        n = int(rem_months)
    except Exception:
        n = 0
    n = max(1, n)

    r = _clamp_monthly_rate(mr)
    if abs(r) < 1e-12:
        return p / float(n)

    base = 1.0 + r
    if base <= 0.0:
        base = 1e-12

    try:
        pow_ = base ** float(n)
    except Exception:
        return p / float(n)

    denom = pow_ - 1.0
    if abs(denom) < 1e-12:
        return p / float(n)

    return p * (r * pow_) / denom


def _annual_effective_dec_to_monthly_log_mu(r_annual: float) -> float:
    """Convert an annual *effective* return (decimal, e.g., 0.06) into monthly log drift (mu).

    We model growth factors as exp(mu + sigma*z - 0.5*sigma^2), so setting mu = ln(1+r_annual)/12
    ensures the expected monthly growth matches the annual effective input when compounded.
    """
    try:
        r = float(r_annual)
    except (TypeError, ValueError):
        r = 0.0
    # Guard log1p domain; cap at just above -100%.
    if r <= -0.999999:
        r = -0.999999
    return math.log1p(r) / 12.0


def _annual_effective_pct_to_monthly_log_mu(pct_annual: float) -> float:
    """Annual effective % (e.g., 6.0) -> monthly log drift."""
    try:
        return _annual_effective_dec_to_monthly_log_mu(float(pct_annual) / 100.0)
    except Exception:
        return 0.0


def _annual_effective_dec_to_monthly_eff(r_annual: float) -> float:
    """Annual *effective* rate (decimal) -> monthly effective rate (decimal)."""
    try:
        r = float(r_annual)
    except (TypeError, ValueError):
        r = 0.0
    if r <= -0.999999:
        r = -0.999999
    try:
        return (1.0 + r) ** (1.0 / 12.0) - 1.0
    except Exception:
        # Fallback for weird edge cases
        return r / 12.0


def _estimate_mc_mem_bytes(num_sims: int, months: int, arrays: int = 8, dtype_bytes: int = 4) -> int:
    """Rough memory estimate for vectorized MC path arrays."""
    try:
        return int(max(0, int(num_sims)) * max(0, int(months)) * int(arrays) * int(dtype_bytes))
    except Exception:
        return 0


def _taxable_gain_after_reg_shelter(gain, basis, years, enabled, initial_room, annual_room):
    """Conservative registered-shelter approximation.

    If enabled, treat up to (initial_room + annual_room * years) of *basis* as sheltered, and shelter gains pro-rata.
    This is NOT a full TFSA/RRSP tax engine; it is a sensitivity knob that reduces taxable capital gains.

    Works with scalars or numpy arrays.
    """
    if not bool(enabled):
        return gain
    try:
        y = int(max(0, int(years)))
    except Exception:
        y = 0
    try:
        cap = max(0.0, float(initial_room)) + max(0.0, float(annual_room)) * float(y)
    except Exception:
        cap = 0.0
    if cap <= 0.0:
        return gain

    g = np.asarray(gain, dtype=np.float64)
    b = np.asarray(basis, dtype=np.float64)

    sheltered_basis = np.minimum(b, cap)
    frac = np.where(b > 0.0, sheltered_basis / b, 0.0)
    taxable = g * (1.0 - frac)

    try:
        if np.isscalar(gain) and np.isscalar(basis):
            return float(taxable)
    except Exception:
        pass
    return taxable


def _cg_tax_due(taxable_gain, eff_cg_rate, policy, threshold):
    """Compute capital gains tax due under an optional inclusion-policy toggle.

    - eff_cg_rate is the *effective* tax rate on gains under the baseline inclusion (decimal; e.g., 0.225).
    - policy:
        - "current" (default): flat eff_cg_rate on all gains.
        - "proposed_2_3_over_250k": applies a 4/3 multiplier to the effective rate above threshold,
          reflecting 50% -> 66.67% inclusion (i.e., 0.5*m -> (2/3)*m).
    Works with scalars or numpy arrays.
    """
    try:
        eff = max(0.0, float(eff_cg_rate))
    except Exception:
        eff = 0.0
    if eff <= 0.0:
        try:
            if np.isscalar(taxable_gain):
                return 0.0
            return np.zeros_like(np.asarray(taxable_gain, dtype=np.float64))
        except Exception:
            return 0.0

    g = np.maximum(0.0, np.asarray(taxable_gain, dtype=np.float64))
    pol = str(policy or "current").strip().lower()
    if pol in ("tiered_50_66", "tiered", "proposed_2_3_over_250k", "proposed", "hypothetical"):
        try:
            t = max(0.0, float(threshold))
        except Exception:
            t = 0.0
        below = np.minimum(g, t)
        above = np.maximum(0.0, g - t)
        tax = eff * below + (eff * (4.0 / 3.0)) * above
    else:
        tax = eff * g

    try:
        if np.isscalar(taxable_gain):
            return float(tax)
    except Exception:
        pass
    return tax


def _run_monte_carlo_vectorized(
    *,
    years: int,
    num_sims: int,
    buyer_mo: float,
    renter_mo: float,
    apprec_annual_dec: float,
    mr_init: float,
    nm: int,
    pmt_init: float,
    down: float,
    close: float,
    mort: float,
    price: float,
    rent: float,
    p_tax_rate: float,
    maint_rate: float,
    repair_rate: float,
    condo: float,
    h_ins: float,
    o_util: float,
    r_ins: float,
    r_util: float,
    sell_cost: float,
    rent_inf_eff: float,
    rent_control_frequency_years: int,
    moving_cost: float,
    moving_freq: float,
    inf_mo: float,
    ret_std: float,
    apprec_std: float,
    invest_diff: bool,
    rent_closing: bool,
    mkt_corr: float,
    rate_mode: str,
    rate_reset_years,
    rate_reset_to,
    rate_reset_step_pp: float,
    rate_shock_enabled: bool,
    rate_shock_start_year,
    rate_shock_duration_years,
    rate_shock_pp: float,
    crisis_enabled: bool,
    crisis_year,
    crisis_stock_dd: float,
    crisis_house_dd: float,
    crisis_duration_months: int,
    budget_enabled: bool,
    monthly_income: float,
    monthly_nonhousing: float,
    income_growth_pct: float,
    budget_allow_withdraw: bool,
    condo_inf_mo: float,
    assume_sale_end: bool,
    is_principal_residence: bool,
    show_liquidation_view: bool,
    cg_tax_end: float,
    home_sale_legal_fee: float,
    mort_rate_nominal_pct: float,
    canadian_compounding: bool,
    prop_tax_growth_model: str,
    prop_tax_hybrid_addon_pct: float,
    investment_tax_mode: str,
    special_assessment_amount: float = 0.0,
    special_assessment_month: int = 0,
    cg_inclusion_policy: str = "current",
    cg_inclusion_threshold: float = 250000.0,
    reg_shelter_enabled: bool = False,
    reg_initial_room: float = 0.0,
    reg_annual_room: float = 0.0,
    mc_seed=None,
    progress_cb=None,
    summary_only: bool = False,
    precomputed_shocks=None,
):
    """Vectorized Monte Carlo simulation.

    Returns (df, win_pct) where df matches the existing MC output schema from run_simulation_core.

    Notes:
    - Preserves the full monthly path medians/means/percentiles used by the UI.
    - Stores only the *random-dependent* per-sim paths as float32 arrays for memory efficiency.
    """

    months = int(max(1, years) * 12)
    num_sims = int(max(1, num_sims))

    # Stable column names expected by the UI (keep consistent across MC pathways)
    _LIQ_B = "Buyer Liquidation NW"
    _LIQ_R = "Renter Liquidation NW"

    # State arrays (float64 for stability; stored paths float32)
    init_r = float(down) + (float(close) if rent_closing else 0.0)
    r_nw = np.full(num_sims, init_r, dtype=np.float64)
    b_nw = np.zeros(num_sims, dtype=np.float64)

    # If monthly surplus investing is OFF, we still track the monthly cost difference as cash (0% return)
    # so comparisons remain economically meaningful.
    r_cash = np.zeros(num_sims, dtype=np.float64)
    b_cash = np.zeros(num_sims, dtype=np.float64)

    r_basis = np.full(num_sims, init_r, dtype=np.float64)
    b_basis = np.zeros(num_sims, dtype=np.float64)

    c_home = np.full(num_sims, float(price), dtype=np.float64)
    tax_base = np.full(num_sims, float(price), dtype=np.float64)

    cum_b_op = np.zeros(num_sims, dtype=np.float64)
    cum_r_op = 0.0

    # Deterministic scalars
    c_mort = float(mort)
    c_rent = float(rent)

    # Rent increase cadence (years). Only meaningful when rent control is enabled in the UI,
    # but we accept any positive integer for robustness.
    try:
        rent_step_years = max(1, int(rent_control_frequency_years))
    except Exception:
        rent_step_years = 1

    c_condo = float(condo)
    c_h_ins = float(h_ins)
    c_o_util = float(o_util)
    c_r_ins = float(r_ins)
    c_r_util = float(r_util)

    # Track nominal annual rate across resets/shocks
    cur_rate_nominal_pct = (
        float(mort_rate_nominal_pct)
        if mort_rate_nominal_pct is not None
        else float(_monthly_rate_to_annual_nominal_pct(float(mr_init), bool(canadian_compounding)))
    )
    mr = float(mr_init)
    pmt = float(pmt_init)
    shock_was_active = False

    # Correlated shocks
    rho = float(np.clip(mkt_corr, -0.999999, 0.999999))
    rho_abs = abs(rho)
    a = math.sqrt(rho_abs)
    b = math.sqrt(max(0.0, 1.0 - rho_abs))
    rho_sign = 1.0 if rho >= 0 else -1.0

    # Monthly sigmas
    ret_std_mo = float(ret_std) / math.sqrt(12.0) if ret_std else 0.0
    app_std_mo = float(apprec_std) / math.sqrt(12.0) if apprec_std else 0.0

    buyer_mu = float(buyer_mo) - 0.5 * (ret_std_mo**2)
    renter_mu = float(renter_mo) - 0.5 * (ret_std_mo**2)
    home_mu = _annual_effective_dec_to_monthly_log_mu(float(apprec_annual_dec)) - 0.5 * (app_std_mo**2)

    rng = np.random.default_rng(int(mc_seed)) if mc_seed is not None else np.random.default_rng()

    # Degenerate MC (volatility effectively zero) still runs through the vectorized pipeline,
    # but we flag it for UI messaging and determinism checks.
    mc_degenerate = (ret_std_mo <= 0.0) and (app_std_mo <= 0.0)

    # Random-dependent stored paths (float32 to reduce memory)
    # For bias/heatmap solvers we optionally run a summary-only mode that computes
    # terminal stats without allocating full (num_sims × months) arrays.
    buyer_nw_paths = renter_nw_paths = buyer_unrec_paths = None
    prop_tax_paths = maint_paths = repair_paths = buy_pmt_paths = deficit_paths = None

    # Deterministic monthly series (used only when emitting the full time-series df)
    interest_vec = condo_vec = hins_vec = util_vec = sa_vec = None
    rent_vec = rins_vec = rutil_vec = moving_vec = rent_pmt_vec = renter_unrec_vec = None

    if not bool(summary_only):
        buyer_nw_paths = np.empty((num_sims, months), dtype=np.float32)
        renter_nw_paths = np.empty((num_sims, months), dtype=np.float32)
        buyer_unrec_paths = np.empty((num_sims, months), dtype=np.float32)
        prop_tax_paths = np.empty((num_sims, months), dtype=np.float32)
        maint_paths = np.empty((num_sims, months), dtype=np.float32)
        repair_paths = np.empty((num_sims, months), dtype=np.float32)
        buy_pmt_paths = np.empty((num_sims, months), dtype=np.float32)
        deficit_paths = np.empty((num_sims, months), dtype=np.float32)

        interest_vec = np.empty(months, dtype=np.float64)
        condo_vec = np.empty(months, dtype=np.float64)
        hins_vec = np.empty(months, dtype=np.float64)
        util_vec = np.empty(months, dtype=np.float64)
        sa_vec = np.empty(months, dtype=np.float64)
        rent_vec = np.empty(months, dtype=np.float64)
        rins_vec = np.empty(months, dtype=np.float64)
        rutil_vec = np.empty(months, dtype=np.float64)
        moving_vec = np.empty(months, dtype=np.float64)
        rent_pmt_vec = np.empty(months, dtype=np.float64)
        renter_unrec_vec = np.empty(months, dtype=np.float64)

    next_move = float(moving_freq) * 12.0

    # Progress pacing (match legacy ~100 updates)
    prog_step = max(1, int(months // 100))

    # Precompute hybrid add-on monthly cap if needed
    try:
        addon_mo = (1.0 + float(prop_tax_hybrid_addon_pct) / 100.0) ** (1.0 / 12.0) - 1.0
    except (TypeError, ValueError):
        addon_mo = 0.0

    prop_mode = str(prop_tax_growth_model or "")

    for m in range(1, months + 1):
        # --- Random growth ---
        if (ret_std_mo > 0.0) or (app_std_mo > 0.0):
            if precomputed_shocks is not None:
                try:
                    z_sys = precomputed_shocks[0][m - 1]
                    z_stock = precomputed_shocks[1][m - 1]
                    z_house = precomputed_shocks[2][m - 1]
                except Exception:
                    z_sys = rng.standard_normal(num_sims)
                    z_stock = rng.standard_normal(num_sims)
                    z_house = rng.standard_normal(num_sims)
            else:
                z_sys = rng.standard_normal(num_sims)
                z_stock = rng.standard_normal(num_sims)
                z_house = rng.standard_normal(num_sims)
            stock_shock = (a * z_sys) + (b * z_stock)
            house_shock = (a * rho_sign * z_sys) + (b * z_house)

            # Clip exponent to keep values finite even under extreme volatility inputs
            _EXP_CLIP = 50.0
            b_growth = np.exp(np.clip(buyer_mu + ret_std_mo * stock_shock, -_EXP_CLIP, _EXP_CLIP))
            r_growth = np.exp(np.clip(renter_mu + ret_std_mo * stock_shock, -_EXP_CLIP, _EXP_CLIP))
            home_growth = np.exp(np.clip(home_mu + app_std_mo * house_shock, -_EXP_CLIP, _EXP_CLIP))
        else:
            bg = math.exp(float(buyer_mo))
            rg = math.exp(float(renter_mo))
            hg = math.exp(_annual_effective_dec_to_monthly_log_mu(float(apprec_annual_dec)))
            b_growth = bg
            r_growth = rg
            home_growth = hg

        # --- Mortgage rate resets (renewals) ---
        rate_changed = False
        if rate_mode == "Reset every N years" and (rate_reset_years is not None) and (rate_reset_to is not None):
            try:
                reset_months = int(rate_reset_years) * 12
            except Exception:
                reset_months = 0
            if reset_months > 0 and m > 1 and ((m - 1) % reset_months == 0):
                reset_idx = int((m - 1) / reset_months)
                cur_rate_nominal_pct = float(rate_reset_to) + float(rate_reset_step_pp) * max(0, reset_idx - 1)
                rate_changed = True

        shock_active = False
        if rate_shock_enabled and (rate_shock_pp is not None):
            try:
                start_m = int(rate_shock_start_year) * 12 + 1
                dur_m = int(rate_shock_duration_years) * 12
                end_m = start_m + max(0, dur_m) - 1
            except (TypeError, ValueError):
                start_m, end_m = 61, 120
            shock_active = start_m <= m <= end_m

        eff_nominal = float(cur_rate_nominal_pct) + (float(rate_shock_pp) if shock_active else 0.0)
        mr = _clamp_monthly_rate(float(_annual_nominal_pct_to_monthly_rate(eff_nominal, bool(canadian_compounding))))

        if rate_changed or (shock_active != shock_was_active):
            rem_months = max(1, int(nm) - (m - 1))
            pmt = _mortgage_payment(float(c_mort), float(mr), int(rem_months))
        shock_was_active = shock_active

        # --- Property tax modeling ---
        if prop_mode.startswith("Market"):
            tax_base = c_home
        elif prop_mode.startswith("Inflation"):
            tax_base = tax_base * (1.0 + float(inf_mo))
        else:
            cap_mo = (1.0 + float(inf_mo)) * (1.0 + float(addon_mo)) - 1.0
            target = c_home
            up = target >= tax_base
            tax_base = np.where(
                up, np.minimum(tax_base * (1.0 + cap_mo), target), np.maximum(tax_base / (1.0 + cap_mo), target)
            )

        m_tax = tax_base * float(p_tax_rate) / 12.0
        m_maint = c_home * float(maint_rate) / 12.0
        m_repair = c_home * float(repair_rate) / 12.0

        # One-time special assessment shock (buyer-only, unrecoverable)
        try:
            _sa_m = int(special_assessment_month)
        except Exception:
            _sa_m = 0
        m_special = float(special_assessment_amount) if (_sa_m > 0 and m == _sa_m) else 0.0

        inte = float(c_mort) * float(mr) if float(c_mort) > 0 else 0.0
        princ = (float(pmt) - inte) if float(c_mort) > 0 else 0.0
        if princ > float(c_mort):
            princ = float(c_mort)

        # Buyer outflows (capture the *current* deterministic fees before applying monthly inflation)
        condo_paid = float(c_condo)
        h_ins_paid = float(c_h_ins)
        o_util_paid = float(c_o_util)

        b_pmt0 = float(pmt) if float(c_mort) > 0 else 0.0
        b_out = b_pmt0 + m_tax + m_maint + m_repair + condo_paid + h_ins_paid + o_util_paid + m_special
        b_op = float(inte) + m_tax + m_maint + m_repair + condo_paid + h_ins_paid + o_util_paid + m_special

        # Renter outflows (deterministic)
        rent_paid = float(c_rent)
        r_ins_paid = float(c_r_ins)
        r_util_paid = float(c_r_util)
        skip_last_move = bool(assume_sale_end) and (m == months)
        m_moving = float(moving_cost) if (m == next_move and not skip_last_move) else 0.0
        r_out = (
            float(c_rent) + float(c_r_ins) + float(c_r_util) + float(m_moving)
        )  # Total renter outflow (incl. moving)
        if m == next_move:
            next_move += float(moving_freq) * 12.0

        diff = b_out - float(r_out)

        # Budget / investing
        if budget_enabled:
            inc0 = float(monthly_income) if monthly_income is not None else 0.0
            nonh = float(monthly_nonhousing) if monthly_nonhousing is not None else 0.0
            g = float(income_growth_pct) / 100.0 if income_growth_pct is not None else 0.0
            inc0 = max(0.0, inc0)
            nonh = max(0.0, nonh)
            g = max(-0.99, g)
            inc_t = inc0 * ((1.0 + g) ** ((m - 1) / 12.0)) if g != 0 else inc0

            b_budget_net = float(inc_t) - nonh - b_out
            r_budget_net = float(inc_t) - nonh - float(r_out)

            # Buyer
            pos = b_budget_net >= 0
            if np.any(pos):
                b_nw[pos] += b_budget_net[pos]
                b_basis[pos] += b_budget_net[pos]
            neg = ~pos
            if np.any(neg):
                need = -b_budget_net[neg]
                if budget_allow_withdraw:
                    have = b_nw[neg]
                    ok = have >= need
                    if np.any(ok):
                        idx = np.flatnonzero(neg)[ok]
                        need_ok = need[ok]
                        have_ok = have[ok]
                        # adjust basis proportionally
                        nz = have_ok > 0
                        if np.any(nz):
                            b_basis[idx[nz]] = b_basis[idx[nz]] * np.maximum(
                                0.0, (have_ok[nz] - need_ok[nz]) / have_ok[nz]
                            )
                        b_nw[idx] = have_ok - need_ok
                    if np.any(~ok):
                        idx2 = np.flatnonzero(neg)[~ok]
                        # shortfall accum not used in MC summary; ensure portfolio goes to 0
                        b_basis[idx2] = 0.0
                        b_nw[idx2] = 0.0
                else:
                    # no withdraw allowed: no change to portfolio
                    pass

            # Renter (scalar budget_net applied to all sims)
            if r_budget_net >= 0:
                r_nw += float(r_budget_net)
                r_basis += float(r_budget_net)
            else:
                need_r = -float(r_budget_net)
                if budget_allow_withdraw:
                    okr = r_nw >= need_r
                    if np.any(okr):
                        idx_ok = np.flatnonzero(okr)
                        have_ok = r_nw[idx_ok]
                        nz = have_ok > 0
                        if np.any(nz):
                            idx_nz = idx_ok[nz]
                            have_nz = have_ok[nz]
                            r_basis[idx_nz] = r_basis[idx_nz] * np.maximum(0.0, (have_nz - need_r) / have_nz)
                        r_nw[idx_ok] = have_ok - need_r
                    if np.any(~okr):
                        idx_bad = np.flatnonzero(~okr)
                        r_basis[idx_bad] = 0.0
                        r_nw[idx_bad] = 0.0
                else:
                    pass

        elif invest_diff:
            mask = diff > 0
            if np.any(mask):
                r_nw[mask] += diff[mask]
                r_basis[mask] += diff[mask]
            if np.any(~mask):
                d2 = -diff[~mask]
                b_nw[~mask] += d2
                b_basis[~mask] += d2

        else:
            # Surplus investing OFF → track the monthly difference as cash (0% return), not invested.
            mask = diff > 0
            if np.any(mask):
                r_nw[mask] += diff[mask]
                r_basis[mask] += diff[mask]
                r_cash[mask] += diff[mask]
            if np.any(~mask):
                d2 = -diff[~mask]
                b_nw[~mask] += d2
                b_basis[~mask] += d2
                b_cash[~mask] += d2

        # Apply growth
        # Cash (r_cash/b_cash) earns 0% return, so we only apply market growth to the invested portion.
        r_nw = (r_nw - r_cash) * r_growth + r_cash
        b_nw = (b_nw - b_cash) * b_growth + b_cash
        c_home = c_home * home_growth

        # Crisis shock (apply only to the invested portion, not to cash)
        if crisis_enabled:
            try:
                crisis_m_start = int(max(1.0, float(crisis_year)) * 12)
            except (TypeError, ValueError):
                crisis_m_start = int(5 * 12)
            dur = int(max(1, int(crisis_duration_months))) if crisis_duration_months is not None else 1
            if crisis_m_start <= m < crisis_m_start + dur:
                stock_dd = float(np.clip(crisis_stock_dd, 0.0, 0.95))
                house_dd = float(np.clip(crisis_house_dd, 0.0, 0.95))
                b_invested = b_nw - b_cash
                r_invested = r_nw - r_cash
                b_invested *= 1.0 - stock_dd
                r_invested *= 1.0 - stock_dd
                b_nw = b_invested + b_cash
                r_nw = r_invested + r_cash
                c_home *= 1.0 - house_dd

        # Mortgage balance update
        if float(c_mort) > 0:
            c_mort -= float(princ)
        if float(c_mort) < 0:
            c_mort = 0.0

        # Rent inflation (stepwise cadence when rent control frequency > 1)
        if rent_step_years <= 1:
            if (m % 12) == 0:
                c_rent *= 1.0 + float(rent_inf_eff)
        else:
            if (m % (12 * rent_step_years)) == 0:
                c_rent *= (1.0 + float(rent_inf_eff)) ** float(rent_step_years)

        # Exit costs at horizon
        exit_cost = (c_home * float(sell_cost)) if (assume_sale_end and m == months) else 0.0
        exit_legal_fee = (
            float(home_sale_legal_fee) if (assume_sale_end and m == months and home_sale_legal_fee is not None) else 0.0
        )

        # Accumulate unrecoverable costs (match simulate_single order: update then report)
        cum_b_op += b_op
        cum_r_op += float(r_out)

        # Buyer net worth should reflect closing costs paid at purchase.
        b_val = (c_home - float(c_mort)) + b_nw - float(close) - exit_cost - float(exit_legal_fee)
        b_unrec = cum_b_op + float(close) + exit_cost + float(exit_legal_fee)

        # Store paths (full output mode only)
        if buyer_nw_paths is not None:
            idx = m - 1
            buyer_nw_paths[:, idx] = b_val.astype(np.float32, copy=False)
            renter_nw_paths[:, idx] = r_nw.astype(np.float32, copy=False)
            buyer_unrec_paths[:, idx] = b_unrec.astype(np.float32, copy=False)
            prop_tax_paths[:, idx] = m_tax.astype(np.float32, copy=False)
            maint_paths[:, idx] = m_maint.astype(np.float32, copy=False)
            repair_paths[:, idx] = m_repair.astype(np.float32, copy=False)
            buy_pmt_paths[:, idx] = b_out.astype(np.float32, copy=False)
            deficit_paths[:, idx] = diff.astype(np.float32, copy=False)

            # Deterministic series
            interest_vec[idx] = float(inte)
            condo_vec[idx] = float(condo_paid)
            hins_vec[idx] = float(h_ins_paid)
            util_vec[idx] = float(o_util_paid)
            sa_vec[idx] = float(m_special)
            rent_vec[idx] = float(rent_paid)
            rins_vec[idx] = float(r_ins_paid)
            rutil_vec[idx] = float(r_util_paid)
            moving_vec[idx] = float(m_moving)
            rent_pmt_vec[idx] = float(r_out)
            renter_unrec_vec[idx] = float(cum_r_op)

        # CPI inflation for deterministic fees (applied AFTER storing the month-m values)
        c_condo *= 1.0 + (float(condo_inf_mo) if condo_inf_mo is not None else float(inf_mo))
        c_h_ins *= 1.0 + float(inf_mo)
        c_o_util *= 1.0 + float(inf_mo)
        c_r_ins *= 1.0 + float(inf_mo)
        c_r_util *= 1.0 + float(inf_mo)

        # Progress
        if progress_cb is not None and ((m % prog_step == 0) or (m == months)):
            done = int(round((m / months) * num_sims))
            try:
                progress_cb(done, num_sims)
            except Exception:
                pass

    # Summary-only mode: compute terminal stats only (bias solver acceleration)
    if bool(summary_only):
        try:
            b_last = np.asarray(b_val, dtype=np.float64)
            r_last = np.asarray(r_nw, dtype=np.float64)
        except Exception:
            b_last = np.full(num_sims, np.nan, dtype=np.float64)
            r_last = np.full(num_sims, np.nan, dtype=np.float64)

        finite = np.isfinite(b_last) & np.isfinite(r_last)
        win_pct = None
        if np.any(finite):
            b_f = b_last[finite]
            r_f = r_last[finite]
            diff = b_f - r_f
            scale = float(np.nanmedian(np.abs(np.concatenate([b_f, r_f])))) if b_f.size else 1.0
            scale = max(1.0, scale)
            tol = max(1e-6, 1e-9 * scale)
            wins = int(np.count_nonzero(diff > tol))
            ties = int(np.count_nonzero(np.abs(diff) <= tol))
            denom = float(b_f.size)
            win_pct = (wins + 0.5 * ties) / max(1.0, denom) * 100.0
            if (not np.isfinite(win_pct)) or (win_pct < -1e-9) or (win_pct > 100.0 + 1e-9):
                win_pct = None

            b_mean = float(np.mean(b_f))
            r_mean = float(np.mean(r_f))
            b_med = float(np.median(b_f))
            r_med = float(np.median(r_f))
        else:
            b_mean = float("nan")
            r_mean = float("nan")
            b_med = float("nan")
            r_med = float("nan")

        df = pd.DataFrame(
            {
                "Month": [int(months)],
                "Year": [int(years)],
                "Buyer Net Worth": [b_med],
                "Renter Net Worth": [r_med],
                "Buyer NW Mean": [b_mean],
                "Renter NW Mean": [r_mean],
            }
        )

        # Optional after-tax liquidation view at horizon (summary-only)
        liq_win_pct = None
        if bool(show_liquidation_view):
            try:
                try:
                    eff_cg = max(0.0, float(cg_tax_end) / 100.0)
                except (TypeError, ValueError):
                    eff_cg = 0.0

                # If annual drag mode is active, don't apply extra CG at liquidation
                if str(investment_tax_mode or "").startswith("Annual"):
                    eff_cg = 0.0

                exit_cost_final = (c_home * float(sell_cost)) if bool(assume_sale_end) else 0.0
                exit_legal_fee_final = (
                    float(home_sale_legal_fee) if (bool(assume_sale_end) and home_sale_legal_fee is not None) else 0.0
                )

                b_gain = np.maximum(0.0, b_nw - b_basis)
                r_gain = np.maximum(0.0, r_nw - r_basis)

                b_taxable_gain = _taxable_gain_after_reg_shelter(
                    b_gain, b_basis, years, reg_shelter_enabled, reg_initial_room, reg_annual_room
                )
                r_taxable_gain = _taxable_gain_after_reg_shelter(
                    r_gain, r_basis, years, reg_shelter_enabled, reg_initial_room, reg_annual_room
                )

                b_tax = _cg_tax_due(b_taxable_gain, eff_cg, cg_inclusion_policy, cg_inclusion_threshold)
                r_tax = _cg_tax_due(r_taxable_gain, eff_cg, cg_inclusion_policy, cg_inclusion_threshold)

                b_port_after_tax = b_nw - b_tax
                r_port_after_tax = r_nw - r_tax

                # Home capital gains tax (only if selling at horizon AND not principal residence)
                is_principal_residence = bool(is_principal_residence)
                eff_home_cg = 0.0
                try:
                    eff_home_cg = max(0.0, float(cg_tax_end) / 100.0)
                except Exception:
                    eff_home_cg = 0.0

                home_tax_final = 0.0
                if bool(assume_sale_end) and (not is_principal_residence) and eff_home_cg > 0.0:
                    home_acb = float(price) + float(close)  # purchase price + acquisition costs proxy
                    home_proceeds_net = (
                        np.asarray(c_home, dtype=np.float64)
                        - np.asarray(exit_cost_final, dtype=np.float64)
                        - float(exit_legal_fee_final)
                    )
                    home_gain = np.maximum(0.0, home_proceeds_net - float(home_acb))
                    home_tax_final = _cg_tax_due(home_gain, eff_home_cg, cg_inclusion_policy, cg_inclusion_threshold)

                home_cash = (
                    (np.asarray(c_home, dtype=np.float64) - np.asarray(c_mort, dtype=np.float64))
                    if bool(assume_sale_end)
                    else 0.0
                )

                b_liq_vals = (
                    np.asarray(home_cash, dtype=np.float64)
                    + np.asarray(b_port_after_tax, dtype=np.float64)
                    - np.asarray(close, dtype=np.float64)
                    - np.asarray(exit_cost_final, dtype=np.float64)
                    - float(exit_legal_fee_final)
                    - np.asarray(home_tax_final, dtype=np.float64)
                )
                r_liq_vals = r_port_after_tax

                finite2 = np.isfinite(b_liq_vals) & np.isfinite(r_liq_vals)
                if np.any(finite2):
                    b2 = b_liq_vals[finite2]
                    r2 = r_liq_vals[finite2]
                    diff2 = b2 - r2
                    scale2 = float(np.nanmedian(np.abs(np.concatenate([b2, r2])))) if b2.size else 1.0
                    scale2 = max(1.0, scale2)
                    tol2 = max(1e-6, 1e-9 * scale2)
                    wins2 = int(np.count_nonzero(diff2 > tol2))
                    ties2 = int(np.count_nonzero(np.abs(diff2) <= tol2))
                    liq_win_pct = (wins2 + 0.5 * ties2) / max(1.0, float(b2.size)) * 100.0
                    if (not np.isfinite(liq_win_pct)) or (liq_win_pct < -1e-9) or (liq_win_pct > 100.0 + 1e-9):
                        liq_win_pct = None

                # Ensure liquidation columns are always present
                try:
                    df[_LIQ_B] = [float(np.nanmedian(b_liq_vals)) if np.any(np.isfinite(b_liq_vals)) else float("nan")]
                    df[_LIQ_R] = [float(np.nanmedian(r_liq_vals)) if np.any(np.isfinite(r_liq_vals)) else float("nan")]
                except Exception:
                    df[_LIQ_B] = [float("nan")]
                    df[_LIQ_R] = [float("nan")]
            except Exception as _e:
                df[_LIQ_B] = [float("nan")]
                df[_LIQ_R] = [float("nan")]
                try:
                    df.attrs["liquidation_error"] = str(_e)
                except Exception:
                    pass

        try:
            df.attrs["win_pct_pre_tax"] = float(win_pct) if win_pct is not None else None
            df.attrs["mc_num_sims"] = int(num_sims)
            df.attrs["mc_seed"] = None if mc_seed is None else int(mc_seed)
            df.attrs["win_pct_liquidation"] = liq_win_pct

            # Guardrails: record non-finite terminal values
            df.attrs["mc_win_n_finite"] = int(np.count_nonzero(finite))
            df.attrs["mc_end_n_nonfinite"] = int(np.count_nonzero(~finite))

            if win_pct is None:
                if not np.any(finite):
                    _msg = "No finite simulations for win% calculation (check extreme inputs)."
                else:
                    _msg = "Win% unavailable (non-finite or invalid)."
                _prev = str(df.attrs.get("mc_error", "") or "").strip()
                if _msg and (_msg not in _prev):
                    df.attrs["mc_error"] = (_prev + (" " if _prev else "") + _msg).strip()
        except Exception:
            pass
        return df, win_pct

    # Win rate (final-month values per-sim) with:
    # - finite filtering
    # - tolerance-based tie handling (avoids floating noise)
    b_last = buyer_nw_paths[:, -1].astype(np.float64)
    r_last = renter_nw_paths[:, -1].astype(np.float64)
    finite = np.isfinite(b_last) & np.isfinite(r_last)

    wins = 0
    ties = 0
    win_pct = None
    if np.any(finite):
        b_f = b_last[finite]
        r_f = r_last[finite]
        diff = b_f - r_f
        # Scale-aware tolerance (kept small; still resolves deterministic equality cleanly)
        scale = float(np.nanmedian(np.abs(np.concatenate([b_f, r_f])))) if b_f.size else 1.0
        scale = max(1.0, scale)
        tol = max(1e-6, 1e-9 * scale)
        wins = int(np.count_nonzero(diff > tol))
        ties = int(np.count_nonzero(np.abs(diff) <= tol))
        denom = float(b_f.size)
        win_pct = (wins + 0.5 * ties) / max(1.0, denom) * 100.0

        # Sanity: never silently emit an out-of-range probability
        if (not np.isfinite(win_pct)) or (win_pct < -1e-9) or (win_pct > 100.0 + 1e-9):
            win_pct = None
    else:
        win_pct = None

    # Summary series
    buyer_nw_med = np.median(buyer_nw_paths, axis=0)
    renter_nw_med = np.median(renter_nw_paths, axis=0)
    buyer_nw_low = np.percentile(buyer_nw_paths, 5, axis=0)
    buyer_nw_high = np.percentile(buyer_nw_paths, 95, axis=0)
    renter_nw_low = np.percentile(renter_nw_paths, 5, axis=0)
    renter_nw_high = np.percentile(renter_nw_paths, 95, axis=0)

    buyer_nw_mean = np.mean(buyer_nw_paths, axis=0)
    renter_nw_mean = np.mean(renter_nw_paths, axis=0)

    buyer_unrec_med = np.median(buyer_unrec_paths, axis=0)
    buyer_unrec_mean = np.mean(buyer_unrec_paths, axis=0)

    prop_tax_med = np.median(prop_tax_paths, axis=0)
    maint_med = np.median(maint_paths, axis=0)
    repair_med = np.median(repair_paths, axis=0)
    buy_pmt_med = np.median(buy_pmt_paths, axis=0)
    deficit_med = np.median(deficit_paths, axis=0)

    df = pd.DataFrame(
        {
            "Month": np.arange(1, months + 1, dtype=int),
            "Year": ((np.arange(1, months + 1, dtype=int) - 1) // 12 + 1),
            "Buyer Net Worth": buyer_nw_med,
            "Renter Net Worth": renter_nw_med,
            "Buyer NW Mean": buyer_nw_mean,
            "Renter NW Mean": renter_nw_mean,
            "Buyer NW Low": buyer_nw_low,
            "Buyer NW High": buyer_nw_high,
            "Renter NW Low": renter_nw_low,
            "Renter NW High": renter_nw_high,
            "Buyer Unrecoverable": buyer_unrec_med,
            "Renter Unrecoverable": renter_unrec_vec,
            "Buyer Unrec Mean": buyer_unrec_mean,
            "Renter Unrec Mean": renter_unrec_vec,
            "Interest": interest_vec,
            "Property Tax": prop_tax_med,
            "Maintenance": maint_med,
            "Repairs": repair_med,
            "Special Assessment": sa_vec,
            "Condo Fees": condo_vec,
            "Home Insurance": hins_vec,
            "Utilities": util_vec,
            "Rent": rent_vec,
            "Rent Insurance": rins_vec,
            "Rent Utilities": rutil_vec,
            "Moving": moving_vec,
            "Buy Payment": buy_pmt_med,
            "Rent Payment": rent_pmt_vec,
            # Smooth recurring rent cost (excludes moving spikes). Useful for charts.
            "Rent Cost (Recurring)": (rent_vec + rins_vec + rutil_vec),
            "Deficit": deficit_med,
        }
    )

    # Attach MC diagnostics for UI/debug (non-breaking; attrs are optional)
    try:
        df.attrs["win_pct_pre_tax"] = float(win_pct) if win_pct is not None else None
        df.attrs["mc_num_sims"] = int(num_sims)
        df.attrs["mc_seed"] = None if mc_seed is None else int(mc_seed)
        df.attrs["mc_degenerate"] = bool(mc_degenerate)
        df.attrs["mc_sigma_inv_annual"] = float(ret_std)
        df.attrs["mc_sigma_app_annual"] = float(apprec_std)
        df.attrs["mc_win_n_wins"] = int(wins)
        df.attrs["mc_win_n_ties"] = int(ties)

        # Best-effort finite count (only for the win% basis)
        try:
            df.attrs["mc_win_n_finite"] = int(np.count_nonzero(finite))
        except Exception:
            pass

        # Guardrails: non-finite end values and any NaN/Inf in key MC paths (when present).
        try:
            df.attrs["mc_end_n_nonfinite"] = int(np.count_nonzero(~finite))
        except Exception:
            pass

        try:
            _nf = 0
            if buyer_nw_paths is not None:
                _nf += int(np.count_nonzero(~np.isfinite(buyer_nw_paths)))
            if renter_nw_paths is not None:
                _nf += int(np.count_nonzero(~np.isfinite(renter_nw_paths)))
            if buyer_unrec_paths is not None:
                _nf += int(np.count_nonzero(~np.isfinite(buyer_unrec_paths)))
            df.attrs["mc_path_n_nonfinite"] = int(_nf)
            if _nf:
                _prev = str(df.attrs.get("mc_error", "") or "").strip()
                _msg = f"Non-finite values detected in Monte Carlo paths (count={_nf})."
                if _msg and (_msg not in _prev):
                    df.attrs["mc_error"] = (_prev + (" " if _prev else "") + _msg).strip()
        except Exception:
            pass

        # Make failures explicit (never silently emit 0%)
        if win_pct is None:
            if not np.any(finite):
                _msg = "No finite simulations for win% calculation (check extreme inputs)."
            else:
                _msg = "Win% unavailable (non-finite or invalid)."
            _prev = str(df.attrs.get("mc_error", "") or "").strip()
            if _msg and (_msg not in _prev):
                df.attrs["mc_error"] = (_prev + (" " if _prev else "") + _msg).strip()
    except Exception:
        pass

    # Deterministic equivalence check for degenerate Monte Carlo (σ=0)
    try:
        if bool(mc_degenerate):
            df_det = simulate_single(
                years,
                buyer_mo,
                renter_mo,
                apprec_annual_dec,
                mr_init,
                nm,
                pmt_init,
                down,
                close,
                mort,
                price,
                rent,
                p_tax_rate,
                maint_rate,
                repair_rate,
                condo,
                h_ins,
                o_util,
                r_ins,
                r_util,
                sell_cost,
                rent_inf_eff,
                rent_control_frequency_years,
                moving_cost,
                moving_freq,
                inf_mo,
                0.0,
                0.0,
                invest_diff,
                rent_closing,
                mkt_corr,
                rate_mode,
                rate_reset_years,
                rate_reset_to,
                rate_reset_step_pp,
                rate_shock_enabled,
                rate_shock_start_year,
                rate_shock_duration_years,
                rate_shock_pp,
                crisis_enabled,
                crisis_year,
                crisis_stock_dd,
                crisis_house_dd,
                crisis_duration_months,
                budget_enabled,
                monthly_income,
                monthly_nonhousing,
                income_growth_pct,
                budget_allow_withdraw,
                condo_inf_mo,
                assume_sale_end,
                show_liquidation_view,
                cg_tax_end,
                home_sale_legal_fee,
                mort_rate_nominal_pct,
                canadian_compounding,
                prop_tax_growth_model,
                prop_tax_hybrid_addon_pct,
                investment_tax_mode,
                special_assessment_amount,
                special_assessment_month,
                cg_inclusion_policy,
                cg_inclusion_threshold,
                reg_shelter_enabled,
                reg_initial_room,
                reg_annual_room,
            )
            b_ok = np.allclose(
                df["Buyer Net Worth"].to_numpy(dtype=np.float64),
                df_det["Buyer Net Worth"].to_numpy(dtype=np.float64),
                rtol=1e-6,
                atol=1.0,
            )
            r_ok = np.allclose(
                df["Renter Net Worth"].to_numpy(dtype=np.float64),
                df_det["Renter Net Worth"].to_numpy(dtype=np.float64),
                rtol=1e-6,
                atol=1.0,
            )
            det_ok = bool(b_ok and r_ok)
            df.attrs["mc_det_equiv_ok"] = det_ok
            if not det_ok:
                _prev = str(df.attrs.get("mc_error", "") or "").strip()
                _msg = "Degenerate MC mismatch vs deterministic path."
                if _msg not in _prev:
                    df.attrs["mc_error"] = (_prev + (" " if _prev else "") + _msg).strip()
    except Exception:
        # Don't break the run; just mark it
        try:
            df.attrs["mc_det_equiv_ok"] = False
        except Exception:
            pass

    # Optional after-tax liquidation view at horizon (cash-in-hand)
    liq_win_pct = None
    if bool(show_liquidation_view):
        try:
            try:
                eff_cg = max(0.0, float(cg_tax_end) / 100.0)
            except (TypeError, ValueError):
                eff_cg = 0.0

            # If annual drag mode is active, don't apply extra CG at liquidation
            if str(investment_tax_mode or "").startswith("Annual"):
                eff_cg = 0.0

            # Final-period exit costs/fees (only if selling at horizon)
            exit_cost_final = (c_home * float(sell_cost)) if bool(assume_sale_end) else 0.0
            exit_legal_fee_final = (
                float(home_sale_legal_fee) if (bool(assume_sale_end) and home_sale_legal_fee is not None) else 0.0
            )

            # After-tax portfolios (principal residence assumed tax-free; portfolio CG taxed)
            b_gain = np.maximum(0.0, b_nw - b_basis)
            r_gain = np.maximum(0.0, r_nw - r_basis)

            b_taxable_gain = _taxable_gain_after_reg_shelter(
                b_gain, b_basis, years, reg_shelter_enabled, reg_initial_room, reg_annual_room
            )
            r_taxable_gain = _taxable_gain_after_reg_shelter(
                r_gain, r_basis, years, reg_shelter_enabled, reg_initial_room, reg_annual_room
            )

            b_tax = _cg_tax_due(b_taxable_gain, eff_cg, cg_inclusion_policy, cg_inclusion_threshold)
            r_tax = _cg_tax_due(r_taxable_gain, eff_cg, cg_inclusion_policy, cg_inclusion_threshold)

            b_port_after_tax = b_nw - b_tax
            r_port_after_tax = r_nw - r_tax

            # Home capital gains tax (only if selling at horizon AND not principal residence)
            is_principal_residence = bool(is_principal_residence)
            eff_home_cg = 0.0
            try:
                eff_home_cg = max(0.0, float(cg_tax_end) / 100.0)
            except Exception:
                eff_home_cg = 0.0

            home_tax_final = 0.0
            if bool(assume_sale_end) and (not is_principal_residence) and eff_home_cg > 0.0:
                home_acb = float(price) + float(close)  # purchase price + acquisition costs proxy
                home_proceeds_net = (
                    np.asarray(c_home, dtype=np.float64)
                    - np.asarray(exit_cost_final, dtype=np.float64)
                    - float(exit_legal_fee_final)
                )
                home_gain = np.maximum(0.0, home_proceeds_net - float(home_acb))
                home_tax_final = _cg_tax_due(home_gain, eff_home_cg, cg_inclusion_policy, cg_inclusion_threshold)

            home_cash = (
                (np.asarray(c_home, dtype=np.float64) - np.asarray(c_mort, dtype=np.float64))
                if bool(assume_sale_end)
                else 0.0
            )

            b_liq_vals = (
                np.asarray(home_cash, dtype=np.float64)
                + np.asarray(b_port_after_tax, dtype=np.float64)
                - np.asarray(close, dtype=np.float64)
                - np.asarray(exit_cost_final, dtype=np.float64)
                - float(exit_legal_fee_final)
                - np.asarray(home_tax_final, dtype=np.float64)
            )
            r_liq_vals = r_port_after_tax

            # Win% on a cash-out basis (tolerance-based ties)
            finite2 = np.isfinite(b_liq_vals) & np.isfinite(r_liq_vals)
            if np.any(finite2):
                b2 = b_liq_vals[finite2]
                r2 = r_liq_vals[finite2]
                diff2 = b2 - r2
                scale2 = float(np.nanmedian(np.abs(np.concatenate([b2, r2])))) if b2.size else 1.0
                scale2 = max(1.0, scale2)
                tol2 = max(1e-6, 1e-9 * scale2)
                wins2 = int(np.count_nonzero(diff2 > tol2))
                ties2 = int(np.count_nonzero(np.abs(diff2) <= tol2))
                liq_win_pct = (wins2 + 0.5 * ties2) / max(1.0, float(b2.size)) * 100.0
                if (not np.isfinite(liq_win_pct)) or (liq_win_pct < -1e-9) or (liq_win_pct > 100.0 + 1e-9):
                    liq_win_pct = None

            # Store liquidation summaries on the final row (match deterministic convention: only populated at horizon)
            buyer_liq_series = np.full(months, np.nan, dtype=np.float64)
            renter_liq_series = np.full(months, np.nan, dtype=np.float64)
            buyer_liq_mean_series = np.full(months, np.nan, dtype=np.float64)
            renter_liq_mean_series = np.full(months, np.nan, dtype=np.float64)
            buyer_liq_low_series = np.full(months, np.nan, dtype=np.float64)
            buyer_liq_high_series = np.full(months, np.nan, dtype=np.float64)
            renter_liq_low_series = np.full(months, np.nan, dtype=np.float64)
            renter_liq_high_series = np.full(months, np.nan, dtype=np.float64)

            buyer_liq_series[-1] = float(np.nanmedian(b_liq_vals))
            renter_liq_series[-1] = float(np.nanmedian(r_liq_vals))
            buyer_liq_mean_series[-1] = float(np.nanmean(b_liq_vals))
            renter_liq_mean_series[-1] = float(np.nanmean(r_liq_vals))
            buyer_liq_low_series[-1] = float(np.nanpercentile(b_liq_vals, 5))
            buyer_liq_high_series[-1] = float(np.nanpercentile(b_liq_vals, 95))
            renter_liq_low_series[-1] = float(np.nanpercentile(r_liq_vals, 5))
            renter_liq_high_series[-1] = float(np.nanpercentile(r_liq_vals, 95))

            df[_LIQ_B] = buyer_liq_series
            df[_LIQ_R] = renter_liq_series
            df["Buyer Liquidation NW Mean"] = buyer_liq_mean_series
            df["Renter Liquidation NW Mean"] = renter_liq_mean_series
            df["Buyer Liquidation NW Low"] = buyer_liq_low_series
            df["Buyer Liquidation NW High"] = buyer_liq_high_series
            df["Renter Liquidation NW Low"] = renter_liq_low_series
            df["Renter Liquidation NW High"] = renter_liq_high_series
        except Exception as _e:
            # If liquidation calc fails, still attach placeholder columns so the UI never "disappears".
            df[_LIQ_B] = np.full(months, np.nan, dtype=np.float64)
            df[_LIQ_R] = np.full(months, np.nan, dtype=np.float64)
            liq_win_pct = None
            try:
                df.attrs["liquidation_error"] = str(_e)
            except Exception:
                pass

    # Attach (optional) liquidation win% for UI consumption
    try:
        df.attrs["win_pct_liquidation"] = liq_win_pct
    except Exception:
        pass

    return df, win_pct


def run_heatmap_mc_batch(
    cfg: dict,
    buyer_ret_pct: float,
    renter_ret_pct: float,
    app_vals_pct: np.ndarray,
    rent_vals_pct: np.ndarray,
    invest_diff: bool,
    rent_closing: bool,
    mkt_corr: float,
    *,
    y_axis: str = "rent_inf",
    num_sims: int,
    mc_seed=None,
    rate_override_pct: float | None = None,
    crisis_enabled: bool = False,
    crisis_year: int = 5,
    crisis_stock_dd: float = 0.30,
    crisis_house_dd: float = 0.20,
    crisis_duration_months: int = 1,
    budget_enabled: bool = False,
    monthly_income: float = 0.0,
    monthly_nonhousing: float = 0.0,
    income_growth_pct: float = 0.0,
    budget_allow_withdraw: bool = True,
    cell_mask_Z=None,
    progress_cb=None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Batch Monte Carlo heatmap execution.

    Returns:
        win_pct_Z, expected_delta_Z, expected_pv_delta_Z
    where each matrix is shape (len(rent_vals_pct), len(app_vals_pct)).

    Notes:
    - Optimized for heatmap metrics (Win% / Expected Δ). Avoids allocating full (sims × months) path arrays.
    - Uses common random numbers across all grid cells (correlated draws) for smoother heatmaps.
    - Executes the full grid in *chunks* of cells to keep memory bounded even at large sim counts.
    - Optional cell_mask_Z allows computing only a subset of cells (others return NaN), enabling adaptive refinement.
    - If budget mode is enabled, this function currently falls back to per-cell evaluation for correctness.

    Axis flexibility:
    - x-axis is always app_vals_pct (Home appreciation %/yr)
    - y-axis is interpreted by y_axis: 'rent_inf' (Rent inflation %/yr) or 'renter_ret' (Renter investment return %/yr)
    """
    app_vals_pct = np.asarray(app_vals_pct, dtype=float)
    rent_vals_pct = np.asarray(rent_vals_pct, dtype=float)

    # y_axis controls how rent_vals_pct is interpreted in the grid.
    # - 'rent_inf': rent_vals_pct is Rent inflation (%/yr)
    # - 'renter_ret': rent_vals_pct is Renter investment return (%/yr); rent inflation uses cfg['rent_inf'] (optionally capped).
    y_axis_norm = str(y_axis or 'rent_inf').strip().lower()
    if y_axis_norm in ('rent', 'rent_infl', 'rent_inflation'):
        y_axis_norm = 'rent_inf'
    if y_axis_norm in ('renter', 'renter_return', 'renter_ret', 'investment', 'inv_ret'):
        y_axis_norm = 'renter_ret'
    if y_axis_norm not in ('rent_inf', 'renter_ret'):
        y_axis_norm = 'rent_inf'

    # Base rent inflation (annual decimal). Used when y-axis is not rent inflation.
    # Note: some app paths historically passed percent values; normalize here defensively.
    rent_inf_base_dec = float(_f(cfg.get('rent_inf', 0.0), 0.0))
    if abs(rent_inf_base_dec) > 1.0:
        rent_inf_base_dec = rent_inf_base_dec / 100.0
    try:
        if bool(cfg.get('rent_control_enabled', False)) and (cfg.get('rent_control_cap') is not None):
            _cap = float(cfg.get('rent_control_cap'))
            if abs(_cap) > 1.0:
                _cap = _cap / 100.0
            rent_inf_base_dec = min(rent_inf_base_dec, _cap)
    except Exception:
        pass
    rent_inf_base_pct_eff = rent_inf_base_dec * 100.0

    n_app = int(app_vals_pct.size)
    n_rent = int(rent_vals_pct.size)
    if n_app <= 0 or n_rent <= 0:
        Z = np.full((max(1, n_rent), max(1, n_app)), np.nan, dtype=float)
        return Z, Z.copy(), Z.copy()

    # Budget mode is less common and much more complex to batch correctly; preserve correctness via fallback.
    if bool(budget_enabled):
        winZ = np.full((n_rent, n_app), np.nan, dtype=float)
        dZ = np.full((n_rent, n_app), np.nan, dtype=float)
        pvZ = np.full((n_rent, n_app), np.nan, dtype=float)

        total = n_rent * n_app
        done = 0
        for i, r in enumerate(rent_vals_pct):
            for j, a in enumerate(app_vals_pct):
                df, _close, _pmt, win = run_simulation_core(
                    cfg,
                    float(buyer_ret_pct),
                    float(r) if y_axis_norm == 'renter_ret' else float(renter_ret_pct),
                    float(a),
                    bool(invest_diff),
                    bool(rent_closing),
                    float(mkt_corr),
                    force_deterministic=False,
                    mc_seed=mc_seed,
                    rate_override_pct=rate_override_pct,
                    rent_inf_override_pct=(float(r) if y_axis_norm == 'rent_inf' else float(rent_inf_base_pct_eff)),
                    crisis_enabled=bool(crisis_enabled),
                    crisis_year=int(crisis_year),
                    crisis_stock_dd=float(crisis_stock_dd),
                    crisis_house_dd=float(crisis_house_dd),
                    crisis_duration_months=int(crisis_duration_months),
                    budget_enabled=True,
                    monthly_income=float(monthly_income),
                    monthly_nonhousing=float(monthly_nonhousing),
                    income_growth_pct=float(income_growth_pct),
                    budget_allow_withdraw=bool(budget_allow_withdraw),
                    force_use_volatility=True,
                    num_sims_override=int(num_sims),
                )
                # Expected deltas use mean columns when present
                b_mean = float(
                    df.iloc[-1]["Buyer NW Mean"] if "Buyer NW Mean" in df.columns else df.iloc[-1]["Buyer Net Worth"]
                )
                r_mean = float(
                    df.iloc[-1]["Renter NW Mean"] if "Renter NW Mean" in df.columns else df.iloc[-1]["Renter Net Worth"]
                )
                disc_annual = _f(cfg.get("discount_rate", 0.0), 0.0)
                # Defensive normalization: UI widgets often express % as percent-points (e.g., 3.0 for 3%),
                # but the engine expects a decimal fraction (0.03). If a caller accidentally passes
                # percent-points, normalize here to avoid PV underflow to ~0.
                if disc_annual > 1.0:
                    disc_annual = disc_annual / 100.0
                    try:
                        df.attrs["discount_rate_autonormalized"] = True
                    except Exception:
                        pass
                disc_mo = _annual_effective_dec_to_monthly_eff(disc_annual)
                months = int(max(1, int(cfg.get("years", 1))) * 12)
                d = b_mean - r_mean
                dZ[i, j] = d
                pvZ[i, j] = d / ((1.0 + disc_mo) ** months) if disc_mo != 0 else d
                winZ[i, j] = np.nan if win is None else float(win)

                done += 1
                if progress_cb is not None:
                    progress_cb(done, total)
        return winZ, dZ, pvZ

    # --- Common setup (mirrors run_simulation_core, but optimized) ---
    years = max(1, _i(cfg.get("years", 1), 1))
    months = int(years * 12)

    # Optional investment taxes: annual return drag applies equally to BOTH portfolios.
    inv_mode = str(cfg.get("investment_tax_mode", "") or "").strip()
    tax_r = _f(cfg.get("tax_r", 0.0), 0.0)
    drag = 1.0
    if inv_mode == "Annual return drag" and tax_r > 0:
        drag = max(0.0, 1.0 - tax_r / 100.0)

    # Convert annual effective returns into monthly log drift (used by exp(mu + sigma*z - 0.5*sigma^2)).
    buyer_mo = _annual_effective_pct_to_monthly_log_mu(_f(buyer_ret_pct) * drag)
    renter_mo = _annual_effective_pct_to_monthly_log_mu(_f(renter_ret_pct) * drag)

    # Base inputs
    price = _f(cfg.get("price", 0.0), 0.0)
    rent0 = _f(cfg.get("rent", 0.0), 0.0)
    down = _f(cfg.get("down", 0.0), 0.0)

    rate = _f(cfg.get("rate", 0.0), 0.0)
    sell_cost = _f(cfg.get("sell_cost", 0.0), 0.0)
    # ── cfg unit guard: auto-convert percent-like values stored as decimal fractions ──
    # general_inf, ret_std, apprec_std: engine expects decimal (0.025 = 2.5%).
    # Protect against callers who pass percent values (e.g. general_inf=2.5 instead of 0.025).
    _cfg_general_inf = _f(cfg.get("general_inf", 0.0), 0.0)
    if _cfg_general_inf > 1.0:
        cfg = dict(cfg)  # defensive copy — never mutate caller's dict
        cfg["general_inf"] = _cfg_general_inf / 100.0
    _cfg_ret_std = _f(cfg.get("ret_std", 0.0), 0.0)
    if _cfg_ret_std > 1.0:
        cfg = dict(cfg)
        cfg["ret_std"] = _cfg_ret_std / 100.0
    _cfg_apprec_std = _f(cfg.get("apprec_std", 0.0), 0.0)
    if _cfg_apprec_std > 1.0:
        cfg = dict(cfg)
        cfg["apprec_std"] = _cfg_apprec_std / 100.0

    p_tax_rate = _f(cfg.get("p_tax_rate", 0.0), 0.0)
    maint_rate = _f(cfg.get("maint_rate", 0.0), 0.0)
    repair_rate = _f(cfg.get("repair_rate", 0.0), 0.0)
    condo = _f(cfg.get("condo", 0.0), 0.0)
    h_ins = _f(cfg.get("h_ins", 0.0), 0.0)
    o_util = _f(cfg.get("o_util", 0.0), 0.0)
    r_ins = _f(cfg.get("r_ins", 0.0), 0.0)
    r_util = _f(cfg.get("r_util", 0.0), 0.0)
    moving_cost = _f(cfg.get("moving_cost", 0.0), 0.0)
    moving_freq = _f(cfg.get("moving_freq", 5.0), 5.0)

    mort = _f(cfg.get("mort", 0.0), 0.0)
    close = _f(cfg.get("close", 0.0), 0.0)
    pst = _f(cfg.get("pst", 0.0), 0.0)
    nm = max(1, _i(cfg.get("nm", 1), 1))

    # Special assessment (one-time buyer shock)
    special_assessment_amount = _f(cfg.get("special_assessment_amount", 0.0), 0.0)
    special_assessment_month = _i(cfg.get("special_assessment_month", 0), 0)

    # Mortgage recompute (matches run_simulation_core; price/down overrides not used for heatmap currently)
    mort_rate_nominal_pct_use = float(rate_override_pct) if rate_override_pct is not None else float(rate)
    canadian_compounding = bool(cfg.get("canadian_compounding", True))
    mr_use = _clamp_monthly_rate(_annual_nominal_pct_to_monthly_rate(mort_rate_nominal_pct_use, canadian_compounding))
    if float(mort) > 0:
        pmt_use = _mortgage_payment(float(mort), float(mr_use), int(nm))
    else:
        pmt_use = 0.0

    # Inflation (kept consistent with run_simulation_core)
    general_inf = _f(cfg.get("general_inf", 0.0), 0.0)
    inf_mo = _annual_effective_dec_to_monthly_eff(general_inf)
    condo_inf = _f(cfg.get("condo_inf", 0.0), 0.0)
    condo_inf_mo = _annual_effective_dec_to_monthly_eff(condo_inf)

    assume_sale_end = bool(cfg.get("assume_sale_end", True))
    home_sale_legal_fee = _f(cfg.get("home_sale_legal_fee", 0.0), 0.0)

    # Rent control frequency (cadence in years)
    rent_control_frequency_years = max(1, _i(cfg.get("rent_control_frequency_years", 1), 1))

    # Rate mode / renewal + shocks
    rate_mode = str(cfg.get("rate_mode", "Fixed"))
    rate_reset_years_eff = cfg.get("rate_reset_years_eff", None)
    rate_reset_to_eff = cfg.get("rate_reset_to_eff", None)
    rate_reset_step_pp_eff = _f(cfg.get("rate_reset_step_pp_eff", 0.0), 0.0)
    rate_shock_enabled_eff = bool(cfg.get("rate_shock_enabled_eff", False))
    rate_shock_start_year_eff = cfg.get("rate_shock_start_year_eff", None)
    rate_shock_duration_years_eff = cfg.get("rate_shock_duration_years_eff", None)
    rate_shock_pp_eff = _f(cfg.get("rate_shock_pp_eff", 0.0), 0.0)

    # Property tax growth model knobs
    prop_mode = str(cfg.get("prop_tax_growth_model", "Hybrid (recommended for Toronto)") or "")
    prop_tax_hybrid_addon_pct = _f(cfg.get("prop_tax_hybrid_addon_pct", 0.5), 0.5)
    try:
        addon_mo = (1.0 + float(prop_tax_hybrid_addon_pct) / 100.0) ** (1.0 / 12.0) - 1.0
    except (TypeError, ValueError):
        addon_mo = 0.0

    # Volatility inputs (force-use for MC heatmap metrics)
    ret_std = _f(cfg.get("ret_std", 0.0), 0.0)
    apprec_std = _f(cfg.get("apprec_std", 0.0), 0.0)

    # Correlated shocks
    rho = float(np.clip(mkt_corr, -0.999999, 0.999999))
    rho_abs = abs(rho)
    a_corr = math.sqrt(rho_abs)
    b_corr = math.sqrt(max(0.0, 1.0 - rho_abs))
    rho_sign = 1.0 if rho >= 0 else -1.0

    ret_std_mo = float(ret_std) / math.sqrt(12.0) if ret_std else 0.0
    app_std_mo = float(apprec_std) / math.sqrt(12.0) if apprec_std else 0.0

    buyer_mu = float(buyer_mo) - 0.5 * (ret_std_mo**2)
    renter_mu = float(renter_mo) - 0.5 * (ret_std_mo**2)

    # Build scenario grid (cells = n_rent * n_app)
    # x-axis is always app_vals_pct (home appreciation).
    A, Y = np.meshgrid(app_vals_pct, rent_vals_pct, indexing="xy")
    app_cells_dec = (A.reshape(-1) / 100.0).astype(np.float64)  # annual decimal

    if y_axis_norm == 'rent_inf':
        rent_cells_dec = (Y.reshape(-1) / 100.0).astype(np.float64)  # annual decimal
        renter_ret_cells_pct = None
    else:
        # y-axis sweeps renter return; rent inflation stays at the base assumption (optionally capped).
        rent_cells_dec = np.full(app_cells_dec.shape, float(rent_inf_base_dec), dtype=np.float64)
        renter_ret_cells_pct = Y.reshape(-1).astype(np.float64)

    n_cells = int(app_cells_dec.size)

    # Optional subset evaluation (adaptive refinement): compute only masked cells; others remain NaN.
    sel_idx = None
    n_sel = n_cells
    if cell_mask_Z is not None:
        try:
            _m = np.asarray(cell_mask_Z, dtype=bool)
            if _m.shape == (n_rent, n_app):
                _mf = _m.reshape(-1)
            elif _m.size == n_cells:
                _mf = _m.reshape(-1)
            else:
                _mf = None
            if _mf is not None:
                sel_idx = np.nonzero(_mf)[0].astype(np.int64, copy=False)
                n_sel = int(sel_idx.size)
        except Exception:
            sel_idx = None
            n_sel = n_cells

    home_mu_cells = (np.log1p(np.clip(app_cells_dec, -0.999999, None)) / 12.0) - 0.5 * (app_std_mo**2)

    # Optional: per-cell renter drift when y-axis sweeps renter investment return.
    renter_mu_cells = None
    renter_mo_cells = None
    if renter_ret_cells_pct is not None:
        rr_dec = np.clip(renter_ret_cells_pct / 100.0, -0.999999, None)
        renter_mo_cells = np.log1p(rr_dec) / 12.0
        renter_mu_cells = renter_mo_cells - 0.5 * (ret_std_mo**2)

    # RNG (shared across all cells -> common random numbers)
    rng = np.random.default_rng(int(mc_seed)) if mc_seed is not None else np.random.default_rng()

    # Choose a cell-chunk size to keep peak memory bounded.
    num_sims = int(max(1, int(num_sims)))
    # Rough peak arrays: r_nw, b_nw, c_home, tax_base, cum_b_op, home_growth tmp
    _TARGET_BYTES = 250_000_000  # ~250MB for the per-chunk state (does not include precomputed shocks)
    _ARRAYS = 6
    try:
        chunk_cells = int(max(8, min(n_sel, _TARGET_BYTES // max(1, (_ARRAYS * num_sims * 4)))))
    except Exception:
        chunk_cells = min(n_cells, 64)
    # Round down to a friendly multiple
    if chunk_cells > 8:
        chunk_cells = int(max(8, (chunk_cells // 8) * 8))
    chunk_cells = int(max(1, min(n_sel, chunk_cells)))

    # Precompute common random shocks across months (to reuse across chunks and keep CRN smooth).
    stock_shocks = None
    house_shocks = None
    if (ret_std_mo > 0.0) or (app_std_mo > 0.0):
        try:
            # Two float32 matrices: stock_shocks + house_shocks
            est_bytes = int(2 * months * num_sims * 4)
            _PRECOMP_MAX_BYTES = 350_000_000
            if est_bytes <= _PRECOMP_MAX_BYTES:
                stock_shocks = np.empty((months, num_sims), dtype=np.float32)
                house_shocks = np.empty((months, num_sims), dtype=np.float32)
                for mi in range(months):
                    z_sys = rng.standard_normal(num_sims).astype(np.float32, copy=False)
                    z_stock = rng.standard_normal(num_sims).astype(np.float32, copy=False)
                    z_house = rng.standard_normal(num_sims).astype(np.float32, copy=False)
                    stock_shocks[mi, :] = (a_corr * z_sys) + (b_corr * z_stock)
                    house_shocks[mi, :] = (a_corr * rho_sign * z_sys) + (b_corr * z_house)
        except Exception:
            # Fallback: no precompute; re-generate shocks per chunk (still deterministic given seed).
            stock_shocks = None
            house_shocks = None

    disc_annual = _f(cfg.get("discount_rate", 0.0), 0.0)

    # Defensive normalization: UI widgets often express % as percent-points (e.g., 3.0 for 3%),

    # but the engine expects a decimal fraction (0.03). If a caller accidentally passes

    # percent-points, normalize here to avoid PV underflow to ~0.

    if disc_annual > 1.0:
        disc_annual = disc_annual / 100.0

    disc_mo = _annual_effective_dec_to_monthly_eff(disc_annual)
    # Outputs (flat, then reshaped)
    win_flat = np.full(n_cells, np.nan, dtype=np.float64)
    d_flat = np.full(n_cells, np.nan, dtype=np.float64)
    pv_flat = np.full(n_cells, np.nan, dtype=np.float64)

    # Progress pacing: update per chunk
    done_cells = 0

    _EXP_CLIP = 50.0
    bg_const = math.exp(float(buyer_mo)) if ret_std_mo <= 0.0 else None
    rg_const = math.exp(float(renter_mo)) if (ret_std_mo <= 0.0 and renter_mu_cells is None) else None

    # Iterate chunks of the flattened grid
    for s in range(0, n_sel, chunk_cells):
        e = min(n_sel, s + chunk_cells)
        k = int(e - s)

        if sel_idx is not None:
            idx_block = sel_idx[s:e]
            rent_chunk = rent_cells_dec[idx_block].astype(np.float64, copy=False)
            home_mu_chunk = home_mu_cells[idx_block].astype(np.float64, copy=False)
            app_chunk_dec = app_cells_dec[idx_block].astype(np.float64, copy=False)
            renter_mu_chunk = (
                renter_mu_cells[idx_block].astype(np.float64, copy=False) if renter_mu_cells is not None else None
            )
            out_idx = idx_block
        else:
            rent_chunk = rent_cells_dec[s:e].astype(np.float64, copy=False)
            home_mu_chunk = home_mu_cells[s:e].astype(np.float64, copy=False)
            app_chunk_dec = app_cells_dec[s:e].astype(np.float64, copy=False)
            renter_mu_chunk = (
                renter_mu_cells[s:e].astype(np.float64, copy=False) if renter_mu_cells is not None else None
            )
            out_idx = slice(s, e)

        # --- Per-chunk state init (reset deterministic scalars each chunk) ---
        init_r = float(down) + (float(close) if bool(rent_closing) else 0.0)
        r_nw = np.full((num_sims, k), init_r, dtype=np.float32)
        b_nw = np.zeros((num_sims, k), dtype=np.float32)

        c_home = np.full((num_sims, k), float(price), dtype=np.float32)
        tax_base = np.full((num_sims, k), float(price), dtype=np.float32)
        cum_b_op = np.zeros((num_sims, k), dtype=np.float32)

        c_rent = np.full((k,), float(rent0), dtype=np.float32)

        # Deterministic scalars for monthly fees / mortgage schedule
        c_mort = float(mort)
        c_condo = float(condo)
        c_h_ins = float(h_ins)
        c_o_util = float(o_util)
        c_r_ins = float(r_ins)
        c_r_util = float(r_util)

        cur_rate_nominal_pct = float(mort_rate_nominal_pct_use)
        mr = float(mr_use)
        pmt = float(pmt_use)
        shock_was_active = False

        next_move = float(moving_freq) * 12.0

        # Progress pacing (match legacy ~100 updates, but per chunk)
        prog_step = max(1, int(months // 100))

        for m in range(1, months + 1):
            # --- Random growth ---
            if (ret_std_mo > 0.0) or (app_std_mo > 0.0):
                if stock_shocks is not None and house_shocks is not None:
                    stock_shock = stock_shocks[m - 1]
                    house_shock = house_shocks[m - 1]
                else:
                    z_sys = rng.standard_normal(num_sims)
                    z_stock = rng.standard_normal(num_sims)
                    z_house = rng.standard_normal(num_sims)
                    stock_shock = (a_corr * z_sys) + (b_corr * z_stock)
                    house_shock = (a_corr * rho_sign * z_sys) + (b_corr * z_house)

                b_growth = np.exp(np.clip(buyer_mu + ret_std_mo * stock_shock, -_EXP_CLIP, _EXP_CLIP)).astype(
                    np.float32, copy=False
                )
                # Renter growth must broadcast across (num_sims, chunk_cells) when y-axis varies renter return.
                # stock_shock is (num_sims,), renter_mu_chunk is (chunk_cells,) -> add shock as (num_sims, 1)
                if renter_mu_chunk is not None:
                    r_mu_term = renter_mu_chunk[None, :]
                    r_shock_term = ret_std_mo * stock_shock[:, None]
                else:
                    r_mu_term = renter_mu
                    r_shock_term = ret_std_mo * stock_shock
                r_growth = np.exp(np.clip(r_mu_term + r_shock_term, -_EXP_CLIP, _EXP_CLIP)).astype(
                    np.float32, copy=False
                )

                # home growth varies by cell (different apprec means)
                home_growth = np.exp(
                    np.clip(home_mu_chunk[None, :] + app_std_mo * house_shock[:, None], -_EXP_CLIP, _EXP_CLIP)
                ).astype(np.float32, copy=False)
            else:
                b_growth = bg_const
                r_growth = (
                    np.exp(renter_mu_chunk).astype(np.float32, copy=False) if renter_mu_chunk is not None else rg_const
                )
                home_growth = np.exp(np.log1p(np.clip(app_chunk_dec, -0.999999, None))[None, :] / 12.0).astype(
                    np.float32, copy=False
                )

            # --- Mortgage rate resets (renewals) ---
            rate_changed = False
            if (
                rate_mode == "Reset every N years"
                and (rate_reset_years_eff is not None)
                and (rate_reset_to_eff is not None)
            ):
                try:
                    reset_months = int(rate_reset_years_eff) * 12
                except Exception:
                    reset_months = 0
                if reset_months > 0 and m > 1 and ((m - 1) % reset_months == 0):
                    reset_idx = int((m - 1) / reset_months)
                    cur_rate_nominal_pct = float(rate_reset_to_eff) + float(rate_reset_step_pp_eff) * max(
                        0, reset_idx - 1
                    )
                    rate_changed = True

            shock_active = False
            if rate_shock_enabled_eff and (rate_shock_pp_eff is not None):
                try:
                    start_m = int(rate_shock_start_year_eff) * 12 + 1
                    dur_m = int(rate_shock_duration_years_eff) * 12
                    end_m = start_m + max(0, dur_m) - 1
                except (TypeError, ValueError):
                    start_m, end_m = 61, 120
                shock_active = start_m <= m <= end_m

            eff_nominal = float(cur_rate_nominal_pct) + (float(rate_shock_pp_eff) if shock_active else 0.0)
            mr = _clamp_monthly_rate(
                float(_annual_nominal_pct_to_monthly_rate(eff_nominal, bool(canadian_compounding)))
            )

            if rate_changed or (shock_active != shock_was_active):
                rem_months = max(1, int(nm) - (m - 1))
                pmt = _mortgage_payment(float(c_mort), float(mr), int(rem_months))
            shock_was_active = shock_active

            # --- Property tax modeling ---
            if prop_mode.startswith("Market"):
                tax_base = c_home
            elif prop_mode.startswith("Inflation"):
                tax_base = tax_base * (1.0 + float(inf_mo))
            else:
                cap_mo = (1.0 + float(inf_mo)) * (1.0 + float(addon_mo)) - 1.0
                target = c_home
                up = target >= tax_base
                tax_base = np.where(
                    up,
                    np.minimum(tax_base * (1.0 + cap_mo), target),
                    np.maximum(tax_base / (1.0 + cap_mo), target),
                ).astype(np.float32, copy=False)

            m_tax = tax_base * float(p_tax_rate) / 12.0
            m_maint = c_home * float(maint_rate) / 12.0
            m_repair = c_home * float(repair_rate) / 12.0

            inte = float(c_mort) * float(mr) if float(c_mort) > 0 else 0.0
            princ = (float(pmt) - inte) if float(c_mort) > 0 else 0.0
            if princ > float(c_mort):
                princ = float(c_mort)

            # Special assessment (one-time buyer shock)
            m_special = (
                float(special_assessment_amount)
                if (int(special_assessment_month) > 0 and m == int(special_assessment_month))
                else 0.0
            )

            # Buyer outflows (arrays per sim×cell)
            b_pmt0 = float(pmt) if float(c_mort) > 0 else 0.0
            b_out = b_pmt0 + m_tax + m_maint + m_repair + float(c_condo) + float(c_h_ins) + float(c_o_util) + m_special
            b_op = (
                float(inte) + m_tax + m_maint + m_repair + float(c_condo) + float(c_h_ins) + float(c_o_util) + m_special
            )

            # Renter outflows (per cell, broadcast over sims)
            skip_last_move = bool(assume_sale_end) and (m == months)
            m_moving = float(moving_cost) if (m == next_move and not skip_last_move) else 0.0
            r_out = c_rent + float(c_r_ins) + float(c_r_util) + float(m_moving)  # Total (incl. moving)
            r_out_recurring = c_rent + float(c_r_ins) + float(c_r_util)  # Recurring only (no moving spike)
            if m == next_move:
                next_move += float(moving_freq) * 12.0

            diff = b_out - r_out[None, :]

            if bool(invest_diff):
                mask = diff > 0
                if np.any(mask):
                    r_nw[mask] += diff[mask]
                if np.any(~mask):
                    b_nw[~mask] += -diff[~mask]

            # Apply growth
            if isinstance(r_growth, np.ndarray):
                # r_growth can be: (num_sims,), (k,), or (num_sims, k) depending on axis mode
                if r_growth.ndim == 2:
                    r_nw *= r_growth
                else:
                    if r_growth.shape[0] == r_nw.shape[0]:
                        r_nw *= r_growth[:, None]
                    elif r_growth.shape[0] == r_nw.shape[1]:
                        r_nw *= r_growth[None, :]
                    else:
                        r_nw *= r_growth.reshape((-1, 1))
                # buyer growth remains per-sim
                if isinstance(b_growth, np.ndarray):
                    b_nw *= b_growth[:, None]
                else:
                    b_nw *= float(b_growth)
            else:
                r_nw *= float(r_growth)
                b_nw *= float(b_growth)
            c_home *= home_growth

            # Crisis shock
            if bool(crisis_enabled):
                try:
                    crisis_m_start = int(max(1.0, float(crisis_year)) * 12)
                except (TypeError, ValueError):
                    crisis_m_start = int(5 * 12)
                dur = int(max(1, int(crisis_duration_months))) if crisis_duration_months is not None else 1
                if crisis_m_start <= m < crisis_m_start + dur:
                    stock_dd = float(np.clip(crisis_stock_dd, 0.0, 0.95))
                    house_dd = float(np.clip(crisis_house_dd, 0.0, 0.95))
                    b_nw *= 1.0 - stock_dd
                    r_nw *= 1.0 - stock_dd
                    c_home *= 1.0 - house_dd

            # Mortgage balance update (deterministic)
            if float(c_mort) > 0:
                c_mort -= float(princ)
            if float(c_mort) < 0:
                c_mort = 0.0

            # Rent inflation (respects rent control frequency cadence)
            if rent_control_frequency_years <= 1:
                if (m % 12) == 0:
                    c_rent *= 1.0 + rent_chunk.astype(np.float32, copy=False)
            else:
                if (m % (12 * rent_control_frequency_years)) == 0:
                    compound = np.power(1.0 + rent_chunk, float(rent_control_frequency_years)).astype(
                        np.float32, copy=False
                    )
                    c_rent *= compound

            # Accumulate buyer unrecoverable operating costs
            cum_b_op += b_op.astype(np.float32, copy=False)

            # CPI inflation for deterministic fees (applied AFTER month-m calculation)
            c_condo *= 1.0 + (float(condo_inf_mo) if condo_inf_mo is not None else float(inf_mo))
            c_h_ins *= 1.0 + float(inf_mo)
            c_o_util *= 1.0 + float(inf_mo)
            c_r_ins *= 1.0 + float(inf_mo)
            c_r_util *= 1.0 + float(inf_mo)

            # Progress (approx 100 updates)
            if progress_cb is not None and ((m % prog_step == 0) or (m == months)):
                # Treat each month update as a fraction of the chunk to create a smooth progress bar.
                frac = m / months
                done = int(min(n_cells, done_cells + round(frac * k)))
                progress_cb(done, int(n_cells))

        # --- Terminal stats for this chunk ---
        exit_cost_final = (c_home * float(sell_cost)) if bool(assume_sale_end) else 0.0
        exit_legal_fee_final = (
            float(home_sale_legal_fee) if (bool(assume_sale_end) and home_sale_legal_fee is not None) else 0.0
        )

        b_last = (c_home - float(c_mort)) + b_nw - float(close) - exit_cost_final - float(exit_legal_fee_final)
        r_last = r_nw

        # Mask non-finite
        finite = np.isfinite(b_last) & np.isfinite(r_last)
        b_last_m = np.where(np.isfinite(b_last), b_last, np.nan)
        r_last_m = np.where(np.isfinite(r_last), r_last, np.nan)

        b_mean = np.nanmean(b_last_m, axis=0)
        r_mean = np.nanmean(r_last_m, axis=0)
        d_mean = b_mean - r_mean
        pv_d_mean = d_mean / ((1.0 + float(disc_mo)) ** months) if float(disc_mo) != 0 else d_mean

        # Win% per cell (scale-aware tolerance, vectorized)
        diff = np.where(finite, (b_last - r_last), np.nan)
        scale = np.nanmedian(np.maximum(np.abs(b_last_m), np.abs(r_last_m)), axis=0)
        scale = np.where(np.isfinite(scale), scale, 1.0)
        scale = np.maximum(1.0, scale)
        tol = np.maximum(1e-6, 1e-9 * scale)

        wins = np.sum((diff > tol) & finite, axis=0)
        ties = np.sum((np.abs(diff) <= tol) & finite, axis=0)
        denom = np.sum(finite, axis=0)
        w = (wins + 0.5 * ties) / np.maximum(1.0, denom) * 100.0
        w = np.where(denom > 0, w, np.nan)

        win_flat[out_idx] = w.astype(np.float64, copy=False)
        d_flat[out_idx] = d_mean.astype(np.float64, copy=False)
        pv_flat[out_idx] = pv_d_mean.astype(np.float64, copy=False)

        done_cells += int(k)
        if progress_cb is not None:
            progress_cb(done_cells, int(n_sel))

    # Reshape back to Z matrices (rent rows × app cols)
    winZ = win_flat.reshape((n_rent, n_app))
    dZ = d_flat.reshape((n_rent, n_app))
    pvZ = pv_flat.reshape((n_rent, n_app))
    return winZ, dZ, pvZ


def run_simulation_core(
    cfg: dict,
    buyer_ret_pct,
    renter_ret_pct,
    apprec_pct,
    invest_diff,
    rent_closing,
    mkt_corr,
    *,
    force_deterministic=False,
    mc_seed=None,
    rate_override_pct=None,
    rent_inf_override_pct=None,
    progress_cb=None,
    crisis_enabled=False,
    crisis_year=5,
    crisis_stock_dd=0.30,
    crisis_house_dd=0.20,
    crisis_duration_months=1,
    budget_enabled=False,
    monthly_income=0.0,
    monthly_nonhousing=0.0,
    income_growth_pct=0.0,
    budget_allow_withdraw=True,
    param_overrides=None,
    force_use_volatility=None,
    num_sims_override=None,
    mc_summary_only: bool = False,
    mc_precomputed_shocks=None,
):
    """Pure simulation engine. No Streamlit calls.

    `cfg` contains all baseline model inputs (from UI), while `param_overrides` allows per-evaluation overrides
    (used by bias flip-points and heatmaps) without mutating globals.
    """

    # Stable column names expected by the UI (keep consistent across MC pathways)
    _LIQ_B = "Buyer Liquidation NW"
    _LIQ_R = "Renter Liquidation NW"

    # Convert percentages to monthly decimals
    years = max(1, _i(cfg.get("years", 1), 1))

    # Optional investment taxes: annual return drag applies equally to BOTH portfolios.
    inv_mode = str(cfg.get("investment_tax_mode", "") or "").strip()
    tax_r = _f(cfg.get("tax_r", 0.0), 0.0)
    drag = 1.0
    if inv_mode == "Annual return drag" and tax_r > 0:
        drag = max(0.0, 1.0 - tax_r / 100.0)

    # Convert annual effective returns into monthly log drift (used by exp(mu + sigma*z - 0.5*sigma^2)).
    buyer_mo = _annual_effective_pct_to_monthly_log_mu(_f(buyer_ret_pct) * drag)
    renter_mo = _annual_effective_pct_to_monthly_log_mu(_f(renter_ret_pct) * drag)

    # Annual appreciation decimal; simulate_single converts to monthly internally.
    apprec_decimal = _f(apprec_pct) / 100.0

    # Apply overrides (no globals mutation)
    _overrides = dict(param_overrides or {})

    # Base inputs
    price = _f(cfg.get("price", 0.0), 0.0)
    rent = _f(cfg.get("rent", 0.0), 0.0)
    down = _f(cfg.get("down", 0.0), 0.0)

    price_use = _f(_overrides.get("price", price), price)
    rent_use = _f(_overrides.get("rent", rent), rent)
    down_use = _f(_overrides.get("down", down), down)

    # Allow down payment override as a percent (either 0-1 fraction or 0-100 percent)
    if ("down_pct" in _overrides) and ("down" not in _overrides):
        try:
            _dp = float(_overrides.get("down_pct", 0.0))
            if _dp <= 1.0:
                down_use = _dp * price_use
            else:
                down_use = (_dp / 100.0) * price_use
        except (TypeError, ValueError):
            pass

    # Clamp down payment to [0, price]
    down_use = max(0.0, min(float(down_use), float(price_use))) if price_use > 0 else max(0.0, float(down_use))

    rate = _f(cfg.get("rate", 0.0), 0.0)
    rent_inf = _f(cfg.get("rent_inf", 0.0), 0.0)
    sell_cost = _f(cfg.get("sell_cost", 0.0), 0.0)
    # ── cfg unit guard: auto-convert percent-like values stored as decimal fractions ──
    # general_inf, ret_std, apprec_std: engine expects decimal (0.025 = 2.5%).
    # Protect against callers who pass percent values (e.g. general_inf=2.5 instead of 0.025).
    _cfg_general_inf = _f(cfg.get("general_inf", 0.0), 0.0)
    if _cfg_general_inf > 1.0:
        cfg = dict(cfg)  # defensive copy — never mutate caller's dict
        cfg["general_inf"] = _cfg_general_inf / 100.0
    _cfg_ret_std = _f(cfg.get("ret_std", 0.0), 0.0)
    if _cfg_ret_std > 1.0:
        cfg = dict(cfg)
        cfg["ret_std"] = _cfg_ret_std / 100.0
    _cfg_apprec_std = _f(cfg.get("apprec_std", 0.0), 0.0)
    if _cfg_apprec_std > 1.0:
        cfg = dict(cfg)
        cfg["apprec_std"] = _cfg_apprec_std / 100.0

    p_tax_rate = _f(cfg.get("p_tax_rate", 0.0), 0.0)
    maint_rate = _f(cfg.get("maint_rate", 0.0), 0.0)
    repair_rate = _f(cfg.get("repair_rate", 0.0), 0.0)
    condo = _f(cfg.get("condo", 0.0), 0.0)
    h_ins = _f(cfg.get("h_ins", 0.0), 0.0)
    o_util = _f(cfg.get("o_util", 0.0), 0.0)
    r_ins = _f(cfg.get("r_ins", 0.0), 0.0)
    r_util = _f(cfg.get("r_util", 0.0), 0.0)
    moving_cost = _f(cfg.get("moving_cost", 0.0), 0.0)
    moving_freq = _f(cfg.get("moving_freq", 5.0), 5.0)

    mort = _f(cfg.get("mort", 0.0), 0.0)
    close = _f(cfg.get("close", 0.0), 0.0)
    pst = _f(cfg.get("pst", 0.0), 0.0)

    nm = max(1, _i(cfg.get("nm", 1), 1))

    # Apply override knobs
    rate_use = _f(_overrides.get("rate", rate), rate)
    rent_inf_base = _f(_overrides.get("rent_inf", rent_inf), rent_inf)
    sell_cost_use = _f(_overrides.get("sell_cost", sell_cost), sell_cost)
    p_tax_rate_use = _f(_overrides.get("p_tax_rate", p_tax_rate), p_tax_rate)
    maint_rate_use = _f(_overrides.get("maint_rate", maint_rate), maint_rate)
    repair_rate_use = _f(_overrides.get("repair_rate", repair_rate), repair_rate)
    condo_use = _f(_overrides.get("condo", condo), condo)
    h_ins_use = _f(_overrides.get("h_ins", h_ins), h_ins)
    o_util_use = _f(_overrides.get("o_util", o_util), o_util)
    r_ins_use = _f(_overrides.get("r_ins", r_ins), r_ins)
    r_util_use = _f(_overrides.get("r_util", r_util), r_util)
    moving_cost_use = _f(_overrides.get("moving_cost", moving_cost), moving_cost)
    moving_freq_use = _f(_overrides.get("moving_freq", moving_freq), moving_freq)

    # Recompute loan + CMHC premium if down/price overridden
    mort_use = float(mort)
    close_use = float(close)

    if ("down" in _overrides) or ("down_pct" in _overrides) or ("price" in _overrides):
        loan_use = max(float(price_use) - float(down_use), 0.0)
        ltv_use = (loan_use / float(price_use)) if float(price_use) > 0 else 0.0

        # Mortgage loan insurance (CMHC / other insurer proxies).
        # We key eligibility rules off an as-of date so results remain auditable over time.
        _asof_raw = _overrides.get("asof_date", cfg.get("asof_date", None))
        asof_date = None
        if _asof_raw:
            try:
                if hasattr(_asof_raw, "year"):
                    asof_date = _asof_raw
                else:
                    import datetime as _dt

                    asof_date = _dt.date.fromisoformat(str(_asof_raw)[:10])
            except Exception:
                asof_date = None
        if asof_date is None:
            import datetime as _dt

            asof_date = _dt.date.today()

        price_cap = insured_mortgage_price_cap(asof_date)
        min_down = min_down_payment_canada(float(price_use), asof_date)

        cmhc_r_use = 0.0
        prem_use = 0.0
        pst_use = 0.0

        cmhc_attempt = (float(price_use) > 0.0) and (ltv_use > 0.8)
        cmhc_eligible = (
            cmhc_attempt and (float(price_use) < float(price_cap)) and (float(down_use) + 1e-9 >= float(min_down))
        )

        if cmhc_eligible:
            dp_source_use = str(
                _overrides.get("down_payment_source", cfg.get("down_payment_source", "Traditional")) or "Traditional"
            )
            cmhc_r_use = cmhc_premium_rate_from_ltv(float(ltv_use), dp_source_use)
            prem_use = loan_use * float(cmhc_r_use)

            # Provincial sales tax on the insurance premium is province-dependent (see policy_canada).
            _prov_use = str(_overrides.get("province", cfg.get("province", "")) or "").strip()
            _pst_rate_use = mortgage_default_insurance_sales_tax_rate(_prov_use, asof_date)
            pst_use = prem_use * float(_pst_rate_use)

        # Base closing costs excluding PST/QST on the insurance premium.
        # (The UI usually pre-adds pst into `close`; when price/down are overridden we must recompute.)
        try:
            _close_base = float(close) - float(pst)
        except Exception:
            _close_base = float(close)

        close_use = float(_close_base) + float(pst_use)

        # Mortgage principal includes the premium when applicable.
        mort_use = float(loan_use) + float(prem_use)

    # Mortgage nominal annual rate (possibly overridden)
    mort_rate_nominal_pct_use = float(rate_override_pct) if rate_override_pct is not None else float(rate_use)

    canadian_compounding = bool(cfg.get("canadian_compounding", True))
    mr_use = _annual_nominal_pct_to_monthly_rate(mort_rate_nominal_pct_use, canadian_compounding)

    # Recompute payment from principal + effective monthly rate
    mr_use = _clamp_monthly_rate(float(mr_use))
    if float(mort_use) > 0:
        pmt_use = _mortgage_payment(float(mort_use), float(mr_use), int(nm))
    else:
        pmt_use = 0.0

    # Rent inflation override
    # Contract:
    #   - cfg['rent_inf'] is annual effective *decimal* (e.g., 0.03 == 3%)
    #   - rent_inf_override_pct is in percent points (e.g., 3.0 == 3%)
    rent_inf_use = float(rent_inf_base)
    if rent_inf_override_pct is not None:
        rent_inf_use = float(rent_inf_override_pct) / 100.0
    # Guard against log-domain issues (used downstream in some growth models).
    if rent_inf_use <= -1.0:
        rent_inf_use = -0.99

    # Rent control
    rent_control_enabled = bool(cfg.get("rent_control_enabled", False))
    rent_control_cap = cfg.get("rent_control_cap", None)
    if rent_control_enabled and (rent_control_cap is not None):
        rent_inf_use = min(rent_inf_use, float(rent_control_cap))

    # Rent control frequency/cadence (years). Backward-compatible with legacy string labels.
    rent_control_frequency_years = 1
    if rent_control_enabled:
        _raw_freq = cfg.get("rent_control_frequency_years", cfg.get("rent_control_frequency", 1))
        try:
            if isinstance(_raw_freq, str):
                s = _raw_freq.strip().lower()
                nums = re.findall(r"[-+]?\d+", s)
                rent_control_frequency_years = int(nums[0]) if nums else 1
            else:
                rent_control_frequency_years = int(float(_raw_freq))
        except Exception:
            rent_control_frequency_years = 1
        rent_control_frequency_years = max(1, min(10, rent_control_frequency_years))
    else:
        rent_control_frequency_years = 1

    use_vol = bool(cfg.get("use_volatility", False)) if force_use_volatility is None else bool(force_use_volatility)
    num_sims = int(num_sims_override) if num_sims_override is not None else int(_i(cfg.get("num_sims", 0), 0))
    is_mc = use_vol and (not force_deterministic) and (num_sims > 1)

    # Rate mode / renewal + shocks
    rate_mode = str(cfg.get("rate_mode", "Fixed"))
    rate_reset_years_eff = cfg.get("rate_reset_years_eff", None)
    rate_reset_to_eff = cfg.get("rate_reset_to_eff", None)
    rate_reset_step_pp_eff = cfg.get("rate_reset_step_pp_eff", 0.0)
    rate_shock_enabled_eff = bool(cfg.get("rate_shock_enabled_eff", False))
    rate_shock_start_year_eff = cfg.get("rate_shock_start_year_eff", 5)
    rate_shock_duration_years_eff = cfg.get("rate_shock_duration_years_eff", 5)
    rate_shock_pp_eff = cfg.get("rate_shock_pp_eff", 0.0)

    general_inf = _f(cfg.get("general_inf", 0.0), 0.0)
    ret_std = _f(cfg.get("ret_std", 0.0), 0.0)
    apprec_std = _f(cfg.get("apprec_std", 0.0), 0.0)
    # Defensive: tolerate volatility inputs accidentally expressed as percent (e.g., 15 instead of 0.15)
    if ret_std > 2.0:
        ret_std = ret_std / 100.0
    if apprec_std > 2.0:
        apprec_std = apprec_std / 100.0
    condo_inf = _f(cfg.get("condo_inf", 0.0), 0.0)

    assume_sale_end = bool(cfg.get("assume_sale_end", False))
    show_liquidation_view = bool(cfg.get("show_liquidation_view", False))
    is_principal_residence_cfg = bool(cfg.get("is_principal_residence", True))
    cg_tax_end = _f(cfg.get("cg_tax_end", 0.0), 0.0)
    home_sale_legal_fee = _f(cfg.get("home_sale_legal_fee", 0.0), 0.0)

    # --- Optional modeling layers (all opt-in / explicit) ---
    special_assessment_amount = _f(cfg.get("special_assessment_amount", 0.0), 0.0)
    special_assessment_month = _i(cfg.get("special_assessment_month", 0), 0)

    cg_inclusion_policy = str(cfg.get("cg_inclusion_policy", "current") or "current")
    cg_inclusion_threshold = _f(cfg.get("cg_inclusion_threshold", 250000.0), 250000.0)

    reg_shelter_enabled = bool(cfg.get("reg_shelter_enabled", False))
    reg_initial_room = _f(cfg.get("reg_initial_room", 0.0), 0.0)
    reg_annual_room = _f(cfg.get("reg_annual_room", 0.0), 0.0)

    prop_tax_growth_model = str(cfg.get("prop_tax_growth_model", "Hybrid (recommended for Toronto)"))
    prop_tax_hybrid_addon_pct = _f(cfg.get("prop_tax_hybrid_addon_pct", 0.5), 0.5)
    investment_tax_mode = str(cfg.get("investment_tax_mode", "Pre-tax (no investment taxes)"))

    win_pct = None

    if is_mc:
        # Phase 1: vectorized Monte Carlo core (faster; eliminates per-sim pandas overhead)
        use_vectorized = bool(cfg.get("vectorized_mc", True))
        months = int(years) * 12
        mem_est = _estimate_mc_mem_bytes(num_sims, months, arrays=8, dtype_bytes=4)
        # Keep a conservative ceiling to avoid OOM on very large sims/horizons
        mem_ceiling = int(cfg.get("vectorized_mc_mem_ceiling_bytes", 850_000_000))

        if use_vectorized and num_sims > 0 and mem_est <= mem_ceiling:
            df, win_pct = _run_monte_carlo_vectorized(
                years=years,
                num_sims=num_sims,
                buyer_mo=buyer_mo,
                renter_mo=renter_mo,
                apprec_annual_dec=apprec_decimal,
                mr_init=mr_use,
                nm=nm,
                pmt_init=pmt_use,
                down=down_use,
                close=close_use,
                mort=mort_use,
                price=price_use,
                rent=rent_use,
                p_tax_rate=p_tax_rate_use,
                maint_rate=maint_rate_use,
                repair_rate=repair_rate_use,
                condo=condo_use,
                h_ins=h_ins_use,
                o_util=o_util_use,
                r_ins=r_ins_use,
                r_util=r_util_use,
                sell_cost=sell_cost_use,
                rent_inf_eff=rent_inf_use,
                rent_control_frequency_years=rent_control_frequency_years,
                moving_cost=moving_cost_use,
                moving_freq=moving_freq_use,
                inf_mo=_annual_effective_dec_to_monthly_eff(general_inf),
                ret_std=ret_std,
                apprec_std=apprec_std,
                invest_diff=invest_diff,
                rent_closing=rent_closing,
                mkt_corr=mkt_corr,
                rate_mode=rate_mode,
                rate_reset_years=rate_reset_years_eff,
                rate_reset_to=rate_reset_to_eff,
                rate_reset_step_pp=rate_reset_step_pp_eff,
                rate_shock_enabled=rate_shock_enabled_eff,
                rate_shock_start_year=rate_shock_start_year_eff,
                rate_shock_duration_years=rate_shock_duration_years_eff,
                rate_shock_pp=rate_shock_pp_eff,
                crisis_enabled=crisis_enabled,
                crisis_year=crisis_year,
                crisis_stock_dd=crisis_stock_dd,
                crisis_house_dd=crisis_house_dd,
                crisis_duration_months=crisis_duration_months,
                budget_enabled=budget_enabled,
                monthly_income=monthly_income,
                monthly_nonhousing=monthly_nonhousing,
                income_growth_pct=income_growth_pct,
                budget_allow_withdraw=budget_allow_withdraw,
                condo_inf_mo=_annual_effective_dec_to_monthly_eff(condo_inf),
                assume_sale_end=assume_sale_end,
                is_principal_residence=is_principal_residence_cfg,
                show_liquidation_view=show_liquidation_view,
                cg_tax_end=cg_tax_end,
                home_sale_legal_fee=home_sale_legal_fee,
                mort_rate_nominal_pct=mort_rate_nominal_pct_use,
                canadian_compounding=canadian_compounding,
                prop_tax_growth_model=prop_tax_growth_model,
                prop_tax_hybrid_addon_pct=prop_tax_hybrid_addon_pct,
                investment_tax_mode=investment_tax_mode,
                special_assessment_amount=special_assessment_amount,
                special_assessment_month=special_assessment_month,
                cg_inclusion_policy=cg_inclusion_policy,
                cg_inclusion_threshold=cg_inclusion_threshold,
                reg_shelter_enabled=reg_shelter_enabled,
                reg_initial_room=reg_initial_room,
                reg_annual_room=reg_annual_room,
                mc_seed=mc_seed,
                progress_cb=progress_cb,
                summary_only=bool(mc_summary_only),
                precomputed_shocks=mc_precomputed_shocks,
            )
        else:
            # Legacy per-sim loop (fallback for extremely large sims/horizons or when explicitly disabled)
            buyer_nws, renter_nws = [], []
            buyer_unrecs, renter_unrecs = [], []

            buyer_liq_ends, renter_liq_ends = [], []

            buyer_ints, buyer_taxes, buyer_maints = [], [], []
            buyer_repairs, buyer_condos, buyer_ins = [], [], []
            buyer_utils, renter_rents, renter_ins_list = [], [], []
            renter_utils, renter_movings, buyer_pmts = [], [], []
            renter_pmts, deficits = [], []
            wins = 0
            ties = 0

            _mc_step = max(1, int(num_sims // 100)) if num_sims > 0 else 1

            for sim in range(num_sims):
                if mc_seed is not None:
                    np.random.seed(int(mc_seed) + sim)

                df_sim = simulate_single(
                    years,
                    buyer_mo,
                    renter_mo,
                    apprec_decimal,
                    mr_use,
                    nm,
                    pmt_use,
                    down_use,
                    close_use,
                    mort_use,
                    price_use,
                    rent_use,
                    p_tax_rate_use,
                    maint_rate_use,
                    repair_rate_use,
                    condo_use,
                    h_ins_use,
                    o_util_use,
                    r_ins_use,
                    r_util_use,
                    sell_cost_use,
                    rent_inf_use,
                    rent_control_frequency_years,
                    moving_cost_use,
                    moving_freq_use,
                    _annual_effective_dec_to_monthly_eff(general_inf),
                    (ret_std / math.sqrt(12.0)) if ret_std else 0.0,
                    (apprec_std / math.sqrt(12.0)) if apprec_std else 0.0,
                    invest_diff,
                    rent_closing,
                    mkt_corr,
                    rate_mode,
                    rate_reset_years_eff,
                    rate_reset_to_eff,
                    rate_reset_step_pp_eff,
                    rate_shock_enabled_eff,
                    rate_shock_start_year_eff,
                    rate_shock_duration_years_eff,
                    rate_shock_pp_eff,
                    crisis_enabled,
                    crisis_year,
                    crisis_stock_dd,
                    crisis_house_dd,
                    crisis_duration_months,
                    budget_enabled,
                    monthly_income,
                    monthly_nonhousing,
                    income_growth_pct,
                    budget_allow_withdraw,
                    _annual_effective_dec_to_monthly_eff(float(condo_inf)),
                    assume_sale_end,
                    show_liquidation_view,
                    cg_tax_end,
                    home_sale_legal_fee,
                    mort_rate_nominal_pct_use,
                    canadian_compounding,
                    prop_tax_growth_model,
                    prop_tax_hybrid_addon_pct,
                    investment_tax_mode,
                    special_assessment_amount,
                    special_assessment_month,
                    cg_inclusion_policy,
                    cg_inclusion_threshold,
                    reg_shelter_enabled,
                    reg_initial_room,
                    reg_annual_room,
                    is_principal_residence_cfg,
                )

                if bool(show_liquidation_view):
                    try:
                        buyer_liq_ends.append(float(df_sim.iloc[-1][_LIQ_B]))
                        renter_liq_ends.append(float(df_sim.iloc[-1][_LIQ_R]))
                    except Exception:
                        buyer_liq_ends.append(float("nan"))
                        renter_liq_ends.append(float("nan"))

                try:
                    b_end = float(df_sim.iloc[-1]["Buyer Net Worth"])
                    r_end = float(df_sim.iloc[-1]["Renter Net Worth"])
                    scale = max(1.0, abs(b_end), abs(r_end))
                    tol = max(1e-6, 1e-9 * scale)
                    if (b_end - r_end) > tol:
                        wins += 1
                    elif abs(b_end - r_end) <= tol:
                        ties += 1
                except Exception:
                    pass

                buyer_nws.append(df_sim["Buyer Net Worth"])
                renter_nws.append(df_sim["Renter Net Worth"])
                buyer_unrecs.append(df_sim["Buyer Unrecoverable"])
                renter_unrecs.append(df_sim["Renter Unrecoverable"])

                buyer_ints.append(df_sim["Interest"])
                buyer_taxes.append(df_sim["Property Tax"])
                buyer_maints.append(df_sim["Maintenance"])
                buyer_repairs.append(df_sim["Repairs"])
                buyer_condos.append(df_sim["Condo Fees"])
                buyer_ins.append(df_sim["Home Insurance"])
                buyer_utils.append(df_sim["Utilities"])
                renter_rents.append(df_sim["Rent"])
                renter_ins_list.append(df_sim["Rent Insurance"])
                renter_utils.append(df_sim["Rent Utilities"])
                renter_movings.append(df_sim["Moving"])
                buyer_pmts.append(df_sim["Buy Payment"])
                renter_pmts.append(df_sim["Rent Payment"])
                deficits.append(df_sim["Deficit"])

                if progress_cb is not None and (((sim + 1) % _mc_step == 0) or ((sim + 1) == num_sims)):
                    progress_cb(sim + 1, num_sims)

            if num_sims > 0:
                win_pct = (wins + 0.5 * ties) / float(num_sims) * 100.0
            else:
                win_pct = 0.0

            buyer_nw_med = np.median(buyer_nws, axis=0)
            renter_nw_med = np.median(renter_nws, axis=0)
            buyer_nw_low = np.percentile(buyer_nws, 5, axis=0)
            buyer_nw_high = np.percentile(buyer_nws, 95, axis=0)
            renter_nw_low = np.percentile(renter_nws, 5, axis=0)
            renter_nw_high = np.percentile(renter_nws, 95, axis=0)
            buyer_unrec_med = np.median(buyer_unrecs, axis=0)
            renter_unrec_med = np.median(renter_unrecs, axis=0)

            buyer_int_med = np.median(buyer_ints, axis=0)
            buyer_tax_med = np.median(buyer_taxes, axis=0)
            buyer_maint_med = np.median(buyer_maints, axis=0)
            buyer_repair_med = np.median(buyer_repairs, axis=0)
            buyer_condo_med = np.median(buyer_condos, axis=0)
            buyer_ins_med = np.median(buyer_ins, axis=0)
            buyer_util_med = np.median(buyer_utils, axis=0)
            renter_rent_med = np.median(renter_rents, axis=0)
            renter_ins_med = np.median(renter_ins_list, axis=0)
            renter_util_med = np.median(renter_utils, axis=0)
            renter_moving_med = np.median(renter_movings, axis=0)
            buyer_pmt_med = np.median(buyer_pmts, axis=0)
            renter_pmt_med = np.median(renter_pmts, axis=0)
            deficit_med = np.median(deficits, axis=0)

            buyer_nw_mean = np.mean(buyer_nws, axis=0)
            renter_nw_mean = np.mean(renter_nws, axis=0)
            buyer_unrec_mean = np.mean(buyer_unrecs, axis=0)
            renter_unrec_mean = np.mean(renter_unrecs, axis=0)

            df = pd.DataFrame(
                {
                    "Month": range(1, years * 12 + 1),
                    "Year": [(m - 1) // 12 + 1 for m in range(1, years * 12 + 1)],
                    "Buyer Net Worth": buyer_nw_med,
                    "Renter Net Worth": renter_nw_med,
                    "Buyer NW Mean": buyer_nw_mean,
                    "Renter NW Mean": renter_nw_mean,
                    "Buyer NW Low": buyer_nw_low,
                    "Buyer NW High": buyer_nw_high,
                    "Renter NW Low": renter_nw_low,
                    "Renter NW High": renter_nw_high,
                    "Buyer Unrecoverable": buyer_unrec_med,
                    "Renter Unrecoverable": renter_unrec_med,
                    "Buyer Unrec Mean": buyer_unrec_mean,
                    "Renter Unrec Mean": renter_unrec_mean,
                    "Interest": buyer_int_med,
                    "Property Tax": buyer_tax_med,
                    "Maintenance": buyer_maint_med,
                    "Repairs": buyer_repair_med,
                    "Condo Fees": buyer_condo_med,
                    "Home Insurance": buyer_ins_med,
                    "Utilities": buyer_util_med,
                    "Rent": renter_rent_med,
                    "Rent Insurance": renter_ins_med,
                    "Rent Utilities": renter_util_med,
                    "Moving": renter_moving_med,
                    "Buy Payment": buyer_pmt_med,
                    "Rent Payment": renter_pmt_med,
                    # Smooth recurring rent cost (excludes moving spikes). Useful for charts.
                    "Rent Cost (Recurring)": (renter_rent_med + renter_ins_med + renter_util_med),
                    "Deficit": deficit_med,
                }
            )

            # Optional after-tax liquidation view at horizon (cash-in-hand)
            liq_win_pct = None
            if bool(show_liquidation_view):
                try:
                    b_liq = np.asarray(buyer_liq_ends, dtype=np.float64)
                    r_liq = np.asarray(renter_liq_ends, dtype=np.float64)

                    # Always attach placeholder columns so the UI doesn't "disappear".
                    b_liq_series = np.full(years * 12, np.nan, dtype=np.float64)
                    r_liq_series = np.full(years * 12, np.nan, dtype=np.float64)
                    b_liq_mean_series = np.full(years * 12, np.nan, dtype=np.float64)
                    r_liq_mean_series = np.full(years * 12, np.nan, dtype=np.float64)
                    b_liq_low_series = np.full(years * 12, np.nan, dtype=np.float64)
                    b_liq_high_series = np.full(years * 12, np.nan, dtype=np.float64)
                    r_liq_low_series = np.full(years * 12, np.nan, dtype=np.float64)
                    r_liq_high_series = np.full(years * 12, np.nan, dtype=np.float64)

                    finite2 = np.isfinite(b_liq) & np.isfinite(r_liq)
                    if np.any(finite2):
                        b2 = b_liq[finite2]
                        r2 = r_liq[finite2]
                        b_liq_series[-1] = float(np.nanmedian(b2))
                        r_liq_series[-1] = float(np.nanmedian(r2))
                        b_liq_mean_series[-1] = float(np.nanmean(b2))
                        r_liq_mean_series[-1] = float(np.nanmean(r2))
                        b_liq_low_series[-1] = float(np.nanpercentile(b2, 5))
                        b_liq_high_series[-1] = float(np.nanpercentile(b2, 95))
                        r_liq_low_series[-1] = float(np.nanpercentile(r2, 5))
                        r_liq_high_series[-1] = float(np.nanpercentile(r2, 95))

                        diff2 = b2 - r2
                        scale2 = float(np.nanmedian(np.abs(np.concatenate([b2, r2])))) if b2.size else 1.0
                        scale2 = max(1.0, scale2)
                        tol2 = max(1e-6, 1e-9 * scale2)
                        wins2 = int(np.count_nonzero(diff2 > tol2))
                        ties2 = int(np.count_nonzero(np.abs(diff2) <= tol2))
                        liq_win_pct = (wins2 + 0.5 * ties2) / max(1.0, float(b2.size)) * 100.0
                        if (not np.isfinite(liq_win_pct)) or (liq_win_pct < -1e-9) or (liq_win_pct > 100.0 + 1e-9):
                            liq_win_pct = None

                    df[_LIQ_B] = b_liq_series
                    df[_LIQ_R] = r_liq_series
                    df["Buyer Liquidation NW Mean"] = b_liq_mean_series
                    df["Renter Liquidation NW Mean"] = r_liq_mean_series
                    df["Buyer Liquidation NW Low"] = b_liq_low_series
                    df["Buyer Liquidation NW High"] = b_liq_high_series
                    df["Renter Liquidation NW Low"] = r_liq_low_series
                    df["Renter Liquidation NW High"] = r_liq_high_series
                except Exception as _e:
                    df[_LIQ_B] = np.full(years * 12, np.nan, dtype=np.float64)
                    df[_LIQ_R] = np.full(years * 12, np.nan, dtype=np.float64)
                    liq_win_pct = None
                    try:
                        df.attrs["liquidation_error"] = str(_e)
                    except Exception:
                        pass

            # Attach MC diagnostics as attrs (UI consumes these)
            try:
                df.attrs["win_pct_pre_tax"] = float(win_pct) if win_pct is not None else None
                df.attrs["win_pct_liquidation"] = liq_win_pct
                df.attrs["mc_num_sims"] = int(num_sims)
                df.attrs["mc_seed"] = None if mc_seed is None else int(mc_seed)
            except Exception:
                pass
    else:
        df = simulate_single(
            years,
            buyer_mo,
            renter_mo,
            apprec_decimal,
            mr_use,
            nm,
            pmt_use,
            down_use,
            close_use,
            mort_use,
            price_use,
            rent_use,
            p_tax_rate_use,
            maint_rate_use,
            repair_rate_use,
            condo_use,
            h_ins_use,
            o_util_use,
            r_ins_use,
            r_util_use,
            sell_cost_use,
            rent_inf_use,
            rent_control_frequency_years,
            moving_cost_use,
            moving_freq_use,
            _annual_effective_dec_to_monthly_eff(general_inf),
            0.0,
            0.0,
            invest_diff,
            rent_closing,
            mkt_corr,
            rate_mode,
            rate_reset_years_eff,
            rate_reset_to_eff,
            rate_reset_step_pp_eff,
            rate_shock_enabled_eff,
            rate_shock_start_year_eff,
            rate_shock_duration_years_eff,
            rate_shock_pp_eff,
            crisis_enabled,
            crisis_year,
            crisis_stock_dd,
            crisis_house_dd,
            crisis_duration_months,
            budget_enabled,
            monthly_income,
            monthly_nonhousing,
            income_growth_pct,
            budget_allow_withdraw,
            _annual_effective_dec_to_monthly_eff(float(condo_inf)),
            assume_sale_end,
            show_liquidation_view,
            cg_tax_end,
            home_sale_legal_fee,
            mort_rate_nominal_pct_use,
            canadian_compounding,
            prop_tax_growth_model,
            prop_tax_hybrid_addon_pct,
            investment_tax_mode,
            special_assessment_amount,
            special_assessment_month,
            cg_inclusion_policy,
            cg_inclusion_threshold,
            reg_shelter_enabled,
            reg_initial_room,
            reg_annual_room,
            is_principal_residence_cfg,
        )

    # PV series (discounted net worth delta)
    disc_annual = _f(cfg.get("discount_rate", 0.0), 0.0)
    # Defensive normalization: UI widgets often express % as percent-points (e.g., 3.0 for 3%),
    # but the engine expects a decimal fraction (0.03). If a caller accidentally passes
    # percent-points, normalize here to avoid PV underflow to ~0.
    if disc_annual > 1.0:
        disc_annual = disc_annual / 100.0
        try:
            df.attrs["discount_rate_autonormalized"] = True
        except Exception:
            pass
    disc_mo = _annual_effective_dec_to_monthly_eff(disc_annual)
    if disc_mo > 0:
        pv_b = df["Buyer Net Worth"] / ((1 + disc_mo) ** df["Month"])
        pv_r = df["Renter Net Worth"] / ((1 + disc_mo) ** df["Month"])
        df["Buyer PV NW"] = pv_b
        df["Renter PV NW"] = pv_r
        df["PV Delta"] = pv_b - pv_r
        # If Monte Carlo mean series exist, also provide PV of the mean path (for Expected PV Δ).
        if "Buyer NW Mean" in df.columns and "Renter NW Mean" in df.columns:
            df["Buyer PV NW Mean"] = df["Buyer NW Mean"] / ((1 + disc_mo) ** df["Month"])
            df["Renter PV NW Mean"] = df["Renter NW Mean"] / ((1 + disc_mo) ** df["Month"])
            df["PV Delta Mean"] = df["Buyer PV NW Mean"] - df["Renter PV NW Mean"]
    else:
        df["Buyer PV NW"] = df["Buyer Net Worth"]
        df["Renter PV NW"] = df["Renter Net Worth"]
        df["PV Delta"] = df["Buyer Net Worth"] - df["Renter Net Worth"]
        # If Monte Carlo mean series exist, also provide PV of the mean path (for Expected PV Δ).
        if "Buyer NW Mean" in df.columns and "Renter NW Mean" in df.columns:
            df["Buyer PV NW Mean"] = df["Buyer NW Mean"]
            df["Renter PV NW Mean"] = df["Renter NW Mean"]
            df["PV Delta Mean"] = df["Buyer PV NW Mean"] - df["Renter PV NW Mean"]

    close_cash = down_use + close_use
    return df, close_cash, pmt_use, win_pct


def simulate_single(
    years,
    buyer_mo,
    renter_mo,
    apprec_annual_dec,
    mr,
    nm,
    pmt,
    down,
    close,
    mort,
    price,
    rent,
    p_tax_rate,
    maint_rate,
    repair_rate,
    condo,
    h_ins,
    o_util,
    r_ins,
    r_util,
    sell_cost,
    rent_inf_eff,
    rent_control_frequency_years,
    moving_cost,
    moving_freq,
    inf_mo,
    ret_std_mo,
    apprec_std_mo,
    invest_diff,
    rent_closing,
    mkt_corr,
    rate_mode,
    rate_reset_years,
    rate_reset_to,
    rate_reset_step_pp,
    rate_shock_enabled,
    rate_shock_start_year,
    rate_shock_duration_years,
    rate_shock_pp,
    crisis_enabled,
    crisis_year,
    crisis_stock_dd,
    crisis_house_dd,
    crisis_duration_months,
    budget_enabled,
    monthly_income,
    monthly_nonhousing,
    income_growth_pct,
    budget_allow_withdraw,
    condo_inf_mo,
    assume_sale_end,
    show_liquidation_view,
    cg_tax_end,
    home_sale_legal_fee,
    mort_rate_nominal_pct,
    canadian_compounding,
    prop_tax_growth_model="Hybrid (recommended for Toronto)",
    prop_tax_hybrid_addon_pct=0.5,
    investment_tax_mode=None,
    special_assessment_amount=0.0,
    special_assessment_month=0,
    cg_inclusion_policy="current",
    cg_inclusion_threshold=250000.0,
    reg_shelter_enabled=False,
    reg_initial_room=0.0,
    reg_annual_room=0.0,
    is_principal_residence=True,
):
    res = []

    # RENTER CAPITAL LOGIC
    r_nw = (down + close) if rent_closing else down
    b_nw = 0.0

    # Track taxable cost-basis for deferred capital gains / liquidation view
    r_basis = float(r_nw)  # renter portfolio principal (initial)
    b_basis = float(b_nw)  # buyer portfolio principal (initial)

    # Cash portion (0% return) for surplus tracking when invest_diff=False
    r_cash = 0.0
    b_cash = 0.0

    c_mort = mort
    c_home = price
    c_rent = rent

    # Rent increase cadence (years)
    try:
        rent_step_years = max(1, int(rent_control_frequency_years))
    except Exception:
        rent_step_years = 1

    # Track the quoted nominal annual mortgage rate (for resets/shocks), then derive the effective monthly rate.
    cur_rate_nominal_pct = (
        float(mort_rate_nominal_pct)
        if mort_rate_nominal_pct is not None
        else float(_monthly_rate_to_annual_nominal_pct(mr, bool(canadian_compounding)))
    )
    shock_was_active = False

    cum_b_op = 0.0
    cum_r_op = 0.0
    b_shortfall = 0.0
    r_shortfall = 0.0

    c_condo = condo
    c_h_ins = h_ins
    c_o_util = o_util
    c_r_ins = r_ins
    c_r_util = r_util

    next_move = moving_freq * 12

    # Correlation between stock and housing shocks (Monte Carlo).
    rho = float(np.clip(mkt_corr, -0.999999, 0.999999))
    rho_abs = abs(rho)
    a = math.sqrt(rho_abs)
    b = math.sqrt(1.0 - rho_abs)
    rho_sign = 1.0 if rho >= 0 else -1.0

    # Property tax base for modeling assessment/policy smoothing
    tax_base = float(price)

    for m in range(1, years * 12 + 1):
        if ret_std_mo > 0 or apprec_std_mo > 0:
            z_systemic = np.random.normal()
            z_stock_idio = np.random.normal()
            z_house_idio = np.random.normal()

            stock_shock = (a * z_systemic) + (b * z_stock_idio)
            house_shock = (a * rho_sign * z_systemic) + (b * z_house_idio)

            b_growth = np.exp(buyer_mo - 0.5 * ret_std_mo**2 + ret_std_mo * stock_shock)
            r_growth = np.exp(renter_mo - 0.5 * ret_std_mo**2 + ret_std_mo * stock_shock)

            monthly_sigma = apprec_std_mo
            home_growth = np.exp(
                _annual_effective_dec_to_monthly_log_mu(apprec_annual_dec)
                - 0.5 * monthly_sigma**2
                + monthly_sigma * house_shock
            )
        else:
            b_growth = np.exp(buyer_mo)
            r_growth = np.exp(renter_mo)
            home_growth = np.exp(_annual_effective_dec_to_monthly_log_mu(apprec_annual_dec))

        # Mortgage rate resets (renewals)
        rate_changed = False
        if rate_mode == "Reset every N years" and (rate_reset_years is not None) and (rate_reset_to is not None):
            reset_months = int(rate_reset_years) * 12
            if reset_months > 0 and m > 1 and ((m - 1) % reset_months == 0):
                reset_idx = int((m - 1) / reset_months)
                cur_rate_nominal_pct = float(rate_reset_to) + float(rate_reset_step_pp) * max(0, reset_idx - 1)
                rate_changed = True

        shock_active = False
        if rate_shock_enabled and (rate_shock_pp is not None):
            try:
                start_m = int(rate_shock_start_year) * 12 + 1
                dur_m = int(rate_shock_duration_years) * 12
                end_m = start_m + max(0, dur_m) - 1
            except (TypeError, ValueError):
                start_m, end_m = 61, 120
            shock_active = start_m <= m <= end_m

        eff_nominal = float(cur_rate_nominal_pct) + (float(rate_shock_pp) if shock_active else 0.0)
        mr = _clamp_monthly_rate(_annual_nominal_pct_to_monthly_rate(eff_nominal, bool(canadian_compounding)))

        if rate_changed or (shock_active != shock_was_active):
            rem_months = max(1, nm - (m - 1))
            pmt = _mortgage_payment(float(c_mort), float(mr), int(rem_months))
        shock_was_active = shock_active

        # Property tax modeling
        if str(prop_tax_growth_model).startswith("Market"):
            tax_base = float(c_home)
        elif str(prop_tax_growth_model).startswith("Inflation"):
            tax_base *= 1.0 + float(inf_mo)
        else:
            try:
                addon_mo = (1.0 + float(prop_tax_hybrid_addon_pct) / 100.0) ** (1.0 / 12.0) - 1.0
            except (TypeError, ValueError):
                addon_mo = 0.0
            cap_mo = (1.0 + float(inf_mo)) * (1.0 + addon_mo) - 1.0
            target = float(c_home)
            if target >= tax_base:
                tax_base = min(tax_base * (1.0 + cap_mo), target)
            else:
                tax_base = max(tax_base / (1.0 + cap_mo), target)

        m_tax = tax_base * p_tax_rate / 12.0
        m_maint = c_home * maint_rate / 12.0
        m_repair = c_home * repair_rate / 12.0

        # One-time special assessment shock (buyer-only, unrecoverable)
        try:
            _sa_m = int(special_assessment_month)
        except Exception:
            _sa_m = 0
        m_special = float(special_assessment_amount) if (_sa_m > 0 and m == _sa_m) else 0.0

        inte = c_mort * mr if c_mort > 0 else 0.0
        princ = pmt - inte if c_mort > 0 else 0.0
        if princ > c_mort:
            princ = c_mort

        b_out = (pmt if c_mort > 0 else 0.0) + m_tax + m_maint + m_repair + c_condo + c_h_ins + c_o_util + m_special
        b_op = inte + m_tax + m_maint + m_repair + c_condo + c_h_ins + c_o_util + m_special

        rent_paid = c_rent
        condo_paid = c_condo
        h_ins_paid = c_h_ins
        o_util_paid = c_o_util
        r_ins_paid = c_r_ins
        r_util_paid = c_r_util

        skip_last_move = bool(assume_sale_end) and (m == years * 12)
        m_moving = moving_cost if (m == next_move and not skip_last_move) else 0.0
        r_out = c_rent + c_r_ins + c_r_util + m_moving  # Total (incl. moving)
        r_out_recurring = c_rent + c_r_ins + c_r_util  # Recurring only
        r_op = r_out
        if m == next_move:
            next_move += moving_freq * 12

        # Budget / investing
        diff = b_out - r_out
        gap = diff
        inc_t = None
        b_budget_net = None
        r_budget_net = None

        if budget_enabled:
            inc0 = float(monthly_income) if monthly_income is not None else 0.0
            nonh = float(monthly_nonhousing) if monthly_nonhousing is not None else 0.0
            g = float(income_growth_pct) / 100.0 if income_growth_pct is not None else 0.0
            inc0 = max(0.0, inc0)
            nonh = max(0.0, nonh)
            g = max(-0.99, g)

            inc_t = inc0 * ((1.0 + g) ** ((m - 1) / 12.0)) if g != 0 else inc0

            b_budget_net = inc_t - nonh - b_out
            r_budget_net = inc_t - nonh - r_out

            # Buyer
            if b_budget_net >= 0:
                b_nw += b_budget_net
                b_basis += b_budget_net
            else:
                need = -b_budget_net
                if budget_allow_withdraw:
                    if b_nw >= need:
                        if b_nw > 0:
                            b_basis = b_basis * max(0.0, (b_nw - need) / b_nw)
                        b_nw -= need
                    else:
                        b_shortfall += need - b_nw
                        b_basis = 0.0
                        b_nw = 0.0
                else:
                    b_shortfall += need

            # Renter
            if r_budget_net >= 0:
                r_nw += r_budget_net
                r_basis += r_budget_net
            else:
                need = -r_budget_net
                if budget_allow_withdraw:
                    if r_nw >= need:
                        if r_nw > 0:
                            r_basis = r_basis * max(0.0, (r_nw - need) / r_nw)
                        r_nw -= need
                    else:
                        r_shortfall += need - r_nw
                        r_basis = 0.0
                        r_nw = 0.0
                else:
                    r_shortfall += need

        elif invest_diff:
            if diff > 0:
                r_nw += diff
                r_basis += diff
            else:
                b_nw += abs(diff)
                b_basis += abs(diff)

        else:
            # Surplus investing OFF: track as cash (0% return) to match vectorized MC
            if diff > 0:
                r_nw += diff
                r_basis += diff
                r_cash += diff
            elif diff < 0:
                b_nw += abs(diff)
                b_basis += abs(diff)
                b_cash += abs(diff)

        # Apply growth (cash earns 0%, only invested portion grows)
        r_nw = (r_nw - r_cash) * r_growth + r_cash
        b_nw = (b_nw - b_cash) * b_growth + b_cash
        c_home *= home_growth

        # Crisis shock (apply only to the invested portion, not to cash)
        if crisis_enabled:
            try:
                crisis_m_start = int(max(1.0, float(crisis_year)) * 12)
            except (TypeError, ValueError):
                crisis_m_start = int(5 * 12)
            dur = int(max(1, crisis_duration_months)) if crisis_duration_months is not None else 1
            if crisis_m_start <= m < crisis_m_start + dur:
                stock_dd = float(np.clip(crisis_stock_dd, 0.0, 0.95))
                house_dd = float(np.clip(crisis_house_dd, 0.0, 0.95))
                b_invested = b_nw - b_cash
                r_invested = r_nw - r_cash
                b_invested *= 1.0 - stock_dd
                r_invested *= 1.0 - stock_dd
                b_nw = b_invested + b_cash
                r_nw = r_invested + r_cash
                c_home *= 1.0 - house_dd

        if c_mort > 0:
            c_mort -= princ
        if c_mort < 0:
            c_mort = 0.0
        if rent_step_years <= 1:
            if m % 12 == 0:
                c_rent *= 1 + rent_inf_eff
        else:
            if m % (12 * rent_step_years) == 0:
                c_rent *= (1 + rent_inf_eff) ** float(rent_step_years)

        # CPI Inflation
        c_condo *= 1 + (condo_inf_mo if condo_inf_mo is not None else inf_mo)
        c_h_ins *= 1 + inf_mo
        c_o_util *= 1 + inf_mo
        c_r_ins *= 1 + inf_mo
        c_r_util *= 1 + inf_mo

        exit_cost = (c_home * sell_cost) if (assume_sale_end and m == years * 12) else 0.0
        exit_legal_fee = (
            float(home_sale_legal_fee)
            if (assume_sale_end and m == years * 12 and home_sale_legal_fee is not None)
            else 0.0
        )
        b_val = (c_home - c_mort) + b_nw - float(close) - exit_cost - exit_legal_fee

        # Optional after-tax liquidation view at horizon
        b_liq = None
        r_liq = None
        if show_liquidation_view and (m == years * 12):
            try:
                eff_cg = max(0.0, float(cg_tax_end) / 100.0)
            except (TypeError, ValueError):
                eff_cg = 0.0

            # If annual drag mode is active, don't apply extra CG at liquidation
            if str(investment_tax_mode or "").startswith("Annual"):
                eff_cg = 0.0

            b_gain = max(0.0, b_nw - b_basis)
            r_gain = max(0.0, r_nw - r_basis)

            b_taxable_gain = _taxable_gain_after_reg_shelter(
                b_gain, b_basis, years, reg_shelter_enabled, reg_initial_room, reg_annual_room
            )
            r_taxable_gain = _taxable_gain_after_reg_shelter(
                r_gain, r_basis, years, reg_shelter_enabled, reg_initial_room, reg_annual_room
            )

            b_tax = _cg_tax_due(b_taxable_gain, eff_cg, cg_inclusion_policy, cg_inclusion_threshold)
            r_tax = _cg_tax_due(r_taxable_gain, eff_cg, cg_inclusion_policy, cg_inclusion_threshold)

            b_port_after_tax = b_nw - b_tax
            r_port_after_tax = r_nw - r_tax

            # Buyer liquidation (cash-out): home equity (net of selling costs, and home CG tax if not a principal residence)
            is_principal_residence = bool(is_principal_residence)
            eff_home_cg = 0.0
            try:
                eff_home_cg = max(0.0, float(cg_tax_end) / 100.0)
            except Exception:
                eff_home_cg = 0.0

            home_tax = 0.0
            if bool(assume_sale_end) and (not is_principal_residence) and eff_home_cg > 0.0:
                home_acb = float(price) + float(close)  # purchase price + acquisition costs proxy
                home_proceeds_net = float(c_home) - float(exit_cost) - float(exit_legal_fee)
                home_gain = max(0.0, home_proceeds_net - float(home_acb))
                home_tax = float(_cg_tax_due(home_gain, eff_home_cg, cg_inclusion_policy, cg_inclusion_threshold))

            home_cash = ((c_home - c_mort) - exit_cost - exit_legal_fee - home_tax) if bool(assume_sale_end) else 0.0
            b_liq = home_cash + b_port_after_tax - float(close)
            r_liq = r_port_after_tax

        cum_b_op += b_op
        cum_r_op += r_op

        res.append(
            {
                "Month": m,
                "Year": (m - 1) // 12 + 1,
                "Buyer Net Worth": b_val,
                "Renter Net Worth": r_nw,
                "Buyer Unrecoverable": cum_b_op + close + exit_cost + exit_legal_fee,
                "Renter Unrecoverable": cum_r_op,
                "Buyer Home Equity": c_home - c_mort,
                "Rent Payment": r_out,
                "Rent Cost (Recurring)": r_out_recurring,
                "Buy Payment": b_out,
                "Deficit": gap,
                "Interest": inte,
                "Property Tax": m_tax,
                "Maintenance": m_maint,
                "Repairs": m_repair,
                "Special Assessment": m_special,
                "Condo Fees": condo_paid,
                "Home Insurance": h_ins_paid,
                "Utilities": o_util_paid,
                "Rent": rent_paid,
                "Rent Insurance": r_ins_paid,
                "Rent Utilities": r_util_paid,
                "Moving": m_moving,
                "Income (Monthly)": inc_t,
                "Buyer Net Cash": b_budget_net,
                "Renter Net Cash": r_budget_net,
                "Buyer Shortfall (Cum)": b_shortfall,
                "Renter Shortfall (Cum)": r_shortfall,
                "Buyer Liquidation NW": b_liq,
                "Renter Liquidation NW": r_liq,
            }
        )

    return pd.DataFrame(res)
