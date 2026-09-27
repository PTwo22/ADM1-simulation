"""Compare dynamic ADM1 predictions with experimental time-series data.

This module reports fit statistics and can optimise selected food-to-ADM1
translation parameters.  It requires observations supplied by the project and
does not contain fabricated calibration data.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import csv
import math
from pathlib import Path
from typing import Iterable, Mapping

import numpy as np
from scipy.optimize import least_squares

from AD.adm1.results import ADM1SimulationResult
from scenarios.inputs import SimulationInputs


SUPPORTED_VARIABLES = {
    "pH",
    "vfa_kg_cod_m3",
    "tan_kg_n_m3",
    "free_ammonia_kg_n_m3",
    "methane_rate_nm3_m3_d",
    "carbon_dioxide_rate_nm3_m3_d",
    "biogas_rate_nm3_m3_d",
    "methane_fraction",
    "cumulative_methane_nm3_m3",
}


@dataclass(frozen=True)
class CalibrationObservation:
    time_d: float
    variable: str
    value: float
    scale: float = 1.0

    def validate(self) -> None:
        if self.variable not in SUPPORTED_VARIABLES:
            raise ValueError(
                f"Unsupported calibration variable {self.variable!r}; "
                f"choose one of {sorted(SUPPORTED_VARIABLES)}"
            )
        if not all(
            math.isfinite(float(item))
            for item in (self.time_d, self.value, self.scale)
        ):
            raise ValueError("Calibration observations must be finite")
        if self.time_d < 0 or self.scale <= 0:
            raise ValueError("Observation time must be non-negative and scale positive")


@dataclass(frozen=True)
class CalibrationReport:
    observation_count: int
    rmse_scaled: float
    mae_scaled: float
    bias_scaled: float
    observed: tuple[float, ...]
    predicted: tuple[float, ...]
    residuals_scaled: tuple[float, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "observation_count": self.observation_count,
            "rmse_scaled": self.rmse_scaled,
            "mae_scaled": self.mae_scaled,
            "bias_scaled": self.bias_scaled,
            "observed": list(self.observed),
            "predicted": list(self.predicted),
            "residuals_scaled": list(self.residuals_scaled),
        }


@dataclass(frozen=True)
class CalibrationFit:
    parameter_values: Mapping[str, float]
    initial_report: CalibrationReport
    final_report: CalibrationReport
    success: bool
    message: str
    function_evaluations: int


def load_observations_csv(path: str | Path) -> tuple[CalibrationObservation, ...]:
    """Load columns ``time_d,variable,value,scale`` from a CSV file."""
    observations: list[CalibrationObservation] = []
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"time_d", "variable", "value"}
        if reader.fieldnames is None or not required <= set(reader.fieldnames):
            raise ValueError("Calibration CSV requires time_d, variable and value columns")
        for line_number, row in enumerate(reader, start=2):
            try:
                observation = CalibrationObservation(
                    time_d=float(row["time_d"]),
                    variable=row["variable"].strip(),
                    value=float(row["value"]),
                    scale=float(row.get("scale") or 1.0),
                )
                observation.validate()
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"Invalid calibration observation on CSV line {line_number}: {error}"
                ) from error
            observations.append(observation)
    if not observations:
        raise ValueError("Calibration CSV contains no observations")
    return tuple(observations)


def _series(result: ADM1SimulationResult, variable: str) -> np.ndarray:
    if variable not in SUPPORTED_VARIABLES:
        raise ValueError(f"Unsupported calibration variable: {variable}")
    return np.asarray(getattr(result, variable), dtype=float)


def calibration_residuals(
    result: ADM1SimulationResult,
    observations: Iterable[CalibrationObservation],
) -> np.ndarray:
    """Return scaled prediction-minus-observation residuals."""
    rows = tuple(observations)
    if not rows:
        raise ValueError("At least one calibration observation is required")
    residuals: list[float] = []
    for observation in rows:
        observation.validate()
        if observation.time_d > float(result.time_d[-1]):
            raise ValueError(
                f"Observation at {observation.time_d} d exceeds the simulation duration"
            )
        prediction = float(
            np.interp(
                observation.time_d,
                result.time_d,
                _series(result, observation.variable),
            )
        )
        residuals.append((prediction - observation.value) / observation.scale)
    return np.asarray(residuals, dtype=float)


def evaluate_calibration(
    result: ADM1SimulationResult,
    observations: Iterable[CalibrationObservation],
) -> CalibrationReport:
    rows = tuple(observations)
    residuals = calibration_residuals(result, rows)
    predicted = tuple(
        float(
            np.interp(
                row.time_d,
                result.time_d,
                _series(result, row.variable),
            )
        )
        for row in rows
    )
    return CalibrationReport(
        observation_count=len(rows),
        rmse_scaled=float(np.sqrt(np.mean(residuals**2))),
        mae_scaled=float(np.mean(np.abs(residuals))),
        bias_scaled=float(np.mean(residuals)),
        observed=tuple(row.value for row in rows),
        predicted=predicted,
        residuals_scaled=tuple(float(value) for value in residuals),
    )


def calibrate_translation_parameters(
    *,
    scenario_id: str,
    observations: Iterable[CalibrationObservation],
    parameter_bounds: Mapping[str, tuple[float, float]],
    inputs: SimulationInputs | None = None,
    max_function_evaluations: int = 30,
) -> CalibrationFit:
    """Fit selected ADM1 translation parameters to supplied observations."""
    # Imported here to avoid a circular import with scenarios.runner.
    from scenarios.runner import run_scenario

    rows = tuple(observations)
    if not rows:
        raise ValueError("At least one calibration observation is required")
    settings = inputs or SimulationInputs()
    settings.validate()
    allowed = set(settings.adm1_translation)
    names = tuple(parameter_bounds)
    if not names or not set(names) <= allowed:
        raise ValueError(
            f"Choose one or more ADM1 translation parameters from {sorted(allowed)}"
        )
    lower = np.asarray([parameter_bounds[name][0] for name in names], dtype=float)
    upper = np.asarray([parameter_bounds[name][1] for name in names], dtype=float)
    initial = np.asarray([settings.adm1_translation[name] for name in names], dtype=float)
    if np.any(~np.isfinite(lower)) or np.any(~np.isfinite(upper)):
        raise ValueError("Calibration parameter bounds must be finite")
    if np.any(lower < 0) or np.any(upper <= lower):
        raise ValueError("Calibration bounds must be non-negative and increasing")
    if np.any(initial < lower) or np.any(initial > upper):
        raise ValueError("Initial parameter values must fall inside their bounds")
    if max_function_evaluations < 1:
        raise ValueError("max_function_evaluations must be positive")

    required_duration = max(row.time_d for row in rows)
    duration = max(settings.duration_d, required_duration)
    points = max(settings.output_points, int(math.ceil(duration)) + 1)

    def simulate(values: np.ndarray) -> ADM1SimulationResult:
        translation = dict(settings.adm1_translation)
        translation.update(
            {name: float(value) for name, value in zip(names, values, strict=True)}
        )
        configured = replace(
            settings,
            adm1_translation=translation,
            duration_d=duration,
            output_points=points,
        )
        return run_scenario(scenario_id, inputs=configured)

    initial_result = simulate(initial)
    initial_report = evaluate_calibration(initial_result, rows)
    fit = least_squares(
        lambda values: calibration_residuals(simulate(values), rows),
        initial,
        bounds=(lower, upper),
        max_nfev=max_function_evaluations,
    )
    final_result = simulate(fit.x)
    final_report = evaluate_calibration(final_result, rows)
    return CalibrationFit(
        parameter_values={
            name: float(value) for name, value in zip(names, fit.x, strict=True)
        },
        initial_report=initial_report,
        final_report=final_report,
        success=bool(fit.success),
        message=str(fit.message),
        function_evaluations=int(fit.nfev),
    )

