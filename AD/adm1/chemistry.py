"""Acid-base speciation and charge-balance pH calculation for ADM1."""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
from scipy.optimize import brentq

from AD.adm1.parameters import ADM1Parameters
from AD.adm1.states import STATE_INDEX


VFA_COD_PER_KMOL = {
    "S_va": 208.0,
    "S_bu": 160.0,
    "S_pro": 112.0,
    "S_ac": 64.0,
}


@dataclass(frozen=True)
class AcidBaseState:
    pH: float
    hydrogen_kmol_m3: float
    hydroxide_kmol_m3: float
    bicarbonate_kmol_m3: float
    carbon_dioxide_kmol_m3: float
    ammonium_kmol_m3: float
    free_ammonia_kmol_m3: float
    vfa_anions_kmol_m3: dict[str, float]


def _species_at_hydrogen(
    liquid: np.ndarray,
    hydrogen: float,
    parameters: ADM1Parameters,
    temperature_c: float,
) -> AcidBaseState:
    constants = parameters.equilibrium_constants(temperature_c)
    inorganic_carbon = max(float(liquid[STATE_INDEX["S_IC"]]), 0.0)
    inorganic_nitrogen = max(float(liquid[STATE_INDEX["S_IN"]]), 0.0)
    bicarbonate = inorganic_carbon * constants["co2"] / (constants["co2"] + hydrogen)
    carbon_dioxide = inorganic_carbon - bicarbonate
    ammonium = inorganic_nitrogen * hydrogen / (constants["in"] + hydrogen)
    free_ammonia = inorganic_nitrogen - ammonium
    anions: dict[str, float] = {}
    for state, cod_per_kmol in VFA_COD_PER_KMOL.items():
        total_kmol = max(float(liquid[STATE_INDEX[state]]), 0.0) / cod_per_kmol
        anions[state] = total_kmol * constants[state] / (constants[state] + hydrogen)
    return AcidBaseState(
        pH=-math.log10(hydrogen),
        hydrogen_kmol_m3=hydrogen,
        hydroxide_kmol_m3=constants["water"] / hydrogen,
        bicarbonate_kmol_m3=bicarbonate,
        carbon_dioxide_kmol_m3=carbon_dioxide,
        ammonium_kmol_m3=ammonium,
        free_ammonia_kmol_m3=free_ammonia,
        vfa_anions_kmol_m3=anions,
    )


def charge_residual(
    liquid: np.ndarray,
    hydrogen: float,
    strong_cations_kmol_m3: float,
    strong_anions_kmol_m3: float,
    parameters: ADM1Parameters,
    temperature_c: float = 35.0,
) -> float:
    """Return positive minus negative charge in kmol charge m-3."""
    species = _species_at_hydrogen(liquid, hydrogen, parameters, temperature_c)
    positive = (
        strong_cations_kmol_m3
        + species.ammonium_kmol_m3
        + species.hydrogen_kmol_m3
    )
    negative = (
        strong_anions_kmol_m3
        + species.bicarbonate_kmol_m3
        + species.hydroxide_kmol_m3
        + sum(species.vfa_anions_kmol_m3.values())
    )
    return positive - negative


def solve_pH(
    liquid: np.ndarray,
    strong_cations_kmol_m3: float,
    strong_anions_kmol_m3: float,
    parameters: ADM1Parameters,
    temperature_c: float = 35.0,
) -> AcidBaseState:
    """Solve electroneutrality for pH between 3 and 12."""

    def residual(log_hydrogen: float) -> float:
        hydrogen = 10.0**log_hydrogen
        return charge_residual(
            liquid,
            hydrogen,
            strong_cations_kmol_m3,
            strong_anions_kmol_m3,
            parameters,
            temperature_c,
        )

    lower, upper = -12.0, -3.0
    low_value, high_value = residual(lower), residual(upper)
    if low_value * high_value <= 0:
        log_hydrogen = brentq(residual, lower, upper, xtol=1e-11)
    else:
        # Extreme transient states can briefly fall outside the physical
        # bracket. Use the least-residual boundary rather than crashing the
        # integrator; result validation records any out-of-range pH.
        log_hydrogen = lower if abs(low_value) < abs(high_value) else upper
    return _species_at_hydrogen(
        liquid, 10.0**log_hydrogen, parameters, temperature_c
    )


def cations_for_target_pH(
    liquid: np.ndarray,
    target_pH: float,
    strong_anions_kmol_m3: float,
    parameters: ADM1Parameters,
    temperature_c: float = 35.0,
) -> float:
    """Calculate strong cations needed to initialise a target feed pH."""
    if not 3.0 <= target_pH <= 12.0:
        raise ValueError("Target pH must be between 3 and 12")
    hydrogen = 10.0 ** (-target_pH)
    residual_without_cations = charge_residual(
        liquid,
        hydrogen,
        0.0,
        strong_anions_kmol_m3,
        parameters,
        temperature_c,
    )
    return max(0.0, -residual_without_cations)
