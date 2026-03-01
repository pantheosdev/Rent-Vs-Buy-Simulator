# Assumptions & Known Simplifications

This document lists what the Rent vs Buy Simulator **does** and **does not** model.
For the underlying mathematics see [METHODOLOGY.md](METHODOLOGY.md).

---

## What IS Modeled

| Feature | Notes |
|---|---|
| **Semi-annual compounding** | Canadian Bank Act convention; see METHODOLOGY §A |
| **CMHC default insurance** | Full tiered rate schedule including non-traditional DP tier (4.50%) |
| **PST on CMHC premiums** | Ontario (8%), Saskatchewan (6%), Quebec (9% / 9.975%) — date-aware |
| **Minimum down payment rules** | Date-aware insured price cap ($1.5M post 2024-12-15, $1M before) |
| **Land transfer tax — all 13 provinces/territories** | Progressive bracket schedules, date-aware |
| **FTHB LTT exemptions** | Ontario (up to $4,000 rebate) and BC (full exemption to $500k) — date-aware |
| **GST/HST on new construction** | Applied where applicable by province |
| **Mortgage renewal / rate resets** | Staircase modeling for multi-term simulations |
| **Condo fee inflation** | CPI + configurable spread |
| **Capital gains tax on investment gains** | Applied at liquidation using inclusion rate tiers |
| **Principal residence exemption** | Home sale exempt from capital gains tax |
| **Special assessments** | One-time buyer shock in a configurable year |
| **Rent control** | Configurable frequency-based modeling |
| **Crisis / shock scenarios** | Short-term market disruption overlays |
| **Moving costs for renters** | Frequency-based cost modeling |
| **Budget mode** | Income-based affordability pre-screening |
| **Insured 30-year amortization** | Date-aware eligibility: FTB and/or new-build (2024 policy schedule) |
| **Foreign buyer taxes** | BC APTT (20%) and Ontario NRST (25%) — opt-in, date-aware rate history |
| **RRSP Home Buyers' Plan (HBP)** | Withdrawal up to $60k (post-2024-04-16) / $35k (prior) toward down payment; 15-year repayment obligation modeled as monthly buyer cash outflow with 2-year grace period |
| **FHSA (First Home Savings Account)** | Pre-purchase tax-advantaged accumulation ($8k/yr, $40k lifetime, available since 2023-04-01); balance applied to down payment supplement with contribution deduction credit |
| **Mortgage prepayment penalty (IRD)** | Opt-in modeling of the Interest Rate Differential penalty when selling before the mortgage term ends; uses max(3-month interest, IRD) formula |

---

## What is NOT Modeled (Known Simplifications)

### Mortgage & Financing

- **No foreclosure / default modeling** — if the buyer's net worth goes deeply negative the
  simulation assumes they continue making payments.  No strategic default decision is modeled.
- **OSFI B-20 stress test (informational display only)** — the B-20 qualifying rate (contract rate + 2%, floor 5.25%) is displayed below the mortgage rate input as an informational hint. The simulator does not enforce this gate; users must self-screen for eligibility.
- **IRD penalty is a simplified model** — the IRD calculation uses the linear formula `balance × rate_diff × remaining_term_years`, which is a common approximation. Actual lender IRD calculations vary and may use discounted posted rates or NPV-based methods. The user-supplied "rate drop assumption" is a proxy for the comparison rate.
- **Insurance below 80% LTV** — some buyers opt for portfolio insurance at lower LTVs to access
  better rates; the simulator treats < 80% LTV as uninsured.

### Government Programs & Accounts

- **HBP is modeled as full-repayment scenario** — the simulation assumes the buyer makes all 15-year HBP repayments on schedule. If repayments are missed, CRA adds the shortfall to taxable income; that income inclusion is not modeled here.
- **FHSA is a first-order estimate** — the FHSA balance and tax savings are computed using a simplified compound-growth model. Actual results depend on investment choices, contribution timing, and tax-year deduction elections.
- **Foreign buyer tax exemptions not modeled** — both BC and Ontario have exemption criteria (e.g., certain visa categories, nominees, spouses of citizens). The simulator applies the full rate when the "foreign buyer" toggle is enabled; users must self-screen for eligibility.

### Taxes

- **No property value reassessment timing** — property tax assessments may lag current market
  values.  The simulator uses the purchase price as the assessment base.

### Income & Rental

- **No rental income from owned property** — the buyer scenario does not model renting out
  rooms or additional units (e.g., basement suite income).

### Input Validation

- **Upper-bound input validation** — extreme inputs (e.g., 99% mortgage rate, 500% annual
  appreciation) will produce mathematically valid but economically absurd results.  The simulator
  does not cap or warn on most upper-bound scenarios.

---

## Data Freshness

Policy rules (CMHC rates, LTT brackets, price caps, PST rates) are date-gated in the source code
and timestamped with `POLICY_LAST_REVIEWED` markers in `rbv/core/policy_canada.py`.

A CI workflow (`policy-freshness.yml`) automatically creates reminder issues when review dates
become stale.

> **Users should always verify current rates and rules with their lender, insurer, and/or a
> licensed mortgage professional before making real financial decisions.**
