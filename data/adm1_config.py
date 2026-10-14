"""Project-specific translation settings for the dynamic ADM1 engine.

The standard ADM1 kinetic defaults live in :mod:`AD.adm1.parameters`. Values
in this file connect the supplied food-waste CSVs to those ADM1 states. Items
marked provisional require calibration before predictive or design use.
"""

ADM1_TRANSLATION = {
    "total_cod_reference_kg_m3": 197.0,
    "scod_control_kg_cod_m3": 68.4,
    "alpha_scod": 1.41,
    "alpha_hyd": 2.5,
    "inert_cod_per_kg_vs": 1.42,
    "inorganic_carbon_kmol_m3": 0.20,
    "inorganic_nitrogen_kmol_m3": 0.04,
    "strong_anions_kmol_m3": 0.02,
}

ADM1_TRANSLATION_STATUS = {
    "total_cod_reference_kg_m3": "supplied_dataset",
    "scod_control_kg_cod_m3": "provisional_cross_study",
    "alpha_scod": "provisional_cross_study_calibration",
    "alpha_hyd": "exploratory_proxy",
    "inert_cod_per_kg_vs": "provisional_adm1_fractionation",
    "inorganic_carbon_kmol_m3": "provisional_adm1_fractionation",
    "inorganic_nitrogen_kmol_m3": "provisional_adm1_fractionation",
    "strong_anions_kmol_m3": "provisional_charge_balance",
}

DEFAULT_ADM1_RUN = {
    "duration_d": 100.0,
    "output_points": 201,
    "liquid_volume_m3": 1.0,
    "gas_volume_m3": 0.10,
}
