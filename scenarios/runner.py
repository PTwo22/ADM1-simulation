"""Public scenario API connecting project inputs to the dynamic ADM1 model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from AD.adm1.influent import build_influent
from AD.adm1.model import ADM1Model, ADM1ReactorConfig
from AD.adm1.parameters import ADM1Parameters
from AD.adm1.results import ADM1SimulationResult
from data.adm1_config import ADM1_TRANSLATION, ADM1_TRANSLATION_STATUS
from data.config import (
    BMP_CONSTANTS,
    FPSI_WEIGHTS,
    PRETREATMENT_BASELINE,
    PRETREATMENT_CONFIG,
)
from model_analysis.stability import (
    StabilityConfig,
    assess_stability,
)
from model_analysis.validation import all_screening_checks_pass, screening_consistency
from pretreatment import NoPretreatment, Pretreatment
from scenarios.definitions import SCENARIOS, ScenarioSpec, get_scenario
from scenarios.inputs import SimulationInputs


class _CustomTreatment:
    def __init__(self, effectiveness, fpsi: float) -> None:
        self.A = dict(effectiveness)
        self.fpsi = float(fpsi)


@dataclass(frozen=True)
class ScenarioComparison:
    results: tuple[ADM1SimulationResult, ...]
    control_id: str
    best_scenario_id: str

    def summaries(self) -> list[dict[str, object]]:
        control = next(result for result in self.results if result.scenario_id == self.control_id)
        control_yield = control.methane_yield_l_per_kg_vs
        rows: list[dict[str, object]] = []
        for result in self.results:
            row = result.summary()
            row["improvement_pct_vs_control"] = (
                (result.methane_yield_l_per_kg_vs - control_yield)
                / control_yield
                * 100.0
                if control_yield > 0
                else 0.0
            )
            row["is_best"] = result.scenario_id == self.best_scenario_id
            rows.append(row)
        return rows

    def to_payload(self, *, include_time_series: bool = True) -> dict[str, object]:
        """Return a JSON-serializable control-versus-scenarios payload."""
        return {
            "control_id": self.control_id,
            "best_scenario_id": self.best_scenario_id,
            "summaries": self.summaries(),
            "results": [
                result.to_payload(include_time_series=include_time_series)
                for result in self.results
            ],
        }


def _build_treatment(spec: ScenarioSpec):
    if spec.pretreatment_kind == "none":
        return NoPretreatment()
    if spec.pretreatment_kind in {"custom", "chemical_cao_proxy"}:
        return _CustomTreatment(spec.effectiveness_override, spec.fpsi_override)
    doses = {name: spec.enzyme_dose_u_g for name in FPSI_WEIGHTS}
    return Pretreatment(
        temp_pre=PRETREATMENT_BASELINE["temperature_c"],
        ph_pre=PRETREATMENT_BASELINE["pH"],
        time_pre=spec.pretreatment_time_h,
        enzyme_doses=doses,
        config=PRETREATMENT_CONFIG,
        weights=FPSI_WEIGHTS,
    )


def run_scenario(
    scenario: str | ScenarioSpec,
    *,
    duration_d: float | None = None,
    output_points: int | None = None,
    parameters: ADM1Parameters | None = None,
    inputs: SimulationInputs | None = None,
    stability_config: StabilityConfig | None = None,
) -> ADM1SimulationResult:
    """Run one scenario and return UI-ready time-series data."""
    spec = get_scenario(scenario) if isinstance(scenario, str) else scenario
    spec.validate()
    settings = inputs or SimulationInputs()
    settings.validate()
    treatment = _build_treatment(spec)
    feedstock = settings.build_feedstock(spec.scg_fraction_vs)
    adm1_parameters = parameters or ADM1Parameters()
    influent = build_influent(
        feedstock,
        treatment,
        olr_kg_vs_m3_d=spec.olr_kg_vs_m3_d,
        hrt_d=spec.hrt_d,
        target_pH=settings.influent_pH,
        temperature_c=settings.temperature_c,
        bmp_constants=BMP_CONSTANTS,
        parameters=adm1_parameters,
        soluble_cod_fraction_override=spec.soluble_cod_fraction_override,
        **settings.adm1_translation,
    )
    run_duration_d = settings.duration_d if duration_d is None else duration_d
    run_output_points = (
        settings.output_points if output_points is None else output_points
    )
    reactor = ADM1ReactorConfig(
        hrt_d=spec.hrt_d,
        olr_kg_vs_m3_d=spec.olr_kg_vs_m3_d,
        liquid_volume_m3=settings.liquid_volume_m3,
        gas_volume_m3=settings.gas_volume_m3,
        temperature_c=settings.temperature_c,
        duration_d=run_duration_d,
        output_points=run_output_points,
    )
    model = ADM1Model(
        influent.state,
        influent.initial_state,
        strong_cations_kmol_m3=influent.strong_cations_kmol_m3,
        strong_anions_kmol_m3=influent.strong_anions_kmol_m3,
        hydrolysis_multipliers=influent.hydrolysis_multipliers,
        reactor=reactor,
        parameters=adm1_parameters,
    )
    parameter_status = dict(ADM1_TRANSLATION_STATUS)
    for name, value in settings.adm1_translation.items():
        if float(value) != float(ADM1_TRANSLATION[name]):
            parameter_status[name] = "user_supplied_unvalidated"
    input_snapshot = settings.as_dict()
    input_snapshot["duration_d"] = run_duration_d
    input_snapshot["output_points"] = run_output_points
    theoretical_bmp_l_per_kg_vs = (
        feedstock.calculate_theoretical_bmp(BMP_CONSTANTS) * 1000.0
    )
    result = model.simulate(
        scenario_id=spec.scenario_id,
        scenario_name=spec.name,
        fpsi=treatment.fpsi,
        scg_fraction_vs=spec.scg_fraction_vs,
        metadata={
            "changed_variable": spec.changed_variable,
            "pretreatment_kind": spec.pretreatment_kind,
            "pretreatment_time_h": spec.pretreatment_time_h,
            "enzyme_dose_u_g": spec.enzyme_dose_u_g,
            "fpsi_applicable": spec.fpsi_applicable,
            "soluble_cod_fraction_override": spec.soluble_cod_fraction_override,
            "scenario_inputs_provisional": spec.provisional,
            "provisional": spec.provisional
            or any(status != "supplied_dataset" for status in ADM1_TRANSLATION_STATUS.values()),
            "parameter_status": parameter_status,
            "simulation_inputs": input_snapshot,
            "influent_notes": influent.notes,
            "influent_total_cod_kg_m3": influent.total_cod_kg_m3,
            "influent_soluble_cod_fraction": influent.soluble_cod_fraction,
            "influent_scod_kg_cod_m3": (
                influent.total_cod_kg_m3 * influent.soluble_cod_fraction
            ),
            "feed_wet_mass_kg": feedstock.m_wet,
            "feed_total_solids_kg": feedstock.m_ts,
            "feed_volatile_solids_kg": feedstock.m_vs,
            "theoretical_bmp_l_per_kg_vs": theoretical_bmp_l_per_kg_vs,
            "methane_lhv_mj_nm3": 35.8,
        },
    )
    if stability_config is not None:
        assessment = assess_stability(
            pH=result.pH,
            vfa_kg_cod_m3=result.vfa_kg_cod_m3,
            free_ammonia_kg_n_m3=result.free_ammonia_kg_n_m3,
            config=stability_config,
            temperature_c=settings.temperature_c,
        )
        result.stability_risk_index = assessment.combined_risk_index
        result.stability_status = assessment.status
        result.stability_limiting_indicator = assessment.limiting_indicator
        result.stability_basis = assessment.source
        result.metadata["stability_profile"] = stability_config.as_dict()
    else:
        result.metadata["stability_profile"] = None
    checks = screening_consistency(result)
    result.metadata["screening_consistency"] = {
        "all_within_ranges": all_screening_checks_pass(checks),
        "checks": checks,
        "interpretation": (
            "Literature-range consistency check only; not experimental validation."
        ),
    }
    return result


def run_scenario_set(
    scenario_ids: Iterable[str] = ("S1", "S3", "S6"),
    *,
    duration_d: float | None = None,
    output_points: int | None = None,
    parameters: ADM1Parameters | None = None,
    inputs: SimulationInputs | None = None,
    stability_config: StabilityConfig | None = None,
) -> ScenarioComparison:
    """Run scenarios and identify the highest predicted methane yield."""
    ids = tuple(scenario_ids)
    if "S1" not in {item.upper() for item in ids}:
        ids = ("S1",) + ids
    results = tuple(
        run_scenario(
            scenario_id,
            duration_d=duration_d,
            output_points=output_points,
            parameters=parameters,
            inputs=inputs,
            stability_config=stability_config,
        )
        for scenario_id in ids
    )
    maximum_yield = max(result.methane_yield_l_per_kg_vs for result in results)
    # Prefer the first/lower-severity case when predictions are practically
    best = next(
        result
        for result in results
        if maximum_yield - result.methane_yield_l_per_kg_vs <= 0.1
    )
    return ScenarioComparison(results=results, control_id="S1", best_scenario_id=best.scenario_id)


def list_scenarios() -> list[dict[str, object]]:
    """Return scenario inputs without running the ODE model."""
    return [
        {
            "scenario_id": spec.scenario_id,
            "name": spec.name,
            "pretreatment_kind": spec.pretreatment_kind,
            "enzyme_dose_u_g": spec.enzyme_dose_u_g,
            "pretreatment_time_h": spec.pretreatment_time_h,
            "scg_fraction_vs": spec.scg_fraction_vs,
            "olr_kg_vs_m3_d": spec.olr_kg_vs_m3_d,
            "hrt_d": spec.hrt_d,
            "changed_variable": spec.changed_variable,
            "reference_scenario_id": spec.reference_scenario_id,
            "provisional": spec.provisional,
            "fpsi_applicable": spec.fpsi_applicable,
        }
        for spec in SCENARIOS.values()
    ]
