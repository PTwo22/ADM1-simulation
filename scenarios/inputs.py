"""Validated, UI-independent inputs for ADM1 scenario runs."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from numbers import Integral
from typing import Mapping

from AD.feedstock import Feedstock
from data.adm1_config import ADM1_TRANSLATION, DEFAULT_ADM1_RUN
from data.config import FEEDSTOCK_BASELINE, FW_FRACTIONS, SCG_FRACTIONS


def input_schema() -> list[dict[str, object]]:
    """Return the simple UI input contract with units and validation bounds."""
    return [
        {"name": "wet_feed_mass_kg", "unit": "kg wet feed", "default": FEEDSTOCK_BASELINE["m_wet"], "minimum_exclusive": 0.0},
        {"name": "total_solids_fraction", "unit": "fraction wet basis", "default": FEEDSTOCK_BASELINE["f_ts"], "minimum_exclusive": 0.0, "maximum": 1.0},
        {"name": "volatile_solids_fraction_of_ts", "unit": "fraction of TS", "default": FEEDSTOCK_BASELINE["f_vs_ts"], "minimum_exclusive": 0.0, "maximum": 1.0},
        {"name": "influent_pH", "unit": "pH", "default": 7.2, "minimum": 3.0, "maximum": 12.0},
        {"name": "liquid_volume_m3", "unit": "m3", "default": DEFAULT_ADM1_RUN["liquid_volume_m3"], "minimum_exclusive": 0.0},
        {"name": "gas_volume_m3", "unit": "m3", "default": DEFAULT_ADM1_RUN["gas_volume_m3"], "minimum_exclusive": 0.0},
        {"name": "temperature_c", "unit": "degC", "default": 35.0, "minimum_exclusive": 0.0, "maximum_exclusive": 100.0},
        {"name": "duration_d", "unit": "d", "default": DEFAULT_ADM1_RUN["duration_d"], "minimum_exclusive": 0.0},
        {"name": "output_points", "unit": "count", "default": DEFAULT_ADM1_RUN["output_points"], "minimum": 2, "integer": True},
        {"name": "food_waste_fractions", "unit": "fraction of VS by class", "default": dict(FW_FRACTIONS), "advanced": True},
        {"name": "scg_fractions", "unit": "fraction of VS by class", "default": dict(SCG_FRACTIONS), "advanced": True},
        {"name": "adm1_translation", "unit": "mixed; see data/adm1_config.py", "default": dict(ADM1_TRANSLATION), "advanced": True},
    ]


@dataclass(frozen=True)
class SimulationInputs:
    """Inputs shared by all scenarios in one comparison.

    Scenario-specific pretreatment, SCG fraction, OLR and HRT remain in
    :class:`ScenarioSpec`. These values describe the common feed, reactor and
    ADM1 fractionation settings, allowing a UI to configure the model without
    importing its internal equation modules.
    """

    wet_feed_mass_kg: float = FEEDSTOCK_BASELINE["m_wet"]
    total_solids_fraction: float = FEEDSTOCK_BASELINE["f_ts"]
    volatile_solids_fraction_of_ts: float = FEEDSTOCK_BASELINE["f_vs_ts"]
    food_waste_fractions: Mapping[str, float] = field(
        default_factory=lambda: dict(FW_FRACTIONS)
    )
    scg_fractions: Mapping[str, float] = field(
        default_factory=lambda: dict(SCG_FRACTIONS)
    )
    influent_pH: float = 7.2
    liquid_volume_m3: float = DEFAULT_ADM1_RUN["liquid_volume_m3"]
    gas_volume_m3: float = DEFAULT_ADM1_RUN["gas_volume_m3"]
    temperature_c: float = 35.0
    duration_d: float = DEFAULT_ADM1_RUN["duration_d"]
    output_points: int = DEFAULT_ADM1_RUN["output_points"]
    adm1_translation: Mapping[str, float] = field(
        default_factory=lambda: dict(ADM1_TRANSLATION)
    )

    def validate(self) -> None:
        # Feedstock performs fraction and solids validation.
        self.build_feedstock(scg_fraction_vs=0.0)
        numeric = (
            self.influent_pH,
            self.liquid_volume_m3,
            self.gas_volume_m3,
            self.temperature_c,
            self.duration_d,
        )
        if not all(math.isfinite(float(value)) for value in numeric):
            raise ValueError("Simulation inputs must be finite")
        if not 3.0 <= self.influent_pH <= 12.0:
            raise ValueError("Influent pH must be between 3 and 12")
        if self.liquid_volume_m3 <= 0 or self.gas_volume_m3 <= 0:
            raise ValueError("Reactor liquid and gas volumes must be positive")
        if not 0.0 < self.temperature_c < 100.0:
            raise ValueError("Reactor temperature must be between 0 and 100 C")
        if (
            self.duration_d <= 0
            or not isinstance(self.output_points, Integral)
            or isinstance(self.output_points, bool)
            or self.output_points < 2
        ):
            raise ValueError("Simulation duration and output resolution are invalid")
        required = set(ADM1_TRANSLATION)
        if set(self.adm1_translation) != required:
            missing = sorted(required - set(self.adm1_translation))
            extra = sorted(set(self.adm1_translation) - required)
            raise ValueError(
                f"ADM1 translation keys do not match defaults; missing={missing}, extra={extra}"
            )
        if any(
            not math.isfinite(float(value)) or float(value) < 0
            for value in self.adm1_translation.values()
        ):
            raise ValueError("ADM1 translation values must be finite and non-negative")

    def build_feedstock(self, scg_fraction_vs: float) -> Feedstock:
        return Feedstock(
            m_wet=self.wet_feed_mass_kg,
            f_ts=self.total_solids_fraction,
            f_vs_ts=self.volatile_solids_fraction_of_ts,
            f_scg=scg_fraction_vs,
            fw_fractions=self.food_waste_fractions,
            scg_fractions=self.scg_fractions,
        )

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-friendly snapshot for traceability and UI display."""
        return {
            "wet_feed_mass_kg": self.wet_feed_mass_kg,
            "total_solids_fraction": self.total_solids_fraction,
            "volatile_solids_fraction_of_ts": self.volatile_solids_fraction_of_ts,
            "food_waste_fractions": dict(self.food_waste_fractions),
            "scg_fractions": dict(self.scg_fractions),
            "influent_pH": self.influent_pH,
            "liquid_volume_m3": self.liquid_volume_m3,
            "gas_volume_m3": self.gas_volume_m3,
            "temperature_c": self.temperature_c,
            "duration_d": self.duration_d,
            "output_points": self.output_points,
            "adm1_translation": dict(self.adm1_translation),
        }
