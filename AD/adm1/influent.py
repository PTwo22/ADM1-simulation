"""Translate project feedstock and pretreatment inputs into ADM1 states."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np

from AD.adm1.chemistry import cations_for_target_pH
from AD.adm1.parameters import ADM1Parameters
from AD.adm1.states import STATE_INDEX, empty_state


@dataclass(frozen=True)
class InfluentDefinition:
    """Model-ready feed definition and its traceable conversion metadata."""

    state: np.ndarray
    initial_state: np.ndarray
    strong_cations_kmol_m3: float
    strong_anions_kmol_m3: float
    total_cod_kg_m3: float
    cod_per_kg_vs: float
    soluble_cod_fraction: float
    hydrolysis_multipliers: dict[str, float]
    notes: tuple[str, ...]


def _component_cod_factors(
    bmp_constants: Mapping[str, float],
    parameters: ADM1Parameters,
    inert_cod_per_kg_vs: float,
) -> dict[str, float]:
    # One kmol CH4 occupies 22.414 Nm3 and represents 64 kg COD.
    cod_per_nm3_ch4 = parameters.cod_per_kmol_ch4 / parameters.normal_m3_per_kmol
    return {
        "carb": float(bmp_constants["carb"]) * cod_per_nm3_ch4,
        "protein": float(bmp_constants["protein"]) * cod_per_nm3_ch4,
        "lipid": float(bmp_constants["lipid"]) * cod_per_nm3_ch4,
        # No methane is assigned to inert VS, but it still contributes COD.
        "inert": inert_cod_per_kg_vs,
    }


def build_influent(
    feedstock,
    pretreatment,
    *,
    olr_kg_vs_m3_d: float,
    hrt_d: float,
    target_pH: float,
    temperature_c: float,
    bmp_constants: Mapping[str, float],
    parameters: ADM1Parameters,
    scod_control_kg_cod_m3: float = 68.4,
    total_cod_reference_kg_m3: float = 197.0,
    alpha_scod: float = 1.41,
    alpha_hyd: float = 2.5,
    inert_cod_per_kg_vs: float = 1.42,
    inorganic_carbon_kmol_m3: float = 0.05,
    inorganic_nitrogen_kmol_m3: float = 0.04,
    strong_anions_kmol_m3: float = 0.02,
    soluble_cod_fraction_override: float | None = None,
) -> InfluentDefinition:
    """Create a COD-conserving ADM1 influent from project inputs.

    Pretreatment moves COD from particulate to matching soluble states and
    changes hydrolysis rates; it never creates COD. The SCOD relationship is
    the supplied Phase-1 equation and remains provisional until calibrated.
    """
    if olr_kg_vs_m3_d <= 0 or hrt_d <= 0:
        raise ValueError("OLR and HRT must be positive")
    if total_cod_reference_kg_m3 <= 0:
        raise ValueError("Reference total COD must be positive")

    cod_factors = _component_cod_factors(
        bmp_constants, parameters, inert_cod_per_kg_vs
    )
    cod_per_kg_vs = sum(
        feedstock.mixed_fractions[name] * cod_factors[name]
        for name in feedstock.organic_classes
    )
    vs_concentration = olr_kg_vs_m3_d * hrt_d
    component_cod = {
        name: vs_concentration
        * feedstock.mixed_fractions[name]
        * cod_factors[name]
        for name in feedstock.organic_classes
    }
    total_cod = sum(component_cod.values())

    baseline_soluble_fraction = min(
        0.95, max(0.0, scod_control_kg_cod_m3 / total_cod_reference_kg_m3)
    )
    if soluble_cod_fraction_override is None:
        soluble_fraction = min(
            0.95,
            baseline_soluble_fraction * (1.0 + alpha_scod * float(pretreatment.fpsi)),
        )
        fractionation_note = "SCOD-to-ADM1 fractionation and alpha_SCOD are provisional."
    else:
        if not 0.0 <= soluble_cod_fraction_override <= 0.95:
            raise ValueError("Soluble COD fraction override must be between 0 and 0.95")
        soluble_fraction = float(soluble_cod_fraction_override)
        fractionation_note = (
            "Soluble COD fraction is an explicit treatment-evidence override."
        )

    state = empty_state()
    state[STATE_INDEX["S_su"]] = component_cod["carb"] * soluble_fraction
    state[STATE_INDEX["X_ch"]] = component_cod["carb"] * (1.0 - soluble_fraction)
    state[STATE_INDEX["S_aa"]] = component_cod["protein"] * soluble_fraction
    state[STATE_INDEX["X_pr"]] = component_cod["protein"] * (1.0 - soluble_fraction)
    state[STATE_INDEX["S_fa"]] = component_cod["lipid"] * soluble_fraction
    state[STATE_INDEX["X_li"]] = component_cod["lipid"] * (1.0 - soluble_fraction)

    # Inert material is not made biodegradable by pretreatment.
    inert_soluble_fraction = min(0.10, baseline_soluble_fraction)
    state[STATE_INDEX["S_I"]] = component_cod["inert"] * inert_soluble_fraction
    state[STATE_INDEX["X_I"]] = component_cod["inert"] * (1.0 - inert_soluble_fraction)
    state[STATE_INDEX["S_IC"]] = inorganic_carbon_kmol_m3
    state[STATE_INDEX["S_IN"]] = inorganic_nitrogen_kmol_m3

    cations = cations_for_target_pH(
        state,
        target_pH,
        strong_anions_kmol_m3,
        parameters,
        temperature_c,
    )
    state[STATE_INDEX["S_cat"]] = cations
    state[STATE_INDEX["S_an"]] = strong_anions_kmol_m3
    hydrolysis_multipliers = {
        name: 1.0 + alpha_hyd * float(pretreatment.A.get(name, 0.0))
        for name in ("carb", "protein", "lipid")
    }
    initial = default_initial_state(state, parameters, temperature_c)
    return InfluentDefinition(
        state=state,
        initial_state=initial,
        strong_cations_kmol_m3=cations,
        strong_anions_kmol_m3=strong_anions_kmol_m3,
        total_cod_kg_m3=total_cod,
        cod_per_kg_vs=cod_per_kg_vs,
        soluble_cod_fraction=soluble_fraction,
        hydrolysis_multipliers=hydrolysis_multipliers,
        notes=(
            "Feed COD is derived from component BMP and COD equivalence.",
            fractionation_note,
            "Initial active biomass uses published BSM2 ADM1 seed values.",
        ),
    )


def default_initial_state(
    influent: np.ndarray, parameters: ADM1Parameters, temperature_c: float = 35.0
) -> np.ndarray:
    """Create a viable start-up state using BSM2 biomass seed values."""
    initial = np.array(influent, dtype=float, copy=True)
    benchmark_values = {
        "S_va": 0.0123,
        "S_bu": 0.0140,
        "S_pro": 0.0176,
        "S_ac": 0.0893,
        "S_h2": 2.5055e-7,
        "S_ch4": 0.0555,
        "X_su": 0.3122,
        "X_aa": 0.9317,
        "X_fa": 0.3384,
        "X_c4": 0.3258,
        "X_pro": 0.1011,
        "X_ac": 0.6772,
        "X_h2": 0.2848,
    }
    # Food-waste OLR is substantially higher than the BSM2 sludge benchmark.
    # Scaling only the active inoculum avoids an artificial start-up acid
    # crash while leaving the scenario feed and steady equations unchanged.
    inoculum_scale = 5.0
    for name, value in benchmark_values.items():
        initial[STATE_INDEX[name]] = (
            value * inoculum_scale if name.startswith("X_") else value
        )

    dry_pressure = (
        parameters.atmospheric_pressure_bar
        - parameters.water_vapour_pressure(temperature_c)
    )
    p_h2 = 1.0e-5
    p_ch4 = 0.60 * (dry_pressure - p_h2)
    p_co2 = dry_pressure - p_h2 - p_ch4
    gas_factor = parameters.gas_constant_bar_m3_per_kmol_k * (temperature_c + 273.15)
    initial[STATE_INDEX["G_h2"]] = (
        p_h2 / gas_factor * parameters.cod_per_kmol_h2
    )
    initial[STATE_INDEX["G_ch4"]] = (
        p_ch4 / gas_factor * parameters.cod_per_kmol_ch4
    )
    initial[STATE_INDEX["G_co2"]] = p_co2 / gas_factor
    return initial
