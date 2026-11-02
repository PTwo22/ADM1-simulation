"""Reproducible equation audit and deterministic diagnostic sensitivity.
Unverified coefficients get diagnostic perturbations, NOT literature confidence ranges.
"""
from copy import deepcopy
from pathlib import Path
import numpy as np
import pandas as pd
from AD.biochar_inoculum import evaluate_batch, finite_charge_curve
from data.biochar_config import BIOCHAR_MODEL, EXPLORATORY_OPTIONS, SI_LEVELS

YIELD = 'Adjusted batch specific CH4 at 25d (L/kgVS)'
FORMULA = 'Complete Formula Notation Scenario Literature Data - 6102026.pdf'
FEEDBACK = 'Bita feedback after our meeting in week 9.pdf'


def parameter_table():
    # Existing values refer to the archived implementation before this review.
    items = [
        ('Biochar dose', 'C_add', '0,5,10,15', '0,5,10,15', 'g/L working volume', '5,10,15', FORMULA+' p25; feedback p5; Ovi 2022 DOI 10.1016/j.fuel.2022.123188', '84-86', 'Literature-supported design levels', 'Verified design; not calibrated response', 'Keep same RHB550 identity'),
        ('Biochar identity', 'material', 'RHB550', 'RHB550', 'rice-husk biochar at 550 C', 'RHB550', FORMULA+' p25; Ovi 2022 institutional abstract', '84-86', 'Material identity anchor only; batch properties unavailable', 'Partially verified', 'Measure surface area, conductivity, ash, pH and adsorption'),
        ('Benefit coefficient', 'alpha_add', '0.5', '0.5', 'dimensionless', 'Not supplied', FORMULA+' p20 Eq85', '85', 'Exploratory magnitude only', 'Unverified', 'Retain only as explicit empirical option; calibrate'),
        ('Half-response concentration', 'K_add', '5', '5', 'g/L', 'Not supplied', FORMULA+' p20 Eq84', '84', 'Not inferable from one experimental dose response', 'Unverified', 'Calibrate; diagnostic +/-20% is not a literature range'),
        ('Hill shape', 'n', '1 implicit', '1 explicit', 'dimensionless', 'Not supplied', FORMULA+' p20 Eq84', '84', 'Assumed shape', 'Unverified', 'Fit dose series'),
        ('Inhibition concentration', 'K_I_add', '30', '30 inactive by default', 'g/L', 'Not supplied', FORMULA+' p20 Eq86', '86', 'No matched high-dose inhibition data', 'Unverified', 'Disable by default; exploratory sensitivity only'),
        ('Inhibition shape', 'm', '2 implicit', '2 explicit, inactive', 'dimensionless', 'Not supplied', FORMULA+' p20 Eq86', '86', 'Assumed attenuation', 'Unverified', 'Fit only if evidence supports inhibition'),
        ('Inhibition switch', 'enabled', 'Always on', 'False', 'boolean', 'Omit without evidence', FORMULA+' p20 Eq86 recommendation', '86', 'Evidence guard', 'Consistent with recommendation', 'Enable only explicitly'),
        ('S3 inoculum baseline', 'SI_ref', '1', '1', 'g substrate VS/g inoculum VS', 'No assigned S3 baseline', FORMULA+' p22 Eq89; feedback pp2-4 OAT', '89', 'Explicit modelling baseline, not measured', 'Unverified assumption', 'Preserve for regression; measure inoculum activity'),
        ('Official S24', 'SI_24', '2', '0.33', 'g substrate VS/g inoculum VS', '0.33,0.5,1,2,4', FORMULA+' pp22,25; Kawai 2014 DOI 10.1016/j.biortech.2014.01.018', '89', 'Literature initial anchor; not universal optimum', 'Verified scenario recommendation', 'Retain 2 as additional sensitivity'),
        ('Inoculum mass', 'M_I', 'M_S/SI', 'M_S/SI', 'kg VS', 'Mass-ratio identity', FORMULA+' p22 Eq89', '89', 'Algebraic mass relation', 'Verified algebra and units', 'No independent yield prediction'),
        ('Inoculum half-capacity', 'h', '1 implicit', '1 explicit', 'relative biomass dimensionless', 'Not supplied', 'Author-selected; not in supplied PDFs', 'Empirical fI=(1+h)/(1+h*SI/SI_ref)', 'Unverified saturating response', 'Unverified', 'Optional proxy; fit or disable'),
        ('Additional lag scaling', 'lambda/fB/fI', 'Enabled', 'Removed', 'days', 'Not supplied', 'No supporting relation in Eq84-86/89', 'None', 'Double kinetic coupling unsupported', 'Unsupported', 'Keep inherited S3 lag fixed'),
        ('Apparent conversion rate', 'k_app', 'Inherited k_hyd times fB*fI', 'Same empirical rate mapping; fixed lag', '1/day', 'No matched fitted coefficient', 'Molecules pp20-21 Eqs40-41; project Digester', 'Gompertz proxy only', 'Empirical Rmax=P*k_app/e, NOT ADM1 k_meth', 'Uncalibrated', 'Do not transfer ADM1 constants into this proxy'),
        ('Observation duration', 't', '25', '25', 'days', 'S3 HRT25 reference; manuscript curves30', FORMULA+' p25; Molecules p8 Fig4', '31 / batch curve', 'Fixed-charge window is not a CSTR HRT balance', 'Verified scenario convention', 'Compare only matched duration'),
        ('Substrate VS', 'M_S', '2.25', '2.25', 'kg VS', '10 kg wet;TS.25;VS/TS.9', 'Molecules p16 section4.3', '1,2,89', '10*.25*.9', 'Verified algebra/reference basis', 'Batch yield uses actual VS'),
        ('Nominal OLR denominator', 'OLR', '2.5 vs actual2.25', 'Legacy retained', 'kg VS/m3/day', 'S3 nominal2.5', FORMULA+' p25; main.py', 'Legacy specific yield', 'Known legacy inconsistency', 'Unresolved legacy limitation', 'Do not use OLR as batch mass; preserve S3 legacy output'),
        ('Heuristic stability', 's', '0.735935091988353', 'unchanged', 'dimensionless', 'No validated correction', 'Molecules pp15-16,19; formula Eq25', '25,26', 'Screening multiplier; no mechanistic inoculum/biochar inhibition', 'Heuristic uncalibrated', 'Report adjusted and unpenalised outputs separately'),
        ('Reaction temperature', 'T_AD', 'Not used in batch kinetics', 'Not used', 'C', 'PeerJ37+/-0.1; Ovi mesophilic', 'PeerJ p3 Table1; Ovi abstract', 'Not implemented here', 'Pretreatment30 C is not AD temperature', 'Not verified for comparative validation', 'Measure/set for matched experiments'),
    ]
    return pd.DataFrame(items, columns=['Parameter','Symbol','Existing code value','Current value','Units','Literature value or range','Exact document and reference','Equation','Scientific justification','Verification status','Recommended action'])


def sensitivity_analysis(base, run_scenario, volume):
    rows = []
    def evaluate(case, parameters=None, options=None):
        _, _, d, c = run_scenario(case)
        return evaluate_batch(d, case, c, volume, parameters, options)
    probe = deepcopy(base); probe['biochar_g_L'] = 10.0
    _, _, d, _ = run_scenario(base)
    fixed_lag = d.modified_kinetics['lag_modified']
    for parameter, levels, target, source, enabled in (
        ('Biochar concentration', (0,5,10,15), 'dose', 'Formula p25 / Ovi study design', False),
        ('S:I', SI_LEVELS, 'ratio', 'Formula p25 / Kawai study design', False),
        ('half_saturation_g_L', (4,5,6), 'biochar', 'Unverified legacy coefficient +/-20% diagnostic only', False),
        ('benefit_amplitude', (.4,.5,.6), 'biochar', 'Unverified legacy coefficient +/-20% diagnostic only', False),
        ('response_exponent', (.8,1,1.2), 'biochar', 'Unverified shape +/-20% diagnostic only', False),
        ('inhibition_scale_g_L', (24,30,36), 'biochar', 'Unverified inhibition +/-20%; conditional inhibition-on diagnostic', True),
        ('inhibition_exponent', (1.6,2,2.4), 'biochar', 'Unverified inhibition shape +/-20%; conditional diagnostic', True),
        ('empirical_rate_scale', (.8,1,1.2), 'option', 'Uncalibrated Gompertz rate +/-20%; NOT methanogenic k_meth sensitivity', False),
        ('inoculum_half_capacity', (.8,1,1.2), 'inoculum', 'Unverified capacity +/-20% at S:I2 diagnostic only', False),
    ):
        case = deepcopy(base if target in ('ratio','dose','inoculum') else probe)
        if target == 'inoculum': case['si_ratio'] = 2.0
        params = {'inhibition_enabled': enabled}
        reference, _ = evaluate(case, params)
        for value in levels:
            variant = deepcopy(case); pp = dict(params); opt = {}
            if target == 'dose': variant['biochar_g_L'] = value
            elif target == 'ratio': variant['si_ratio'] = value
            elif target in ('option','inoculum'): opt[parameter] = value
            else: pp[parameter] = value
            row, curve = evaluate(variant, pp, opt)
            rows.append({'Parameter':parameter,'Value':value,'Source/range status':source,
                         'Inhibition enabled':enabled, 'Probe biochar (g/L)':variant['biochar_g_L'],
                         'Probe S:I':variant['si_ratio'], YIELD:row[YIELD],
                         'Change from probe default (%)':(row[YIELD]/reference[YIELD]-1)*100,
                         'Day10 adjusted yield (L/kgVS)':curve['adjusted'][10]*1000/row['Substrate charge VS (kg)'],
                         'Batch lag (days)':fixed_lag})
    return pd.DataFrame(rows)


def literature_comparison(selected):
    by_id = selected.set_index('Scenario ID')
    records = []
    for sid, study, observed, uncertainty, basis, source, reason in (
        ('S3','Ovi control',333.32,14.9,'mL CH4/g VS_added',FORMULA+' p25; feedback p5; Ovi2022 abstract DOI10.1016/j.fuel.2022.123188','Control lacks matched fungal treatment; substrate/sludge, inoculum activity, temperature/pressure standard and duration not fully matched'),
        ('S21','Ovi RHB550 5g/L',455.83,17.9,'mL CH4/g VS_added',FORMULA+' p25; feedback p5; Ovi2022 abstract DOI10.1016/j.fuel.2022.123188','Same identity/dose only; no matched feedstock, fungal treatment, time series or duration'),
        ('S24','Kawai standard food waste SI0.33',435.0,np.nan,'mL CH4/g substrate VS',FORMULA+' pp22,25; Kawai2014 publisher abstract DOI10.1016/j.biortech.2014.01.018','Ultimate experimental yield vs day25 heuristic screening; composition, inoculum and fungal treatment differ'),
        ('S3','Rocha sewage-sludge BMP',124.0,6.72,'mL CH4/g VS', 'peerj-16720.pdf p1 abstract, p3 Table1, pp6-9 methodology; DOI10.7717/peerj.16720','Sewage sludge, 11days,37C,100mL, I/S1:1 by volume is not VS ratio; methodology only'),
        ('S3','Molecules moderate fungal screening',284.4,np.nan,'L CH4/kg VS screening','molecules-31-03594.pdf section2.2.2; DOI10.3390/molecules31203594','Model output, not observed measurement; different kinetics/risk and manuscript30-day curves'),
    ):
        row = by_id.loc[sid]
        records.append({'Scenario ID':sid,'Study/case':study,'Reported yield':observed,'Reported uncertainty':uncertainty,
                        'Reported basis':basis,'Unit equivalence':'1 mL/g = 1 L/kg; gas reference conditions still require matching',
                        'Model unpenalised day25 (L/kgVS)':row['Batch specific CH4 at 25d (L/kgVS)'],
                        'Model screening-adjusted day25 (L/kgVS)':row[YIELD],
                        'Directly comparable':False,'Reason':reason,'Exact source':source,
                        'MAE':np.nan,'RMSE':np.nan,'Percentage prediction error':np.nan,
                        'Validation status':'Not independently validated; plausibility/context only'})
    return pd.DataFrame(records)


def export_verification(selected, scenarios, run_scenario, volume, out):
    out = Path(out) / "supporting"
    out.mkdir(parents=True, exist_ok=True)
    parameter_table().to_csv(out/'s21_s24_parameter_verification.csv', index=False)
    comparison = literature_comparison(selected)
    comparison.to_csv(out/'s21_s24_literature_comparison.csv',index=False)
    base = next(s for s in scenarios if s['id']=='S3')
    sensitivity = sensitivity_analysis(base, run_scenario, volume)
    sensitivity.to_csv(out/'s21_s24_parameter_sensitivity.csv',index=False)
