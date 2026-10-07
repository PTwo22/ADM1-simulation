"""Transparent stability screening for food-waste ADM1 simulations.

The project formula list defines dimensionless VFA, pH and free-ammonia
risk terms. This module keeps that equation, adds explicit literature-based
screening bands, and records every assumption used. The result is a
screening indicator, not a validated failure-probability model.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class StabilityConfig:
    """Limits, weights and provenance for a stability screening profile."""

    vfa_critical_kg_cod_m3: float
    pH_optimal: float
    free_ammonia_critical_kg_n_m3: float
    weight_vfa: float
    weight_pH: float
    weight_free_ammonia: float
    source: str
    profile_id: str = "custom"
    pH_stable_min: float | None = None
    pH_stable_max: float | None = None
    pH_failure_min: float | None = None
    temperature_stable_min_c: float | None = None
    temperature_stable_max_c: float | None = None
    vfa_high_risk_kg_cod_m3: float | None = None
    free_ammonia_high_risk_kg_n_m3: float | None = None
    citations: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def validate(self) -> None:
        required_values = (
            self.vfa_critical_kg_cod_m3,
            self.pH_optimal,
            self.free_ammonia_critical_kg_n_m3,
            self.weight_vfa,
            self.weight_pH,
            self.weight_free_ammonia,
        )
        if not all(math.isfinite(float(value)) for value in required_values):
            raise ValueError("Stability limits and weights must be finite")
        if (
            self.vfa_critical_kg_cod_m3 <= 0
            or self.pH_optimal <= 0
            or self.free_ammonia_critical_kg_n_m3 <= 0
        ):
            raise ValueError("Stability critical values must be positive")
        weights = (self.weight_vfa, self.weight_pH, self.weight_free_ammonia)
        if any(weight < 0 for weight in weights) or sum(weights) <= 0:
            raise ValueError("Stability weights must be non-negative and not all zero")
        if not self.source.strip() or not self.profile_id.strip():
            raise ValueError("Stability profile ID and source cannot be empty")

        optional_values = (
            self.pH_stable_min,
            self.pH_stable_max,
            self.pH_failure_min,
            self.temperature_stable_min_c,
            self.temperature_stable_max_c,
            self.vfa_high_risk_kg_cod_m3,
            self.free_ammonia_high_risk_kg_n_m3,
        )
        if any(
            value is not None
            and (not math.isfinite(float(value)) or float(value) <= 0)
            for value in optional_values
        ):
            raise ValueError("Optional stability thresholds must be positive and finite")
        if (self.pH_stable_min is None) != (self.pH_stable_max is None):
            raise ValueError("Supply both ends of the stable pH range or neither")
        if (
            self.pH_stable_min is not None
            and self.pH_stable_max is not None
            and self.pH_stable_min >= self.pH_stable_max
        ):
            raise ValueError("Stable pH minimum must be below its maximum")
        if (self.temperature_stable_min_c is None) != (
            self.temperature_stable_max_c is None
        ):
            raise ValueError("Supply both ends of the stable temperature range or neither")
        if (
            self.temperature_stable_min_c is not None
            and self.temperature_stable_max_c is not None
            and self.temperature_stable_min_c >= self.temperature_stable_max_c
        ):
            raise ValueError("Stable temperature minimum must be below its maximum")
        if (
            self.vfa_high_risk_kg_cod_m3 is not None
            and self.vfa_high_risk_kg_cod_m3 < self.vfa_critical_kg_cod_m3
        ):
            raise ValueError("High-risk VFA threshold cannot be below its warning threshold")
        if (
            self.free_ammonia_high_risk_kg_n_m3 is not None
            and self.free_ammonia_high_risk_kg_n_m3
            < self.free_ammonia_critical_kg_n_m3
        ):
            raise ValueError("High-risk FAN threshold cannot be below its warning threshold")

    def as_dict(self) -> dict[str, object]:
        self.validate()
        return asdict(self)


@dataclass(frozen=True)
class StabilityAssessment:
    """Risk terms and status over time; lower risk-index values are better."""

    vfa_risk: np.ndarray
    pH_risk: np.ndarray
    free_ammonia_risk: np.ndarray
    combined_risk_index: np.ndarray
    status: np.ndarray
    limiting_indicator: np.ndarray
    source: str
    profile_id: str


def food_waste_literature_profile() -> StabilityConfig:
    """Return the documented default food-waste screening profile.

    Equal weights are a project convention because the supplied formula list
    does not prescribe them. VFA totals are inferred by COD-converting the
    reported acetate, propionate and butyrate thresholds.
    """

    return StabilityConfig(
        profile_id="food_waste_screening_v1",
        vfa_critical_kg_cod_m3=1.31,
        pH_optimal=7.0,
        free_ammonia_critical_kg_n_m3=0.045,
        weight_vfa=1.0,
        weight_pH=1.0,
        weight_free_ammonia=1.0,
        pH_stable_min=6.8,
        pH_stable_max=7.2,
        pH_failure_min=6.5,
        temperature_stable_min_c=35.0,
        temperature_stable_max_c=37.0,
        vfa_high_risk_kg_cod_m3=4.67,
        free_ammonia_high_risk_kg_n_m3=0.100,
        source=(
            "Project pH guidance plus food-waste AD literature; equal risk "
            "weights are an explicit screening convention"
        ),
        citations=(
            "Shi et al. (2017), DOI: 10.1016/j.jes.2016.07.006",
            "Bioresource Technology Reports (2026), DOI: 10.1016/j.biteb.2026.102896",
            "Li et al. (2016), PMCID: PMC4845381",
            "Project guidance: stable pH 6.8-7.2; failure warning below 6.5",
        ),
        notes=(
            "VFA thresholds aggregate reported acetate, propionate and butyrate limits after COD conversion.",
            "FAN thresholds vary with acclimation, feed and temperature; 0.045 kg N/m3 is conservative.",
            "Status is for screening and does not replace target-reactor calibration.",
        ),
    )


def load_stability_config(path: str | Path) -> StabilityConfig:
    """Load an alternative stability profile from a JSON file."""

    with Path(path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Stability configuration must be a JSON object")
    payload = dict(payload)
    for name in ("citations", "notes"):
        if name in payload:
            payload[name] = tuple(payload[name])
    try:
        config = StabilityConfig(**payload)
    except TypeError as error:
        raise ValueError(f"Invalid stability configuration fields: {error}") from error
    config.validate()
    return config


def _status_for_point(
    pH: float,
    vfa: float,
    fan: float,
    config: StabilityConfig,
    temperature_c: float | None,
) -> tuple[str, str]:
    high_risk_reasons: list[str] = []
    watch_reasons: list[str] = []

    if config.pH_failure_min is not None and pH < config.pH_failure_min:
        high_risk_reasons.append("pH")
    elif (
        config.pH_stable_min is not None
        and config.pH_stable_max is not None
        and not config.pH_stable_min <= pH <= config.pH_stable_max
    ):
        watch_reasons.append("pH")

    if (
        config.vfa_high_risk_kg_cod_m3 is not None
        and vfa >= config.vfa_high_risk_kg_cod_m3
    ):
        high_risk_reasons.append("VFA")
    elif vfa >= config.vfa_critical_kg_cod_m3:
        watch_reasons.append("VFA")

    if (
        config.free_ammonia_high_risk_kg_n_m3 is not None
        and fan >= config.free_ammonia_high_risk_kg_n_m3
    ):
        high_risk_reasons.append("FAN")
    elif fan >= config.free_ammonia_critical_kg_n_m3:
        watch_reasons.append("FAN")

    if (
        temperature_c is not None
        and config.temperature_stable_min_c is not None
        and config.temperature_stable_max_c is not None
        and not config.temperature_stable_min_c
        <= temperature_c
        <= config.temperature_stable_max_c
    ):
        watch_reasons.append("temperature")

    if high_risk_reasons:
        return "High risk", ", ".join(high_risk_reasons)
    if watch_reasons:
        return "Watch", ", ".join(watch_reasons)
    return "Stable", "none"


def assess_stability(
    *,
    pH: np.ndarray,
    vfa_kg_cod_m3: np.ndarray,
    free_ammonia_kg_n_m3: np.ndarray,
    config: StabilityConfig,
    temperature_c: float | np.ndarray | None = None,
) -> StabilityAssessment:
    """Calculate the formula-list risk index and traceable status bands."""

    config.validate()
    pH_values = np.asarray(pH, dtype=float)
    vfa_values = np.asarray(vfa_kg_cod_m3, dtype=float)
    fan_values = np.asarray(free_ammonia_kg_n_m3, dtype=float)
    if pH_values.shape != vfa_values.shape or pH_values.shape != fan_values.shape:
        raise ValueError("Stability indicator arrays must have matching shapes")
    if not (
        np.all(np.isfinite(pH_values))
        and np.all(np.isfinite(vfa_values))
        and np.all(np.isfinite(fan_values))
    ):
        raise ValueError("Stability indicators must be finite")
    if np.any(vfa_values < 0) or np.any(fan_values < 0):
        raise ValueError("VFA and free-ammonia values cannot be negative")
    if temperature_c is None:
        temperature_values = np.full(pH_values.shape, np.nan)
    else:
        temperature_values = np.broadcast_to(
            np.asarray(temperature_c, dtype=float), pH_values.shape
        )
        if not np.all(np.isfinite(temperature_values)):
            raise ValueError("Temperature values must be finite")

    vfa_risk = vfa_values / config.vfa_critical_kg_cod_m3
    pH_risk = np.abs(config.pH_optimal - pH_values) / config.pH_optimal
    free_ammonia_risk = fan_values / config.free_ammonia_critical_kg_n_m3
    total_weight = config.weight_vfa + config.weight_pH + config.weight_free_ammonia
    combined = (
        config.weight_vfa * vfa_risk
        + config.weight_pH * pH_risk
        + config.weight_free_ammonia * free_ammonia_risk
    ) / total_weight

    status_and_reason = [
        _status_for_point(
            pH_value,
            vfa_value,
            fan_value,
            config,
            None if np.isnan(temperature_value) else float(temperature_value),
        )
        for pH_value, vfa_value, fan_value, temperature_value in zip(
            pH_values.flat,
            vfa_values.flat,
            fan_values.flat,
            temperature_values.flat,
        )
    ]
    status = np.asarray(
        [item[0] for item in status_and_reason], dtype="U16"
    ).reshape(pH_values.shape)
    limiting = np.asarray(
        [item[1] for item in status_and_reason], dtype="U32"
    ).reshape(pH_values.shape)
    return StabilityAssessment(
        vfa_risk=vfa_risk,
        pH_risk=pH_risk,
        free_ammonia_risk=free_ammonia_risk,
        combined_risk_index=combined,
        status=status,
        limiting_indicator=limiting,
        source=config.source,
        profile_id=config.profile_id,
    )


# Practical-yield post-processing used by the reference scenario graph.


@dataclass(frozen=True)
class PracticalYieldStabilityConfig:
    """Constants for converting raw methane yield into practical yield."""

    control_vfa_mg_l: float = 1800.0
    control_fan_mg_l: float = 180.0
    control_tan_mg_l: float = 1200.0

    critical_vfa_mg_l: float = 6000.0
    critical_fan_mg_l: float = 600.0
    critical_tan_mg_l: float = 3500.0
    critical_olr_kg_vs_m3_d: float = 5.0

    baseline_olr_kg_vs_m3_d: float = 2.5
    initial_pH: float = 7.2
    optimal_pH: float = 7.1
    minimum_pH: float = 6.2
    maximum_pH: float = 7.8

    fpsi_to_vfa: float = 0.55
    excess_olr_to_vfa: float = 0.25
    protein_to_fan: float = 0.70
    protein_to_tan: float = 0.20
    vfa_to_pH_drop: float = 0.45

    weight_vfa: float = 0.35
    weight_ammonia: float = 0.25
    weight_pH: float = 0.20
    weight_olr: float = 0.20


DEFAULT_PRACTICAL_YIELD_STABILITY = PracticalYieldStabilityConfig()


@dataclass(frozen=True)
class PracticalYieldStability:
    """Stability score, individual risks, and estimated concentrations."""

    score: float
    total_risk: float
    vfa_risk: float
    ammonia_risk: float
    pH_risk: float
    olr_risk: float
    vfa_mg_l: float
    fan_mg_l: float
    tan_mg_l: float
    estimated_pH: float


def _clip(value: float, minimum: float, maximum: float) -> float:
    return min(maximum, max(minimum, value))


def calculate_practical_yield_stability(
    *,
    fpsi: float,
    protein_effectiveness: float,
    olr_kg_vs_m3_d: float,
    config: PracticalYieldStabilityConfig = DEFAULT_PRACTICAL_YIELD_STABILITY,
) -> PracticalYieldStability:
    """Calculate the post-processing stability score for practical yield."""

    excess_olr_fraction = (
        max(olr_kg_vs_m3_d - config.baseline_olr_kg_vs_m3_d, 0.0)
        / config.baseline_olr_kg_vs_m3_d
    )
    vfa_mg_l = config.control_vfa_mg_l * (
        1.0
        + config.fpsi_to_vfa * fpsi
        + config.excess_olr_to_vfa * excess_olr_fraction
    )
    fan_mg_l = config.control_fan_mg_l * (
        1.0 + config.protein_to_fan * protein_effectiveness
    )
    tan_mg_l = config.control_tan_mg_l * (
        1.0 + config.protein_to_tan * protein_effectiveness
    )
    estimated_pH = _clip(
        config.initial_pH
        - config.vfa_to_pH_drop * (vfa_mg_l / config.critical_vfa_mg_l),
        config.minimum_pH,
        config.maximum_pH,
    )

    vfa_risk = vfa_mg_l / config.critical_vfa_mg_l
    ammonia_risk = max(
        fan_mg_l / config.critical_fan_mg_l,
        tan_mg_l / config.critical_tan_mg_l,
    )
    pH_risk = abs(estimated_pH - config.optimal_pH) / config.optimal_pH
    olr_risk = olr_kg_vs_m3_d / config.critical_olr_kg_vs_m3_d
    total_risk = (
        config.weight_vfa * vfa_risk
        + config.weight_ammonia * ammonia_risk
        + config.weight_pH * pH_risk
        + config.weight_olr * olr_risk
    )

    return PracticalYieldStability(
        score=_clip(1.0 - total_risk, 0.0, 1.0),
        total_risk=_clip(total_risk, 0.0, 1.5),
        vfa_risk=vfa_risk,
        ammonia_risk=ammonia_risk,
        pH_risk=pH_risk,
        olr_risk=olr_risk,
        vfa_mg_l=vfa_mg_l,
        fan_mg_l=fan_mg_l,
        tan_mg_l=tan_mg_l,
        estimated_pH=estimated_pH,
    )
