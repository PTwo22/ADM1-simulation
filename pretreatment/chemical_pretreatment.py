import math
from typing import Dict


class ChemicalPretreatment:
    """NaOH pretreatment model for scenarios S18-S20."""

    def __init__(self, concentration_wt_percent: float, wet_feed_mass_kg: float,
                 config: Dict):
        self.config = config
        self.concentration_wt_percent = concentration_wt_percent
        self.time_pre = config['contact_time_h']
        self.ph_pre = config['neutralised_pH']  # post-treatment target, not reactor pH

        if not math.isfinite(concentration_wt_percent) or not 0 <= concentration_wt_percent <= 3:
            raise ValueError("NaOH concentration must be between 0 and 3 wt%")
        if not math.isfinite(wet_feed_mass_kg) or wet_feed_mass_kg < 0:
            raise ValueError("Wet food-waste mass must be finite and non-negative")
        for key in ('K_C_wt_percent', 'n', 'alpha_chem', 'beta_chem', 'K_I', 'm'):
            if not math.isfinite(config[key]) or config[key] < 0:
                raise ValueError(f"Chemical coefficient {key} must be finite and non-negative")
        if any(config[key] == 0 for key in ('K_C_wt_percent', 'n', 'K_I', 'm')):
            raise ValueError("K_C, n, K_I and m must be positive")
        if config['chemical'] != 'NaOH' or config['inhibition_enabled']:
            raise ValueError("This configuration supports NaOH with inhibition disabled only")
        if concentration_wt_percent not in config['source_benchmark']:
            raise ValueError("No literature benchmark is available for this NaOH concentration")

        self.naoh_mass_kg = wet_feed_mass_kg * concentration_wt_percent / 100.0
        self.source_sodium_mol_L = (
            concentration_wt_percent
            * config['source_sodium_mol_L_per_wt_percent']
        )
        self.K_I = config['K_I']
        self.inhibition_exponent = config['m']
        self.pretreatment_temperature_C = config['pretreatment_temperature_C']
        self.benchmark = config['source_benchmark'][concentration_wt_percent]
        self.control_benchmark = config['source_benchmark'][0.0]
        # Compatibility with the existing Digester; no fungal treatment is applied.
        self.A = {i: 0.0 for i in ('carb', 'protein', 'lipid', 'inert')}
        self.fpsi = 0.0
        self.R_chem = self._calculate_chemical_response()
        self.scod_multiplier = 1.0 + config['alpha_chem'] * self.R_chem
        self.hydrolysis_multiplier = 1.0 + config['beta_chem'] * self.R_chem
        self.methane_yield_multiplier = (
            self.benchmark['methane_yield_mean_mL_gVS']
            / self.control_benchmark['methane_yield_mean_mL_gVS']
        )
        treated_relative_sd = (
            self.benchmark['methane_yield_sd_mL_gVS']
            / self.benchmark['methane_yield_mean_mL_gVS']
        )
        control_relative_sd = (
            self.control_benchmark['methane_yield_sd_mL_gVS']
            / self.control_benchmark['methane_yield_mean_mL_gVS']
        )
        self.methane_yield_multiplier_sd = self.methane_yield_multiplier * math.sqrt(
            treated_relative_sd**2 + control_relative_sd**2
        )
        # Final net-response accounting: Zhen et al.'s observed methane yields
        # already include the sodium present after each NaOH treatment. Applying
        # another inhibition multiplier would double-count the same effect.
        self.inhibition_factor = 1.0

    @property
    def source_scod_increase_pct(self) -> float:
        """Returns the reported SCOD increase relative to the source control."""
        return (
            self.benchmark['scod_mean'] / self.control_benchmark['scod_mean'] - 1.0
        ) * 100.0

    @property
    def source_methane_improvement_pct(self) -> float:
        """Returns the reported methane-yield increase relative to the source control."""
        return (self.methane_yield_multiplier - 1.0) * 100.0

    def _calculate_chemical_response(self) -> float:
        """Returns the bounded chemical concentration response."""
        concentration = self.concentration_wt_percent
        half_saturation = self.config['K_C_wt_percent']
        response_shape = self.config['n']

        # Formula 63 — Chemical concentration response
        # Source: Complete Formula Notation Scenario Literature Data, 6 Oct 2026.
        return concentration**response_shape / (
            half_saturation**response_shape + concentration**response_shape
        )

    def _calculate_chemical_scod(self, scod_control: float) -> float:
        """Returns treated SCOD in the same unit as baseline SCOD."""
        # Formula 64 — Chemical-treatment SCOD response
        # Source: Complete Formula Notation Scenario Literature Data, 6 Oct 2026.
        return scod_control * self.scod_multiplier

    def _calculate_chemical_hydrolysis(self, k_hyd_control: float) -> float:
        """Returns the final treated hydrolysis rate (1/day)."""
        # Formula 65 — Chemical-treatment hydrolysis modification
        # Source: Complete Formula Notation Scenario Literature Data, 6 Oct 2026.
        return k_hyd_control * self.hydrolysis_multiplier
