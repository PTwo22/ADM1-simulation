"""Traceable S1-S9 scenario definitions requested for the project."""

from __future__ import annotations

from dataclasses import dataclass
import math
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class ScenarioSpec:
    scenario_id: str
    name: str
    pretreatment_kind: str
    enzyme_dose_u_g: float
    pretreatment_time_h: float
    scg_fraction_vs: float
    olr_kg_vs_m3_d: float
    hrt_d: float
    changed_variable: str
    reference_scenario_id: str | None = None
    provisional: bool = True
    effectiveness_override: Mapping[str, float] | None = None
    fpsi_override: float | None = None
    fpsi_applicable: bool = True
    soluble_cod_fraction_override: float | None = None
    pretreatment_profile: str = "legacy"
    enzyme_dose_basis: str = "U/g dry food waste"

    def validate(self) -> None:
        if not self.scenario_id.strip() or not self.name.strip():
            raise ValueError("Scenario ID and name cannot be empty")
        if self.pretreatment_kind not in {
            "none",
            "fungal_enzyme_proxy",
            "chemical_cao_proxy",
            "custom",
        }:
            raise ValueError(f"Unsupported pretreatment kind: {self.pretreatment_kind}")
        if self.pretreatment_profile not in {"legacy", "bita_s3_reference"}:
            raise ValueError(
                f"Unsupported pretreatment profile: {self.pretreatment_profile}"
            )
        numeric = (
            self.enzyme_dose_u_g,
            self.pretreatment_time_h,
            self.scg_fraction_vs,
            self.olr_kg_vs_m3_d,
            self.hrt_d,
        )
        if not all(math.isfinite(float(value)) for value in numeric):
            raise ValueError("Scenario numeric inputs must be finite")
        if self.enzyme_dose_u_g < 0 or self.pretreatment_time_h < 0:
            raise ValueError("Pretreatment dose and duration cannot be negative")
        if not 0.0 <= self.scg_fraction_vs <= 1.0:
            raise ValueError("SCG fraction must be between zero and one")
        if self.olr_kg_vs_m3_d <= 0 or self.hrt_d <= 0:
            raise ValueError("OLR and HRT must be positive")
        if self.pretreatment_kind in {"custom", "chemical_cao_proxy"}:
            if self.effectiveness_override is None or self.fpsi_override is None:
                raise ValueError("Custom treatment requires effectiveness and FPSI")
            if not 0.0 <= self.fpsi_override <= 1.0:
                raise ValueError("Custom FPSI must be between zero and one")
            required = {"carb", "protein", "lipid", "inert"}
            if set(self.effectiveness_override) != required:
                raise ValueError("Custom effectiveness must define all four feed classes")
            if any(not 0.0 <= value <= 1.0 for value in self.effectiveness_override.values()):
                raise ValueError("Custom effectiveness values must be between zero and one")
        if (
            self.soluble_cod_fraction_override is not None
            and not 0.0 <= self.soluble_cod_fraction_override <= 0.95
        ):
            raise ValueError("Soluble COD fraction override must be between 0 and 0.95")


_SCENARIOS = {
    "S1": ScenarioSpec(
        "S1", "Control food waste; no pretreatment", "none", 0.0, 0.0,
        0.0, 2.5, 25.0, "control", provisional=False,
        pretreatment_profile="bita_s3_reference", enzyme_dose_basis="U/g VS",
    ),
    "S2": ScenarioSpec(
        "S2", "Low fungal pretreatment", "fungal_enzyme_proxy", 30.0, 12.0,
        0.0, 2.5, 25.0, "fungal dose: 30 U/g VS; duration: 12 h", "S1",
        pretreatment_profile="bita_s3_reference", enzyme_dose_basis="U/g VS",
    ),
    "S3": ScenarioSpec(
        scenario_id="S3",
        name="Selected fungal-treatment reference",
        pretreatment_kind="fungal_enzyme_proxy",
        enzyme_dose_u_g=60.0,
        pretreatment_time_h=24.0,
        scg_fraction_vs=0.0,
        olr_kg_vs_m3_d=2.5,
        hrt_d=25.0,
        changed_variable=(
            "fungal reference: 60 U/g VS, 24 h, 30 C, pH 5.5, "
            "no SCG, OLR 2.5, HRT 25 d"
        ),
        reference_scenario_id="S1",
        pretreatment_profile="bita_s3_reference",
        enzyme_dose_basis="U/g VS",
    ),
    "S4": ScenarioSpec(
        "S4", "High fungal pretreatment", "fungal_enzyme_proxy", 90.0, 36.0,
        0.0, 2.5, 25.0, "fungal dose: 90 U/g VS; duration: 36 h", "S3",
        pretreatment_profile="bita_s3_reference", enzyme_dose_basis="U/g VS",
    ),
    "S5": ScenarioSpec(
        "S5", "Long fungal pretreatment", "fungal_enzyme_proxy", 90.0, 72.0,
        0.0, 2.5, 25.0, "fungal dose: 90 U/g VS; duration: 72 h", "S3",
        pretreatment_profile="bita_s3_reference", enzyme_dose_basis="U/g VS",
    ),
    "S6": ScenarioSpec(
        "S6", "Moderate pretreatment + 10% SCG", "fungal_enzyme_proxy", 60.0, 24.0,
        0.10, 2.5, 25.0, "SCG: 10% of mixture VS", "S3",
        pretreatment_profile="bita_s3_reference", enzyme_dose_basis="U/g VS",
    ),
    "S7": ScenarioSpec(
        "S7", "Moderate pretreatment + 20% SCG", "fungal_enzyme_proxy", 60.0, 24.0,
        0.20, 2.5, 25.0, "SCG: 20% of mixture VS", "S3",
        pretreatment_profile="bita_s3_reference", enzyme_dose_basis="U/g VS",
    ),
    "S8": ScenarioSpec(
        "S8", "Moderate pretreatment + 30% SCG", "fungal_enzyme_proxy", 60.0, 24.0,
        0.30, 2.5, 25.0, "SCG: 30% of mixture VS", "S3",
        pretreatment_profile="bita_s3_reference", enzyme_dose_basis="U/g VS",
    ),
    "S9": ScenarioSpec(
        "S9", "Moderate pretreatment + 10% SCG + high OLR", "fungal_enzyme_proxy",
        60.0, 24.0, 0.10, 4.5, 20.0, "OLR: 4.5 kg VS/m3/d", "S6",
        pretreatment_profile="bita_s3_reference", enzyme_dose_basis="U/g VS",
    ),
    "C1": ScenarioSpec(
        scenario_id="C1",
        name="1% CaO chemical pretreatment (literature proxy)",
        pretreatment_kind="chemical_cao_proxy",
        enzyme_dose_u_g=0.0,
        pretreatment_time_h=0.0,
        scg_fraction_vs=0.0,
        olr_kg_vs_m3_d=2.0,
        hrt_d=20.0,
        changed_variable="pretreatment method: 1 wt% CaO",
        reference_scenario_id="S1",
        provisional=True,
        effectiveness_override={
            "carb": 0.0,
            "protein": 0.0,
            "lipid": 0.0,
            "inert": 0.0,
        },
        fpsi_override=0.0,
        fpsi_applicable=False,
        soluble_cod_fraction_override=0.6606,
    ),
}

SCENARIOS: Mapping[str, ScenarioSpec] = MappingProxyType(_SCENARIOS)

# These methods were requested in meeting notes, but the supplied datasets do
# not define their conversion, inhibition or dose-response parameters. They
# can be run through ``make_custom_scenario`` once those measurements exist.
UNPARAMETERIZED_TREATMENTS = MappingProxyType(
    {
        "chemical_catalysis": (
            "C1 is only a 1% CaO fractionation proxy; a catalyst-specific model still "
            "needs catalyst, dose, pH, time and ADM1 fractionation effects."
        ),
        "algae": "Needs algae species, dose, COD/VS composition and substrate-release effects.",
        "archaea": "Needs inoculum/guild changes and methanogen kinetic parameters.",
        "hybrid": "Needs the component treatments and interaction rule.",
    }
)


def get_scenario(scenario_id: str) -> ScenarioSpec:
    try:
        scenario = SCENARIOS[scenario_id.upper()]
    except KeyError as error:
        choices = ", ".join(SCENARIOS)
        raise KeyError(f"Unknown scenario {scenario_id!r}; choose {choices}") from error
    scenario.validate()
    return scenario


def make_custom_scenario(
    *,
    scenario_id: str,
    name: str,
    effectiveness: Mapping[str, float],
    fpsi: float,
    scg_fraction_vs: float = 0.0,
    olr_kg_vs_m3_d: float = 2.0,
    hrt_d: float = 20.0,
) -> ScenarioSpec:
    """Create a non-fungal scenario from externally validated effects."""
    scenario = ScenarioSpec(
        scenario_id=scenario_id,
        name=name,
        pretreatment_kind="custom",
        enzyme_dose_u_g=0.0,
        pretreatment_time_h=0.0,
        scg_fraction_vs=scg_fraction_vs,
        olr_kg_vs_m3_d=olr_kg_vs_m3_d,
        hrt_d=hrt_d,
        changed_variable="custom measured treatment effect",
        reference_scenario_id="S1",
        provisional=False,
        effectiveness_override=dict(effectiveness),
        fpsi_override=fpsi,
        fpsi_applicable=True,
    )
    scenario.validate()
    return scenario
