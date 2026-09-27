from __future__ import annotations

import json
import math
import unittest

import numpy as np

from AD import Feedstock
from AD.adm1.chemistry import solve_pH
from AD.adm1.influent import build_influent
from AD.adm1.kinetics import _pH_inhibition
from AD.adm1.parameters import ADM1Parameters
from AD.adm1.states import COD_LIQUID_STATES, LIQUID_STATES, STATE_INDEX, STATE_NAMES
from AD.adm1.stoichiometry import build_stoichiometric_matrix, elemental_residuals
from data.adm1_config import ADM1_TRANSLATION
from data.config import (
    BMP_CONSTANTS,
    ENZYME_DOSES,
    FPSI_WEIGHTS,
    FW_FRACTIONS,
    PRETREATMENT_BASELINE,
    PRETREATMENT_CONFIG,
    SCG_FRACTIONS,
)
from model_analysis.calibration import (
    CalibrationObservation,
    evaluate_calibration,
)
from model_analysis.sensitivity import run_oat_sensitivity
from model_analysis.stability import (
    StabilityConfig,
    assess_stability,
    food_waste_literature_profile,
)
from model_analysis.validation import screening_consistency
from pretreatment import NoPretreatment, Pretreatment
from run_adm1 import _parse_scenario_ids, _parse_sensitivity_factor
from scenarios import (
    SCENARIOS,
    SimulationInputs,
    get_scenario,
    input_schema,
    list_scenarios,
    make_custom_scenario,
    run_scenario,
    run_scenario_set,
)


class ADM1StructureTests(unittest.TestCase):
    def test_state_vector_contains_standard_liquid_and_gas_states(self):
        self.assertEqual(len(LIQUID_STATES), 26)
        self.assertEqual(len(STATE_NAMES), 29)
        self.assertIn("S_ac", STATE_NAMES)
        self.assertIn("X_ac", STATE_NAMES)
        self.assertIn("S_cat", STATE_NAMES)
        self.assertIn("G_ch4", STATE_NAMES)

    def test_stoichiometry_closes_carbon_nitrogen_and_cod(self):
        parameters = ADM1Parameters()
        matrix = build_stoichiometric_matrix(parameters)
        carbon, nitrogen = elemental_residuals(matrix, parameters)
        self.assertLess(float(np.max(np.abs(carbon))), 1e-12)
        self.assertLess(float(np.max(np.abs(nitrogen))), 1e-12)
        cod_rows = [STATE_INDEX[name] for name in COD_LIQUID_STATES]
        self.assertLess(float(np.max(np.abs(matrix[cod_rows, :].sum(axis=0)))), 1e-12)

    def test_bsm2_ph_inhibition_has_half_response_at_midpoint(self):
        self.assertAlmostEqual(_pH_inhibition(6.5, 6.0, 7.0), 0.5)
        self.assertLess(_pH_inhibition(6.0, 6.0, 7.0), 0.5)
        self.assertGreater(_pH_inhibition(7.0, 6.0, 7.0), 0.5)

    def test_temperature_adjusts_equilibrium_and_henry_constants(self):
        parameters = ADM1Parameters()
        equilibrium_25 = parameters.equilibrium_constants(25.0)
        equilibrium_35 = parameters.equilibrium_constants(35.0)
        henry_25 = parameters.henry_constants(25.0)
        henry_35 = parameters.henry_constants(35.0)
        self.assertNotEqual(equilibrium_25["co2"], equilibrium_35["co2"])
        self.assertNotEqual(henry_25["ch4"], henry_35["ch4"])
        self.assertGreater(
            parameters.water_vapour_pressure(35.0),
            parameters.water_vapour_pressure(25.0),
        )


class FeedstockAndPretreatmentTests(unittest.TestCase):
    @staticmethod
    def _feedstock(scg_fraction_vs: float = 0.0) -> Feedstock:
        return Feedstock(
            1.0,
            0.20,
            0.90,
            scg_fraction_vs,
            FW_FRACTIONS,
            SCG_FRACTIONS,
        )

    @staticmethod
    def _treatment() -> Pretreatment:
        return Pretreatment(
            temp_pre=PRETREATMENT_BASELINE["temperature_c"],
            ph_pre=PRETREATMENT_BASELINE["pH"],
            time_pre=PRETREATMENT_BASELINE["time_h"],
            enzyme_doses=ENZYME_DOSES,
            config=PRETREATMENT_CONFIG,
            weights=FPSI_WEIGHTS,
        )

    def test_solids_and_mass_balance(self):
        feedstock = self._feedstock()
        self.assertAlmostEqual(feedstock.m_ts, 0.20)
        self.assertAlmostEqual(feedstock.m_vs, 0.18)
        self.assertAlmostEqual(feedstock.mass_balance_error_kg_vs, 0.0)

    def test_scg_ratio_is_converted_to_total_fraction(self):
        self.assertAlmostEqual(
            Feedstock.scg_fraction_from_fw_ratio(0.04),
            0.04 / 1.04,
        )

    def test_theoretical_bmp_is_composition_weighted(self):
        scg_fraction = Feedstock.scg_fraction_from_fw_ratio(0.04)
        feedstock = self._feedstock(scg_fraction)
        fw_bmp = 0.50 * 0.415 + 0.25 * 0.496 + 0.20 * 1.014
        scg_bmp = 0.42 * 0.415 + 0.16 * 0.496 + 0.22 * 1.014
        expected = (1.0 - scg_fraction) * fw_bmp + scg_fraction * scg_bmp
        self.assertAlmostEqual(feedstock.calculate_theoretical_bmp(BMP_CONSTANTS), expected)

    def test_invalid_fractions_are_rejected(self):
        invalid = dict(FW_FRACTIONS)
        invalid["carb"] = 0.60
        with self.assertRaises(ValueError):
            Feedstock(1.0, 0.20, 0.90, 0.0, invalid, SCG_FRACTIONS)

    def test_no_pretreatment_has_zero_effect(self):
        control = NoPretreatment()
        self.assertEqual(control.fpsi, 0.0)
        self.assertTrue(all(value == 0.0 for value in control.A.values()))

    def test_baseline_fpsi_matches_response_equation(self):
        expected = 0.5 * (1.0 - math.exp(-0.4 * 24.0))
        self.assertAlmostEqual(self._treatment().fpsi, expected)

    def test_negative_enzyme_dose_is_rejected(self):
        doses = dict(ENZYME_DOSES)
        doses["carb"] = -1.0
        with self.assertRaises(ValueError):
            Pretreatment(
                temp_pre=60.0,
                ph_pre=4.8,
                time_pre=24.0,
                enzyme_doses=doses,
                config=PRETREATMENT_CONFIG,
                weights=FPSI_WEIGHTS,
            )


class ADM1InfluentTests(unittest.TestCase):
    def setUp(self):
        self.parameters = ADM1Parameters()
        self.feedstock = Feedstock(
            1.0,
            0.20,
            0.90,
            0.0,
            FW_FRACTIONS,
            SCG_FRACTIONS,
        )
        self.influent = build_influent(
            self.feedstock,
            NoPretreatment(),
            olr_kg_vs_m3_d=2.0,
            hrt_d=20.0,
            target_pH=7.2,
            temperature_c=35.0,
            bmp_constants=BMP_CONSTANTS,
            parameters=self.parameters,
            **ADM1_TRANSLATION,
        )

    def test_fractionation_preserves_total_cod(self):
        cod_total = sum(
            self.influent.state[STATE_INDEX[name]] for name in COD_LIQUID_STATES
        )
        self.assertAlmostEqual(cod_total, self.influent.total_cod_kg_m3)

    def test_strong_ion_balance_sets_requested_feed_pH(self):
        chemistry = solve_pH(
            self.influent.state[: len(LIQUID_STATES)],
            self.influent.strong_cations_kmol_m3,
            self.influent.strong_anions_kmol_m3,
            self.parameters,
        )
        self.assertAlmostEqual(chemistry.pH, 7.2, places=6)


class ScenarioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.comparison = run_scenario_set(
            ("S1", "S3", "S6"), duration_d=60.0, output_points=61
        )

    def test_all_requested_scenarios_are_defined(self):
        self.assertTrue({f"S{number}" for number in range(1, 10)} <= set(SCENARIOS))
        self.assertIn("C1", SCENARIOS)
        self.assertEqual(get_scenario("s6").scg_fraction_vs, 0.10)
        self.assertEqual(get_scenario("S9").olr_kg_vs_m3_d, 4.0)
        self.assertEqual(get_scenario("S3").reference_scenario_id, "S1")
        self.assertEqual(get_scenario("S5").reference_scenario_id, "S3")
        self.assertEqual(get_scenario("S9").reference_scenario_id, "S6")

    def test_command_line_scenario_selection(self):
        self.assertEqual(_parse_scenario_ids("s1, S3 s6"), ("S1", "S3", "S6"))
        self.assertEqual(_parse_scenario_ids("1 2"), ("S1", "S2"))
        self.assertEqual(_parse_scenario_ids("S3 S3"), ("S3",))
        with self.assertRaises(ValueError):
            _parse_scenario_ids("S10")

    def test_command_line_sensitivity_selection(self):
        self.assertEqual(_parse_sensitivity_factor("1"), "enzyme_dose")
        self.assertEqual(_parse_sensitivity_factor("2"), "pretreatment_time")
        self.assertEqual(_parse_sensitivity_factor("hrt"), "hrt")
        with self.assertRaises(ValueError):
            _parse_sensitivity_factor("6")

    def test_control_and_priority_scenarios_run(self):
        self.assertEqual(len(self.comparison.results), 3)
        for result in self.comparison.results:
            self.assertTrue(np.all(np.isfinite(result.states)))
            self.assertTrue(np.all(result.states >= 0))
            self.assertGreater(result.methane_yield_l_per_kg_vs, 0.0)
            self.assertGreater(result.final_pH, 3.0)
            self.assertLess(result.final_pH, 12.0)
            self.assertLess(abs(result.cod_balance_residual_kg[-1]), 1e-5)
            self.assertLess(abs(result.carbon_balance_residual_kmol[-1]), 1e-7)
            self.assertLess(abs(result.nitrogen_balance_residual_kmol[-1]), 1e-7)

    def test_moderate_pretreatment_changes_control_prediction(self):
        results = {result.scenario_id: result for result in self.comparison.results}
        self.assertGreater(
            results["S3"].methane_yield_l_per_kg_vs,
            results["S1"].methane_yield_l_per_kg_vs,
        )
        self.assertEqual(results["S6"].scg_fraction_vs, 0.10)

    def test_custom_treatment_requires_complete_measured_effects(self):
        with self.assertRaises(ValueError):
            make_custom_scenario(
                scenario_id="CHEM",
                name="Chemical treatment",
                effectiveness={"carb": 0.5},
                fpsi=0.5,
            )

    def test_simulation_inputs_reject_invalid_solids(self):
        with self.assertRaises(ValueError):
            SimulationInputs(total_solids_fraction=1.2).validate()

    def test_ui_ready_outputs_are_complete(self):
        result = self.comparison.results[0]
        summary = result.summary()
        expected = {
            "methane_rate_nm3_m3_d",
            "hydrogen_rate_nm3_m3_d",
            "carbon_dioxide_rate_nm3_m3_d",
            "biogas_rate_nm3_m3_d",
            "cumulative_methane_nm3_m3",
            "methane_fraction",
            "hydrogen_fraction",
            "carbon_dioxide_fraction",
            "pH",
            "vfa_kg_cod_m3",
            "tan_kg_n_m3",
            "free_ammonia_kg_n_m3",
            "bicarbonate_alkalinity_kmol_charge_m3",
            "model_soluble_cod_kg_m3",
            "gross_energy_kwh_for_2_25kg_vs",
            "gross_energy_kwh_for_feed_batch",
            "methane_volume_nm3_for_feed_batch",
            "feed_volatile_solids_kg",
            "theoretical_bmp_l_per_kg_vs",
            "cod_balance_residual_kg",
            "carbon_balance_residual_kmol",
            "nitrogen_balance_residual_kmol",
        }
        self.assertTrue(expected.issubset(summary))
        time_series_only = {
            "methane_rate_nm3_m3_d",
            "hydrogen_rate_nm3_m3_d",
            "carbon_dioxide_rate_nm3_m3_d",
            "biogas_rate_nm3_m3_d",
            "cumulative_methane_nm3_m3",
            "methane_fraction",
            "hydrogen_fraction",
            "carbon_dioxide_fraction",
            "pH",
            "vfa_kg_cod_m3",
            "tan_kg_n_m3",
            "free_ammonia_kg_n_m3",
            "bicarbonate_alkalinity_kmol_charge_m3",
            "model_soluble_cod_kg_m3",
            "cod_balance_residual_kg",
            "carbon_balance_residual_kmol",
            "nitrogen_balance_residual_kmol",
        }
        self.assertTrue(time_series_only <= result.time_records()[0].keys())
        self.assertLessEqual(
            result.methane_yield_l_per_kg_vs,
            summary["theoretical_bmp_l_per_kg_vs"],
        )

    def test_ui_payloads_are_json_serializable(self):
        result = self.comparison.results[0]
        payload = result.to_payload()
        json.dumps(payload)
        self.assertEqual(set(payload["final_states"]), set(STATE_NAMES))
        gas_fraction_sum = (
            result.hydrogen_fraction
            + result.methane_fraction
            + result.carbon_dioxide_fraction
        )
        self.assertTrue(np.allclose(gas_fraction_sum, 1.0))
        json.dumps(self.comparison.to_payload(include_time_series=False))
        json.dumps(list_scenarios())
        json.dumps(input_schema())

    def test_custom_common_inputs_reach_model_metadata(self):
        inputs = SimulationInputs(
            wet_feed_mass_kg=2.0,
            influent_pH=7.0,
            duration_d=20.0,
            output_points=21,
        )
        result = run_scenario("S1", inputs=inputs)
        recorded = result.metadata["simulation_inputs"]
        self.assertEqual(recorded["wet_feed_mass_kg"], 2.0)
        self.assertEqual(recorded["influent_pH"], 7.0)
        self.assertEqual(len(result.time_d), 21)
        summary = result.summary()
        self.assertAlmostEqual(summary["feed_total_solids_kg"], 0.4)
        self.assertAlmostEqual(summary["feed_volatile_solids_kg"], 0.36)
        self.assertGreater(summary["gross_energy_kwh_for_feed_batch"], 0.0)

    def test_ui_inputs_reject_nan_and_non_integer_resolution(self):
        with self.assertRaises(ValueError):
            SimulationInputs(influent_pH=float("nan")).validate()
        with self.assertRaises(ValueError):
            SimulationInputs(output_points=10.5).validate()

    def test_all_implemented_scenarios_complete_with_finite_outputs(self):
        comparison = run_scenario_set(
            tuple(SCENARIOS), duration_d=40.0, output_points=41
        )
        self.assertEqual(len(comparison.results), len(SCENARIOS))
        for result in comparison.results:
            self.assertTrue(np.all(np.isfinite(result.states)))
            self.assertTrue(np.all(np.isfinite(result.pH)))
            self.assertTrue(np.all(np.isfinite(result.methane_rate_nm3_m3_d)))

    def test_formula_list_stability_risk_is_calculated_when_configured(self):
        config = StabilityConfig(
            vfa_critical_kg_cod_m3=2.0,
            pH_optimal=7.0,
            free_ammonia_critical_kg_n_m3=0.5,
            weight_vfa=2.0,
            weight_pH=1.0,
            weight_free_ammonia=1.0,
            source="unit-test values only",
        )
        assessment = assess_stability(
            pH=np.asarray([7.0, 6.3]),
            vfa_kg_cod_m3=np.asarray([1.0, 2.0]),
            free_ammonia_kg_n_m3=np.asarray([0.25, 0.5]),
            config=config,
        )
        expected_final = (2.0 * 1.0 + 1.0 * 0.1 + 1.0 * 1.0) / 4.0
        self.assertAlmostEqual(assessment.combined_risk_index[-1], expected_final)

    def test_calibration_report_compares_measurements_with_time_series(self):
        result = self.comparison.results[0]
        observations = (
            CalibrationObservation(
                time_d=float(result.time_d[-1]),
                variable="pH",
                value=float(result.pH[-1]),
                scale=0.1,
            ),
            CalibrationObservation(
                time_d=float(result.time_d[-1]),
                variable="methane_rate_nm3_m3_d",
                value=float(result.methane_rate_nm3_m3_d[-1]),
                scale=0.1,
            ),
        )
        report = evaluate_calibration(result, observations)
        self.assertEqual(report.observation_count, 2)
        self.assertAlmostEqual(report.rmse_scaled, 0.0)
        json.dumps(report.as_dict())

    def test_result_includes_stability_risk_when_limits_are_supplied(self):
        config = StabilityConfig(
            vfa_critical_kg_cod_m3=2.0,
            pH_optimal=7.0,
            free_ammonia_critical_kg_n_m3=0.5,
            weight_vfa=1.0,
            weight_pH=1.0,
            weight_free_ammonia=1.0,
            source="unit-test values only",
        )
        result = run_scenario(
            "S1", duration_d=5.0, output_points=6, stability_config=config
        )
        summary = result.summary()
        self.assertIsNotNone(summary["stability_risk_index"])
        self.assertIn(summary["stability_status"], {"Stable", "Watch", "High risk"})
        self.assertEqual(summary["stability_basis"], "unit-test values only")
        self.assertIn("stability_risk_index", result.time_records()[0])

    def test_default_stability_profile_has_traceable_status_and_sources(self):
        profile = food_waste_literature_profile()
        unscored = run_scenario("S1", duration_d=5.0, output_points=6)
        self.assertEqual(unscored.summary()["stability_status"], "Not assessed")
        self.assertIsNone(unscored.summary()["stability_risk_index"])

        result = run_scenario(
            "S1",
            duration_d=5.0,
            output_points=6,
            stability_config=profile,
        )
        summary = result.summary()
        self.assertIn(summary["stability_status"], {"Stable", "Watch", "High risk"})
        self.assertEqual(
            result.metadata["stability_profile"]["profile_id"], profile.profile_id
        )
        self.assertTrue(result.metadata["stability_profile"]["citations"])
        self.assertIn("stability_status", result.time_records()[0])

        temperature_warning = assess_stability(
            pH=np.asarray([7.0]),
            vfa_kg_cod_m3=np.asarray([0.0]),
            free_ammonia_kg_n_m3=np.asarray([0.0]),
            temperature_c=40.0,
            config=profile,
        )
        self.assertEqual(temperature_warning.status[-1], "Watch")
        self.assertEqual(temperature_warning.limiting_indicator[-1], "temperature")

    def test_chemical_proxy_uses_soluble_fraction_without_fpsi(self):
        result = run_scenario("C1", duration_d=5.0, output_points=6)
        summary = result.summary()
        self.assertFalse(summary["fpsi_applicable"])
        self.assertAlmostEqual(result.metadata["influent_soluble_cod_fraction"], 0.6606)

    def test_screening_checks_are_json_ready(self):
        result = self.comparison.results[0]
        checks = screening_consistency(result)
        self.assertEqual(len(checks), 5)
        json.dumps(checks)

    def test_oat_analysis_changes_only_selected_factor(self):
        report = run_oat_sensitivity(
            "olr",
            values=(1.0, 2.0),
            duration_d=5.0,
            output_points=6,
        )
        self.assertEqual(len(report.rows), 2)
        self.assertEqual(report.factor.key, "olr_kg_vs_m3_d")
        json.dumps(report.to_payload())


if __name__ == "__main__":
    unittest.main()
