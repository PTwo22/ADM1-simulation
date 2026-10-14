"""Feedstock composition and mass-basis calculations."""

from __future__ import annotations

import math
from typing import Dict, Mapping, Tuple


class Feedstock:
    """Represent a food-waste/SCG mixture on a volatile-solids basis.

    ``f_scg`` is the fraction of total mixture VS supplied by spent coffee
    grounds. Use :meth:`scg_fraction_from_fw_ratio` when the literature value
    is reported as kg SCG VS per kg food-waste VS.
    """

    organic_classes = ("carb", "protein", "lipid", "inert")

    def __init__(
        self,
        m_wet: float,
        f_ts: float,
        f_vs_ts: float,
        f_scg: float,
        fw_fractions: Mapping[str, float],
        scg_fractions: Mapping[str, float],
    ) -> None:
        self.m_wet = float(m_wet)
        self.f_ts = float(f_ts)
        self.f_vs_ts = float(f_vs_ts)
        self.f_scg = float(f_scg)
        self.fw_fractions = dict(fw_fractions)
        self.scg_fractions = dict(scg_fractions)

        self._validate_inputs()
        self.m_ts, self.m_vs = self._calculate_solids()
        self.mixed_fractions = self._calculate_mixed_fractions()
        self.component_masses = self._calculate_component_masses()

    @staticmethod
    def scg_fraction_from_fw_ratio(r_scg_to_fw: float) -> float:
        """Convert ``SCG/FW`` VS ratio to the SCG fraction of total VS."""
        if r_scg_to_fw < 0:
            raise ValueError("SCG-to-food-waste ratio cannot be negative")
        return r_scg_to_fw / (1.0 + r_scg_to_fw)

    def _validate_inputs(self) -> None:
        if self.m_wet <= 0:
            raise ValueError("Wet feed mass must be greater than zero")
        for name, value in (("TS fraction", self.f_ts), ("VS/TS fraction", self.f_vs_ts)):
            if not 0.0 < value <= 1.0:
                raise ValueError(f"{name} must be in the interval (0, 1]")
        if not 0.0 <= self.f_scg <= 1.0:
            raise ValueError("SCG fraction must be between zero and one")

        for label, fractions in (
            ("Food-waste", self.fw_fractions),
            ("SCG", self.scg_fractions),
        ):
            missing = set(self.organic_classes) - set(fractions)
            if missing:
                raise ValueError(f"{label} fractions are missing: {sorted(missing)}")
            if any(fractions[name] < 0 for name in self.organic_classes):
                raise ValueError(f"{label} fractions cannot be negative")
            if not math.isclose(
                sum(fractions[name] for name in self.organic_classes),
                1.0,
                rel_tol=0.0,
                abs_tol=1e-9,
            ):
                raise ValueError(f"{label} fractions must sum to 1.0")

    def _calculate_solids(self) -> Tuple[float, float]:
        """Return total-solids and volatile-solids masses in kg."""
        m_ts = self.m_wet * self.f_ts
        m_vs = m_ts * self.f_vs_ts
        return m_ts, m_vs

    def _calculate_mixed_fractions(self) -> Dict[str, float]:
        """Return mixture composition as fractions of total mixture VS."""
        return {
            name: (1.0 - self.f_scg) * self.fw_fractions[name]
            + self.f_scg * self.scg_fractions[name]
            for name in self.organic_classes
        }

    def _calculate_component_masses(self) -> Dict[str, float]:
        """Return the mass of each organic-matter class in kg VS."""
        return {
            name: self.m_vs * self.mixed_fractions[name]
            for name in self.organic_classes
        }

    def calculate_theoretical_bmp(self, bmp_constants: Mapping[str, float]) -> float:
        """Return theoretical methane potential in Nm3 CH4 per kg VS."""
        return sum(
            self.mixed_fractions[name] * float(bmp_constants[name])
            for name in ("carb", "protein", "lipid")
        )

    @property
    def mass_balance_error_kg_vs(self) -> float:
        """Absolute VS mass-balance residual for the feed representation."""
        return abs(sum(self.component_masses.values()) - self.m_vs)
