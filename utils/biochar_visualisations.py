"""Exports use the same finite-charge, stability-adjusted 25-day metric."""
from copy import deepcopy
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from AD.biochar_inoculum import evaluate_batch
from data.biochar_config import SI_LEVELS, OFFICIAL_S24_SI

YIELD = 'Adjusted batch specific CH4 at 25d (L/kgVS)'
CHANGE = 'Adjusted batch yield change vs S3 (%)'
NOMINAL10 = 'Day-10 screening metric (legacy nominal-loading convention)'
NOMINAL10_CHANGE = 'Day-10 legacy nominal-loading change vs S3 (%)'
NOMINAL25 = 'Day-25 screening metric (legacy nominal-loading convention)'
NOMINAL25_CHANGE = 'Day-25 legacy nominal-loading change vs S3 (%)'
SCENARIO_COLOURS = {'S3': '#3569a8', 'S21': '#43936c', 'S22': '#43936c', 'S23': '#43936c', 'S24': '#d88a32'}


def export_biochar_analysis(results, curves, scenarios, run_scenario, volume):
    out = Path('output/s21_s24')
    out.mkdir(parents=True, exist_ok=True)
    supporting = out / "supporting"
    supporting.mkdir(exist_ok=True)
    ids = ['S3', 'S21', 'S22', 'S23', 'S24']
    selected = results[results['Scenario ID'].isin(ids)].copy()
    if set(selected['Scenario ID']) != set(ids):
        raise ValueError('Biochar analysis requires S3 and S21-S24')
    reference = selected.loc[selected['Scenario ID'] == 'S3', YIELD].iloc[0]
    results.loc[selected.index, CHANGE] = (selected[YIELD] / reference - 1) * 100
    # Each screening yield is computed by its own Digester, before rounding.
    project = 'Project screening yield (L/kgVS)'
    project_reference = results.loc[results['Scenario ID'] == 'S3', project].iloc[0]
    results.loc[selected.index, 'Project screening change vs S3 (%)'] = (results.loc[selected.index, project] / project_reference - 1) * 100
    early = 'Adjusted batch specific CH4 at 10d (L/kgVS)'
    early_reference = results.loc[results['Scenario ID'] == 'S3', early].iloc[0]
    results.loc[selected.index, 'Adjusted day10 batch yield change vs S3 (%)'] = (results.loc[selected.index, early] / early_reference - 1) * 100
    selected = add_day25_nominal_comparison(results.loc[selected.index].copy())
    for column in (NOMINAL10, NOMINAL10_CHANGE, NOMINAL25, NOMINAL25_CHANGE):
        results.loc[selected.index, column] = selected[column]
    leading = ['Scenario ID', 'Scenario', early, 'Adjusted day10 batch yield change vs S3 (%)', YIELD, CHANGE, project, 'Project screening change vs S3 (%)']
    selected = selected[leading + [c for c in selected.columns if c not in leading]]
    selected.to_csv(out / 'biochar_inoculum_summary.csv', index=False)
    export_presentation_summary(selected, out)
    daily_rows = []
    for sid, data in curves.items():
        mass_vs = selected.loc[selected['Scenario ID'] == sid, 'Substrate charge VS (kg)'].iloc[0]
        for day, cumulative, adjusted in zip(data['time'], data['methane'], data['adjusted']):
            daily_rows.append({'Scenario ID': sid, 'Day': day, 'Cumulative CH4 (Nm3)': cumulative,
                               'Adjusted cumulative CH4 (Nm3)': adjusted,
                               'Substrate VS (kg)': mass_vs,
                               'Unpenalised batch yield (L/kgVS)': cumulative * 1000 / mass_vs,
                               'Adjusted batch yield (L/kgVS)': adjusted * 1000 / mass_vs,
                               'Adjusted daily CH4 (Nm3/day)': 0.0 if day == 0 else data['adjusted'][int(day)] - data['adjusted'][int(day)-1],
                               'Daily CH4 (Nm3/day)': 0.0 if day == 0 else data['daily'][int(day)-1]})
    pd.DataFrame(daily_rows).to_csv(supporting / 'biochar_inoculum_timeseries.csv', index=False)

    plot_combined_methane_yield(out)
    plot_cumulative_methane_comparison(out)

    base = next(s for s in scenarios if s['id'] == 'S3')
    from utils.s24_sensitivity import export_s24_sensitivity
    export_s24_sensitivity(base, run_scenario, volume, out)
    def sensitivity(field, levels):
        rows = []
        for value in levels:
            case = deepcopy(base)
            case[field] = float(value)
            _, _, digester, config = run_scenario(case)
            row, _ = evaluate_batch(digester, case, config, volume)
            row[CHANGE] = (row[YIELD] / reference - 1) * 100
            rows.append(row)
        return pd.DataFrame(rows)

    ratios = sensitivity('si_ratio', SI_LEVELS)
    ratios['Role'] = ['Official S24' if r == OFFICIAL_S24_SI else 'S3 reference' if r == 1 else 'Additional sensitivity' for r in SI_LEVELS]
    # Supporting results are retained as CSVs; do not generate sensitivity PNGs.
    from utils.biochar_verification import export_verification
    export_verification(selected, scenarios, run_scenario, volume, out)


def plot_combined_methane_yield(output_dir='output/s21_s24'):
    """Generate the three main finite-time bar charts; supporting outputs remain CSV-only."""
    return tuple(plot_nominal_time_comparison(output_dir,day) for day in (10,15,25))


def team_screening_comparison(results):
    """Use full-precision get_practical_yields exports, never finite-time volumes."""
    ids=['S3','S21','S22','S23','S24']
    frame=results.set_index('Scenario ID').loc[ids].copy()
    loading=frame['Screening nominal loading (kgVS/m3/day)'].to_numpy(dtype=float)
    values=frame['Project screening yield (L/kgVS)'].to_numpy(dtype=float)
    if not np.isfinite(loading).all() or (loading<=0).any() or not np.all(loading==loading[0]):
        raise ValueError('Team screening requires a shared positive nominal-loading convention')
    if not np.isfinite(values).all() or (values<0).any() or values[0]<=0:
        raise ValueError('Invalid full-potential screening values')
    frame['Team screening change vs S3 (%)']=(values/values[0]-1)*100
    return frame.reset_index()


def plot_team_screening_comparison(output_dir='output/s21_s24'):
    from matplotlib.patches import Patch
    out=Path(output_dir)
    frame=team_screening_comparison(pd.read_csv(out/'biochar_inoculum_summary.csv'))
    values=frame['Project screening yield (L/kgVS)'].to_numpy()
    ids=frame['Scenario ID'].tolist()
    fig,ax=plt.subplots(figsize=(11,6.5))
    bars=ax.bar(ids,values,color=[SCENARIO_COLOURS[sid] for sid in ids],edgecolor='black',width=.6)
    for bar,value,pct in zip(bars,values,frame['Team screening change vs S3 (%)']):
        ax.annotate(f'{value:.1f}',(bar.get_x()+bar.get_width()/2,value),xytext=(0,7),textcoords='offset points',ha='center',fontweight='bold')
        ax.text(bar.get_x()+bar.get_width()/2,value/2,f'{pct:+.1f}%',ha='center',color='white',fontweight='bold')
    ax.axhline(values[0],color='black',ls='--',lw=1.2)
    ax.set(title='Biochar and Inoculum Sensitivities vs. S3 Reference',xlabel='Scenario ID',ylabel='Specific Methane Screening Metric (Legacy L CH4/kg VS Convention)',ylim=(0,values.max()*1.20))
    ax.legend(handles=[Patch(color=SCENARIO_COLOURS['S3'],label='S3 reference'),Patch(color=SCENARIO_COLOURS['S21'],label='Biochar scenarios'),Patch(color=SCENARIO_COLOURS['S24'],label='Inoculum scenario')],loc='upper center',ncol=3,fontsize=9)
    ax.grid(axis='y',ls='--',alpha=.3)
    ax.set_axisbelow(True)
    fig.text(.5,.10,f'S3 full-potential reference = {values[0]:.3f}; all scenarios retain identical potential and stability.',ha='center',fontsize=9)
    fig.text(.5,.065,'Original get_practical_yields convention: 1000 x adjusted full potential / nominal OLR; not a finite-time batch yield.',ha='center',fontsize=8)
    fig.text(.5,.03,'Inherited dimensional limitation retained. Exploratory simulation results; experimentally uncalibrated.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.15,1,1))
    support=out/'supporting';support.mkdir(exist_ok=True)
    path=support/'s21_s24_team_screening_comparison.png'
    fig.savefig(path,dpi=300)
    plt.close(fig)
    return path


def add_day25_nominal_comparison(results):
    """Compatibility helper: derive both times; leave original metrics intact."""
    frame=results.copy()
    denominator=frame['Screening nominal loading (kgVS/m3/day)'].to_numpy(dtype=float)
    if not np.isfinite(denominator).all() or (denominator<=0).any() or not np.all(denominator==denominator[0]):
        raise ValueError('Expected equal positive nominal denominators')
    for day,metric,change in ((10,NOMINAL10,NOMINAL10_CHANGE),(25,NOMINAL25,NOMINAL25_CHANGE)):
        volume=frame[f'Adjusted batch cumulative CH4 at {day}d (Nm3)'].to_numpy(dtype=float)
        if not np.isfinite(volume).all() or (volume<0).any():raise ValueError('Invalid adjusted cumulative methane')
        frame[metric]=1000*volume/denominator
        reference=frame.loc[frame['Scenario ID']=='S3',metric]
        if len(reference)!=1 or reference.iloc[0]<=0:raise ValueError('Expected one positive S3 reference')
        frame[change]=(frame[metric]/reference.iloc[0]-1)*100
    return frame


def day15_nominal_comparison(output_dir='output/s21_s24'):
    """Read actual saved Day15 outputs, without interpolation or CSV mutation."""
    out=Path(output_dir)
    frame=pd.read_csv(out/'biochar_inoculum_summary.csv')
    times=pd.read_csv(out/'supporting'/'biochar_inoculum_timeseries.csv')
    selected=times.loc[(times['Day']==15)&times['Scenario ID'].isin(frame['Scenario ID'])]
    if selected['Scenario ID'].duplicated().any() or set(selected['Scenario ID'])!=set(frame['Scenario ID']):
        raise ValueError('Expected exactly one saved Day15 output per scenario')
    volume=frame['Scenario ID'].map(selected.set_index('Scenario ID')['Adjusted cumulative CH4 (Nm3)'])
    loading=frame['Screening nominal loading (kgVS/m3/day)']
    if not np.isfinite(volume).all() or (volume<0).any() or not np.isfinite(loading).all() or (loading<=0).any() or not (loading==loading.iloc[0]).all():
        raise ValueError('Invalid saved Day15 volumes or nominal loading')
    frame['Day-15 legacy metric']=1000*volume/loading
    reference=frame.loc[frame['Scenario ID']=='S3','Day-15 legacy metric']
    if len(reference)!=1 or reference.iloc[0]<=0:
        raise ValueError('Expected one positive S3 reference')
    frame['Day-15 change vs S3 (%)']=(frame['Day-15 legacy metric']/reference.iloc[0]-1)*100
    return frame


def plot_nominal_time_comparison(output_dir='output/s21_s24',day=25):
    """Finite-time reporting index, not actual-mass batch yield or BMP."""
    from matplotlib.ticker import FormatStrFormatter
    if day not in (10,15,25):raise ValueError('Expected Day10, Day15 or Day25')
    out=Path(output_dir)
    frame=day15_nominal_comparison(out) if day==15 else add_day25_nominal_comparison(pd.read_csv(out/'biochar_inoculum_summary.csv'))
    ids=['S3','S21','S22','S23','S24'];frame=frame.set_index('Scenario ID').loc[ids]
    metric,change=('Day-15 legacy metric','Day-15 change vs S3 (%)') if day==15 else (NOMINAL10,NOMINAL10_CHANGE) if day==10 else (NOMINAL25,NOMINAL25_CHANGE)
    values=frame[metric].to_numpy(dtype=float);percentages=frame[change].to_numpy(dtype=float)
    fig,ax=plt.subplots(figsize=(12,7))
    ax.bar(np.arange(5),values,color=[SCENARIO_COLOURS[sid] for sid in ids],edgecolor='black',width=.6)
    ax.axhline(values[0],color=SCENARIO_COLOURS['S3'],linestyle='--',linewidth=1.2)
    for x,(value,pct) in enumerate(zip(values,percentages)):
        ax.annotate(f'{value:.3f}\n({pct:+.3f}% vs S3)',(x,value),xytext=(0,8),textcoords='offset points',ha='center',fontsize=10)
    ax.set_title(f'Day-{day} Methane Production \u2014 S3 vs S21\u2013S24',fontsize=16,pad=16)
    ax.set_ylabel('Finite-Time Comparison Metric (Legacy Nominal-Loading Convention)')
    ax.set_xlabel('Scenario ID');ax.set_xticks(np.arange(5),ids);ax.set_ylim(0,values.max()*1.20)
    ax.yaxis.set_major_formatter(FormatStrFormatter('%.1f'));ax.grid(axis='y',linestyle=':',alpha=.35);ax.set_axisbelow(True)
    loading=frame.loc['S3','Screening nominal loading (kgVS/m3/day)']
    fig.text(.5,.13,f'1000 x adjusted cumulative methane at Day {day} / inherited nominal loading ({loading:g}).',ha='center',fontsize=10)
    fig.text(.5,.09,'Not an actual-mass-specific methane yield, experimentally validated BMP or physically corrected normalisation.',ha='center',fontsize=9)
    fig.text(.5,.055,f'Full-potential screening S3 = {frame.loc["S3","Project screening yield (L/kgVS)"]:.3f}; finite-time comparisons are different quantities.',ha='center',fontsize=9)
    fig.text(.5,.02,'S3 blue | S21-S23 green | S24 orange. Exploratory, experimentally uncalibrated.',ha='center',fontsize=9)
    fig.subplots_adjust(left=.11,right=.97,bottom=.23,top=.85)
    support=out/'supporting';support.mkdir(exist_ok=True)
    path=out/('s21_s24_day15_methane_comparison.png' if day==15 else f's21_s24_day{day}_legacy_nominal_comparison.png');fig.savefig(path,dpi=300);plt.close(fig)
    return path


def plot_day25_nominal_comparison(output_dir='output/s21_s24'):
    """Backward-compatible entry point for the approved Day25 metric."""
    return plot_nominal_time_comparison(output_dir,25)


def plot_inoculum_ratio_sensitivity(ratios, output_dir='output/s21_s24'):
    from matplotlib.ticker import FormatStrFormatter
    fig,ax = plt.subplots(figsize=(10,6))
    ax.plot(ratios['S:I (gVS/gVS)'],ratios[YIELD],color=SCENARIO_COLOURS['S21'],marker='o',label='S:I sensitivity')
    for ratio,sid,label in ((1,'S3','S3 reference'),(OFFICIAL_S24_SI,'S24','Official S24')):
        row=ratios[ratios['S:I (gVS/gVS)']==ratio].iloc[0]
        ax.scatter([ratio],[row[YIELD]],color=SCENARIO_COLOURS[sid],s=80,label=label,zorder=3)
    ax.set_xlabel('S:I (g substrate VS / g inoculum VS)')
    ax.set_ylabel('Adjusted Day-25 Methane Yield (L CH4/kg Substrate VS)')
    ax.yaxis.set_major_formatter(FormatStrFormatter('%.1f'))
    ax.set_title('Inoculum Ratio Sensitivity - Exploratory, Uncalibrated')
    ax.legend();ax.grid(axis='y',linestyle=':',alpha=.4)
    fig.tight_layout();fig.savefig(Path(output_dir)/'supporting'/'inoculum_ratio_sensitivity.png',dpi=180);plt.close(fig)


def plot_cumulative_methane_comparison(output_dir='output/s21_s24'):
    """Presentation curves read exclusively from saved stability-adjusted data."""
    out = Path(output_dir)
    saved = pd.read_csv(out / 'supporting' / 'biochar_inoculum_timeseries.csv')
    ids = ['S3', 'S21', 'S22', 'S23', 'S24']
    column = 'Adjusted cumulative CH4 (Nm3)'
    styles = {'S3':'-', 'S21':'--', 'S22':'-.', 'S23':':', 'S24':'-'}
    curve_colours = {'S3':'#3569a8', 'S21':'#009E73', 'S22':'#CC79A7', 'S23':'#6F42C1', 'S24':'#d88a32'}
    fig, ax = plt.subplots(figsize=(12, 7))
    for index, sid in enumerate(ids):
        data = saved.loc[saved['Scenario ID'] == sid].sort_values('Day')
        if (data.empty or data['Day'].duplicated().any() or
                data['Day'].min() != 0 or data['Day'].max() != 25 or
                not {10, 25}.issubset(set(data['Day']))):
            raise ValueError(f'{sid}: expected unique days spanning 0-25, including 10 and 25')
        values = data[column].to_numpy(dtype=float)
        if not np.isfinite(values).all() or (values < 0).any() or (np.diff(values) < 0).any():
            raise ValueError(f'{sid}: invalid cumulative methane data')
        colour = curve_colours[sid]
        ax.plot(data['Day'], values, color=colour, linestyle=styles[sid], label=sid, linewidth=2, zorder=3)
        comparison = data.set_index('Day').loc[[10, 25]]
        ax.scatter(comparison.index, comparison[column], color=colour, s=32,
                   edgecolors='white', linewidths=.6, zorder=4, clip_on=False)

    # Neutral dashed lines sit behind the scenario curves. Labels stay above
    # the plotting area rather than crossing curves or the scenario legend.
    for day, label in (
        (10, 'Day 10 \u2013 Early methane production'),
        (25, 'Day 25 \u2013 Final comparison'),
    ):
        ax.axvline(day, color='#555555', linestyle='--', linewidth=1.5,
                   alpha=.85, zorder=2)
        ax.text(day, 1.035, label, transform=ax.get_xaxis_transform(),
                ha='right' if day == 25 else 'center', va='bottom',
                fontsize=10, color='#333333', clip_on=False)

    ax.set_xlim(0, 26)  # margin makes day-25 markers/reference line visible
    ax.set_ylim(bottom=0, top=saved.loc[saved['Scenario ID'].isin(ids), column].max() * 1.12)
    ax.set_xticks([0, 5, 10, 15, 20, 25])
    from matplotlib.ticker import FormatStrFormatter
    ax.yaxis.set_major_formatter(FormatStrFormatter('%.1f'))
    ax.set_xlabel('Digestion Time (Days)', fontsize=12)
    ax.set_ylabel('Stability-Adjusted Cumulative CH\u2084 (Nm\u00b3)', fontsize=12)
    ax.set_axisbelow(True)
    ax.grid(True, linestyle=':', alpha=.35)
    ax.legend(title='Scenario', loc='upper left', framealpha=.95)
    fig.suptitle('Cumulative Methane Production: S3 vs S21\u2013S24 (25 Days)',
                 fontsize=16, y=.97)
    fig.text(.5, .035, 'Exploratory simulation results \u2013 not experimentally calibrated.',
             ha='center', va='center', fontsize=10, color='#555555')
    fig.subplots_adjust(left=.10, right=.97, bottom=.15, top=.82)
    standard = out / 'biochar_inoculum_gompertz_curve.png'
    fig.savefig(standard, dpi=300)
    plt.close(fig)
    return standard


def export_presentation_summary(results, output_dir='output/s21_s24'):
    """Display-only strings; percentages are computed BEFORE formatting.
    Inputs retain their precision. Never use this table to drive the model.
    """
    frame = results.set_index('Scenario ID').loc[['S3','S21','S22','S23','S24']]
    presentation = pd.DataFrame(index=frame.index)
    presentation['Biochar (g/L)'] = frame['Biochar (g/L)'].map(lambda x: f'{x:g}')
    presentation['S:I (gVS/gVS)'] = frame['S:I (gVS/gVS)'].map(lambda x: f'{x:g}')
    for day in (10,25):
        col = f'Adjusted batch specific CH4 at {day}d (L/kgVS)'
        raw = f'Batch specific CH4 at {day}d (L/kgVS)'
        reference = frame.loc['S3', col]
        presentation[f'Day-{day} adjusted yield (L CH4/kg substrate VS)'] = frame[col].map(lambda x:f'{x:.{3}f}')
        presentation[f'Day-{day} change vs S3 (%)'] = ((frame[col]/reference-1)*100).map(lambda x:f'{x:+.{3}f}')
        presentation[f'Day-{day} unpenalised yield (L CH4/kg substrate VS)'] = frame[raw].map(lambda x:f'{x:.{3}f}')
    nominal = add_day25_nominal_comparison(frame.reset_index()).set_index('Scenario ID')
    for day,metric,change in ((10,NOMINAL10,NOMINAL10_CHANGE),(25,NOMINAL25,NOMINAL25_CHANGE)):
        presentation[f'Day-{day} legacy nominal-loading screening metric'] = nominal[metric].map(lambda x:f'{x:.3f}')
        presentation[f'Day-{day} legacy nominal-loading change vs S3 (%)'] = nominal[change].map(lambda x:f'{x:+.3f}')
    presentation['Finite-time nominal metric definition'] = 'Adjusted cumulative volume / inherited nominal loading; not actual-mass batch yield or validated BMP'
    presentation['Apparent conversion rate (1/day)'] = frame['Apparent conversion rate (1/day)'].map(lambda x:f'{x:.6f}')
    presentation['Empirical Gompertz Rmax (Nm3/day)'] = frame['Empirical Gompertz Rmax (Nm3/day)'].map(lambda x:f'{x:.6f}')
    presentation['Rmax description'] = 'Underlying unnormalised Gompertz parameter P*k/e; not measured daily production or the exact peak derivative of the origin-normalised stability-adjusted curve'
    presentation['Day-25 incremental yield vs S3 (L CH4/kg substrate VS)'] = (frame[YIELD]-frame.loc['S3',YIELD]).map(lambda x:f'{x:.3f}')
    col = 'Project screening yield (L/kgVS)'
    presentation['Legacy screening yield (L CH4/kg VS)'] = frame[col].map(lambda x:f'{x:.3f}')
    presentation['Legacy screening change vs S3 (%)'] = ((frame[col]/frame.loc['S3',col]-1)*100).map(lambda x:f'{x:+.3f}')
    destination = Path(output_dir)/'biochar_inoculum_summary_presentation.csv'
    lead = ['Biochar (g/L)', 'S:I (gVS/gVS)', 'Legacy screening yield (L CH4/kg VS)', 'Legacy screening change vs S3 (%)']
    presentation = presentation[lead + [c for c in presentation.columns if c not in lead]]
    presentation.to_csv(destination)
    return destination
