"""CLI / headless entry point for the RBV simulator.

Usage
-----
Run with a JSON scenario file:
    python -m rbv --config scenario.json --output results.csv

Dump an example scenario file:
    python -m rbv --example

Override individual parameters on the command line:
    python -m rbv --config scenario.json --set years=10 --set rate=6.5

The JSON config maps directly to the engine's ``cfg`` dict.  See --example
for all supported keys and their default values.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Default cfg — matches the engine's expected keys and types
# ---------------------------------------------------------------------------
_DEFAULT_CFG: dict = {
    # Core scenario
    "years": 25,
    "province": "Ontario",
    "price": 800000.0,
    "down": 160000.0,
    "rent": 3000.0,
    # Mortgage
    "rate": 5.0,           # annual nominal rate, percent
    "nm": 300,             # amortization in months (25 yr default)
    "canadian_compounding": True,
    # Ongoing ownership costs (fractions of home price per year, unless noted)
    "sell_cost": 0.05,     # 5% selling costs
    "p_tax_rate": 0.01,    # 1% property tax
    "maint_rate": 0.01,    # 1% maintenance
    "repair_rate": 0.005,  # 0.5% repairs
    "condo": 0.0,          # monthly condo fee ($)
    # Insurance & utilities (monthly $)
    "h_ins": 120.0,        # home insurance
    "r_ins": 35.0,         # renter insurance
    "o_util": 0.0,         # owner utilities above renter baseline
    "r_util": 0.0,         # renter utilities
    # Inflation (decimal, e.g. 0.02 = 2%)
    "general_inf": 0.02,
    "rent_inf": 0.02,
    # Monte Carlo
    "use_volatility": False,
    "ret_std": 0.15,
    "apprec_std": 0.10,
    # Tax / liquidation
    "investment_tax_mode": "Pre-tax (no investment taxes)",
    "assume_sale_end": True,
    "show_liquidation_view": True,
    "is_principal_residence": True,
    "discount_rate": 0.0,
    # Moving costs
    "moving_cost": 2000.0,
    "moving_freq": 5.0,
}

_DEFAULT_RUN: dict = {
    "buyer_ret_pct": 7.0,
    "renter_ret_pct": 7.0,
    "apprec_pct": 3.0,
    "invest_diff": 0.0,
    "rent_closing": False,
    "mkt_corr": 0.25,
    "mc_seed": 42,
    "force_deterministic": True,
    "num_sims_override": 1,
}


def _build_example() -> dict:
    """Return a complete example scenario dict (cfg + run parameters merged)."""
    return {
        "_comment": (
            "RBV CLI scenario file. 'cfg' keys feed the engine directly; "
            "'run' keys are top-level simulation parameters."
        ),
        "cfg": _DEFAULT_CFG.copy(),
        "run": _DEFAULT_RUN.copy(),
    }


def _apply_overrides(d: dict, overrides: list[str]) -> dict:
    """Apply --set key=value overrides, with basic type coercion."""
    for kv in overrides or []:
        if "=" not in kv:
            print(f"Warning: ignoring malformed --set argument (expected key=value): {kv!r}", file=sys.stderr)
            continue
        key, _, raw = kv.partition("=")
        key = key.strip()
        raw = raw.strip()
        # Coerce type: try int → float → bool → str
        coerced: bool | int | float | str
        if raw.lower() in ("true", "false"):
            coerced = raw.lower() == "true"
        else:
            try:
                coerced = int(raw)
            except ValueError:
                try:
                    coerced = float(raw)
                except ValueError:
                    coerced = raw
        d[key] = coerced
    return d


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m rbv",
        description="Rent vs Buy Simulator — headless/CLI mode.",
    )
    parser.add_argument(
        "--config", "-c",
        metavar="FILE",
        help="Path to a JSON scenario file. Use --example to generate a template.",
    )
    parser.add_argument(
        "--output", "-o",
        metavar="FILE",
        default="-",
        help="Output CSV file path. Use '-' (default) to print to stdout.",
    )
    parser.add_argument(
        "--set", "-s",
        dest="overrides",
        metavar="key=value",
        action="append",
        help="Override a cfg or run parameter. Repeat for multiple overrides.",
    )
    parser.add_argument(
        "--example",
        action="store_true",
        help="Print an example JSON scenario file and exit.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output summary as JSON instead of a CSV time-series.",
    )

    args = parser.parse_args(argv)

    if args.example:
        print(json.dumps(_build_example(), indent=2))
        return 0

    # Build scenario from config file (or pure defaults)
    scenario = _build_example()
    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"Error: config file not found: {config_path}", file=sys.stderr)
            return 1
        with config_path.open() as fh:
            user_scenario = json.load(fh)
        scenario["cfg"].update(user_scenario.get("cfg", {}))
        scenario["run"].update(user_scenario.get("run", {}))

    # Apply --set overrides (can target either cfg or run sub-dicts)
    for kv in args.overrides or []:
        if "=" not in kv:
            continue
        key, _, raw = kv.partition("=")
        key = key.strip()
        if key in scenario["run"]:
            _apply_overrides(scenario["run"], [kv])
        else:
            _apply_overrides(scenario["cfg"], [kv])

    # Import engine (deferred so --example works without heavy deps installed)
    try:
        from rbv.core.engine import run_simulation_core
    except ImportError as exc:
        print(f"Error importing engine: {exc}", file=sys.stderr)
        print("Ensure all dependencies are installed: pip install -r requirements.txt", file=sys.stderr)
        return 1

    cfg = scenario["cfg"]
    run = scenario["run"]

    print(
        f"Running simulation: price=${cfg['price']:,.0f}, down=${cfg['down']:,.0f}, "
        f"rate={cfg['rate']}%, years={cfg['years']}, "
        f"{'deterministic' if run['force_deterministic'] else 'Monte Carlo'}",
        file=sys.stderr,
    )

    try:
        df, close_cash, monthly_pmt, win_pct = run_simulation_core(
            cfg,
            buyer_ret_pct=run["buyer_ret_pct"],
            renter_ret_pct=run["renter_ret_pct"],
            apprec_pct=run["apprec_pct"],
            invest_diff=run["invest_diff"],
            rent_closing=run["rent_closing"],
            mkt_corr=run["mkt_corr"],
            force_deterministic=run["force_deterministic"],
            mc_seed=run["mc_seed"],
            num_sims_override=run["num_sims_override"],
        )
    except Exception as exc:
        print(f"Simulation error: {exc}", file=sys.stderr)
        return 1

    if df is None or df.empty:
        print("Error: simulation returned no data.", file=sys.stderr)
        return 1

    pmt_str = f"${monthly_pmt:,.2f}" if monthly_pmt is not None else "n/a"
    close_str = f"${close_cash:,.2f}" if close_cash is not None else "n/a"
    win_str = f"{win_pct:.1f}%" if win_pct is not None else "n/a"
    print(
        f"Complete. Monthly payment: {pmt_str}  |  "
        f"Closing costs: {close_str}  |  "
        f"Buyer wins: {win_str}",
        file=sys.stderr,
    )

    if args.json:
        # Output a compact summary JSON
        last = df.iloc[-1]
        buyer_nw_col = next((c for c in df.columns if "buyer" in c.lower() and "worth" in c.lower()), None)
        renter_nw_col = next((c for c in df.columns if "renter" in c.lower() and "worth" in c.lower()), None)
        summary = {
            "horizon_years": cfg["years"],
            "monthly_payment": round(monthly_pmt, 2) if monthly_pmt is not None else None,
            "closing_costs": round(close_cash, 2) if close_cash is not None else None,
            "buyer_win_pct": round(win_pct, 2) if win_pct is not None else None,
            "final_buyer_net_worth": round(float(last[buyer_nw_col]), 2) if buyer_nw_col else None,
            "final_renter_net_worth": round(float(last[renter_nw_col]), 2) if renter_nw_col else None,
        }
        output = json.dumps(summary, indent=2)
        if args.output == "-":
            print(output)
        else:
            Path(args.output).write_text(output + "\n")
        return 0

    # Default: CSV output
    csv_str = df.to_csv(index=False)
    if args.output == "-":
        print(csv_str, end="")
    else:
        out_path = Path(args.output)
        out_path.write_text(csv_str)
        print(f"Results written to {out_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
