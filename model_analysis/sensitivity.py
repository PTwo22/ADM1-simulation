"""One-factor-at-a-time (OAT) analysis requested in the meeting notes."""

from __future__ import annotations

from dataclasses import dataclass, replace
import math
from statistics import mean, pstdev
from typing import Iterable

from model_analysis.stability import StabilityConfig
from scenarios.definitions import ScenarioSpec, get_scenario
from scenarios.inputs import SimulationInputs
from scenarios.runner import run_scenario


@dataclass(frozen=True)
class SensitivityFactor:
    key: str
    label: str
    unit: str
    values: tuple[float, ...]
    source: str


OAT_FACTORS = {
    "enzyme_dose": SensitivityFactor(
        "enzyme_dose_u_g",
        "Fungal-enzyme dose",
        "U/g",
        (5.0, 10.0, 20.0),
        "Project S2-S4 definitions; provisional until calibrated",
    ),
    "pretreatment_time": SensitivityFactor(
        "pretreatment_time_h",
        "Pretreatment duration",
        "h",
        (12.0, 24.0, 72.0),
        "Supplied literature screening range and 24 h meeting baseline",
    ),
    "scg_fraction": SensitivityFactor(
        "scg_fraction_vs",
        "SCG fraction of mixture VS",
        "fraction",
        (0.0, 0.10, 0.20, 0.30),
        "Supplied Phase 1 SCG screening range",
    ),
    "olr": SensitivityFactor(
        "olr_kg_vs_m3_d",
        "Organic loading rate",
        "kg VS/m3/d",
        (1.0, 2.0, 3.0, 4.0),
        "Supplied Phase 1 OLR range",
    ),
    "hrt": SensitivityFactor(
        "hrt_d",
        "Hydraulic retention time",
        "d",
        (15.0, 20.0, 30.0),
        "Supplied Phase 1 HRT range",
    ),
}


@dataclass(frozen=True)
class SensitivityReport:
    factor: SensitivityFactor
    base_scenario_id: str
    rows: tuple[dict[str, object], ...]
    methane_yield_mean: float
    methane_yield_std: float
    methane_yield_min: float
    methane_yield_max: float

    def to_payload(self) -> dict[str, object]:
        return {
            "method": "one_factor_at_a_time",
            "factor": {
                "key": self.factor.key,
                "label": self.factor.label,
                "unit": self.factor.unit,
                "values": list(self.factor.values),
                "source": self.factor.source,
            },
            "base_scenario_id": self.base_scenario_id,
            "rows": list(self.rows),
            "statistics": {
                "methane_yield_mean_l_per_kg_vs": self.methane_yield_mean,
                "methane_yield_population_std_l_per_kg_vs": self.methane_yield_std,
                "methane_yield_min_l_per_kg_vs": self.methane_yield_min,
                "methane_yield_max_l_per_kg_vs": self.methane_yield_max,
            },
            "interpretation": (
                "Screening sensitivity only; values are not probability distributions."
            ),
        }


def run_oat_sensitivity(
    factor_name: str,
    *,
    base_scenario: str | ScenarioSpec = "S3",
    values: Iterable[float] | None = None,
    duration_d: float | None = None,
    output_points: int | None = None,
    inputs: SimulationInputs | None = None,
    stability_config: StabilityConfig | None = None,
) -> SensitivityReport:
    """Change one scenario input at a time and summarize output variation."""

    try:
        factor = OAT_FACTORS[factor_name]
    except KeyError as error:
        choices = ", ".join(OAT_FACTORS)
        raise KeyError(f"Unknown sensitivity factor {factor_name!r}; choose {choices}") from error
    spec = get_scenario(base_scenario) if isinstance(base_scenario, str) else base_scenario
    if spec.pretreatment_kind != "fungal_enzyme_proxy" and factor_name in {
        "enzyme_dose",
        "pretreatment_time",
    }:
        raise ValueError("Dose/time sensitivity requires a fungal-enzyme scenario")

    selected_values = factor.values if values is None else tuple(float(v) for v in values)
    if not selected_values or any(not math.isfinite(v) for v in selected_values):
        raise ValueError("Sensitivity values must be a non-empty finite sequence")

    rows: list[dict[str, object]] = []
    yields: list[float] = []
    for index, value in enumerate(selected_values, start=1):
        varied = replace(
            spec,
            scenario_id=f"OAT-{factor_name}-{index}",
            name=f"{spec.name}; {factor.label}={value:g} {factor.unit}",
            changed_variable=f"{factor.label}: {value:g} {factor.unit}",
            reference_scenario_id=spec.scenario_id,
            **{factor.key: value},
        )
        varied.validate()
        result = run_scenario(
            varied,
            duration_d=duration_d,
            output_points=output_points,
            inputs=inputs,
            stability_config=stability_config,
        )
        summary = result.summary()
        methane_yield = float(summary["methane_yield_l_per_kg_vs"])
        yields.append(methane_yield)
        rows.append(
            {
                "value": value,
                "unit": factor.unit,
                "methane_yield_l_per_kg_vs": methane_yield,
                "methane_fraction": summary["methane_fraction"],
                "pH": summary["pH"],
                "vfa_kg_cod_m3": summary["vfa_kg_cod_m3"],
                "free_ammonia_kg_n_m3": summary["free_ammonia_kg_n_m3"],
                "stability_status": summary["stability_status"],
                "stability_risk_index": summary["stability_risk_index"],
            }
        )

    return SensitivityReport(
        factor=factor,
        base_scenario_id=spec.scenario_id,
        rows=tuple(rows),
        methane_yield_mean=mean(yields),
        methane_yield_std=pstdev(yields),
        methane_yield_min=min(yields),
        methane_yield_max=max(yields),
    )
