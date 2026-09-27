"""Rate equations for ADM1 disintegration, hydrolysis and microbial uptake."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping

import numpy as np

from AD.adm1.chemistry import AcidBaseState, solve_pH
from AD.adm1.parameters import ADM1Parameters
from AD.adm1.states import STATE_INDEX


@dataclass(frozen=True)
class KineticDiagnostics:
    chemistry: AcidBaseState
    inhibition_aa: float
    inhibition_fa: float
    inhibition_c4: float
    inhibition_pro: float
    inhibition_ac: float
    inhibition_h2: float
    nitrogen_limitation: float


def _monod(substrate: float, half_saturation: float) -> float:
    substrate = max(substrate, 0.0)
    denominator = substrate + half_saturation
    return substrate / denominator if denominator > 0 else 0.0


def _pH_inhibition(pH: float, lower: float, upper: float) -> float:
    """Return the BSM2 Hill-function pH inhibition factor."""
    if upper <= lower:
        raise ValueError("Upper pH limit must exceed lower pH limit")
    hydrogen = 10.0 ** (-pH)
    midpoint_hydrogen = 10.0 ** (-(upper + lower) / 2.0)
    exponent = 3.0 / (upper - lower)
    numerator = midpoint_hydrogen**exponent
    return numerator / (hydrogen**exponent + numerator)


def calculate_process_rates(
    liquid: np.ndarray,
    parameters: ADM1Parameters,
    strong_cations_kmol_m3: float,
    strong_anions_kmol_m3: float,
    hydrolysis_multipliers: Mapping[str, float] | None = None,
    temperature_c: float = 35.0,
) -> tuple[np.ndarray, KineticDiagnostics]:
    """Return the 19 ADM1 process rates in kg COD m-3 d-1."""
    c = np.maximum(liquid, 0.0)
    chemistry = solve_pH(
        c,
        strong_cations_kmol_m3,
        strong_anions_kmol_m3,
        parameters,
        temperature_c,
    )
    multiplier = {"carb": 1.0, "protein": 1.0, "lipid": 1.0}
    if hydrolysis_multipliers is not None:
        multiplier.update({key: float(value) for key, value in hydrolysis_multipliers.items()})
    if any(value < 0 for value in multiplier.values()):
        raise ValueError("Hydrolysis multipliers cannot be negative")

    def value(name: str) -> float:
        return float(c[STATE_INDEX[name]])

    nitrogen = value("S_IN")
    nitrogen_limitation = nitrogen / (parameters.K_S_IN + nitrogen) if nitrogen > 0 else 0.0
    pH_aa = _pH_inhibition(
        chemistry.pH, parameters.pH_LL_aa, parameters.pH_UL_aa
    )
    pH_ac = _pH_inhibition(
        chemistry.pH, parameters.pH_LL_ac, parameters.pH_UL_ac
    )
    pH_h2 = _pH_inhibition(
        chemistry.pH, parameters.pH_LL_h2, parameters.pH_UL_h2
    )
    h2 = value("S_h2")
    inhibition_h2_fa = 1.0 / (1.0 + h2 / parameters.K_I_h2_fa)
    inhibition_h2_c4 = 1.0 / (1.0 + h2 / parameters.K_I_h2_c4)
    inhibition_h2_pro = 1.0 / (1.0 + h2 / parameters.K_I_h2_pro)
    inhibition_nh3 = 1.0 / (
        1.0 + chemistry.free_ammonia_kmol_m3 / parameters.K_I_nh3
    )

    inhibition_aa = nitrogen_limitation * pH_aa
    inhibition_fa = inhibition_aa * inhibition_h2_fa
    inhibition_c4 = inhibition_aa * inhibition_h2_c4
    inhibition_pro = inhibition_aa * inhibition_h2_pro
    inhibition_ac = nitrogen_limitation * pH_ac * inhibition_nh3
    inhibition_h2 = nitrogen_limitation * pH_h2

    rates = np.zeros(19, dtype=float)
    rates[0] = parameters.k_dis * value("X_c")
    rates[1] = parameters.k_hyd_ch * multiplier["carb"] * value("X_ch")
    rates[2] = parameters.k_hyd_pr * multiplier["protein"] * value("X_pr")
    rates[3] = parameters.k_hyd_li * multiplier["lipid"] * value("X_li")
    rates[4] = (
        parameters.k_m_su
        * _monod(value("S_su"), parameters.K_S_su)
        * value("X_su")
        * inhibition_aa
    )
    rates[5] = (
        parameters.k_m_aa
        * _monod(value("S_aa"), parameters.K_S_aa)
        * value("X_aa")
        * inhibition_aa
    )
    rates[6] = (
        parameters.k_m_fa
        * _monod(value("S_fa"), parameters.K_S_fa)
        * value("X_fa")
        * inhibition_fa
    )
    c4_total = value("S_va") + value("S_bu")
    valerate_share = value("S_va") / c4_total if c4_total > 0 else 0.0
    butyrate_share = value("S_bu") / c4_total if c4_total > 0 else 0.0
    rates[7] = (
        parameters.k_m_c4
        * _monod(value("S_va"), parameters.K_S_c4)
        * value("X_c4")
        * valerate_share
        * inhibition_c4
    )
    rates[8] = (
        parameters.k_m_c4
        * _monod(value("S_bu"), parameters.K_S_c4)
        * value("X_c4")
        * butyrate_share
        * inhibition_c4
    )
    rates[9] = (
        parameters.k_m_pro
        * _monod(value("S_pro"), parameters.K_S_pro)
        * value("X_pro")
        * inhibition_pro
    )
    rates[10] = (
        parameters.k_m_ac
        * _monod(value("S_ac"), parameters.K_S_ac)
        * value("X_ac")
        * inhibition_ac
    )
    rates[11] = (
        parameters.k_m_h2
        * _monod(value("S_h2"), parameters.K_S_h2)
        * value("X_h2")
        * inhibition_h2
    )
    for offset, biomass in enumerate(
        ("X_su", "X_aa", "X_fa", "X_c4", "X_pro", "X_ac", "X_h2")
    ):
        rates[12 + offset] = parameters.k_dec * value(biomass)

    diagnostics = KineticDiagnostics(
        chemistry=chemistry,
        inhibition_aa=inhibition_aa,
        inhibition_fa=inhibition_fa,
        inhibition_c4=inhibition_c4,
        inhibition_pro=inhibition_pro,
        inhibition_ac=inhibition_ac,
        inhibition_h2=inhibition_h2,
        nitrogen_limitation=nitrogen_limitation,
    )
    return rates, diagnostics
