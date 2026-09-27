"""Structured, UI-independent outputs from a dynamic ADM1 simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from AD.adm1.states import SOLUBLE_COD_STATES, STATE_INDEX, STATE_NAMES


@dataclass
class ADM1SimulationResult:
    scenario_id: str
    scenario_name: str
    time_d: np.ndarray
    states: np.ndarray
    pH: np.ndarray
    vfa_kg_cod_m3: np.ndarray
    tan_kg_n_m3: np.ndarray
    free_ammonia_kg_n_m3: np.ndarray
    bicarbonate_alkalinity_kmol_charge_m3: np.ndarray
    hydrogen_rate_nm3_m3_d: np.ndarray
    methane_rate_nm3_m3_d: np.ndarray
    carbon_dioxide_rate_nm3_m3_d: np.ndarray
    biogas_rate_nm3_m3_d: np.ndarray
    hydrogen_fraction: np.ndarray
    methane_fraction: np.ndarray
    carbon_dioxide_fraction: np.ndarray
    cumulative_methane_nm3_m3: np.ndarray
    cod_balance_residual_kg: np.ndarray
    carbon_balance_residual_kmol: np.ndarray
    nitrogen_balance_residual_kmol: np.ndarray
    olr_kg_vs_m3_d: float
    hrt_d: float
    fpsi: float
    scg_fraction_vs: float
    gross_energy_kwh_for_2_25kg_vs: float
    methane_yield_l_per_kg_vs: float
    metadata: dict[str, Any] = field(default_factory=dict)
    stability_risk_index: np.ndarray | None = None
    stability_status: np.ndarray | None = None
    stability_limiting_indicator: np.ndarray | None = None
    stability_basis: str | None = None

    def state(self, name: str) -> np.ndarray:
        """Return the complete time series for one named ADM1 state."""
        if name not in STATE_INDEX:
            raise KeyError(f"Unknown ADM1 state: {name}")
        return self.states[STATE_INDEX[name], :]

    @property
    def final_pH(self) -> float:
        return float(self.pH[-1])

    @property
    def final_vfa_kg_cod_m3(self) -> float:
        return float(self.vfa_kg_cod_m3[-1])

    @property
    def final_tan_kg_n_m3(self) -> float:
        return float(self.tan_kg_n_m3[-1])

    @property
    def final_methane_fraction(self) -> float:
        return float(self.methane_fraction[-1])

    @property
    def final_methane_rate_nm3_m3_d(self) -> float:
        return float(self.methane_rate_nm3_m3_d[-1])

    @property
    def final_hydrogen_rate_nm3_m3_d(self) -> float:
        return float(self.hydrogen_rate_nm3_m3_d[-1])

    @property
    def final_carbon_dioxide_rate_nm3_m3_d(self) -> float:
        return float(self.carbon_dioxide_rate_nm3_m3_d[-1])

    @property
    def final_biogas_rate_nm3_m3_d(self) -> float:
        return float(self.biogas_rate_nm3_m3_d[-1])

    @property
    def model_soluble_cod_kg_m3(self) -> np.ndarray:
        """Return the sum of soluble organic ADM1 COD states over time."""
        indices = [STATE_INDEX[name] for name in SOLUBLE_COD_STATES]
        return np.sum(self.states[indices, :], axis=0)

    def summary(self) -> dict[str, Any]:
        """Return JSON-friendly values for a UI, table or CSV exporter."""
        methane_yield_nm3_kg_vs = self.methane_yield_l_per_kg_vs / 1000.0
        feed_vs_kg = float(self.metadata.get("feed_volatile_solids_kg", 0.0))
        lhv_mj_nm3 = float(self.metadata.get("methane_lhv_mj_nm3", 35.8))
        methane_for_feed = methane_yield_nm3_kg_vs * feed_vs_kg
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "fpsi": self.fpsi,
            "fpsi_applicable": bool(self.metadata.get("fpsi_applicable", True)),
            "scg_fraction_vs": self.scg_fraction_vs,
            "olr_kg_vs_m3_d": self.olr_kg_vs_m3_d,
            "hrt_d": self.hrt_d,
            "methane_yield_l_per_kg_vs": self.methane_yield_l_per_kg_vs,
            "hydrogen_rate_nm3_m3_d": self.final_hydrogen_rate_nm3_m3_d,
            "methane_rate_nm3_m3_d": self.final_methane_rate_nm3_m3_d,
            "carbon_dioxide_rate_nm3_m3_d": self.final_carbon_dioxide_rate_nm3_m3_d,
            "biogas_rate_nm3_m3_d": self.final_biogas_rate_nm3_m3_d,
            "hydrogen_fraction": float(self.hydrogen_fraction[-1]),
            "methane_fraction": self.final_methane_fraction,
            "carbon_dioxide_fraction": float(self.carbon_dioxide_fraction[-1]),
            "cumulative_methane_nm3_m3": float(self.cumulative_methane_nm3_m3[-1]),
            "methane_volume_nm3_for_2_25kg_vs": methane_yield_nm3_kg_vs * 2.25,
            "methane_volume_nm3_for_feed_batch": methane_for_feed,
            "gross_energy_kwh_for_2_25kg_vs": self.gross_energy_kwh_for_2_25kg_vs,
            "gross_energy_kwh_for_feed_batch": methane_for_feed * lhv_mj_nm3 / 3.6,
            "pH": self.final_pH,
            "vfa_kg_cod_m3": self.final_vfa_kg_cod_m3,
            "tan_kg_n_m3": self.final_tan_kg_n_m3,
            "free_ammonia_kg_n_m3": float(self.free_ammonia_kg_n_m3[-1]),
            "stability_risk_index": (
                float(self.stability_risk_index[-1])
                if self.stability_risk_index is not None
                else None
            ),
            "stability_status": (
                str(self.stability_status[-1])
                if self.stability_status is not None
                else "Not assessed"
            ),
            "stability_limiting_indicator": (
                str(self.stability_limiting_indicator[-1])
                if self.stability_limiting_indicator is not None
                else None
            ),
            "stability_basis": self.stability_basis,
            "bicarbonate_alkalinity_kmol_charge_m3": float(
                self.bicarbonate_alkalinity_kmol_charge_m3[-1]
            ),
            "model_soluble_cod_kg_m3": float(self.model_soluble_cod_kg_m3[-1]),
            "feed_wet_mass_kg": float(self.metadata.get("feed_wet_mass_kg", 0.0)),
            "feed_total_solids_kg": float(
                self.metadata.get("feed_total_solids_kg", 0.0)
            ),
            "feed_volatile_solids_kg": feed_vs_kg,
            "theoretical_bmp_l_per_kg_vs": float(
                self.metadata.get("theoretical_bmp_l_per_kg_vs", 0.0)
            ),
            "cod_balance_residual_kg": float(self.cod_balance_residual_kg[-1]),
            "carbon_balance_residual_kmol": float(
                self.carbon_balance_residual_kmol[-1]
            ),
            "nitrogen_balance_residual_kmol": float(
                self.nitrogen_balance_residual_kmol[-1]
            ),
            "provisional": bool(self.metadata.get("provisional", False)),
        }

    def time_records(self) -> list[dict[str, Any]]:
        """Return flat time records that a UI can chart without model access."""
        records: list[dict[str, Any]] = []
        for index, time in enumerate(self.time_d):
            row = {
                "time_d": float(time),
                "pH": float(self.pH[index]),
                "vfa_kg_cod_m3": float(self.vfa_kg_cod_m3[index]),
                "tan_kg_n_m3": float(self.tan_kg_n_m3[index]),
                "free_ammonia_kg_n_m3": float(self.free_ammonia_kg_n_m3[index]),
                "bicarbonate_alkalinity_kmol_charge_m3": float(
                    self.bicarbonate_alkalinity_kmol_charge_m3[index]
                ),
                "hydrogen_rate_nm3_m3_d": float(
                    self.hydrogen_rate_nm3_m3_d[index]
                ),
                "methane_rate_nm3_m3_d": float(self.methane_rate_nm3_m3_d[index]),
                "carbon_dioxide_rate_nm3_m3_d": float(
                    self.carbon_dioxide_rate_nm3_m3_d[index]
                ),
                "biogas_rate_nm3_m3_d": float(self.biogas_rate_nm3_m3_d[index]),
                "hydrogen_fraction": float(self.hydrogen_fraction[index]),
                "methane_fraction": float(self.methane_fraction[index]),
                "carbon_dioxide_fraction": float(
                    self.carbon_dioxide_fraction[index]
                ),
                "cumulative_methane_nm3_m3": float(
                    self.cumulative_methane_nm3_m3[index]
                ),
                "model_soluble_cod_kg_m3": float(
                    self.model_soluble_cod_kg_m3[index]
                ),
                "cod_balance_residual_kg": float(
                    self.cod_balance_residual_kg[index]
                ),
                "carbon_balance_residual_kmol": float(
                    self.carbon_balance_residual_kmol[index]
                ),
                "nitrogen_balance_residual_kmol": float(
                    self.nitrogen_balance_residual_kmol[index]
                ),
            }
            for state_name in STATE_NAMES:
                row[state_name] = float(self.states[STATE_INDEX[state_name], index])
            if self.stability_risk_index is not None:
                row["stability_risk_index"] = float(
                    self.stability_risk_index[index]
                )
            if self.stability_status is not None:
                row["stability_status"] = str(self.stability_status[index])
            if self.stability_limiting_indicator is not None:
                row["stability_limiting_indicator"] = str(
                    self.stability_limiting_indicator[index]
                )
            records.append(row)
        return records

    def to_payload(self, *, include_time_series: bool = True) -> dict[str, Any]:
        """Return one JSON-serializable payload for a UI or API boundary."""
        payload: dict[str, Any] = {
            "summary": self.summary(),
            "final_states": {
                name: float(self.states[STATE_INDEX[name], -1])
                for name in STATE_NAMES
            },
            "metadata": self.metadata,
        }
        if include_time_series:
            payload["time_series"] = self.time_records()
        return payload
