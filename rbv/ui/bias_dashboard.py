"""Bias and sensitivity dashboard module for the Rent-vs-Buy simulator.

Renders a sensitivity analysis view showing how key inputs affect the
buy-vs-rent decision: a tornado chart of partial sensitivities and, when
Monte Carlo data are available, win-probability details.

Functions
---------
render_bias_dashboard(cfg, results, st_module)
    Display the bias and sensitivity analysis for the current simulation.
"""

from __future__ import annotations

from typing import Any, Dict


def _fmt_delta(v: float) -> str:
    """Format a net-worth delta for display."""
    sign = "+" if v >= 0 else ""
    return f"{sign}${v:,.0f}"


def render_bias_dashboard(cfg: Dict[str, Any], results: Any, st_module: Any) -> None:
    """Render the bias and sensitivity analysis dashboard.

    Displays a tornado chart of how individual input parameters affect
    the final net-worth difference (buyer minus renter), and shows
    Monte Carlo win-probability when available.

    Parameters
    ----------
    cfg : Dict[str, Any]
        Configuration dictionary from sidebar inputs.
    results : Any
        Simulation results dict returned by ``app.run_simulation``.
        Must contain ``final_buyer_net_worth`` and
        ``final_renter_net_worth``.  ``win_pct`` is used when present.
    st_module : Any
        The Streamlit module instance used for rendering.
    """
    try:
        import plotly.graph_objects as go
        from rbv.core.engine import run_simulation_core
    except ImportError as exc:
        st_module.warning(f"Sensitivity dashboard requires plotly: {exc}")
        return

    # ── Extract baseline values ───────────────────────────────────────────────
    base_buyer = float(results.get("final_buyer_net_worth", 0.0) or 0.0)
    base_renter = float(results.get("final_renter_net_worth", 0.0) or 0.0)
    base_delta = base_buyer - base_renter

    win_pct = results.get("win_pct")

    st_module.subheader("Sensitivity Analysis")

    # Win-probability summary (MC only)
    if win_pct is not None:
        try:
            wp = float(win_pct)
            st_module.metric(
                "Buyer wins (MC)",
                f"{wp:.1f}%",
                help="Percentage of Monte Carlo paths where buyer ends with higher net worth.",
            )
        except Exception:
            pass

    # ── Tornado chart ────────────────────────────────────────────────────────
    # Perturb each key input by +/-10% (or a fixed delta for small values)
    # and record the resulting change in (buyer NW - renter NW).

    def _run(cfg_override: dict) -> float:
        """Run a quick deterministic simulation and return buyer-minus-renter."""
        c = dict(cfg)
        c.update(cfg_override)
        try:
            df, _, _, _ = run_simulation_core(
                c,
                buyer_ret_pct=float(c.get("buyer_ret", 7.0)),
                renter_ret_pct=float(c.get("renter_ret", 7.0)),
                apprec_pct=float(c.get("apprec", 3.5)),
                invest_diff=float(c.get("invest_diff", 0.0)),
                rent_closing=bool(c.get("rent_closing", False)),
                mkt_corr=float(c.get("mkt_corr", 0.25)),
                force_deterministic=True,
                num_sims_override=1,
            )
            return float(df.iloc[-1]["Buyer Net Worth"]) - float(df.iloc[-1]["Renter Net Worth"])
        except Exception:
            return base_delta

    # Parameters to perturb: (label, cfg_key, relative_perturbation, absolute_fallback)
    perturbations = [
        ("Home price", "price", 0.10, 50_000.0),
        ("Down payment", "down", 0.10, 20_000.0),
        ("Mortgage rate", "rate", None, 1.0),
        ("Rent", "rent", 0.10, 300.0),
        ("Appreciation", "apprec", None, 1.0),
        ("Buyer return", "buyer_ret", None, 1.0),
        ("General inflation", "general_inf", None, 0.005),
    ]

    labels: list[str] = []
    low_deltas: list[float] = []
    high_deltas: list[float] = []

    with st_module.spinner("Computing sensitivity…"):
        for label, key, rel, abs_delta in perturbations:
            base_val = float(cfg.get(key, 0.0) or 0.0)
            if rel is not None:
                delta = max(base_val * rel, abs_delta)
            else:
                delta = abs_delta
            lo = _run({key: base_val - delta}) - base_delta
            hi = _run({key: base_val + delta}) - base_delta
            labels.append(label)
            low_deltas.append(lo)
            high_deltas.append(hi)

    # Sort by absolute swing (widest bar first)
    swings = [abs(h - l) for h, l in zip(high_deltas, low_deltas)]
    order = sorted(range(len(labels)), key=lambda i: swings[i])
    labels = [labels[i] for i in order]
    low_deltas = [low_deltas[i] for i in order]
    high_deltas = [high_deltas[i] for i in order]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="High input",
            y=labels,
            x=high_deltas,
            orientation="h",
            marker_color="#00B8A9",
        )
    )
    fig.add_trace(
        go.Bar(
            name="Low input",
            y=labels,
            x=low_deltas,
            orientation="h",
            marker_color="#F6416C",
        )
    )
    fig.add_vline(x=0, line_width=1, line_color="white", opacity=0.5)
    fig.update_layout(
        title="Sensitivity Tornado Chart (Δ buyer-minus-renter vs baseline)",
        xaxis_title="Change in (Buyer NW − Renter NW) ($)",
        barmode="overlay",
        template="plotly_dark",
        height=400,
    )
    st_module.plotly_chart(fig, use_container_width=True)
    st_module.caption(
        f"Baseline buyer−renter: {_fmt_delta(base_delta)}. "
        "Bars show how a ±10% (or ±1 pp) change in each input shifts the outcome."
    )
