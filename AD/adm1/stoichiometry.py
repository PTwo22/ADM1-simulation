"""Peterson stoichiometric matrix for the 19 ADM1 biological processes."""

from __future__ import annotations

import numpy as np

from AD.adm1.parameters import ADM1Parameters
from AD.adm1.states import LIQUID_STATES, STATE_INDEX


PROCESS_NAMES = (
    "disintegration",
    "hydrolysis_carbohydrates",
    "hydrolysis_proteins",
    "hydrolysis_lipids",
    "uptake_sugars",
    "uptake_amino_acids",
    "uptake_lcfa",
    "uptake_valerate",
    "uptake_butyrate",
    "uptake_propionate",
    "uptake_acetate",
    "uptake_hydrogen",
    "decay_sugar_degraders",
    "decay_amino_acid_degraders",
    "decay_lcfa_degraders",
    "decay_c4_degraders",
    "decay_propionate_degraders",
    "decay_acetate_degraders",
    "decay_hydrogen_degraders",
)


def build_stoichiometric_matrix(parameters: ADM1Parameters) -> np.ndarray:
    """Return the 24-by-19 liquid-state stoichiometric matrix.

    Organic coefficients are on a kg-COD basis. The inorganic carbon and
    nitrogen rows are calculated from elemental conservation and therefore
    have kmol C or N per kg COD of process units.
    """
    parameters.validate()
    matrix = np.zeros((len(LIQUID_STATES), len(PROCESS_NAMES)), dtype=float)

    def add(process: int, **coefficients: float) -> None:
        for state, coefficient in coefficients.items():
            matrix[STATE_INDEX[state], process] = coefficient

    # R1-R4: disintegration and extracellular hydrolysis
    add(
        0,
        X_c=-1.0,
        S_I=parameters.f_sI_xc,
        X_I=parameters.f_xI_xc,
        X_ch=parameters.f_ch_xc,
        X_pr=parameters.f_pr_xc,
        X_li=parameters.f_li_xc,
    )
    add(1, X_ch=-1.0, S_su=1.0)
    add(2, X_pr=-1.0, S_aa=1.0)
    add(
        3,
        X_li=-1.0,
        S_fa=parameters.f_fa_li,
        S_su=1.0 - parameters.f_fa_li,
    )

    # R5-R6: acidogenesis
    add(
        4,
        S_su=-1.0,
        S_h2=(1.0 - parameters.Y_su) * parameters.f_h2_su,
        S_bu=(1.0 - parameters.Y_su) * parameters.f_bu_su,
        S_pro=(1.0 - parameters.Y_su) * parameters.f_pro_su,
        S_ac=(1.0 - parameters.Y_su) * parameters.f_ac_su,
        X_su=parameters.Y_su,
    )
    add(
        5,
        S_aa=-1.0,
        S_h2=(1.0 - parameters.Y_aa) * parameters.f_h2_aa,
        S_va=(1.0 - parameters.Y_aa) * parameters.f_va_aa,
        S_bu=(1.0 - parameters.Y_aa) * parameters.f_bu_aa,
        S_pro=(1.0 - parameters.Y_aa) * parameters.f_pro_aa,
        S_ac=(1.0 - parameters.Y_aa) * parameters.f_ac_aa,
        X_aa=parameters.Y_aa,
    )

    # R7-R10: acetogenesis
    add(
        6,
        S_fa=-1.0,
        S_ac=(1.0 - parameters.Y_fa) * 0.70,
        S_h2=(1.0 - parameters.Y_fa) * 0.30,
        X_fa=parameters.Y_fa,
    )
    add(
        7,
        S_va=-1.0,
        S_pro=(1.0 - parameters.Y_c4) * 0.54,
        S_ac=(1.0 - parameters.Y_c4) * 0.31,
        S_h2=(1.0 - parameters.Y_c4) * 0.15,
        X_c4=parameters.Y_c4,
    )
    add(
        8,
        S_bu=-1.0,
        S_ac=(1.0 - parameters.Y_c4) * 0.80,
        S_h2=(1.0 - parameters.Y_c4) * 0.20,
        X_c4=parameters.Y_c4,
    )
    add(
        9,
        S_pro=-1.0,
        S_ac=(1.0 - parameters.Y_pro) * 0.57,
        S_h2=(1.0 - parameters.Y_pro) * 0.43,
        X_pro=parameters.Y_pro,
    )

    # R11-R12: acetoclastic and hydrogenotrophic methanogenesis
    add(
        10,
        S_ac=-1.0,
        S_ch4=1.0 - parameters.Y_ac,
        X_ac=parameters.Y_ac,
    )
    add(
        11,
        S_h2=-1.0,
        S_ch4=1.0 - parameters.Y_h2,
        X_h2=parameters.Y_h2,
    )

    # R13-R19: decay returns active biomass to composite material.
    for process, biomass in enumerate(
        ("X_su", "X_aa", "X_fa", "X_c4", "X_pro", "X_ac", "X_h2"),
        start=12,
    ):
        add(process, **{biomass: -1.0, "X_c": 1.0})

    # Elemental closure for every process. S_IC and S_IN are in kmol m-3.
    for process in range(len(PROCESS_NAMES)):
        carbon_change = 0.0
        nitrogen_change = 0.0
        for state in parameters.carbon_content:
            coefficient = matrix[STATE_INDEX[state], process]
            carbon_change += coefficient * parameters.carbon_content[state]
            nitrogen_change += coefficient * parameters.nitrogen_content[state]
        matrix[STATE_INDEX["S_IC"], process] = -carbon_change
        matrix[STATE_INDEX["S_IN"], process] = -nitrogen_change

    return matrix


def elemental_residuals(
    matrix: np.ndarray, parameters: ADM1Parameters
) -> tuple[np.ndarray, np.ndarray]:
    """Return carbon and nitrogen residuals for matrix validation."""
    carbon = np.zeros(matrix.shape[1])
    nitrogen = np.zeros(matrix.shape[1])
    for process in range(matrix.shape[1]):
        carbon[process] = matrix[STATE_INDEX["S_IC"], process]
        nitrogen[process] = matrix[STATE_INDEX["S_IN"], process]
        for state in parameters.carbon_content:
            coefficient = matrix[STATE_INDEX[state], process]
            carbon[process] += coefficient * parameters.carbon_content[state]
            nitrogen[process] += coefficient * parameters.nitrogen_content[state]
    return carbon, nitrogen
