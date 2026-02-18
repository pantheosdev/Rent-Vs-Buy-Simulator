# Methodology (high level)

This document explains the simulator at a high level so users can understand what the outputs mean.

## What the simulator compares
For each month over the analysis horizon, the simulator computes a **cashflow-consistent** trajectory for:
- **Buying**: mortgage payments, property taxes, insurance, maintenance/repairs, condo fees, transaction costs, and equity accumulation.
- **Renting**: rent payments, renter insurance/utilities, and investing the **difference** between rent and the buyer's total outlay (where applicable).

Outputs are summarized as terminal **net worth** (and PV variants where enabled) for rent vs buy.

## Deterministic vs Monte Carlo
- **Deterministic**: uses the input assumptions directly (single-path).
- **Monte Carlo**: samples correlated shocks over time for home appreciation, rent growth, and investment returns (and any other stochastic drivers enabled).

## Breakevens
- When buying leads, the breakeven solver finds the renter investment return that equalizes terminal outcomes.
- When renting leads, it finds the home appreciation rate that equalizes terminal outcomes.

When volatility is enabled, the breakeven solver targets the **MC median** outcome and uses fixed common random numbers during bisection for stability.

## Heatmap
The heatmap evaluates a grid of two chosen parameters (e.g., home appreciation vs renter return) and plots either:
- Expected Δ (buy - rent)
- or Win% (P[buy > rent])

The grid size and MC sims are controlled by Performance mode (Fast/Quality) and optional advanced overrides.
