"""State-vector definitions for the dynamic ADM1 implementation.

Liquid organic states use kg COD m-3. ``S_IC`` and ``S_IN`` use kmol C m-3
and kmol N m-3 respectively. Gas hydrogen and methane use kg COD m-3 of
headspace; gas carbon dioxide uses kmol C m-3 of headspace.
"""

from __future__ import annotations

from typing import Mapping

import numpy as np


LIQUID_STATES = (
    "S_su",
    "S_aa",
    "S_fa",
    "S_va",
    "S_bu",
    "S_pro",
    "S_ac",
    "S_h2",
    "S_ch4",
    "S_IC",
    "S_IN",
    "S_I",
    "S_cat",
    "S_an",
    "X_c",
    "X_ch",
    "X_pr",
    "X_li",
    "X_su",
    "X_aa",
    "X_fa",
    "X_c4",
    "X_pro",
    "X_ac",
    "X_h2",
    "X_I",
)

GAS_STATES = ("G_h2", "G_ch4", "G_co2")
STATE_NAMES = LIQUID_STATES + GAS_STATES
STATE_INDEX = {name: index for index, name in enumerate(STATE_NAMES)}

COD_LIQUID_STATES = tuple(
    name
    for name in LIQUID_STATES
    if name not in {"S_IC", "S_IN", "S_cat", "S_an"}
)

# Soluble organic ADM1 states reported as model SCOD. This is a model-state
# sum; a laboratory SCOD measurement may use a different sample preparation
# or analytical definition and must be compared on the same basis.
SOLUBLE_COD_STATES = (
    "S_su",
    "S_aa",
    "S_fa",
    "S_va",
    "S_bu",
    "S_pro",
    "S_ac",
    "S_h2",
    "S_ch4",
    "S_I",
)


def empty_state() -> np.ndarray:
    """Return a zero-filled ADM1 state vector."""
    return np.zeros(len(STATE_NAMES), dtype=float)


def vector_from_mapping(values: Mapping[str, float]) -> np.ndarray:
    """Build a state vector from a partial state-name mapping."""
    unknown = set(values) - set(STATE_NAMES)
    if unknown:
        raise ValueError(f"Unknown ADM1 state names: {sorted(unknown)}")
    vector = empty_state()
    for name, value in values.items():
        if value < 0:
            raise ValueError(f"ADM1 state {name} cannot be negative")
        vector[STATE_INDEX[name]] = float(value)
    return vector


def mapping_from_vector(vector: np.ndarray) -> dict[str, float]:
    """Return a state-name mapping for one ADM1 state vector."""
    if vector.shape != (len(STATE_NAMES),):
        raise ValueError(f"Expected {len(STATE_NAMES)} ADM1 states")
    return {name: float(vector[index]) for name, index in STATE_INDEX.items()}
