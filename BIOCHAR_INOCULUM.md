# S21-S24: exploratory biochar and inoculum kinetics

This extends the existing deterministic scenario-screening model. Outputs are model-derived estimates, not experimentally validated reactor predictions. No S14-S20 cases are introduced. The existing Digester, Feedstock, Pretreatment and Gompertz methods remain the foundation.

## Reference and OAT inputs

S3: 100% existing FW composition, 10 kg wet substrate, TS=0.25, VS/TS=0.90, hence 2.25 kg substrate VS; 1 m3 reactor; enzymes 60 U/g VS, 24 h pretreatment at 30 C, pH 5.5; 25-day window. Explicit new defaults: biochar 0 g/L, S:I=1 g substrate VS/g inoculum VS. The S:I baseline is an assumption, not a recovered experimental setting. S21/S22/S23 change only biochar to 5/10/15 g/L. S24 changes only S:I to 2 (a literature-tested level), testing reduced inoculum at fixed substrate. Additional sensitivity ratios: 0.33, 0.5, 1, 2, 4.

Biochar identity is rice-husk biochar RHB550, pyrolysed at 550 C. All doses assume the same material. Surface area, conductivity, ash, pH and adsorption constants are unavailable; no numerical claims about these properties are made. Biochar is not added to substrate VS or credited with methane. Dose in g/L times reactor volume in m3 gives kg biochar: 5, 10, 15 kg for 1 m3.

## Mathematical implementation

The existing model has algebraic biodegradability/BMP yields, a hydrolysis-rate proxy, modified Gompertz kinetics and heuristic inhibition scores. It does not solve dP/dt=-kP, Monod guild dynamics, active biomass, DIET, adsorption or acid-base balances. Feedstock.calculate_inoculum_mass existed, but was not connected to methane kinetics.

For dose c in g/L, the exploratory biochar kinetic factor is:

    f_B(c) = [1 + a*c/(K+c)] / [1 + (c/H)^2]

Default a=0.5 (dimensionless), K=5 g/L and H=30 g/L are heuristic sensitivity coefficients requiring calibration. They are NOT measured or fitted RHB550 parameters. Saturating facilitation permits diminishing benefits; attenuation permits high-dose penalties. Neither an optimum nor the direction of actual RHB550 response is established by this assumed function. The plotted 0-30 g/L sweep is exploratory; only 5,10,15 are the official literature-anchored levels.

S:I is VS substrate / VS inoculum. With substrate mass fixed:

    M_inoculum = M_substrate / (S:I)
    x = M_inoculum / M_inoculum,reference = (S:I)reference / (S:I)
    f_I = 2*x/(1+x)

This is a saturating conversion-capacity proxy assuming the same active fraction and inoculum quality in all cases. Its half-saturation is assumed at reference biomass, not measured. Inoculum VS concentration is M_inoculum/V; no microbial growth state is solved. Carrier liquid is assumed adjusted to hold reactor volume fixed; no substrate composition/loading change or inoculum endogenous gas is counted. It is a finite-charge assay comparison, not a continuous-reactor inoculum dosing prescription.

The inherited pretreatment rate k and lag lambda are mapped to apparent conversion parameters:

    k_app = k * f_B * f_I
    lambda_app = lambda / (f_B * f_I)

Hydrolysis output itself is unchanged; k_app is explicitly a conversion proxy. The existing Gompertz function evaluates G(t) with these parameters and unchanged treated charge potential P. The finite-charge curve is origin-normalised:

    C(t) = P * [G(t)-G(0)] / [P-G(0)]
    daily_CH4[n] = [C(n)-C(n-1)] / 1 day

Thus C(0)=0, cumulative methane is nonnegative/nondecreasing, and the asymptote remains P, bounded by the charge theoretical BMP. Daily rows describe the preceding one-day interval; day zero is zero. No methane yield is multiplied directly by inverse S:I.

The existing heuristic stability score s is reported unchanged across these cases: there is no defensible new buffering/adsorption/inoculum inhibition relation. Adjusted C=s*C. Specific batch yield at day 25 is 1000*C(25)/2.25 in L/kg substrate VS, with a separately labelled stability-adjusted equivalent. Percent change uses the adjusted batch specific yield relative to S3, on the same basis for every new chart. Gross energy=C(25)*35.8 MJ/Nm3 and electricity=0.35*gross energy; these use unpenalised methane. No net energy or additive-production benefit is claimed.

## Legacy outputs and units

S1-S13 numerical calculations are preserved. Recalculated S3 treated daily-feed methane potential is 0.9683356212 Nm3/day; legacy adjusted specific yield is 285.0528658 L/kg VS. Legacy nominal OLR=2.5 differs from the actual 2.25 kg VS/m3/day feed; the legacy specific-yield denominator remains 2.5 to avoid silently changing existing results. New batch metrics use actual 2.25 kg substrate VS and therefore differ. Both are retained with distinct column names.

Legacy daily-feed potential is NOT multiplied by 25 to create a cumulative batch volume. Instead, the same 10 kg feed is interpreted as one substrate charge for a separately labelled kinetic assay. Batch mean production is C(25)/25 Nm3/day, not the legacy daily-feed potential. The original S1-S13 time-series plots retain their existing interpretation/limitations. HRT/flow balances are not newly implemented. Each new case has its own inherited untreated control; legacy treated potential, energy and stability columns remain identical to S3 because this extension changes finite-time kinetics only.

## Sources and evidence status

Supervisor source: Bita feedback after our meeting in week 9.pdf, updated 8 October 2026, sections 1,5,6,7,12. Its S1-S9 numerical table belongs to another model version and is not a calibration target.

Ovi et al. (2022), Effect of rice husk and palm tree-based biochar addition on the anaerobic digestion of food waste/sludge, Fuel 315,123188. https://doi.org/10.1016/j.fuel.2022.123188 . Publisher/institutional abstract verifies RHB550/PTB400 and 5/10/15 g/L. This is food-waste/sludge co-digestion, not this fungal-treated substrate. No quantitative kinetic parameters were transferable from accessible material; the accepted-manuscript endpoint returned HTTP 403. No reported methane improvement is imposed on this model.

Kawai et al. (2014), The effect of the labile organic fraction in food waste and the substrate/inoculum ratio on anaerobic digestion for a reliable methane yield, Bioresource Technology 157,174-180. https://doi.org/10.1016/j.biortech.2014.01.018 . Supervisor feedback and abstract list S:I 0.33,0.5,1,2,4 on VS basis. These support the ratio range, not the capacity proxy coefficients or a universal best ratio.

Literature-informed: material identity, dose and S:I study levels, qualitative dependence on kinetics. Assumed: reference S:I, biochar response coefficients, active fraction constancy and saturating conversion proxy. Calibration required: dose-specific time-series data, inoculum activity, lag/rate estimates, adsorption and inhibition data. This model does not demonstrate DIET or microbial attachment, predict measured pH/VFA changes, account for LCFA toxicity or prove any economic/climate optimum.

## Running and outputs

    python main.py
    python main.py --biochar-only
    python -m unittest discover -s tests -v

Full run regenerates existing plots and appends S21-S24 results to the common summary. Independent mode runs S3 plus S21-S24, updates their rows in scenario_summary.csv, and preserves legacy plots and other scenario rows.

output/biochar_inoculum_summary.csv: S3/S21-S24, legacy and clearly separated batch metrics. output/biochar_inoculum_timeseries.csv: daily and cumulative values. output/biochar_dose_sensitivity.csv and inoculum_ratio_sensitivity.csv: supporting sweeps. All charts draw from the same calculated tables/curves; no hardcoded yield values.

Charts: biochar_methane_yield.png (adjusted day-25 specific yield and changes); biochar_inoculum_gompertz_curve.png (unpenalised single-charge cumulative methane); biochar_dose_response.png (assumed dose response, not an established optimum); inoculum_ratio_sensitivity.png (reference and official S24 marked); biochar_inoculum_improvement.png (adjusted day-25 yield differences vs S3).

Files: data/biochar_config.py defines new cases and coefficients; AD/biochar_inoculum.py reuses digestion kinetics for finite-charge sensitivity; main.py provides shared scenario construction/integration and independent mode; utils/biochar_visualisations.py exports tables/charts; tests/test_biochar_inoculum.py checks regression, OAT, VS mass, methane/energy balances, invalid inputs and CSV consistency.
