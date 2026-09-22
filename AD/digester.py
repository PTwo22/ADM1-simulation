"""First-order CSTR screening model for anaerobic digestion.

This is an ADM1-inspired Phase 1 model, not a full ADM1 implementation. It
separates the effect of pretreatment on degradation rate from its effect on
the ultimately biodegradable fraction and preserves an explicit VS basis.
"""

from __future__ import annotations

from typing import Dict, Mapping, Optional

from AD.results import SimulationResult


class Digester:
    """Evaluate methane recovery from untreated or pretreated feedstock."""

    organic_classes = ("carb", "protein", "lipid", "inert")

    def __init__(self, feedstock, pretreatment, config: Mapping[str, object]) -> None:
        self.feedstock = feedstock
        self.pretreatment = pretreatment
        self.calib = dict(config["DIGESTER_CALIBRATION"])
        self.baseline = dict(config["DIGESTER_BASELINE"])
        self.bmp_constants = dict(config["BMP_CONSTANTS"])
        self.system = dict(config["SYSTEM_CONSTANTS"])
        self._validate_config()

    def _validate_config(self) -> None:
        if self.baseline["hrt_d"] <= 0:
            raise ValueError("HRT must be greater than zero")
        if self.baseline["olr_kg_vs_per_m3_d"] < 0:
            raise ValueError("OLR cannot be negative")
        methane_fraction = self.baseline["methane_fraction"]
        if not 0.0 < methane_fraction <= 1.0:
            raise ValueError("Methane fraction must be in the interval (0, 1]")
        if self.system["lhv_ch4_mj_per_nm3"] <= 0:
            raise ValueError("Methane lower heating value must be positive")
        efficiency = self.system["chp_electrical_efficiency"]
        if not 0.0 <= efficiency <= 1.0:
            raise ValueError("CHP electrical efficiency must be between zero and one")

        for name in self.organic_classes:
            if name not in self.baseline["hydrolysis_rates_per_d"]:
                raise ValueError(f"Missing hydrolysis rate for {name}")
            if name not in self.baseline["biodegradability"]:
                raise ValueError(f"Missing biodegradability for {name}")
            if self.baseline["hydrolysis_rates_per_d"][name] < 0:
                raise ValueError("Hydrolysis rates cannot be negative")
            biodegradability = self.baseline["biodegradability"][name]
            if not 0.0 <= biodegradability <= 1.0:
                raise ValueError("Biodegradability values must be between zero and one")

    def _alpha_hyd(self, name: str) -> float:
        value = self.calib["alpha_hyd"]
        if isinstance(value, Mapping):
            return float(value.get(name, 0.0))
        return float(value)

    def _calculate_modified_kinetics(self) -> Dict[str, float]:
        """Calculate substrate-specific hydrolysis constants in d-1."""
        rates: Dict[str, float] = {}
        for name in self.organic_classes:
            base_rate = float(self.baseline["hydrolysis_rates_per_d"][name])
            effectiveness = float(self.pretreatment.A.get(name, 0.0))
            rates[name] = base_rate * (1.0 + self._alpha_hyd(name) * effectiveness)
        return rates

    def _calculate_treated_biodegradability(self) -> Dict[str, float]:
        """Increase accessible fraction without allowing values above one."""
        treated: Dict[str, float] = {}
        for name in self.organic_classes:
            control = float(self.baseline["biodegradability"][name])
            if name == "inert":
                treated[name] = control
                continue
            effectiveness = float(self.pretreatment.A.get(name, 0.0))
            treated[name] = min(1.0, control + (1.0 - control) * effectiveness)
        return treated

    def _cstr_conversion(self, rate_per_d: float) -> float:
        """Return first-order steady-state CSTR conversion at configured HRT."""
        rate_retention = rate_per_d * float(self.baseline["hrt_d"])
        return rate_retention / (1.0 + rate_retention) if rate_retention > 0 else 0.0

    def _yield_from(
        self,
        rates: Mapping[str, float],
        biodegradability: Mapping[str, float],
    ) -> float:
        methane_yield = 0.0
        for name in self.organic_classes:
            methane_yield += (
                self.feedstock.mixed_fractions[name]
                * float(self.bmp_constants.get(name, 0.0))
                * float(biodegradability[name])
                * self._cstr_conversion(float(rates[name]))
            )
        return methane_yield

    def _calculate_baseline_yield(self) -> float:
        return self._yield_from(
            self.baseline["hydrolysis_rates_per_d"],
            self.baseline["biodegradability"],
        )

    def _calculate_treated_yield(self) -> float:
        return self._yield_from(
            self._calculate_modified_kinetics(),
            self._calculate_treated_biodegradability(),
        )

    @staticmethod
    def _calculate_improvement(control: float, treated: float) -> float:
        if control <= 0:
            return 0.0
        return (treated - control) / control * 100.0

    def _calculate_energy(self, methane_rate: float) -> Dict[str, float]:
        energy_mj = methane_rate * float(self.system["lhv_ch4_mj_per_nm3"])
        electricity_kwh = (
            energy_mj * float(self.system["chp_electrical_efficiency"]) / 3.6
        )
        return {
            "energy_mj_per_m3_d": energy_mj,
            "electricity_kwh_per_m3_d": electricity_kwh,
        }

    def simulate(
        self,
        scenario: str,
        control_yield: Optional[float] = None,
    ) -> SimulationResult:
        """Run the screening calculation and return a structured result."""
        modified_rates = self._calculate_modified_kinetics()
        treated_biodegradability = self._calculate_treated_biodegradability()
        methane_yield = self._yield_from(modified_rates, treated_biodegradability)
        baseline_yield = self._calculate_baseline_yield()
        reference_yield = baseline_yield if control_yield is None else control_yield
        methane_rate = methane_yield * float(self.baseline["olr_kg_vs_per_m3_d"])
        energy = self._calculate_energy(methane_rate)

        return SimulationResult(
            scenario=scenario,
            fpsi=float(self.pretreatment.fpsi),
            theoretical_bmp_nm3_per_kg_vs=self.feedstock.calculate_theoretical_bmp(
                self.bmp_constants
            ),
            methane_yield_nm3_per_kg_vs=methane_yield,
            methane_rate_nm3_per_m3_d=methane_rate,
            methane_volume_nm3_feed_basis=methane_yield * self.feedstock.m_vs,
            raw_biogas_rate_nm3_per_m3_d=(
                methane_rate / float(self.baseline["methane_fraction"])
            ),
            energy_mj_per_m3_d=energy["energy_mj_per_m3_d"],
            electricity_kwh_per_m3_d=energy["electricity_kwh_per_m3_d"],
            improvement_pct_vs_control=self._calculate_improvement(
                reference_yield, methane_yield
            ),
            hydrolysis_rates_per_d=modified_rates,
            biodegradability=treated_biodegradability,
            conversion={
                name: self._cstr_conversion(modified_rates[name])
                for name in self.organic_classes
            },
            mass_balance_error_kg_vs=self.feedstock.mass_balance_error_kg_vs,
        )
