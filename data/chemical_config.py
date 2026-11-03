"""Literature-backed configuration for NaOH scenarios S18-S20 only."""


CHEMICAL_PRETREATMENT_CONFIG = {
    'chemical': 'NaOH',
    'concentration_basis': 'wt% NaOH per wet food-waste mass',
    'source_reference': 'Zhen et al. (2023), https://doi.org/10.1515/gps-2023-0072',
    'kinetics_reference': 'Bala et al. (2019), https://doi.org/10.1016/j.jenvman.2019.02.083',
    'sodium_inhibition_reference': 'Hierholtzer and Akunna (2012), https://doi.org/10.2166/wst.2012.345',
    'sodium_threshold_reference': 'Anwar et al. (2016), https://doi.org/10.2166/wst.2016.035',
    'contact_time_h': 24.0,
    'pretreatment_temperature_C': 4.0,
    'neutralised_pH': 6.2,
    'neutralised_pH_tolerance': 0.1,
    'neutralisation_acid': 'HCl',
    'neutralisation_acid_molarity_mol_L': 1.0,
    'source_digestion_temperature_C': 37.0,
    'source_digestion_duration_days': 50,
    'source_waste_mass_g': 100.0,
    'source_inoculum_volume_mL': 300.0,
    'source_working_volume_L': 1.0,
    'source_replicates': 3,
    # Estimated SCOD fit, not coefficients reported by the authors.
    # The reported control/treated SCOD values are used as ratios only.
    'K_C_wt_percent': 0.334,
    'n': 1.370,
    'alpha_chem': 0.898,
    # Final response-calibrated structure: SCOD represents solubilisation and
    # the observed methane ratios represent the net treatment response. A
    # separate hydrolysis multiplier would count the same response twice.
    'beta_chem': 0.0,
    # Literature sodium-inhibition parameters are retained for documentation.
    # They are not multiplied into the observed net methane response again.
    'K_I': 0.21,  # mol Na+/L
    'm': 1.0,
    'inhibition_enabled': False,
    'inhibition_accounting': 'embedded in observed source methane yield',
    # The Zhen et al. 1 L protocol contributes 0.025 mol Na+/L per wt% NaOH.
    'source_sodium_mol_L_per_wt_percent': 0.025,
    # Zhen et al. (2023), section 3.1.2 and Table 5.
    'source_benchmark': {
        0.0: {
            'scod_mean': 134.6, 'scod_sd': 2.4,
            'biogas_yield_mean_mL_gVS': 675.5, 'biogas_yield_sd_mL_gVS': 6.5,
            'methane_yield_mean_mL_gVS': 370.2, 'methane_yield_sd_mL_gVS': 3.1,
            'ch4_fraction_mean_pct': 54.8, 'ch4_fraction_sd_pct': 4.7,
            'co2_fraction_mean_pct': 39.6, 'co2_fraction_sd_pct': 1.5,
            'other_gas_fraction_mean_pct': 5.6, 'other_gas_fraction_sd_pct': 0.4,
        },
        1.0: {
            'scod_mean': 233.5, 'scod_sd': 6.7,
            'biogas_yield_mean_mL_gVS': 650.8, 'biogas_yield_sd_mL_gVS': 7.8,
            'methane_yield_mean_mL_gVS': 393.1, 'methane_yield_sd_mL_gVS': 0.9,
            'ch4_fraction_mean_pct': 60.4, 'ch4_fraction_sd_pct': 3.6,
            'co2_fraction_mean_pct': 31.8, 'co2_fraction_sd_pct': 1.6,
            'other_gas_fraction_mean_pct': 7.8, 'other_gas_fraction_sd_pct': 0.8,
        },
        2.0: {
            'scod_mean': 245.9, 'scod_sd': 5.4,
            'biogas_yield_mean_mL_gVS': 671.0, 'biogas_yield_sd_mL_gVS': 4.5,
            'methane_yield_mean_mL_gVS': 411.3, 'methane_yield_sd_mL_gVS': 2.5,
            'ch4_fraction_mean_pct': 61.3, 'ch4_fraction_sd_pct': 0.9,
            'co2_fraction_mean_pct': 30.6, 'co2_fraction_sd_pct': 1.7,
            'other_gas_fraction_mean_pct': 8.1, 'other_gas_fraction_sd_pct': 0.3,
        },
        3.0: {
            'scod_mean': 249.8, 'scod_sd': 3.4,
            'biogas_yield_mean_mL_gVS': 703.6, 'biogas_yield_sd_mL_gVS': 5.3,
            'methane_yield_mean_mL_gVS': 434.1, 'methane_yield_sd_mL_gVS': 1.7,
            'ch4_fraction_mean_pct': 61.7, 'ch4_fraction_sd_pct': 2.1,
            'co2_fraction_mean_pct': 30.0, 'co2_fraction_sd_pct': 2.1,
            'other_gas_fraction_mean_pct': 8.3, 'other_gas_fraction_sd_pct': 0.6,
        },
    },
}
