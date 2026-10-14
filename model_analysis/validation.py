"""Screening-range checks; these are not experimental model validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ScreeningRange:
    metric: str
    minimum: float
    maximum: float
    unit: str
    source: str


SCREENING_RANGES = (
    ScreeningRange(
        "methane_yield_l_per_kg_vs",
        350.0,
        650.0,
        "L CH4/kg VS",
        "Supplied Phase 1 literature dataset: mixed-food-waste BMP range",
    ),
    ScreeningRange(
        "methane_fraction",
        0.50,
        0.70,
        "fraction",
        "Supplied Phase 1 literature dataset: raw-biogas methane range",
    ),
    ScreeningRange(
        "pH",
        6.8,
        7.5,
        "pH",
        "Supplied Phase 1 literature dataset: AD operating range",
    ),
    ScreeningRange(
        "olr_kg_vs_m3_d",
        1.0,
        4.0,
        "kg VS/m3/d",
        "Supplied Phase 1 literature dataset: OLR screening range",
    ),
    ScreeningRange(
        "hrt_d",
        15.0,
        30.0,
        "d",
        "Supplied Phase 1 literature dataset: HRT screening range",
    ),
)


def screening_consistency(result: Any) -> list[dict[str, object]]:
    """Compare final model outputs/conditions with supplied screening ranges."""

    summary = result.summary()
    checks: list[dict[str, object]] = []
    for expected in SCREENING_RANGES:
        value = float(summary[expected.metric])
        check = asdict(expected)
        check.update(
            {
                "value": value,
                "within_range": expected.minimum <= value <= expected.maximum,
            }
        )
        checks.append(check)
    return checks


def all_screening_checks_pass(checks: list[dict[str, object]]) -> bool:
    return all(bool(check["within_range"]) for check in checks)
