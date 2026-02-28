"""Scenario management module for the Rent‑vs‑Buy simulator.

This module contains functions for saving, loading and comparing
simulation scenarios. The original ``app.py`` implemented a number
of features that allowed users to store their current configuration
to JSON, reload previous scenarios and compare different runs side by
side. Extracting these features into a dedicated module helps reduce
the complexity of the main application file.

Functions
---------
save_scenario(cfg, results)
    Persist the current configuration and results to a file or
    user‑supplied storage.

load_scenario(file_path)
    Load a saved scenario from disk and return its configuration and
    results.

render_scenario_ui(st)
    Display UI controls for saving and loading scenarios.
"""
from __future__ import annotations

from typing import Any, Dict, Tuple

import json
import streamlit as st


def save_scenario(cfg: Dict[str, Any], results: Any, file_path: str) -> None:
    """Save a scenario configuration and results to a JSON file.

    Parameters
    ----------
    cfg : Dict[str, Any]
        The simulation configuration dictionary.
    results : Any
        The simulation results object.
    file_path : str
        The path to the file where the scenario should be saved.

    Notes
    -----
    This function serialises the configuration and results into
    JSON. In Phase 2, you may wish to adjust the structure or
    storage medium (e.g., session state, database, or cloud storage).
    """
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump({"cfg": cfg, "results": results}, f, default=str, indent=2)


def load_scenario(file_path: str) -> Tuple[Dict[str, Any], Any]:
    """Load a scenario from a JSON file.

    Parameters
    ----------
    file_path : str
        The path to the JSON file containing the scenario.

    Returns
    -------
    Tuple[Dict[str, Any], Any]
        The configuration dictionary and results object.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["cfg"], data["results"]


def render_scenario_ui(st_module: Any, cfg: Dict[str, Any], results: Any) -> None:
    """Render Streamlit UI elements for managing scenarios.

    Parameters
    ----------
    st_module : Any
        The Streamlit module instance used for rendering.
    cfg : Dict[str, Any]
        The current configuration dictionary.
    results : Any
        The current simulation results.

    Notes
    -----
    This function provides basic UI controls as a placeholder.
    In a full implementation, you might allow the user to name
    scenarios, view a list of previous scenarios, and compare
    multiple scenarios side by side.
    """
    st_module.subheader("Save or Load Scenario")
    if st_module.button("Save Current Scenario"):
        file_name = st_module.text_input("File name", value="scenario.json")
        if file_name:
            save_scenario(cfg, results, file_name)
            st_module.success(f"Scenario saved to {file_name}.")
    uploaded_file = st_module.file_uploader("Load Scenario", type="json")
    if uploaded_file:
        data = json.load(uploaded_file)
        st_module.write("Loaded scenario:")
        st_module.json(data)
