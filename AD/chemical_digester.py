"""NaOH-specific Digester extension for scenarios S18-S20."""

from typing import Dict

from AD.digester import Digester


class ChemicalDigester(Digester):
    """Extends the original Digester without changing its source behavior."""

    def _calculate_modified_kinetics(self) -> Dict[str, float]:
        scod_control = self.baselines['scod']
        scod_treated = self.pretreatment._calculate_chemical_scod(scod_control)
        return {
            'scod_treated': scod_treated,
            'scod_increase_pct': (
                (scod_treated - scod_control) / scod_control * 100.0
                if scod_control > 0 else 0.0
            ),
            'k_hyd_modified': self.pretreatment._calculate_chemical_hydrolysis(
                self.baselines['k_hyd']
            ),
            'lag_modified': self.baselines['lag_phase'],
        }

    def _calculate_treated_biodegradability(self) -> Dict[str, float]:
        b_treated = {}
        for organic_class in self.organic_classes:
            b_control = self.baselines['b_control'].get(organic_class, 0.0)
            if organic_class == 'inert':
                b_treated[organic_class] = b_control
                continue
            b_treated[organic_class] = min(
                1.0,
                b_control
                * self.pretreatment.methane_yield_multiplier
                * self.pretreatment.inhibition_factor,
            )
        return b_treated

    def _calculate_biogas_profile(self, r_total: float) -> dict:
        benchmark = self.pretreatment.benchmark
        f_ch4 = benchmark['ch4_fraction_mean_pct'] / 100.0
        f_co2 = benchmark['co2_fraction_mean_pct'] / 100.0
        f_other = benchmark['other_gas_fraction_mean_pct'] / 100.0
        biogas_volume = self.y_ch4_treated / f_ch4
        return {
            'ch4_fraction_pct': f_ch4 * 100.0,
            'co2_fraction_pct': f_co2 * 100.0,
            'other_gas_fraction_pct': f_other * 100.0,
            'biogas_volume_m3': biogas_volume,
            'co2_volume_m3': biogas_volume * f_co2,
            'other_gas_volume_m3': biogas_volume * f_other,
        }
