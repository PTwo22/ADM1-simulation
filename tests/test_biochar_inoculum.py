import math
import unittest
from copy import deepcopy
import subprocess
import numpy as np
import pandas as pd
import main
from AD.biochar_inoculum import evaluate_batch, kinetic_factors


class BiocharTests(unittest.TestCase):
    def setUp(self):
        self.cases = {s['id']: s for s in main.scenarios}

    def evaluate(self, case):
        f, p, d, config = main.run_scenario(case)
        row, curve = evaluate_batch(d, case, config, main.REACTOR_VOL)
        return f, d, config, row, curve

    def test_legacy_regression(self):
        old = pd.read_csv(__import__('io').StringIO(subprocess.check_output(
            ['git', 'show', 'HEAD:output/scenario_summary.csv'], text=True)))
        for _, expected in old.iterrows():
            sid = expected['Scenario ID']
            if sid not in {f'S{i}' for i in range(1, 14)}:
                continue
            _, _, d, c = main.run_scenario(self.cases[sid])
            practical = d.get_practical_yields(self.cases[sid]['olr'], c)
            for name, value in [('Treated Yield (Nm3/d)', d.y_ch4_treated),
                                ('Control Yield (Nm3/d)', d.y_ch4_control),
                                ('Specific Yield (L/kgVS)', practical['Specific_Yield_L_kgVS']),
                                ('Stability score', practical['Stability'])]:
                self.assertAlmostEqual(round(value, 3), expected[name], places=3)

    def test_s3_reference(self):
        _, d, c, row, curve = self.evaluate(self.cases['S3'])
        self.assertAlmostEqual(d.y_ch4_treated, .9683356212109677)
        self.assertAlmostEqual(d.get_practical_yields(2.5, c)['Specific_Yield_L_kgVS'], 285.05286578859705)
        self.assertEqual(kinetic_factors(0, 1), (1, 1))
        self.assertEqual(row['Inoculum VS (kg)'], 2.25)

    def test_oat(self):
        for sid in ('S21', 'S22', 'S23', 'S24'):
            changed = {k for k, v in self.cases[sid].items() if v != self.cases['S3'][k]}
            self.assertEqual(changed, {'id', 'description', 'si_ratio' if sid == 'S24' else 'biochar_g_L'})
        _, baseline, _, _, _ = self.evaluate(self.cases['S3'])
        f, d, _, row, _ = self.evaluate(self.cases['S24'])
        self.assertEqual(row['Inoculum VS (kg)'], f.m_vs / 2)
        self.assertEqual(d.y_ch4_treated, baseline.y_ch4_treated)
        self.assertEqual(d.modified_kinetics, baseline.modified_kinetics)
        self.assertLess(row['Inoculum capacity factor'], 1)

    def test_mass_energy_and_daily_balance(self):
        for sid in ('S3', 'S21', 'S22', 'S23', 'S24'):
            f, d, c, row, curve = self.evaluate(self.cases[sid])
            cumulative = curve['methane']
            self.assertEqual(cumulative[0], 0)
            self.assertTrue(np.isfinite(cumulative).all())
            self.assertTrue((np.diff(cumulative) >= 0).all())
            self.assertLessEqual(cumulative[-1], row['Treated charge potential (Nm3)'])
            self.assertLessEqual(row['Treated charge potential (Nm3)'], row['Theoretical charge BMP (Nm3)'])
            self.assertAlmostEqual(curve['daily'].sum(), cumulative[-1])
            self.assertAlmostEqual(row['Adjusted batch specific CH4 at 25d (L/kgVS)'], curve['adjusted'][-1]*1000/f.m_vs)
            self.assertAlmostEqual(row['Batch gross CH4 energy at 25d (MJ)'], cumulative[-1]*35.8)

    def test_invalid_inputs(self):
        for dose, ratio in ((-1, 1), (0, 0), (0, -1), (math.nan, 1), (0, math.inf)):
            with self.assertRaises(ValueError):
                kinetic_factors(dose, ratio)

    def test_csv_matches_calculations(self):
        summary = pd.read_csv('output/biochar_inoculum_summary.csv')
        series = pd.read_csv('output/biochar_inoculum_timeseries.csv')
        reference = summary.loc[summary['Scenario ID'] == 'S3', 'Adjusted batch specific CH4 at 25d (L/kgVS)'].iloc[0]
        for _, row in summary.iterrows():
            sid = row['Scenario ID']
            _, _, _, expected, _ = self.evaluate(self.cases[sid])
            self.assertAlmostEqual(row['Adjusted batch specific CH4 at 25d (L/kgVS)'], expected['Adjusted batch specific CH4 at 25d (L/kgVS)'])
            self.assertAlmostEqual(row['Adjusted batch yield change vs S3 (%)'], (row['Adjusted batch specific CH4 at 25d (L/kgVS)']/reference-1)*100)
            saved = series[series['Scenario ID'] == sid]
            self.assertAlmostEqual(saved['Daily CH4 (Nm3/day)'].sum(), row['Batch cumulative CH4 at 25d (Nm3)'])


if __name__ == '__main__':
    unittest.main()
