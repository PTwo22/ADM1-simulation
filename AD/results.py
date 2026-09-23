"""Structured outputs from the digester screening model."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict


@dataclass(frozen=True)
class SimulationResult:
    scenario: str
    fpsi: float
    theoretical_bmp_nm3_per_kg_vs: float
    methane_yield_nm3_per_kg_vs: float
    methane_rate_nm3_per_m3_d: float
    methane_volume_nm3_feed_basis: float
    raw_biogas_rate_nm3_per_m3_d: float
    energy_mj_per_m3_d: float
    electricity_kwh_per_m3_d: float
    improvement_pct_vs_control: float
    hydrolysis_rates_per_d: Dict[str, float]
    biodegradability: Dict[str, float]
    conversion: Dict[str, float]
    mass_balance_error_kg_vs: float

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)
