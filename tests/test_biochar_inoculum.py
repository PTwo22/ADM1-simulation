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
        np.testing.assert_array_equal(summary['Project screening yield (L/kgVS)'].round(3), summary['Specific Yield (L/kgVS)'])
        np.testing.assert_allclose(summary['Project screening change vs S3 (%)'], 0)
        by_id = summary.set_index('Scenario ID')
        for sid in ('S3','S21','S22','S23','S24'):
            _, _, d, config = main.run_scenario(self.cases[sid])
            expected = d.get_practical_yields(self.cases[sid]['olr'], config)['Specific_Yield_L_kgVS']
            self.assertAlmostEqual(by_id.loc[sid,'Project screening yield (L/kgVS)'],expected,places=10)
            saved = series[(series['Scenario ID']==sid) & (series['Day']==10)].iloc[0]
            self.assertAlmostEqual(by_id.loc[sid,'Adjusted batch specific CH4 at 10d (L/kgVS)'],saved['Adjusted cumulative CH4 (Nm3)']*1000/d.feedstock.m_vs)
        self.assertGreater(by_id.loc['S21','Adjusted batch specific CH4 at 10d (L/kgVS)'],by_id.loc['S3','Adjusted batch specific CH4 at 10d (L/kgVS)'])

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


class ConsistencyReviewTests(unittest.TestCase):
    def test_scenario_settings_and_single_kinetic_application(self):
        expected = {'S3':(0,1),'S21':(5,1),'S22':(10,1),'S23':(15,1),'S24':(0,.33)}
        for case in main.scenarios:
            if case['id'] not in expected: continue
            self.assertEqual((case['biochar_g_L'],case['si_ratio']),expected[case['id']])
            feed,_,dig,config=main.run_scenario(case)
            row,curve=evaluate_batch(dig,case,config)
            b,i=kinetic_factors(case['biochar_g_L'],case['si_ratio'])
            self.assertAlmostEqual(row['Apparent conversion rate (1/day)'],dig.modified_kinetics['k_hyd_modified']*b*i)
            self.assertEqual(row['Batch lag (days)'],dig.modified_kinetics['lag_modified'])
            self.assertEqual(row['Treated charge potential (Nm3)'],dig.y_ch4_treated)
            self.assertAlmostEqual(row['Inoculum VS (kg)']*case['si_ratio'],feed.m_vs)

    def test_exported_time_yield_units_and_percentages(self):
        root='output/s21_s24/'
        summary=pd.read_csv(root+'biochar_inoculum_summary.csv').set_index('Scenario ID')
        series=pd.read_csv(root+'supporting/biochar_inoculum_timeseries.csv')
        reference=summary.loc['S3']
        for sid,row in summary.iterrows():
            data=series[series['Scenario ID']==sid].set_index('Day')
            self.assertEqual(row['Substrate charge VS (kg)'],2.25)
            np.testing.assert_allclose(data['Adjusted batch yield (L/kgVS)'],1000*data['Adjusted cumulative CH4 (Nm3)']/data['Substrate VS (kg)'])
            self.assertAlmostEqual(data['Adjusted daily CH4 (Nm3/day)'].sum(),data.loc[25,'Adjusted cumulative CH4 (Nm3)'])
            for day,change in ((10,'Adjusted day10 batch yield change vs S3 (%)'),(25,'Adjusted batch yield change vs S3 (%)')):
                name=f'Adjusted batch specific CH4 at {day}d (L/kgVS)'
                raw=f'Batch specific CH4 at {day}d (L/kgVS)'
                self.assertAlmostEqual(row[name],data.loc[day,'Adjusted batch yield (L/kgVS)'])
                self.assertAlmostEqual(row[raw],data.loc[day,'Unpenalised batch yield (L/kgVS)'])
                self.assertAlmostEqual(row[change],(row[name]/reference[name]-1)*100)
            screen='Project screening yield (L/kgVS)'
            self.assertAlmostEqual(row['Project screening change vs S3 (%)'],(row[screen]/reference[screen]-1)*100)


class PresentationFormattingTests(unittest.TestCase):
    def test_one_decimal_presentation_preserves_raw_references(self):
        root='output/s21_s24/'
        raw=pd.read_csv(root+'biochar_inoculum_summary.csv').set_index('Scenario ID')
        shown=pd.read_csv(root+'biochar_inoculum_summary_presentation.csv',dtype=str).set_index('Scenario ID')
        self.assertEqual(shown.loc['S24','S:I (gVS/gVS)'],'0.33')
        for day in (10,25):
            col=f'Adjusted batch specific CH4 at {day}d (L/kgVS)'
            for sid,row in raw.iterrows():
                self.assertEqual(shown.loc[sid,f'Day-{day} adjusted yield (L CH4/kg substrate VS)'],f'{row[col]:.{3}f}')
                change=(row[col]/raw.loc['S3',col]-1)*100
                self.assertEqual(shown.loc[sid,f'Day-{day} change vs S3 (%)'],f'{change:+.{3}f}')
        self.assertGreater(raw.loc['S3','Adjusted batch specific CH4 at 25d (L/kgVS)'],316.23)


class BaselineDefinitionTests(unittest.TestCase):
    def test_legacy_and_batch_metrics_have_different_numerators_and_bases(self):
        case=next(s for s in main.scenarios if s['id']=='S3')
        feed,_,dig,config=main.run_scenario(case)
        row,curve=evaluate_batch(dig,case,config)
        practical=dig.get_practical_yields(case['olr'],config)
        full_adjusted=dig.y_ch4_treated*practical['Stability']
        screening=full_adjusted*1000/case['olr']
        batch=curve['adjusted'][-1]*1000/feed.m_vs
        self.assertAlmostEqual(row['Project screening yield (L/kgVS)'],screening)
        self.assertAlmostEqual(row['Adjusted batch specific CH4 at 25d (L/kgVS)'],batch)
        completion=curve['methane'][-1]/dig.y_ch4_treated
        self.assertAlmostEqual(batch/screening,case['olr']/feed.m_vs*completion)
        self.assertNotEqual(screening,batch)


class FinalScenarioPropagationTests(unittest.TestCase):
    def test_inputs_reach_kinetic_function_and_do_not_mutate_reference(self):
        from unittest.mock import patch
        expected={'S3':(0,1),'S21':(5,1),'S22':(10,1),'S23':(15,1),'S24':(0,.33)}
        cases={case['id']:case for case in main.scenarios if case['id'] in expected}
        reference=deepcopy(cases['S3'])
        for sid,(dose,ratio) in expected.items():
            feed,_,dig,config=main.run_scenario(cases[sid])
            original=deepcopy(dig.modified_kinetics)
            with patch('AD.biochar_inoculum.kinetic_factors',wraps=kinetic_factors) as spy:
                row,curve=evaluate_batch(dig,cases[sid],config)
            self.assertEqual(spy.call_count,1)
            self.assertEqual(spy.call_args.args[:2],(dose,ratio))
            self.assertEqual(row['Biochar (g/L)'],dose)
            self.assertAlmostEqual(row['Inoculum VS (kg)'],feed.m_vs/ratio)
            self.assertEqual(dig.modified_kinetics,original)
        self.assertEqual(cases['S3'],reference)

    def test_kinetic_changes_survive_simulation_and_export(self):
        saved=pd.read_csv('output/s21_s24/biochar_inoculum_summary.csv').set_index('Scenario ID')
        trajectories=[];rates=[]
        for case in main.scenarios:
            if case['id'] not in ('S3','S21','S22','S23','S24'):continue
            feed,_,dig,config=main.run_scenario(case)
            row,curve=evaluate_batch(dig,case,config)
            rates.append(row['Apparent conversion rate (1/day)'])
            trajectories.append(curve['adjusted'])
            self.assertAlmostEqual(row['Empirical Gompertz Rmax (Nm3/day)'],dig.y_ch4_treated*row['Apparent conversion rate (1/day)']/np.e)
            self.assertAlmostEqual(saved.loc[case['id'],'Apparent conversion rate (1/day)'],row['Apparent conversion rate (1/day)'])
            for day in (10,25):
                col=f'Adjusted batch specific CH4 at {day}d (L/kgVS)'
                self.assertAlmostEqual(saved.loc[case['id'],col],curve['adjusted'][day]*1000/feed.m_vs)
            asymptote=finite_charge_curve(dig.y_ch4_treated,row['Apparent conversion rate (1/day)'],row['Batch lag (days)'],[0,1000])[-1]
            self.assertAlmostEqual(asymptote,dig.y_ch4_treated)
        # These are assertions about current configured equations, not a universal dose law.
        self.assertEqual(len(set(rates)),5)
        for trajectory in trajectories[1:]:
            self.assertFalse(np.allclose(trajectory,trajectories[0],rtol=0,atol=1e-12))
            self.assertNotAlmostEqual(trajectory[10],trajectories[0][10],places=10)
            self.assertNotAlmostEqual(trajectory[25],trajectories[0][25],places=10)

    def test_remove_only_assigned_response_returns_reference_kinetics(self):
        cases={case['id']:case for case in main.scenarios}
        _,_,baseline,config=main.run_scenario(cases['S3'])
        reference,reference_curve=evaluate_batch(baseline,cases['S3'],config)
        for sid in ('S21','S22','S23','S24'):
            _,_,dig,cfg=main.run_scenario(cases[sid])
            opt={'biochar_response_enabled':False} if sid!='S24' else {'inoculum_response_enabled':False}
            row,curve=evaluate_batch(dig,cases[sid],cfg,options=opt)
            np.testing.assert_allclose(curve['adjusted'],reference_curve['adjusted'],rtol=0,atol=1e-14)
            self.assertAlmostEqual(row['Project screening yield (L/kgVS)'],reference['Project screening yield (L/kgVS)'])

    def test_current_reference_matches_independently_loaded_original_s3(self):
        ns={'__name__':'historical_screening_regression'}
        for name in ('data/config.py','AD/feedstock.py','pretreatment/pretreatment.py','AD/digester.py'):
            source=subprocess.check_output(['git','show','e241207:'+name]).decode('utf-8')
            exec(compile(source.replace('from data.config import *',''),'e241207:'+name,'exec'),ns)
        feed=ns['Feedstock'](10,.25,.9,{'FW':1},{'FW':ns['FW_FRACTIONS']})
        treatment=ns['Pretreatment'](30,5.5,24,{i:60 for i in ('carb','protein','lipid','inert')},ns['PRETREATMENT_CONFIG'],ns['FPSI_WEIGHTS'])
        cfg={key:ns[key] for key in ('DIGESTER_CALIBRATION','DIGESTER_BASELINES','BMP_CONSTANTS','RISK_THRESHOLDS','STABILITY_WEIGHTS','DIGESTER_CONDITIONS')}
        original=ns['Digester'](feed,treatment,cfg)
        case=next(c for c in main.scenarios if c['id']=='S3')
        current_feed,current_pre,current,c=main.run_scenario(case)
        self.assertEqual(original.y_ch4_treated,current.y_ch4_treated)
        self.assertEqual(treatment.A,current_pre.A)
        self.assertEqual(feed.m_vs,current_feed.m_vs)
        self.assertEqual(original.get_practical_yields(2.5,cfg),current.get_practical_yields(case['olr'],c))
        np.testing.assert_array_equal(original.calculate_gompertz_curve(np.arange(26)),current.calculate_gompertz_curve(np.arange(26)))


class IncrementalYieldPresentationTests(unittest.TestCase):
    def test_increment_uses_unrounded_day25_values(self):
        root='output/s21_s24/'
        raw=pd.read_csv(root+'biochar_inoculum_summary.csv').set_index('Scenario ID')
        shown=pd.read_csv(root+'biochar_inoculum_summary_presentation.csv',dtype=str).set_index('Scenario ID')
        metric='Adjusted batch specific CH4 at 25d (L/kgVS)'
        reference=raw.loc['S3',metric]
        for sid,row in raw.iterrows():
            expected=row[metric]-reference
            self.assertEqual(shown.loc[sid,'Day-25 incremental yield vs S3 (L CH4/kg substrate VS)'],f'{expected:.3f}')
            self.assertEqual(shown.loc[sid,'Day-25 change vs S3 (%)'],f'{expected/reference*100:+.3f}')


class LegacyNominalDay25Tests(unittest.TestCase):
    def test_derived_nominal_metric_preserves_all_original_columns(self):
        from utils.biochar_visualisations import add_day25_nominal_comparison,NOMINAL25,NOMINAL25_CHANGE
        frame=pd.read_csv('output/s21_s24/biochar_inoculum_summary.csv')
        original=frame.drop(columns=[NOMINAL25,NOMINAL25_CHANGE])
        result=add_day25_nominal_comparison(original)
        pd.testing.assert_frame_equal(original,result[original.columns])
        denominator=frame['Screening nominal loading (kgVS/m3/day)']
        self.assertTrue((denominator==2.5).all())
        expected=1000*frame['Adjusted batch cumulative CH4 at 25d (Nm3)']/denominator
        np.testing.assert_allclose(result[NOMINAL25],expected,rtol=0,atol=1e-12)
        np.testing.assert_allclose(frame[NOMINAL25],expected,rtol=0,atol=1e-12)
        reference=expected[frame['Scenario ID']=='S3'].iloc[0]
        np.testing.assert_allclose(result[NOMINAL25_CHANGE],(expected/reference-1)*100,atol=1e-12)
        actual=frame['Adjusted batch specific CH4 at 25d (L/kgVS)']
        np.testing.assert_allclose(expected,actual*frame['Substrate charge VS (kg)']/denominator)
        self.assertNotEqual(reference,frame.loc[frame['Scenario ID']=='S3','Project screening yield (L/kgVS)'].iloc[0])

    def test_nominal_presentation_is_rounded_after_calculation(self):
        from utils.biochar_visualisations import NOMINAL25,NOMINAL25_CHANGE
        root='output/s21_s24/'
        raw=pd.read_csv(root+'biochar_inoculum_summary.csv').set_index('Scenario ID')
        shown=pd.read_csv(root+'biochar_inoculum_summary_presentation.csv',dtype=str).set_index('Scenario ID')
        for sid,row in raw.iterrows():
            self.assertEqual(shown.loc[sid,'Day-25 legacy nominal-loading screening metric'],f'{row[NOMINAL25]:.3f}')
            self.assertEqual(shown.loc[sid,'Day-25 legacy nominal-loading change vs S3 (%)'],f'{row[NOMINAL25_CHANGE]:+.3f}')


class BothTimeLegacyConventionTests(unittest.TestCase):
    def test_both_times_use_independent_volumes_and_same_denominator(self):
        from utils.biochar_visualisations import add_day25_nominal_comparison,NOMINAL10,NOMINAL10_CHANGE,NOMINAL25,NOMINAL25_CHANGE
        raw=pd.read_csv('output/s21_s24/biochar_inoculum_summary.csv')
        derived=add_day25_nominal_comparison(raw)
        self.assertTrue((raw['Screening nominal loading (kgVS/m3/day)']==2.5).all())
        for day,metric,change in ((10,NOMINAL10,NOMINAL10_CHANGE),(25,NOMINAL25,NOMINAL25_CHANGE)):
            actual=1000*raw[f'Adjusted batch cumulative CH4 at {day}d (Nm3)']/raw['Screening nominal loading (kgVS/m3/day)']
            np.testing.assert_allclose(derived[metric],actual,rtol=0,atol=1e-12)
            np.testing.assert_allclose(raw[metric],actual,rtol=0,atol=1e-12)
            ref=actual[raw['Scenario ID']=='S3'].iloc[0]
            np.testing.assert_allclose(derived[change],(actual/ref-1)*100,atol=1e-12)
        self.assertTrue((derived[NOMINAL10]<derived[NOMINAL25]).all())

    def test_main_graph_layout_and_metric_precision(self):
        from pathlib import Path
        expected={'biochar_inoculum_gompertz_curve.png','s21_s24_day10_legacy_nominal_comparison.png','s21_s24_day25_legacy_nominal_comparison.png'}
        self.assertEqual({p.name for p in Path('output/s21_s24').glob('*.png')},expected)
        raw=pd.read_csv('output/s21_s24/biochar_inoculum_summary.csv').set_index('Scenario ID')
        shown=pd.read_csv('output/s21_s24/biochar_inoculum_summary_presentation.csv',dtype=str).set_index('Scenario ID')
        for day in (10,25):
            values=1000*raw[f'Adjusted batch cumulative CH4 at {day}d (Nm3)']/raw['Screening nominal loading (kgVS/m3/day)']
            for sid,value in values.items():
                self.assertEqual(shown.loc[sid,f'Day-{day} legacy nominal-loading screening metric'],f'{value:.3f}')
                self.assertEqual(shown.loc[sid,f'Day-{day} legacy nominal-loading change vs S3 (%)'],f'{(value/values.loc["S3"]-1)*100:+.3f}')


class S24SweepTests(unittest.TestCase):
    def test_sweep_oat_mass_metrics_and_saved_results(self):
        from utils.s24_sensitivity import calculate_sweep, RATIOS
        base=deepcopy(next(s for s in main.scenarios if s['id']=='S3'))
        original=deepcopy(base)
        def checked_run(case):
            self.assertEqual({k for k in base if case[k]!=base[k]},set() if case['si_ratio']==1 else {'si_ratio'})
            return main.run_scenario(case)
        frame=calculate_sweep(base,checked_run,main.REACTOR_VOL)
        self.assertEqual(base,original)
        self.assertEqual(tuple(frame['S:I (gVS/gVS)']),RATIOS)
        np.testing.assert_allclose(frame['Inoculum VS (kg)'],2.25/np.array(RATIOS))
        self.assertTrue((frame['Project screening yield (L/kgVS)']==frame.iloc[0]['Project screening yield (L/kgVS)']).all())
        saved=pd.read_csv('output/s21_s24/supporting/s24_ratio_sensitivity.csv')
        pd.testing.assert_frame_equal(frame,saved,check_exact=False,rtol=1e-13,atol=1e-13)
        for day in (10,25):
            metric=frame[f'Day-{day} legacy comparison metric']
            ref=metric.iloc[2]
            np.testing.assert_allclose(metric,1000*frame[f'Adjusted batch cumulative CH4 at {day}d (Nm3)']/2.5)
            np.testing.assert_allclose(frame[f'Day-{day} change vs S3 (%)'],(metric/ref-1)*100)
            raw=pd.read_csv('output/s21_s24/biochar_inoculum_summary.csv').set_index('Scenario ID')
            self.assertAlmostEqual(frame.iloc[2][f'Adjusted batch cumulative CH4 at {day}d (Nm3)'],raw.loc['S3',f'Adjusted batch cumulative CH4 at {day}d (Nm3)'])
        self.assertTrue(np.isfinite(frame['Apparent conversion rate (1/day)']).all())
        self.assertTrue((frame['Apparent conversion rate (1/day)']>0).all())


class TeamScreeningTests(unittest.TestCase):
    def test_independent_original_screening_and_percentages(self):
        from utils.biochar_visualisations import team_screening_comparison
        saved=pd.read_csv('output/s21_s24/biochar_inoculum_summary.csv')
        frame=team_screening_comparison(saved).set_index('Scenario ID')
        reference=None
        for sid in ('S3','S21','S22','S23','S24'):
            case=next(s for s in main.scenarios if s['id']==sid)
            _,_,digester,config=main.run_scenario(case)
            practical=digester.get_practical_yields(case['olr'],config)
            value=practical['Specific_Yield_L_kgVS']
            self.assertEqual(case['olr'],2.5)
            self.assertAlmostEqual(value,1000*digester.y_ch4_treated*practical['Stability']/case['olr'],places=12)
            self.assertAlmostEqual(frame.loc[sid,'Project screening yield (L/kgVS)'],value,places=12)
            if sid=='S3':
                reference=value
                self.assertAlmostEqual(value,285.05286578859705,places=10)
            self.assertAlmostEqual(frame.loc[sid,'Team screening change vs S3 (%)'],(value/reference-1)*100,places=12)
        self.assertTrue((frame['Team screening change vs S3 (%)']==0).all())


if __name__ == '__main__':
    unittest.main()
