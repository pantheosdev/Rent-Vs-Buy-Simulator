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

---

## What is NOT Modeled (Known Simplifications)

### Mortgage & Financing

- **No foreclosure / default modeling** — if the buyer's net worth goes deeply negative the
  simulation assumes they continue making payments.  No strategic default decision is modeled.
- **No OSFI B-20 stress test** — the qualifying rate (contract rate + 2%, floor 5.25%) is not
  enforced.  Users must self-screen for eligibility.  *(Planned for a future release.)*
- **No mortgage prepayment penalties** — breaking a fixed-rate mortgage early typically incurs an
  Interest Rate Differential (IRD) penalty.  This cost is not modeled.
- **Insurance below 80% LTV** — some buyers opt for portfolio insurance at lower LTVs to access
  better rates; the simulator treats < 80% LTV as uninsured.

### Government Programs & Accounts

- **No RRSP Home Buyers' Plan (HBP)** — the up-to-$35,000 withdrawal and 15-year repayment
  schedule are not modeled.  *(Planned for a future release.)*
- **No FHSA (First Home Savings Account)** — tax-advantaged accumulation and withdrawal are not
  modeled.  *(Planned for a future release.)*

### Taxes

- **No foreign buyer taxes** — BC's Foreign Buyer Tax and Ontario's Non-Resident Speculation Tax
  (NRST) are not modeled.
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
