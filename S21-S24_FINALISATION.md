# Final Scenarios S21-S24: Biochar Addition and Inoculum Loading

Updated 28 October 2026 | Branch: `biochar-inoculum`

## Main results: Day-10 and Day-25 methane production

The following are **finite-time legacy nominal-loading metrics**, not the full-potential screening quantity described below. They use each scenario's own stability-adjusted cumulative methane at the stated day divided by the same numerical nominal-loading denominator 2.5. Raw values remain full precision.

| Scenario | Day-10 legacy metric | Day-10 change vs S3 | Day-25 legacy metric | Day-25 change vs S3 |
| --- | --- | --- | --- | --- |
| S3 | 217.531 | +0.000% | 284.607 | +0.000% |
| S21 | 244.915 | +12.589% | 284.984 | +0.132% |
| S22 | 251.507 | +15.619% | 285.016 | +0.144% |
| S23 | 254.412 | +16.954% | 285.026 | +0.147% |
| S24 | 261.961 | +20.424% | 285.042 | +0.153% |

Each percentage compares like-for-like metrics at the same day. The larger early differences reflect modelled conversion speed; small Day-25 differences reflect convergence toward the same assumed potential. These are exploratory predictions, not experimentally validated responses.

## Methodology and exact S3 calculation

The original `Digester.get_practical_yields()` is unchanged:

```text
P = sum(component VS mass * component BMP * treated biodegradability)
s = inherited heuristic stability multiplier
Y_screen = 1000 * P * s / nominal_loading
```

The two finite-time reporting metrics are calculated independently:

```text
Y_legacy(t) = 1000 * C_adjusted(t) / nominal_loading, t=10 or 25 days
C_adjusted(t) = s * C(t)
Change(t) = 100 * [Y_legacy,scenario(t) / Y_legacy,S3(t) - 1]
```

All five cases have nominal loading 2.5. The denominator is read from the retained scenario/output setting; no methane value is hardcoded. The same stability multiplier is applied once, and there is no additional correction to methane potential.

S3 at full precision:

```text
P = 0.9683356212109677 Nm3
s = 0.735935091988353
C_adjusted(10) = 0.5438284773771739 Nm3
C_adjusted(25) = 0.7115179846921761 Nm3
Y_screen = 1000 * P * s / 2.5 = 285.05286578859705
Y_legacy(10) = 1000 * C_adjusted(10) / 2.5 = 217.53139095086956
Y_legacy(25) = 1000 * C_adjusted(25) / 2.5 = 284.60719387687044
```

The original screening calculation uses full methane potential. The finite-time comparisons use cumulative methane released by their respective days. Even with a common denominator, they are not interchangeable: Day 25 is slightly below full potential, and Day 10 is earlier in conversion.

### Dimensional limitation

Nominal OLR has units kgVS/m3/day and is not substrate charge mass. Dividing a batch volume by the numerical loading value 2.5 is an inherited project screening convention, not a general physical L/kgVS equation. These graphs therefore name the convention explicitly and do not label the outputs as actual-substrate-mass yields. Matching the denominator provides project-convention consistency but does not correct that physical limitation.

The original feed charge is 10 kg wet * 0.25 TS * 0.90 VS/TS = 2.25 kg substrate VS. The nominal scenario OLR 2.5 differs from the actual legacy feed loading 2.25 kg VS/m3/day. This existing mismatch is preserved and disclosed, not silently corrected in one scenario group.

## Day-15 methane production comparison

Day 15 uses the actual saved `Adjusted cumulative CH4 (Nm3)` rows at Day = 15, without interpolation or new simulation assumptions. The same inherited convention applies: `1000*C_adjusted(15)/2.5`. Percentages use unrounded Day-15 values and the Day-15 S3 reference. These are finite-time legacy comparison metrics, not experimentally validated specific methane yields. Existing Day-10/Day-25 results are unchanged.

| Scenario | Day-15 legacy comparison metric | Day-15 change vs S3 (%) |
| --- | --- | --- |
| S3 | 271.548 | +0.000% |
| S21 | 280.041 | +3.128% |
| S22 | 281.461 | +3.650% |
| S23 | 282.012 | +3.854% |
| S24 | 283.238 | +4.305% |

![Day-15 Methane Production - S3 vs S21-S24](output/s21_s24/s21_s24_day15_methane_comparison.png)

## Main presentation: Day-10, Day-15, Day-25 and cumulative figures

1. **Day-10 Methane Production - S3 vs S21-S24**: each scenario's stability-adjusted cumulative methane at Day 10, using the inherited denominator 2.5.
2. **Day-25 Methane Production - S3 vs S21-S24**: the same finite-time convention at Day 25. Small differences are preserved without truncating the vertical axis.
3. **Cumulative methane production over 25 days**: the unchanged independent curves in stability-adjusted Nm3.

![Day-10 Methane Production - S3 vs S21-S24](output/s21_s24/s21_s24_day10_legacy_nominal_comparison.png)

![Day-25 Methane Production - S3 vs S21-S24](output/s21_s24/s21_s24_day25_legacy_nominal_comparison.png)

![Cumulative methane production over 25 days](output/s21_s24/biochar_inoculum_gompertz_curve.png)

The cumulative curves use distinct colours: S3 blue, S21 green, S22 pink, S23 purple and S24 orange, with distinct line styles retained. Bar-chart colours remain grouped by scenario type.

The bar charts show finite-time legacy comparison metrics, not experimentally validated specific methane yields. S3 is blue, S21-S23 green and S24 orange. Values and same-day percentage changes are shown to three decimals; each dashed reference line is that time point's S3 value. Supporting numerical CSVs are retained; redundant supporting images are omitted.

## Supporting full-potential screening reference

Direct team comparisons use the original `Digester.get_practical_yields()` calculation from commit `e241207` (18 October 2026), with the inherited nominal OLR denominator 2.5. S3 uses 10 kg wet feed, 2.5 kg TS and 2.25 kg VS; **2.25 kg is VS, not wet mass**. The configured OLR is distinct from the calculated total-solids mass despite both having the numerical value 2.5.

| Scenario | Biochar (g/L) | S ratio | Full-potential screening metric | Change vs S3 |
| --- | --- | --- | --- | --- |
| S3 | 0 | 1 | 285.053 | +0.000% |
| S21 | 5 | 1 | 285.053 | +0.000% |
| S22 | 10 | 1 | 285.053 | +0.000% |
| S23 | 15 | 1 | 285.053 | +0.000% |
| S24 | 0 | 0.33 | 285.053 | +0.000% |

Graph values use the team's one-decimal presentation (285.1); the underlying reference is 285.05286578859705. Each scenario's screening value is independently calculated using its Digester. Identical results are expected: the current additive/inoculum implementation changes apparent conversion rate, while potential and stability remain fixed. This flat comparison does not demonstrate methane enhancement and is not evidence that the kinetic responses are ignored.

The original full-potential screening values remain in the CSVs and table; the redundant flat screening image is omitted.

## Retained actual-mass batch results: supporting analysis

The physical substrate-mass normalisation remains unchanged:

```text
Y_batch(t) = 1000 * C_adjusted(t) / 2.25 kg substrate VS
```

| Scenario | Day-10 batch yield (L CH4/kg substrate VS) | Day-10 change | Day-25 batch yield (L CH4/kg substrate VS) | Day-25 change |
| --- | --- | --- | --- | --- |
| S3 | 241.702 | +0.000% | 316.230 | +0.000% |
| S21 | 272.128 | +12.589% | 316.649 | +0.132% |
| S22 | 279.452 | +15.619% | 316.684 | +0.144% |
| S23 | 282.680 | +16.954% | 316.695 | +0.147% |
| S24 | 291.067 | +20.424% | 316.714 | +0.153% |

These are different numerical quantities from the primary legacy-convention metrics. Their relative percentage changes are equal because the common denominator changes by the same factor for every scenario. Neither actual-mass batch reference is replaced with 285.053.

The relationship is `Y_legacy(t)=Y_batch(t)*2.25/2.5`, derived from the denominators and existing cumulative volume, not an arbitrary fitted multiplier. Actual-mass results remain in the table and CSVs. Older supporting graph copies have been removed; full-precision data remain authoritative.

## Scientific interpretation

Biochar and inoculum changes affect the apparent conversion rate in this implementation. Each factor is applied once. The scenarios have different independently calculated curves and finite-time results, but the same assumed methane potential, inherited lag, biodegradability and stability multiplier.

S3 already reaches approximately 99.844% of the treated potential at Day 25. The available endpoint gain at fixed potential is therefore limited to about 0.157%. Day 10 changes are larger because conversion is incomplete. The small Day 25 differences are expected model behaviour, not evidence that the variables are ignored or of an experimentally small biochar benefit.

Equations 84-86 provide a kinetic response structure, not a validated BMP enhancement. Equation 89 defines inoculum mass only; its added saturating capacity response is an explicit assumption. Literature supports the biochar identity/dose and ratio design levels, not the current response magnitudes. Alpha = 0.5, K = 5 g/L, n = 1 and inoculum half-capacity = 1 remain uncalibrated. Inhibition KI = 30 g/L, m = 2 is unverified and disabled by default. No additional potential/stability mechanism was introduced.

These deterministic outputs do not establish experimental significance, optimal concentration, real-world stability benefit or economic advantage. Matched experimental time series, inoculum activity/blanks, biochar characterisation and separate calibration/validation data remain necessary.

## Scenario parameters

| Scenario | Biochar (g/L) | S:I (g substrate VS/g inoculum VS) | Biochar mass (kg) | Inoculum VS (kg) |
| --- | --- | --- | --- | --- |
| S3 | 0 | 1 | 0.00 | 2.250 |
| S21 | 5 | 1 | 5.00 | 2.250 |
| S22 | 10 | 1 | 10.00 | 2.250 |
| S23 | 15 | 1 | 15.00 | 2.250 |
| S24 | 0 | 0.33 | 0.00 | 6.818 |

All masses in this comparison refer to the **same fixed substrate charge**, not continuous daily inoculum or biochar dosing. S3's S:I baseline of 1 is an explicit modelling assumption. Official S24 was changed from 2 to 0.33 following the formula-register recommendation; 2 remains an additional sensitivity case.

| Shared parameter | Value | Basis/status |
|---|---|---|
| Substrate | 100% baseline food waste; no SCG | Same composition in all five cases |
| Organic fractions | Carbohydrate 0.50; protein 0.25; lipid 0.20; inert 0.05 | Existing project composition |
| Wet substrate charge | 10 kg | Retained reference basis |
| Total solids fraction | 0.25 | 2.5 kg TS |
| VS/TS | 0.90 | **2.25 kg substrate VS** |
| Reactor working-volume basis | 1 m3 | Fixed; inoculum carrier liquid assumed adjusted |
| Fungal enzyme dose | 60 U/g VS | S3 reference |
| Fungal pretreatment | 24 h, 30 C, pH 5.5 | S3 reference; not digestion temperature |
| Batch observation window | 25 days | Same window for all cases; not a solved CSTR HRT balance |
| Biochar identity | Rice-husk biochar RHB550, pyrolysis at 550 C | Same assumed identity across S21-S23; batch properties uncharacterised |
| Nominal legacy OLR | 2.5 kg VS/m3/day | Retained metadata; actual legacy daily feed corresponds to 2.25 |
| Treated methane potential | 0.9683356212 Nm3/charge | Identical across all five cases |
| Composition theoretical methane ceiling | 1.202175 Nm3/charge | No added methane credited to biochar or inoculum |
| Fixed inherited lag | 3.279107 days | No additional biochar/inoculum lag reduction |
| Heuristic stability multiplier | 0.735935092 | Identical across all five cases; uncalibrated |

## Final model parameters and equations

| Parameter | Final setting | Scientific status |
|---|---|---|
| Biochar benefit coefficient, alpha_add | 0.5 | Unverified legacy assumption |
| Half-response concentration, K_add | 5 g/L | Unverified; not inferred from the 5 g/L experimental dose |
| Response exponent, n | 1 | Unverified shape assumption |
| High-dose inhibition | **Disabled by default** | No sufficiently matched inhibition evidence |
| Inhibition concentration, K_I,add | 30 g/L, inactive | Unverified optional sensitivity parameter |
| Inhibition exponent, m | 2, inactive | Unverified optional sensitivity parameter |
| Inoculum half-capacity, h | 1 | Unverified empirical capacity proxy |
| Empirical rate scale | 1 | Reference scaling; not a fitted ADM1 coefficient |
| Additional lag scaling | Removed | Not justified by Equations 84-86 or 89 |

The supplied register provides these relationships:

```text
Eq.84: R_add = C_add^n / (K_add^n + C_add^n)
Eq. 85: k_meth* = k_meth,0 * (1 + alpha_add*R_add) * I_add
Eq.86: I_add = 1 / (1 + (C_add/K_I,add)^m) [optional]
Eq.89: S:I = M_substrate,VS / M_inoculum,VS
       M_inoculum,VS = M_substrate,VS / (S:I)
```

C_add and K_add use the same g/L units; the response and inhibition factors are dimensionless. Equation 89 is a mass identity; it does not independently predict methane production.

**The S21-S24 route uses an empirical Gompertz approximation, not a mechanistic ADM1 methanogenic coefficient.** It uses the dimensionless Eq. 85 response structure as an explicitly exploratory multiplier on apparent conversion speed. It does not claim that the inherited hydrolysis descriptor is a measured k_meth. The separate dynamic ADM1 implementation is not modified by these scenarios.

The optional inoculum response is `f_I=(1+h)/(1+h*(S:I)/(S:I)_reference)`. This saturating proxy is an assumption, not Equation 89. The apparent rate is the inherited rate multiplied once by the biochar and inoculum factors; methane potential and inherited lag remain fixed. The Gompertz curve is origin-normalised to zero cumulative methane at day 0, and daily production is the difference between successive cumulative values.



### Meaning of the exported R_max value

The existing raw CSV column `Empirical Gompertz Rmax (Nm3/day)` is retained for compatibility. Its value is:

```text
R_max,underlying = P * k_app / e
```

It is a parameter of the **underlying, unnormalised, unpenalised Gompertz curve**. It is not a measured maximum daily methane production rate, not a daily time-step increment, and not the exact maximum derivative of the reported origin-normalised, stability-adjusted curve. The presentation CSV includes an explanatory `Rmax description` column; the numerical values are unchanged.

For interpretation, if G(t) denotes the underlying Gompertz curve and s the stability multiplier:

```text
C_adjusted(t) = s * P * [G(t)-G(0)] / [P-G(0)]
dC_adjusted/dt = s * P / [P-G(0)] * dG/dt
```

Thus origin normalisation and stability scaling change the derivative relative to the underlying parameter. This relation explains terminology only; no additional rate correction is applied to the model. Daily methane in the time-series CSV remains the increment between successive cumulative volumes, with adjusted and unpenalised increments labelled separately. Graphs show finite-time yield, percentage change or cumulative volume, not measured R_max.


## S24 substrate-to-inoculum sensitivity study

S3 is fixed at S = 1, no biochar, substrate VS = 2.25 kg and nominal loading = 2.5. Its original full-potential screening result remains 285.053; its finite-time references remain 217.531 at Day 10 and 284.607 at Day 25. These are different output definitions.

Each sensitivity case is a fresh copy of S3 with **only `si_ratio` changed**. Equation 89 gives `inoculum VS = 2.25/S`. The existing empirical response is `f_I=(1+h)/(1+h*S/S_reference)`, with unchanged h = 1 and S_reference = 1; therefore `f_I=2/(1+S)`. It multiplies the apparent conversion rate once. Potential, stability, substrate mass, lag and biochar remain fixed.

Both cumulative columns below are stability-adjusted Nm3. Legacy metrics use `1000*C_adjusted(t)/2.5`; percentages use unrounded same-time S3 values. Unpenalised cumulative volumes and actual-mass batch yields are retained separately in the new full-precision sensitivity CSV.

| S ratio | Inoculum VS (kg) | Day-10 CH4 (Nm3) | Day-25 CH4 (Nm3) | Day-10 legacy metric | Change (%) | Day-25 legacy metric | Change (%) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.33 | 6.818 | 0.654901 | 0.712606 | 261.961 | +20.424 | 285.042 | +0.153 |
| 0.5 | 4.500 | 0.628768 | 0.712539 | 251.507 | +15.619 | 285.016 | +0.144 |
| 1 | 2.250 | 0.543828 | 0.711518 | 217.531 | +0.000 | 284.607 | +0.000 |
| 1.5 | 1.500 | 0.463808 | 0.707687 | 185.523 | -14.714 | 283.075 | -0.538 |
| 2 | 1.125 | 0.396658 | 0.699313 | 158.663 | -27.062 | 279.725 | -1.715 |

Sensitivity results are retained in the table and supporting CSV only; no additional sensitivity figures are generated.

**Recommendation:** retain S = 0.33 for the main S24 configuration because it is the previously documented literature-anchor initial case and tests increased inoculum availability against a defined S3 baseline. Retain S = 2 as the contrasting reduced-inoculum case; it tests slower conversion and incomplete recovery by Day 25. This recommendation is based on the experimental design and documented literature anchor, not on choosing the highest predicted methane value. Neither ratio is an established optimum. S = 0.5 and 1.5 provide intermediate sensitivity checks; 1.5 is a modelling interpolation, not a verified experimental datum from the supplied sources.

Lower S increases assumed conversion speed and early methane; higher S reduces them. Day-25 differences shrink as curves approach the same assumed potential, although slower cases remain further from that limit. All full-potential screening values remain 285.053.

**Validity and limitations:** the proxy is finite and positive throughout 0.33-2, equals one at S3, and is bounded above by two as S approaches zero. Mathematical boundedness does not establish biological validity. All off-baseline response magnitudes are uncalibrated, including the literature-anchor ratio. The model omits inoculum activity differences, endogenous inoculum methane, dilution/working-volume constraints, inhibition from substrate overload and changes in buffering or stability. Holding reactor volume fixed while increasing inoculum VS may be infeasible without measured inoculum solids concentrations and a volume balance. Do not extrapolate this empirical response outside the tested range or interpret it as a calibrated mass-to-methane mechanism.

[Full-precision S24 sensitivity CSV](output/s21_s24/supporting/s24_ratio_sensitivity.csv). Reproduce only these new outputs with `python -B -m utils.s24_sensitivity`. They are also regenerated by `python main.py --biochar-only`. The extended focused suite completed with **28 passed** using `python -B -m pytest tests/test_biochar_inoculum.py -q -p no:cacheprovider`. Existing raw CSVs and original model/configuration files were checked byte-for-byte unchanged during this sensitivity run.

## Recommendations

- **S21, 5 g/L:** first lower-dose biochar experiment. It produces a substantial assumed early kinetic effect with lower material use than S22/S23; this is not proof of a resource or cost optimum.
- **S22/S23:** retain for dose-response calibration. Increasing dose produces faster conversion under the current uncalibrated coefficients; no universal monotonic benefit is claimed.
- **S24, S:I = 0.33:** retain as the literature-anchor increased-inoculum case. It requires 6.818182 kg inoculum VS for 2.25 kg substrate VS, rather than S3's 2.25 kg. Confirm activity, endogenous methane and resource requirements experimentally.
- **S3:** preserve the original screening equations and baseline. Do not compare finite-time results directly against full-potential 285.053 as if they were the same time-dependent quantity.

## Data files and reproduction

- [Raw scenario summary](output/s21_s24/biochar_inoculum_summary.csv): all original columns retained, plus full-precision Day 10/Day 25 legacy-convention derived columns.
- [Presentation summary](output/s21_s24/biochar_inoculum_summary_presentation.csv): comparison values and percentages to 3 decimal places; definitions remain explicit.
- [Raw cumulative time series](output/s21_s24/supporting/biochar_inoculum_timeseries.csv): unchanged methane volumes and actual-mass yields.
- [Shared project summary](output/scenario_summary.csv): existing screening and batch values retained, with appended derived fields.
- Supporting parameter-verification, sensitivity and literature-comparison CSVs remain available. No original simulation output was deleted.

```powershell
python -B main.py --biochar-only
python -B -m unittest discover -s tests -p test_biochar_inoculum.py -q
```

Verification: `python -m pytest tests/test_biochar_inoculum.py -q -p no:cacheprovider` completed with **27 passed**. `git diff --check` also passed.

The exporter maintains four main figures: Day-10, Day-15 and Day-25 comparisons, plus cumulative kinetics. The full-potential screening data and S-ratio CSV remain supporting analyses; supporting PNGs are not generated automatically. Derived metric additions are reporting calculations only; original simulation functions, coefficients, nominal loading, potential and stability remain untouched.

## Team-reporting verification

The team-standard screening update was verified with `python -B -m pytest tests/test_biochar_inoculum.py -q -p no:cacheprovider`: **29 passed**. All existing CSV files, the cumulative graph and original model/configuration files were checked byte-for-byte unchanged. The update changes reporting code, graph placement, the report and focused tests only.

## References

1. Ovi, D.; Chang, S.W.; Wong, J.W.C.; et al. (2022). Effect of rice husk and palm tree-based biochar addition on the anaerobic digestion of food waste/sludge. *Fuel*, 315, 123188. https://doi.org/10.1016/j.fuel.2022.123188
2. Kawai, M.; Nagao, N.; Tajima, N.; Niwa, C.; Matsuyama, T.; Toda, T. (2014). The effect of the labile organic fraction in food waste and the substrate/inoculum ratio on anaerobic digestion for a reliable methane yield. *Bioresource Technology*, 157, 174-180. https://doi.org/10.1016/j.biortech.2014.01.018
3. Rocha, M.E.; Lazarino, T.C.; Oliveira, G.; et al. (2024). Analysis of biogas production from sewage sludge combining BMP experimental assays and the ADM1 model. *PeerJ*, 12, e16720. https://doi.org/10.7717/peerj.16720
4. Zaferanloo, P.; Hossain, M.I.; Maehara, S.; Ektesabi, M.; Malherbe, F.; Zaferanloo, B. (2026). Fungal Pretreatment-Assisted Methane Recovery from Food Waste: A Literature-Informed Simulation Framework. *Molecules*, 31, 3594. https://doi.org/10.3390/molecules31203594
5. *Complete Formula Notation Scenario Literature Data - 6102026.pdf*, supplied working register: p. 20, Equations 84-86; p. 22, Equation 89; pp. 24-25 scenario/literature anchors.
6. *Bita feedback after our meeting in week 9.pdf*, supplied working report, updated 8 October 2026: OAT principles, S3 baseline requirements and Section 6, p. 5 biochar/inoculum literature anchors.

Reference values above come from the supplied documents and the earlier source audit. They are not presented as new measurements or fitted coefficients.

## Final finite-time presentation verification

The two bar charts were regenerated from the existing full-precision CSV cumulative volumes; all same-day percentage changes were recalculated and verified. All existing CSV files, the cumulative graph and protected simulation/configuration files remained byte-for-byte unchanged. The focused suite completed with **29 passed** using `python -B -m pytest tests/test_biochar_inoculum.py -q -p no:cacheprovider`.
