"""Pretreatment response models used by the screening simulation."""

from __future__ import annotations

import math
from typing import Dict, Mapping


class NoPretreatment:
    """Null pretreatment for the untreated control scenario."""

    organic_classes = ("carb", "protein", "lipid", "inert")

    def __init__(self) -> None:
        self.A = {name: 0.0 for name in self.organic_classes}
        self.fpsi = 0.0


class Pretreatment:
    """Calculate substrate-specific effectiveness and the aggregate FPSI.

    This class represents a commercial-enzyme screening treatment. It does
    not yet model fungal growth, respiration, aeration or contamination and
    therefore must not be used as the in-situ SSF model.
    """

    organic_classes = ("carb", "protein", "lipid", "inert")

    def __init__(
        self,
        temp_pre: float,
        ph_pre: float,
        time_pre: float,
        enzyme_doses: Mapping[str, float],
        config: Mapping[str, Mapping[str, float]],
        weights: Mapping[str, float],
    ) -> None:
        self.temp_pre = float(temp_pre)
        self.ph_pre = float(ph_pre)
        self.time_pre = float(time_pre)
        self.enzyme_doses = dict(enzyme_doses)
        self.config = {name: dict(values) for name, values in config.items()}
        self.weights = dict(weights)

        self._validate_inputs()
        self.A = self._calculate_effectiveness()
        self.fpsi = self._calculate_fpsi()

    def _validate_inputs(self) -> None:
        if not all(
            math.isfinite(value)
            for value in (self.temp_pre, self.ph_pre, self.time_pre)
        ):
            raise ValueError("Pretreatment temperature, pH and time must be finite")
        if self.time_pre < 0:
            raise ValueError("Pretreatment time cannot be negative")
        if any(not math.isfinite(value) or value < 0 for value in self.enzyme_doses.values()):
            raise ValueError("Enzyme doses must be finite and non-negative")
        if any(not math.isfinite(value) or value < 0 for value in self.weights.values()):
            raise ValueError("FPSI weights must be finite and non-negative")
        if not math.isclose(sum(self.weights.values()), 1.0, abs_tol=1e-9):
            raise ValueError("FPSI weights must sum to 1.0")

        required = {"K_E", "T_opt", "sigma_T", "pH_opt", "sigma_pH", "k_t"}
        for name in self.organic_classes:
            if name not in self.config:
                raise ValueError(f"Missing pretreatment configuration for {name}")
            missing = required - set(self.config[name])
            if missing:
                raise ValueError(f"Pretreatment configuration for {name} is missing {sorted(missing)}")
            if any(
                not math.isfinite(float(self.config[name][field]))
                for field in required
            ):
                raise ValueError("Pretreatment configuration values must be finite")
            if self.config[name]["K_E"] < 0:
                raise ValueError("K_E cannot be negative")
            if self.config[name]["sigma_T"] <= 0 or self.config[name]["sigma_pH"] <= 0:
                raise ValueError("Temperature and pH tolerance widths must be positive")
            if self.config[name]["k_t"] < 0:
                raise ValueError("Time-response constants cannot be negative")

    def _calculate_dose_response(self, name: str) -> float:
        dose = self.enzyme_doses.get(name, 0.0)
        half_saturation = self.config[name]["K_E"]
        denominator = half_saturation + dose
        return dose / denominator if denominator > 0 else 0.0

    def _calculate_temp_response(self, name: str) -> float:
        values = self.config[name]
        z_score = (self.temp_pre - values["T_opt"]) / values["sigma_T"]
        return math.exp(-0.5 * z_score**2)

    def _calculate_ph_response(self, name: str) -> float:
        values = self.config[name]
        z_score = (self.ph_pre - values["pH_opt"]) / values["sigma_pH"]
        return math.exp(-0.5 * z_score**2)

    def _calculate_time_response(self, name: str) -> float:
        return 1.0 - math.exp(-self.config[name]["k_t"] * self.time_pre)

    def _calculate_effectiveness(self) -> Dict[str, float]:
        effectiveness: Dict[str, float] = {}
        for name in self.organic_classes:
            effectiveness[name] = (
                self._calculate_dose_response(name)
                * self._calculate_temp_response(name)
                * self._calculate_ph_response(name)
                * self._calculate_time_response(name)
            )
        return effectiveness

    def _calculate_fpsi(self) -> float:
        """Return the weighted fungal pretreatment severity index."""
        return sum(self.weights[name] * self.A[name] for name in self.organic_classes)
