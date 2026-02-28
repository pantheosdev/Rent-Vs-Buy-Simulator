"""Scenario management module for the Rent-vs-Buy simulator.

Provides save/load helpers for persisting simulation configurations to
JSON and a Streamlit UI for managing named scenarios within a session.

Functions
---------
save_scenario(cfg, results, file_path)
    Serialise the current configuration and scalar results to a JSON file.

load_scenario(file_path)
    Load a saved scenario from disk and return cfg and results.

build_scenario_payload(cfg, results)
    Build a JSON-serialisable dict from cfg and results.

render_scenario_ui(st_module, cfg, results)
    Display UI controls for saving and loading scenarios.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple


def build_scenario_payload(cfg: Dict[str, Any], results: Any) -> Dict[str, Any]:
    """Build a JSON-serialisable snapshot of the current run.

    The ``results`` dict may contain a pandas DataFrame under the ``"df"``
    key; that is excluded from the snapshot because DataFrames are not
    directly JSON-serialisable and can be large.  All other scalar and
    list values are included.

    Parameters
    ----------
    cfg : Dict[str, Any]
        Simulation configuration dict.
    results : Any
        Results dict returned by ``app.run_simulation``.

    Returns
    -------
    Dict[str, Any]
        A plain dict with ``cfg`` and ``results_summary`` sub-dicts.
    """
    summary: Dict[str, Any] = {}
    if isinstance(results, dict):
        for k, v in results.items():
            if k == "df":
                continue  # skip DataFrame
            try:
                json.dumps(v)  # test serializability
                summary[k] = v
            except (TypeError, ValueError):
                summary[k] = str(v)
    return {"cfg": dict(cfg), "results_summary": summary}


def save_scenario(cfg: Dict[str, Any], results: Any, file_path: str) -> None:
    """Save a scenario configuration and results to a JSON file.

    Parameters
    ----------
    cfg : Dict[str, Any]
        The simulation configuration dictionary.
    results : Any
        The simulation results dict.
    file_path : str
        Path to the destination JSON file.
    """
    payload = build_scenario_payload(cfg, results)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, default=str, indent=2)


def load_scenario(file_path: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Load a scenario from a JSON file.

    Parameters
    ----------
    file_path : str
        Path to a JSON file previously written by ``save_scenario``.

    Returns
    -------
    Tuple[Dict[str, Any], Dict[str, Any]]
        The configuration dict and the results-summary dict.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    cfg = data.get("cfg", {})
    results_summary = data.get("results_summary", data.get("results", {}))
    return cfg, results_summary


def render_scenario_ui(st_module: Any, cfg: Dict[str, Any], results: Any) -> None:
    """Render Streamlit UI elements for managing scenarios.

    Provides controls to:
    - Download the current scenario as a JSON file.
    - Upload a previously saved scenario and display its key metrics.
    - Compare saved scenario metrics against the current run.

    Parameters
    ----------
    st_module : Any
        The Streamlit module instance used for rendering.
    cfg : Dict[str, Any]
        The current configuration dictionary.
    results : Any
        The current simulation results dict.
    """
    st_module.subheader("Scenarios")

    # ── Download current scenario ─────────────────────────────────────────────
    payload = build_scenario_payload(cfg, results)
    payload_json = json.dumps(payload, default=str, indent=2)
    st_module.download_button(
        label="Download current scenario (JSON)",
        data=payload_json,
        file_name="scenario.json",
        mime="application/json",
    )

    # ── Upload and inspect a saved scenario ───────────────────────────────────
    uploaded = st_module.file_uploader(
        "Load a saved scenario (JSON)",
        type="json",
        help="Upload a scenario previously downloaded from this app.",
    )
    if uploaded is not None:
        try:
            data = json.load(uploaded)
        except Exception as exc:
            st_module.error(f"Could not parse uploaded file: {exc}")
            return

        loaded_cfg = data.get("cfg", {})
        loaded_res = data.get("results_summary", data.get("results", {}))

        st_module.success("Scenario loaded.")

        # Side-by-side comparison of key metrics
        col1, col2 = st_module.columns(2)
        with col1:
            st_module.markdown("**Loaded scenario**")
            _show_scenario_metrics(st_module, loaded_cfg, loaded_res)
        with col2:
            st_module.markdown("**Current run**")
            cur_summary = payload.get("results_summary", {})
            _show_scenario_metrics(st_module, cfg, cur_summary)


def _show_scenario_metrics(
    st_module: Any,
    cfg: Dict[str, Any],
    results_summary: Dict[str, Any],
) -> None:
    """Render key metrics for a scenario in compact form."""
    rows: List[Tuple[str, str]] = []

    def _fmt(v: Any) -> str:
        if isinstance(v, float):
            if abs(v) >= 1000:
                return f"${v:,.0f}"
            return f"{v:.2f}"
        return str(v)

    # Config highlights
    for k, label in [
        ("price", "Home price"),
        ("down", "Down payment"),
        ("rate", "Mortgage rate (%)"),
        ("years", "Horizon (yr)"),
        ("rent", "Rent ($/mo)"),
    ]:
        v = cfg.get(k)
        if v is not None:
            rows.append((label, _fmt(v)))

    # Result highlights
    for k, label in [
        ("final_buyer_net_worth", "Final buyer NW"),
        ("final_renter_net_worth", "Final renter NW"),
        ("win_pct", "Buyer win % (MC)"),
    ]:
        v = results_summary.get(k)
        if v is not None:
            rows.append((label, _fmt(v)))

    for label, val in rows:
        st_module.text(f"{label}: {val}")
