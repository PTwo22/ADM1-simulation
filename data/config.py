"""Centralised baseline parameters for the Phase 1 screening model.

Values are literature-informed or provisional inputs from the supplied team
datasets. They are starting values for sensitivity analysis, not universally
validated operating limits.
"""

FW_FRACTIONS = {
    "carb": 0.50,
    "protein": 0.25,
    "lipid": 0.20,
    "inert": 0.05,
}

SCG_FRACTIONS = {
    "carb": 0.42,
    "protein": 0.16,
    "lipid": 0.22,
    "inert": 0.20,
}

FEEDSTOCK_BASELINE = {
    "m_wet": 1.0,
    "f_ts": 0.20,
    "f_vs_ts": 0.90,
    # kg SCG VS per kg food-waste VS; converted before Feedstock construction.
    "r_scg_to_fw": 0.04,
}

BMP_CONSTANTS = {
    "carb": 0.415,
    "protein": 0.496,
    "lipid": 1.014,
    "inert": 0.0,
}

# Provisional commercial fungal-enzyme screening case. A separate kinetic
# model is required for living-fungus SSF and co-culture scenarios.
PRETREATMENT_BASELINE = {
    "time_h": 24.0,
    "temperature_c": 60.0,
    "pH": 4.8,
}

ENZYME_DOSES = {
    "carb": 10.0,
    "protein": 10.0,
    "lipid": 10.0,
    "inert": 10.0,
}

_COMMON_ENZYME_RESPONSE = {
    "K_E": 10.0,
    "T_opt": 60.0,
    "sigma_T": 15.0,
    "pH_opt": 4.8,
    "sigma_pH": 1.5,
    "k_t": 0.4,
}

PRETREATMENT_CONFIG = {
    name: dict(_COMMON_ENZYME_RESPONSE)
    for name in ("carb", "protein", "lipid", "inert")
}

FPSI_WEIGHTS = {
    "carb": 0.25,
    "protein": 0.25,
    "lipid": 0.25,
    "inert": 0.25,
}

DIGESTER_CALIBRATION = {
    "alpha_hyd": 2.5,
}

DIGESTER_BASELINE = {
    "hydrolysis_rates_per_d": {
        "carb": 0.25,
        "protein": 0.20,
        "lipid": 0.10,
        "inert": 0.0,
    },
    "biodegradability": {
        "carb": 0.90,
        "protein": 0.60,
        "lipid": 0.73,
        "inert": 0.0,
    },
    "temperature_c": 35.0,
    "pH": 7.2,
    "olr_kg_vs_per_m3_d": 2.0,
    "hrt_d": 20.0,
    # Used only to estimate total raw-biogas flow in this screening version.
    "methane_fraction": 0.60,
}

SYSTEM_CONSTANTS = {
    "lhv_ch4_mj_per_nm3": 35.8,
    "chp_electrical_efficiency": 0.35,
}

# Retained for later solubilisation calibration; not applied independently in
# the methane model because doing so would double-count pretreatment benefits.
SCOD_CALIBRATION = {
    "control_kg_cod_per_m3": 68.4,
    "alpha_scod": 1.41,
}

MODEL_CONFIG = {
    "BMP_CONSTANTS": BMP_CONSTANTS,
    "DIGESTER_CALIBRATION": DIGESTER_CALIBRATION,
    "DIGESTER_BASELINE": DIGESTER_BASELINE,
    "SYSTEM_CONSTANTS": SYSTEM_CONSTANTS,
}
