from __future__ import annotations

import copy
import math
import unittest

from AD import Digester, Feedstock
from data.config import (
    BMP_CONSTANTS,
    ENZYME_DOSES,
    FPSI_WEIGHTS,
    FW_FRACTIONS,
    MODEL_CONFIG,
    PRETREATMENT_BASELINE,
    PRETREATMENT_CONFIG,
    SCG_FRACTIONS,
)
from main import build_feedstock, run_scenarios
from pretreatment import NoPretreatment, Pretreatment


class FeedstockTests(unittest.TestCase):
    def test_solids_and_mass_balance(self):
        feedstock = build_feedstock()
        self.assertAlmostEqual(feedstock.m_ts, 0.20)
        self.assertAlmostEqual(feedstock.m_vs, 0.18)
        self.assertAlmostEqual(feedstock.mass_balance_error_kg_vs, 0.0)

    def test_scg_ratio_is_converted_to_total_fraction(self):
        self.assertAlmostEqual(
            Feedstock.scg_fraction_from_fw_ratio(0.04),
            0.04 / 1.04,
        )

    def test_theoretical_bmp_is_composition_weighted(self):
        feedstock = build_feedstock()
        fw_bmp = 0.50 * 0.415 + 0.25 * 0.496 + 0.20 * 1.014
        scg_bmp = 0.42 * 0.415 + 0.16 * 0.496 + 0.22 * 1.014
        expected = (1.0 - feedstock.f_scg) * fw_bmp + feedstock.f_scg * scg_bmp
        self.assertAlmostEqual(feedstock.calculate_theoretical_bmp(BMP_CONSTANTS), expected)

    def test_invalid_fractions_are_rejected(self):
        invalid = dict(FW_FRACTIONS)
        invalid["carb"] = 0.60
        with self.assertRaises(ValueError):
            Feedstock(1.0, 0.2, 0.9, 0.0, invalid, SCG_FRACTIONS)


class PretreatmentTests(unittest.TestCase):
    def _treatment(self):
        return Pretreatment(
            temp_pre=PRETREATMENT_BASELINE["temperature_c"],
            ph_pre=PRETREATMENT_BASELINE["pH"],
            time_pre=PRETREATMENT_BASELINE["time_h"],
            enzyme_doses=ENZYME_DOSES,
            config=PRETREATMENT_CONFIG,
            weights=FPSI_WEIGHTS,
        )

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
                60.0,
                4.8,
                24.0,
                doses,
                PRETREATMENT_CONFIG,
                FPSI_WEIGHTS,
            )


class DigesterTests(unittest.TestCase):
    def test_scenarios_are_bounded_and_treatment_improves_screening_yield(self):
        control, treated = run_scenarios()
        self.assertGreater(treated.methane_yield_nm3_per_kg_vs, control.methane_yield_nm3_per_kg_vs)
        self.assertLessEqual(
            treated.methane_yield_nm3_per_kg_vs,
            treated.theoretical_bmp_nm3_per_kg_vs,
        )
        self.assertGreater(treated.improvement_pct_vs_control, 0.0)
        self.assertEqual(treated.biodegradability["inert"], 0.0)

    def test_no_pretreatment_returns_baseline_yield(self):
        feedstock = build_feedstock()
        model = Digester(feedstock, NoPretreatment(), MODEL_CONFIG)
        result = model.simulate("control")
        self.assertAlmostEqual(result.methane_yield_nm3_per_kg_vs, model._calculate_baseline_yield())

    def test_energy_and_rate_units_are_consistent(self):
        _, treated = run_scenarios()
        self.assertAlmostEqual(
            treated.energy_mj_per_m3_d,
            treated.methane_rate_nm3_per_m3_d * 35.8,
        )
        self.assertAlmostEqual(
            treated.electricity_kwh_per_m3_d,
            treated.energy_mj_per_m3_d * 0.35 / 3.6,
        )

    def test_invalid_hrt_is_rejected(self):
        invalid_config = copy.deepcopy(MODEL_CONFIG)
        invalid_config["DIGESTER_BASELINE"]["hrt_d"] = 0.0
        with self.assertRaises(ValueError):
            Digester(build_feedstock(), NoPretreatment(), invalid_config)


if __name__ == "__main__":
    unittest.main()
