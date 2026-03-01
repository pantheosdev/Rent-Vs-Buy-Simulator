# Methodology

This document explains the mathematical models, formulas, and policy rules used by the Rent vs Buy Simulator.
For known simplifications and assumptions see [ASSUMPTIONS.md](ASSUMPTIONS.md).

---

## A. Semi-Annual Compounding (Canadian Mortgage Math)

Canadian mortgages compound **semi-annually** per the federal *Bank Act* (R.S.C. 1991, c. 46, s. 347.1).
Lenders quote a **nominal annual rate**; the simulator converts it to an effective monthly rate before
computing payments.

### Formula

```
monthly_rate = (1 + nominal_rate / 2)^(1/6) - 1
```

This is equivalent to `(1 + nominal_rate / 2)^(2/12) - 1`.

### Worked example — 5.00% nominal

```
monthly_rate = (1 + 0.05 / 2)^(1/6) - 1
             = (1.025)^(1/6) - 1
             ≈ 0.41239% per month
```

**Standard mortgage payment** on a $640,000 principal over 25 years (300 months) at 5.00% nominal:

```
P   = 640,000
mr  = 0.0041239
n   = 300

PMT = P × mr / (1 − (1 + mr)^−n)
    = 640,000 × 0.0041239 / (1 − 1.0041239^−300)
    ≈ $3,722.27 / month
```

### Comparison: US-style monthly compounding

US mortgages compound monthly, so the effective monthly rate is simply:

```
monthly_rate = nominal_rate / 12
```

For 5.00% nominal: `0.05 / 12 ≈ 0.41667%` per month — slightly *higher* than the Canadian rate,
resulting in slightly higher payments for the same nominal rate.

> **Source:** Bank of Canada / *Bank Act* (R.S.C. 1991, c. 46, s. 347.1)

---

## B. CMHC Default Insurance

Mortgage default insurance is **required** when the loan-to-value (LTV) ratio exceeds 80% and the
purchase price is at or below the insured mortgage price cap (see Section C).  The premium is expressed
as a percentage of the **base loan amount** (before the premium is added) and is **financed into the
mortgage**.

### Premium tiers

| LTV Band | Premium Rate |
|---|---|
| ≤ 80.00% | 0.00% (not required) |
| 80.01% – 85.00% | 2.80% |
| 85.01% – 90.00% | 3.10% |
| 90.01% – 95.00% | 4.00% |
| 90.01% – 95.00% (non-traditional DP) | 4.50% |

A **non-traditional down payment** includes borrowed funds, certain gift structures, or other
non-equity sources.

### How the premium is applied

```
insured_loan = base_loan × (1 + premium_rate)
```

The premium amount is added to the mortgage principal and amortized over the full term.

### Provincial sales tax on CMHC premiums

Some provinces levy PST/RST/QST on the insurance premium.  This tax is **due at closing in cash** and
cannot be rolled into the mortgage:

| Province | Tax Rate |
|---|---|
| Ontario | 8% RST |
| Saskatchewan | 6% PST |
| Quebec | 9% (9.975% for premiums paid on or after 2027-01-01) |
| All other provinces | 0% |

> **Source:** CMHC published rate schedule (policy last reviewed 2026-02-23)

---

## C. Minimum Down Payment Rules

| Purchase Price | Minimum Down Payment |
|---|---|
| ≤ $500,000 | 5% of price |
| $500,001 – insured cap | 5% of first $500,000 + 10% of remainder |
| ≥ insured cap | 20% of price |

The **insured mortgage price cap** is:

- **$1,500,000** for purchases on or after 2024-12-15
- **$1,000,000** for purchases before 2024-12-15

### Worked example — $750,000 home (post-2024-12-15)

```
min_dp = 5% × $500,000  +  10% × ($750,000 − $500,000)
       = $25,000         +  $25,000
       = $50,000
```

Resulting LTV: `($750,000 − $50,000) / $750,000 ≈ 93.3%` → CMHC premium applies.

---

## D. Land Transfer Tax

Land transfer tax (LTT) is levied by **all 13 provinces and territories** at closing.  The simulator
applies the correct bracket schedule for each jurisdiction and is date-aware for rule changes and
first-time home buyer (FTHB) exemptions.

### Ontario LTT — bracket structure

Ontario uses a **progressive bracket** schedule (as of 2017):

| Bracket | Rate |
|---|---|
| $0 – $55,000 | 0.5% |
| $55,001 – $250,000 | 1.0% |
| $250,001 – $400,000 | 1.5% |
| $400,001 – $2,000,000 | 2.0% |
| > $2,000,000 | 2.5% |

### Worked example — $800,000 purchase (Ontario)

```
$55,000 × 0.5%                           =     $275.00
($250,000 − $55,000) × 1.0%             =   $1,950.00
($400,000 − $250,000) × 1.5%            =   $2,250.00
($800,000 − $400,000) × 2.0%            =   $8,000.00
─────────────────────────────────────────────────────
Total Ontario LTT                        =  $12,475.00
```

Toronto additionally levies the **Municipal Land Transfer Tax (MLTT)** using the same bracket
structure, roughly doubling the total for Toronto purchases.

### FTHB exemptions

- **Ontario**: first-time buyers receive a full refund up to $4,000 (post-2017 rate schedule).
- **British Columbia**: first-time buyers receive a full exemption on the first $500,000 (with
  phase-out between $500,001 and $525,000) — **date-aware** based on BC policy schedule.

---

## E. Monte Carlo Engine

The simulator uses **log-normal Geometric Brownian Motion (GBM)** for home appreciation and stock
(investment) returns.

### Monthly growth factor

For each simulation step:

```
growth_factor = exp(μ_monthly - 0.5σ²_monthly + σ_monthly × Z)
```

where `Z ~ N(0, 1)` is a standard normal random shock.

### Why the Itô correction (`-0.5σ²`)

Without the `−0.5σ²` term the *expected* log-return would equal `μ_monthly`, but the *expected*
arithmetic return (what matters for average wealth) would be:

```
E[growth_factor] = exp(μ_monthly + 0.5σ²_monthly)
```

— higher than intended.  The Itô (Jensen's inequality) correction subtracts `0.5σ²` from the drift
so that the expected geometric growth rate matches the user-supplied mean return:

```
E[growth_factor] = exp(μ_monthly)   ✓
```

### Monthly log drift from annual return

```
μ_monthly = ln(1 + r_annual) / 12
```

### Correlated shocks (stock × housing)

The stock and housing return shocks are drawn from a **bivariate normal** distribution using a
Cholesky decomposition of the 2×2 correlation matrix:

```
L = cholesky([[1, ρ], [ρ, 1]])
[Z_stock, Z_housing] = L @ [U1, U2]    where U1, U2 ~ N(0,1) i.i.d.
```

This preserves the user-specified correlation `ρ` between equity markets and home values.

---

## F. Opportunity Cost Model

The simulator tracks **two portfolios** simultaneously:

| Portfolio | Starting Value | Monthly Contributions |
|---|---|---|
| Renter | `down_payment + buyer_closing_costs` | `(buyer_monthly_outflow − renter_monthly_outflow)` when `invest_diff = True` |
| Buyer | `0` | Any monthly surplus the buyer has vs the renter (symmetric) |

Both portfolios grow with the same GBM model (same shock draws, same seed), so differences in
terminal value reflect only the rent-vs-buy structural decision.

---

## G. Breakeven Solver

The breakeven solver uses a **bisection method** to find the single input rate that equalizes
buyer and renter terminal net worth.

| Scenario | Solver finds… |
|---|---|
| Buying leads (buyer NW > renter NW) | The renter investment return that would close the gap |
| Renting leads (renter NW > buyer NW) | The home appreciation rate that would close the gap |

### Monte Carlo stability

When Monte Carlo mode is enabled:

- The solver targets the **MC median** terminal net worth (not the mean).
- **Common random numbers** (CRN) are used across bisection iterations: the same random seed
  produces the same shock paths for every candidate rate, ensuring smooth convergence.

---

## H. Heatmap

The heatmap evaluates a **2-D grid** of two chosen parameters (e.g., home appreciation rate ×
renter investment return).

For each cell in the grid a full simulation is run (deterministic or Monte Carlo).  The output
metric for each cell is either:

- **Expected Δ** = `E[buyer_NW − renter_NW]`
- **Win%** = `P(buyer_NW > renter_NW)` (fraction of MC paths where buying wins)

Grid resolution and MC simulation count are controlled by **Performance mode** (Fast / Quality)
and optional advanced overrides.
