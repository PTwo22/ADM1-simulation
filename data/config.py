"""Centralised feedstock and pretreatment inputs for the ADM1 model.

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
    "m_wet": 10.0,
    "f_ts": 0.25,
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
    "temperature_c": 30.0,
    "pH": 5.5,
}

# Pretreatment conditions used by Dr Bita's supplied S1-S9 simulation.
PRETREATMENT_PROFILES = {
    "legacy": {
        "temperature_c": 60.0,
        "pH": 4.8,
        "response_temperature_c": 60.0,
        "response_pH": 4.8,
    },
    "bita_s3_reference": {
        "temperature_c": 30.0,
        "pH": 5.5,
        "response_temperature_c": 30.0,
        "response_pH": 5.5,
    },
}

ENZYME_DOSES = {
    "carb": 24.0,
    "protein": 18.0,
    "lipid": 12.0,
    "inert": 6.0,
}

ENZYME_DOSE_SPLIT = {
    "carb": 0.40,
    "protein": 0.30,
    "lipid": 0.20,
    "inert": 0.10,
}

PRETREATMENT_CONFIG = {
    "carb": {
        "K_E": 50.0, "T_opt": 30.0, "sigma_T": 8.0,
        "pH_opt": 5.5, "sigma_pH": 1.0, "k_t": 0.050,
    },
    "protein": {
        "K_E": 45.0, "T_opt": 32.0, "sigma_T": 8.0,
        "pH_opt": 6.0, "sigma_pH": 1.0, "k_t": 0.040,
    },
    "lipid": {
        "K_E": 60.0, "T_opt": 30.0, "sigma_T": 8.0,
        "pH_opt": 5.5, "sigma_pH": 1.2, "k_t": 0.030,
    },
    # The reference model's SCG-specific response is mapped to the inert/SCG
    # class used by this feed representation.
    "inert": {
        "K_E": 70.0, "T_opt": 28.0, "sigma_T": 10.0,
        "pH_opt": 5.0, "sigma_pH": 1.2, "k_t": 0.035,
    },
}

FPSI_WEIGHTS = {
    "carb": 0.35,
    "protein": 0.25,
    "lipid": 0.20,
    "inert": 0.20,
}
