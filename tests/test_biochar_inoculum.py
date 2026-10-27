import math
import unittest
from copy import deepcopy
import subprocess
import numpy as np
import pandas as pd
import main
from AD.biochar_inoculum import (evaluate_batch, kinetic_factors, additive_response,
    additive_inhibition, additive_modified_coefficient, inoculum_capacity, finite_charge_curve)
from data.biochar_config import OFFICIAL_S24_SI
from utils.biochar_verification import sensitivity_analysis, parameter_table, literature_comparison


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
        self.assertEqual(row['Inoculum VS (kg)'], f.m_vs / OFFICIAL_S24_SI)
        self.assertEqual(d.y_ch4_treated, baseline.y_ch4_treated)
        self.assertEqual(d.modified_kinetics, baseline.modified_kinetics)
        self.assertGreater(row['Inoculum capacity factor'], 1)

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
        summary = pd.read_csv('output/s21_s24/biochar_inoculum_summary.csv')
        series = pd.read_csv('output/s21_s24/supporting/biochar_inoculum_timeseries.csv')
        reference = summary.loc[summary['Scenario ID'] == 'S3', 'Adjusted batch specific CH4 at 25d (L/kgVS)'].iloc[0]
        for _, row in summary.iterrows():
            sid = row['Scenario ID']
            _, _, _, expected, _ = self.evaluate(self.cases[sid])
            self.assertAlmostEqual(row['Adjusted batch specific CH4 at 25d (L/kgVS)'], expected['Adjusted batch specific CH4 at 25d (L/kgVS)'])
            self.assertAlmostEqual(row['Adjusted batch yield change vs S3 (%)'], (row['Adjusted batch specific CH4 at 25d (L/kgVS)']/reference-1)*100)
            saved = series[series['Scenario ID'] == sid]
            self.assertAlmostEqual(saved['Daily CH4 (Nm3/day)'].sum(), row['Batch cumulative CH4 at 25d (Nm3)'])


class EquationVerificationTests(unittest.TestCase):
    setUp = BiocharTests.setUp
    evaluate = BiocharTests.evaluate
    def test_equation_84_analytic_and_bounds(self):
        self.assertEqual(additive_response(0,5,1),0)
        self.assertAlmostEqual(additive_response(5,5,2),.5)
        self.assertAlmostEqual(additive_response(10,5,2),.8)
        self.assertAlmostEqual(additive_response(5000,5000,2),.5)
        self.assertEqual(additive_response(1e300,5,2),1)
        for c in np.logspace(-200,200,25):
            self.assertTrue(0 <= additive_response(c,5,2) <= 1)

    def test_equation_85_algebra(self):
        self.assertEqual(additive_modified_coefficient(8,.5,.5,.8),8)
        self.assertEqual(additive_modified_coefficient(8,.5,0,1),8)
        self.assertEqual(additive_modified_coefficient(8,.5,1,0),0)
        with self.assertRaises(ValueError): additive_modified_coefficient(8,.5,1.1,1)

    def test_equation_86_optional_and_high_dose(self):
        self.assertEqual(additive_inhibition(30,30,2),1)
        self.assertEqual(additive_inhibition(0,30,2,True),1)
        self.assertAlmostEqual(additive_inhibition(30,30,2,True),.5)
        self.assertEqual(additive_inhibition(1e300,30,2,True),0)
        self.assertAlmostEqual(kinetic_factors(10,1)[0],1+.5*10/15)
        self.assertLess(kinetic_factors(10,1,{'inhibition_enabled':True})[0],kinetic_factors(10,1)[0])

    def test_parameter_rejection(self):
        for key,value in [('half_saturation_g_L',0),('response_exponent',0),
                          ('inhibition_scale_g_L',-1),('inhibition_exponent',math.nan),('benefit_amplitude',-1)]:
            with self.assertRaises(ValueError): kinetic_factors(5,1,{key:value})
        with self.assertRaises(ValueError): inoculum_capacity(1,0)

    def test_equation_89_mass_units_and_sensitivity_case(self):
        f,_,_,row,_=self.evaluate(self.cases['S24'])
        self.assertEqual(self.cases['S24']['si_ratio'],.33)
        self.assertAlmostEqual(row['Inoculum VS (kg)']*.33,f.m_vs)
        case=deepcopy(self.cases['S3']);case['si_ratio']=2
        _,_,_,sensitivity,_=self.evaluate(case)
        self.assertAlmostEqual(sensitivity['Inoculum VS (kg)'],1.125)
        for ratio in (math.nan,math.inf,0,-1):
            with self.assertRaises(ValueError): f.calculate_inoculum_mass(ratio)
        case=deepcopy(self.cases['S3']);case['biochar_g_L']=5
        _,_,_,dose,_=self.evaluate(case)
        self.assertEqual(dose['Biochar mass (kg)'],5) # g/L * m3 = kg
        self.assertEqual(sum(f.component_masses.values()),f.m_vs)

    def test_no_response_model_and_fixed_lag(self):
        baseline=self.evaluate(self.cases['S3'])[3]
        for sid in ('S21','S22','S23','S24'):
            _,_,d,c=main.run_scenario(self.cases[sid])
            row,_=evaluate_batch(d,self.cases[sid],c,options={'biochar_response_enabled':False,'inoculum_response_enabled':False})
            self.assertAlmostEqual(row['Adjusted batch specific CH4 at 25d (L/kgVS)'],baseline['Adjusted batch specific CH4 at 25d (L/kgVS)'])
            self.assertEqual(row['Batch lag (days)'],baseline['Batch lag (days)'])

    def test_s3_batch_regression_and_curve_limiting(self):
        _,_,d,c=main.run_scenario(self.cases['S3'])
        row,curve=evaluate_batch(d,self.cases['S3'],c)
        old=pd.read_csv('output/s21_s24/supporting/s21_s24_original/biochar_inoculum_summary.csv').set_index('Scenario ID')
        self.assertAlmostEqual(row['Adjusted batch specific CH4 at 25d (L/kgVS)'],old.loc['S3','Adjusted batch specific CH4 at 25d (L/kgVS)'],places=10)
        for potential,rate,lag in ((0,1,2),(1,0,2),(1,1e-12,2),(1,1e6,2)):
            curve=finite_charge_curve(potential,rate,lag,np.arange(26))
            self.assertTrue(np.isfinite(curve).all())
            self.assertTrue((np.diff(curve)>=0).all())
            self.assertTrue((curve<=potential).all())
            self.assertEqual(curve[0],0)

    def test_reproducible_sensitivity_and_exports(self):
        frame=sensitivity_analysis(self.cases['S3'],main.run_scenario,main.REACTOR_VOL)
        repeat=sensitivity_analysis(self.cases['S3'],main.run_scenario,main.REACTOR_VOL)
        pd.testing.assert_frame_equal(frame,repeat)
        saved=pd.read_csv('output/s21_s24/supporting/s21_s24_parameter_sensitivity.csv')
        np.testing.assert_allclose(frame['Adjusted batch specific CH4 at 25d (L/kgVS)'],saved['Adjusted batch specific CH4 at 25d (L/kgVS)'])
        self.assertTrue((frame['Adjusted batch specific CH4 at 25d (L/kgVS)']>=0).all())
        report=parameter_table()
        self.assertEqual(report.loc[report['Symbol']=='alpha_add','Verification status'].iloc[0],'Unverified')
        comparison=literature_comparison(pd.read_csv('output/s21_s24/biochar_inoculum_summary.csv'))
        self.assertFalse(comparison['Directly comparable'].any())
        self.assertTrue(comparison['RMSE'].isna().all())


if __name__ == '__main__':
    unittest.main()
