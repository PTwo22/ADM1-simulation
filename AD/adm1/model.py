"""Dynamic CSTR and gas-headspace implementation of IWA ADM1."""

from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Integral
from typing import Mapping

import numpy as np
from scipy.integrate import solve_ivp

from AD.adm1.chemistry import solve_pH
from AD.adm1.kinetics import calculate_process_rates
from AD.adm1.parameters import ADM1Parameters
from AD.adm1.results import ADM1SimulationResult
from AD.adm1.states import (
    COD_LIQUID_STATES,
    GAS_STATES,
    LIQUID_STATES,
    STATE_INDEX,
    STATE_NAMES,
)
from AD.adm1.stoichiometry import build_stoichiometric_matrix


@dataclass(frozen=True)
class ADM1ReactorConfig:
    hrt_d: float = 20.0
    olr_kg_vs_m3_d: float = 2.0
    liquid_volume_m3: float = 1.0
    gas_volume_m3: float = 0.10
    temperature_c: float = 35.0
    duration_d: float = 100.0
    output_points: int = 201
    relative_tolerance: float = 1e-6
    absolute_tolerance: float = 1e-9

    def validate(self) -> None:
        numeric = (
            self.hrt_d,
            self.olr_kg_vs_m3_d,
            self.liquid_volume_m3,
            self.gas_volume_m3,
            self.temperature_c,
            self.duration_d,
        )
        if not all(math.isfinite(float(value)) for value in numeric):
            raise ValueError("Reactor inputs must be finite")
        if self.hrt_d <= 0 or self.olr_kg_vs_m3_d <= 0:
            raise ValueError("HRT and OLR must be positive")
        if self.liquid_volume_m3 <= 0 or self.gas_volume_m3 <= 0:
            raise ValueError("Reactor liquid and gas volumes must be positive")
        if (
            self.duration_d <= 0
            or not isinstance(self.output_points, Integral)
            or isinstance(self.output_points, bool)
            or self.output_points < 2
        ):
            raise ValueError("Simulation duration and output resolution are invalid")


@dataclass(frozen=True)
class GasState:
    p_h2_bar: float
    p_ch4_bar: float
    p_co2_bar: float
    total_pressure_bar: float
    gas_flow_m3_d: float
    transfer_h2_kg_cod_m3_d: float
    transfer_ch4_kg_cod_m3_d: float
    transfer_co2_kmol_c_m3_d: float


class ADM1Model:
    """Solve the coupled ADM1 liquid and headspace differential equations."""

    def __init__(
        self,
        influent_state: np.ndarray,
        initial_state: np.ndarray,
        *,
        strong_cations_kmol_m3: float,
        strong_anions_kmol_m3: float,
        hydrolysis_multipliers: Mapping[str, float],
        reactor: ADM1ReactorConfig,
        parameters: ADM1Parameters | None = None,
    ) -> None:
        self.parameters = parameters or ADM1Parameters()
        self.parameters.validate()
        reactor.validate()
        self.reactor = reactor
        self.influent = np.asarray(influent_state, dtype=float)
        self.initial = np.asarray(initial_state, dtype=float)
        expected = (len(STATE_NAMES),)
        if self.influent.shape != expected or self.initial.shape != expected:
            raise ValueError(f"ADM1 vectors must have shape {expected}")
        if np.any(self.influent < 0) or np.any(self.initial < 0):
            raise ValueError("ADM1 concentrations cannot be negative")
        self.strong_cations = float(strong_cations_kmol_m3)
        self.strong_anions = float(strong_anions_kmol_m3)
        if self.strong_cations < 0 or self.strong_anions < 0:
            raise ValueError("Strong-ion concentrations cannot be negative")
        self.hydrolysis_multipliers = dict(hydrolysis_multipliers)
        self.stoichiometry = build_stoichiometric_matrix(self.parameters)

    def gas_state(self, state: np.ndarray, carbon_dioxide_kmol_m3: float) -> GasState:
        p = self.parameters
        temperature_k = self.reactor.temperature_c + 273.15
        gas_factor = p.gas_constant_bar_m3_per_kmol_k * temperature_k
        g_h2 = max(float(state[STATE_INDEX["G_h2"]]), 0.0)
        g_ch4 = max(float(state[STATE_INDEX["G_ch4"]]), 0.0)
        g_co2 = max(float(state[STATE_INDEX["G_co2"]]), 0.0)
        henry = p.henry_constants(self.reactor.temperature_c)
        p_h2 = g_h2 / p.cod_per_kmol_h2 * gas_factor
        p_ch4 = g_ch4 / p.cod_per_kmol_ch4 * gas_factor
        p_co2 = g_co2 * gas_factor
        total_pressure = (
            p_h2
            + p_ch4
            + p_co2
            + p.water_vapour_pressure(self.reactor.temperature_c)
        )
        gas_flow = p.k_p_m3_per_d_bar * max(
            total_pressure - p.atmospheric_pressure_bar, 0.0
        )
        transfer_h2 = p.k_la_per_d * (
            max(float(state[STATE_INDEX["S_h2"]]), 0.0)
            - p.cod_per_kmol_h2 * henry["h2"] * p_h2
        )
        transfer_ch4 = p.k_la_per_d * (
            max(float(state[STATE_INDEX["S_ch4"]]), 0.0)
            - p.cod_per_kmol_ch4 * henry["ch4"] * p_ch4
        )
        transfer_co2 = p.k_la_per_d * (
            max(carbon_dioxide_kmol_m3, 0.0) - henry["co2"] * p_co2
        )
        return GasState(
            p_h2_bar=p_h2,
            p_ch4_bar=p_ch4,
            p_co2_bar=p_co2,
            total_pressure_bar=total_pressure,
            gas_flow_m3_d=gas_flow,
            transfer_h2_kg_cod_m3_d=transfer_h2,
            transfer_ch4_kg_cod_m3_d=transfer_ch4,
            transfer_co2_kmol_c_m3_d=transfer_co2,
        )

    def rhs(self, _time: float, state: np.ndarray) -> np.ndarray:
        liquid = state[: len(LIQUID_STATES)]
        rates, kinetics = calculate_process_rates(
            liquid,
            self.parameters,
            max(float(liquid[STATE_INDEX["S_cat"]]), 0.0),
            max(float(liquid[STATE_INDEX["S_an"]]), 0.0),
            self.hydrolysis_multipliers,
            self.reactor.temperature_c,
        )
        reaction = self.stoichiometry @ rates
        flow = (self.influent[: len(LIQUID_STATES)] - liquid) / self.reactor.hrt_d
        derivative = np.zeros_like(state, dtype=float)
        derivative[: len(LIQUID_STATES)] = flow + reaction

        gas = self.gas_state(state, kinetics.chemistry.carbon_dioxide_kmol_m3)
        derivative[STATE_INDEX["S_h2"]] -= gas.transfer_h2_kg_cod_m3_d
        derivative[STATE_INDEX["S_ch4"]] -= gas.transfer_ch4_kg_cod_m3_d
        derivative[STATE_INDEX["S_IC"]] -= gas.transfer_co2_kmol_c_m3_d

        volume_ratio = self.reactor.liquid_volume_m3 / self.reactor.gas_volume_m3
        outlet_rate = gas.gas_flow_m3_d / self.reactor.gas_volume_m3
        derivative[STATE_INDEX["G_h2"]] = (
            volume_ratio * gas.transfer_h2_kg_cod_m3_d
            - outlet_rate * max(float(state[STATE_INDEX["G_h2"]]), 0.0)
        )
        derivative[STATE_INDEX["G_ch4"]] = (
            volume_ratio * gas.transfer_ch4_kg_cod_m3_d
            - outlet_rate * max(float(state[STATE_INDEX["G_ch4"]]), 0.0)
        )
        derivative[STATE_INDEX["G_co2"]] = (
            volume_ratio * gas.transfer_co2_kmol_c_m3_d
            - outlet_rate * max(float(state[STATE_INDEX["G_co2"]]), 0.0)
        )
        if state.size > len(STATE_NAMES):
            # Auxiliary integrals make cumulative methane and elemental
            # closure independent of the requested output sampling interval.
            methane_kmol_d = (
                gas.gas_flow_m3_d
                * max(float(state[STATE_INDEX["G_ch4"]]), 0.0)
                / self.parameters.cod_per_kmol_ch4
            )
            derivative[len(STATE_NAMES)] = (
                methane_kmol_d
                * self.parameters.normal_m3_per_kmol
                / self.reactor.liquid_volume_m3
            )
            liquid_indices = [STATE_INDEX[name] for name in COD_LIQUID_STATES]
            influent_cod = float(np.sum(self.influent[liquid_indices]))
            liquid_cod = float(np.sum(np.maximum(state[liquid_indices], 0.0)))
            gas_cod = max(float(state[STATE_INDEX["G_h2"]]), 0.0) + max(
                float(state[STATE_INDEX["G_ch4"]]), 0.0
            )
            liquid_flow = self.reactor.liquid_volume_m3 / self.reactor.hrt_d
            derivative[len(STATE_NAMES) + 1] = (
                liquid_flow * (influent_cod - liquid_cod)
                - gas.gas_flow_m3_d * gas_cod
            )
            influent_carbon = float(self.influent[STATE_INDEX["S_IC"]]) + sum(
                max(float(self.influent[STATE_INDEX[name]]), 0.0) * content
                for name, content in self.parameters.carbon_content.items()
            )
            liquid_carbon = max(float(state[STATE_INDEX["S_IC"]]), 0.0) + sum(
                max(float(state[STATE_INDEX[name]]), 0.0) * content
                for name, content in self.parameters.carbon_content.items()
            )
            gas_carbon = (
                max(float(state[STATE_INDEX["G_ch4"]]), 0.0)
                / self.parameters.cod_per_kmol_ch4
                + max(float(state[STATE_INDEX["G_co2"]]), 0.0)
            )
            derivative[len(STATE_NAMES) + 2] = (
                liquid_flow * (influent_carbon - liquid_carbon)
                - gas.gas_flow_m3_d * gas_carbon
            )
            influent_nitrogen = float(self.influent[STATE_INDEX["S_IN"]]) + sum(
                max(float(self.influent[STATE_INDEX[name]]), 0.0) * content
                for name, content in self.parameters.nitrogen_content.items()
            )
            liquid_nitrogen = max(float(state[STATE_INDEX["S_IN"]]), 0.0) + sum(
                max(float(state[STATE_INDEX[name]]), 0.0) * content
                for name, content in self.parameters.nitrogen_content.items()
            )
            derivative[len(STATE_NAMES) + 3] = liquid_flow * (
                influent_nitrogen - liquid_nitrogen
            )
        return derivative

    def simulate(
        self,
        *,
        scenario_id: str,
        scenario_name: str,
        fpsi: float,
        scg_fraction_vs: float,
        metadata: dict[str, object] | None = None,
    ) -> ADM1SimulationResult:
        """Integrate the model and return time-series and summary outputs."""
        output_times = np.linspace(
            0.0, self.reactor.duration_d, self.reactor.output_points
        )
        augmented_initial = np.concatenate((self.initial, np.zeros(4)))
        solution = solve_ivp(
            self.rhs,
            (0.0, self.reactor.duration_d),
            augmented_initial,
            method="BDF",
            t_eval=output_times,
            rtol=self.reactor.relative_tolerance,
            atol=self.reactor.absolute_tolerance,
        )
        if not solution.success:
            raise RuntimeError(f"ADM1 solver failed: {solution.message}")
        minimum = float(np.min(solution.y[: len(STATE_NAMES), :]))
        if minimum < -1e-4:
            raise RuntimeError(
                f"ADM1 solver produced a material negative concentration: {minimum:.3e}"
            )
        states = np.maximum(solution.y[: len(STATE_NAMES), :], 0.0)

        point_count = states.shape[1]
        pH = np.zeros(point_count)
        vfa = np.zeros(point_count)
        tan = np.zeros(point_count)
        free_ammonia = np.zeros(point_count)
        bicarbonate_alkalinity = np.zeros(point_count)
        hydrogen_rate = np.zeros(point_count)
        methane_rate = np.zeros(point_count)
        carbon_dioxide_rate = np.zeros(point_count)
        biogas_rate = np.zeros(point_count)
        hydrogen_fraction = np.zeros(point_count)
        methane_fraction = np.zeros(point_count)
        carbon_dioxide_fraction = np.zeros(point_count)
        q_gas = np.zeros(point_count)

        for index in range(point_count):
            state = states[:, index]
            chemistry = solve_pH(
                state[: len(LIQUID_STATES)],
                state[STATE_INDEX["S_cat"]],
                state[STATE_INDEX["S_an"]],
                self.parameters,
                self.reactor.temperature_c,
            )
            gas = self.gas_state(state, chemistry.carbon_dioxide_kmol_m3)
            pH[index] = chemistry.pH
            vfa[index] = sum(
                state[STATE_INDEX[name]] for name in ("S_va", "S_bu", "S_pro", "S_ac")
            )
            tan[index] = state[STATE_INDEX["S_IN"]] * 14.0
            free_ammonia[index] = chemistry.free_ammonia_kmol_m3 * 14.0
            bicarbonate_alkalinity[index] = chemistry.bicarbonate_kmol_m3
            q_gas[index] = gas.gas_flow_m3_d
            methane_kmol_d = (
                gas.gas_flow_m3_d
                * state[STATE_INDEX["G_ch4"]]
                / self.parameters.cod_per_kmol_ch4
            )
            co2_kmol_d = gas.gas_flow_m3_d * state[STATE_INDEX["G_co2"]]
            h2_kmol_d = (
                gas.gas_flow_m3_d
                * state[STATE_INDEX["G_h2"]]
                / self.parameters.cod_per_kmol_h2
            )
            volume = self.reactor.liquid_volume_m3
            hydrogen_rate[index] = (
                h2_kmol_d * self.parameters.normal_m3_per_kmol / volume
            )
            methane_rate[index] = (
                methane_kmol_d * self.parameters.normal_m3_per_kmol / volume
            )
            carbon_dioxide_rate[index] = (
                co2_kmol_d * self.parameters.normal_m3_per_kmol / volume
            )
            biogas_rate[index] = (
                (methane_kmol_d + co2_kmol_d + h2_kmol_d)
                * self.parameters.normal_m3_per_kmol
                / volume
            )
            dry_pressure = gas.p_h2_bar + gas.p_ch4_bar + gas.p_co2_bar
            hydrogen_fraction[index] = gas.p_h2_bar / dry_pressure if dry_pressure > 0 else 0.0
            methane_fraction[index] = gas.p_ch4_bar / dry_pressure if dry_pressure > 0 else 0.0
            carbon_dioxide_fraction[index] = (
                gas.p_co2_bar / dry_pressure if dry_pressure > 0 else 0.0
            )

        cumulative_methane = np.maximum(solution.y[len(STATE_NAMES), :], 0.0)
        cod_balance = self._cod_balance_residual(
            states, solution.y[len(STATE_NAMES) + 1, :]
        )
        carbon_balance = self._carbon_balance_residual(
            states, solution.y[len(STATE_NAMES) + 2, :]
        )
        nitrogen_balance = self._nitrogen_balance_residual(
            states, solution.y[len(STATE_NAMES) + 3, :]
        )
        tail = max(5, point_count // 10)
        representative_rate = float(np.mean(methane_rate[-tail:]))
        methane_yield_nm3_kg_vs = representative_rate / self.reactor.olr_kg_vs_m3_d
        methane_yield_l_kg_vs = methane_yield_nm3_kg_vs * 1000.0
        gross_energy = methane_yield_nm3_kg_vs * 2.25 * 35.8 / 3.6

        result_metadata = dict(metadata or {})
        result_metadata.update(
            {
                "solver": "scipy.solve_ivp.BDF",
                "solver_message": solution.message,
                "minimum_raw_concentration": minimum,
                "state_units": {
                    "organic_liquid": "kg COD/m3",
                    "S_IC": "kmol C/m3",
                    "S_IN": "kmol N/m3",
                    "S_cat_S_an": "kmol charge/m3",
                    "G_h2_G_ch4": "kg COD/m3 headspace",
                    "G_co2": "kmol C/m3 headspace",
                },
            }
        )
        return ADM1SimulationResult(
            scenario_id=scenario_id,
            scenario_name=scenario_name,
            time_d=solution.t,
            states=states,
            pH=pH,
            vfa_kg_cod_m3=vfa,
            tan_kg_n_m3=tan,
            free_ammonia_kg_n_m3=free_ammonia,
            bicarbonate_alkalinity_kmol_charge_m3=bicarbonate_alkalinity,
            hydrogen_rate_nm3_m3_d=hydrogen_rate,
            methane_rate_nm3_m3_d=methane_rate,
            carbon_dioxide_rate_nm3_m3_d=carbon_dioxide_rate,
            biogas_rate_nm3_m3_d=biogas_rate,
            hydrogen_fraction=hydrogen_fraction,
            methane_fraction=methane_fraction,
            carbon_dioxide_fraction=carbon_dioxide_fraction,
            cumulative_methane_nm3_m3=cumulative_methane,
            cod_balance_residual_kg=cod_balance,
            carbon_balance_residual_kmol=carbon_balance,
            nitrogen_balance_residual_kmol=nitrogen_balance,
            olr_kg_vs_m3_d=self.reactor.olr_kg_vs_m3_d,
            hrt_d=self.reactor.hrt_d,
            fpsi=float(fpsi),
            scg_fraction_vs=float(scg_fraction_vs),
            gross_energy_kwh_for_2_25kg_vs=gross_energy,
            methane_yield_l_per_kg_vs=methane_yield_l_kg_vs,
            metadata=result_metadata,
        )

    def _cod_balance_residual(
        self, states: np.ndarray, integrated_external: np.ndarray
    ) -> np.ndarray:
        liquid_indices = [STATE_INDEX[name] for name in COD_LIQUID_STATES]
        liquid_inventory = (
            np.sum(states[liquid_indices, :], axis=0) * self.reactor.liquid_volume_m3
        )
        gas_inventory = (
            states[STATE_INDEX["G_h2"], :] + states[STATE_INDEX["G_ch4"], :]
        ) * self.reactor.gas_volume_m3
        inventory = liquid_inventory + gas_inventory
        return inventory - inventory[0] - integrated_external

    def _carbon_balance_residual(
        self, states: np.ndarray, integrated_external: np.ndarray
    ) -> np.ndarray:
        liquid_inventory = states[STATE_INDEX["S_IC"], :].copy()
        for name, content in self.parameters.carbon_content.items():
            liquid_inventory += states[STATE_INDEX[name], :] * content
        liquid_inventory *= self.reactor.liquid_volume_m3
        gas_inventory = (
            states[STATE_INDEX["G_ch4"], :] / self.parameters.cod_per_kmol_ch4
            + states[STATE_INDEX["G_co2"], :]
        ) * self.reactor.gas_volume_m3
        inventory = liquid_inventory + gas_inventory
        return inventory - inventory[0] - integrated_external

    def _nitrogen_balance_residual(
        self, states: np.ndarray, integrated_external: np.ndarray
    ) -> np.ndarray:
        inventory = states[STATE_INDEX["S_IN"], :].copy()
        for name, content in self.parameters.nitrogen_content.items():
            inventory += states[STATE_INDEX[name], :] * content
        inventory *= self.reactor.liquid_volume_m3
        return inventory - inventory[0] - integrated_external
