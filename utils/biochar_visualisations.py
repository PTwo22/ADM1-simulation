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
    selected = results.loc[selected.index].copy()
    selected.to_csv(out / 'biochar_inoculum_summary.csv', index=False)
    plot_combined_methane_yield(out)
    daily_rows = []
    for sid, data in curves.items():
        for day, cumulative, adjusted in zip(data['time'], data['methane'], data['adjusted']):
            daily_rows.append({'Scenario ID': sid, 'Day': day, 'Cumulative CH4 (Nm3)': cumulative,
                               'Adjusted cumulative CH4 (Nm3)': adjusted,
                               'Daily CH4 (Nm3/day)': 0.0 if day == 0 else data['daily'][int(day)-1]})
    pd.DataFrame(daily_rows).to_csv(supporting / 'biochar_inoculum_timeseries.csv', index=False)

    def save(name, ylabel):
        plt.ylabel(ylabel)
        plt.title('Exploratory sensitivity (uncalibrated)')
        plt.grid(axis='y', linestyle='--', alpha=.4)
        plt.tight_layout()
        plt.savefig(out / name, dpi=180)
        plt.close()

    plot_cumulative_methane_comparison(out)

    base = next(s for s in scenarios if s['id'] == 'S3')
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
    plt.figure(figsize=(10, 6))
    plt.plot(ratios['S:I (gVS/gVS)'], ratios[YIELD], marker='o', label='Sensitivity')
    for ratio, label in ((1, 'S3 reference'), (OFFICIAL_S24_SI, 'Official S24')):
        row = ratios[ratios['S:I (gVS/gVS)'] == ratio].iloc[0]
        plt.scatter([ratio], [row[YIELD]], s=80, label=label)
    plt.xlabel('S:I (g substrate VS / g inoculum VS)')
    plt.legend()
    save('inoculum_ratio_sensitivity.png', YIELD)
    from utils.biochar_verification import export_verification
    export_verification(selected, scenarios, run_scenario, volume, out)


def plot_combined_methane_yield(output_dir='output/s21_s24'):
    """Plot saved results only; no simulation or kinetic calculations."""
    from matplotlib.patches import Patch
    out = Path(output_dir)
    ids = ['S3', 'S21', 'S22', 'S23', 'S24']
    saved = pd.read_csv(out / 'biochar_inoculum_summary.csv').set_index('Scenario ID')
    frame = saved.loc[ids]
    if len(frame) != len(ids):
        raise ValueError('Expected exactly one row per comparison scenario')
    yields = frame[YIELD].to_numpy(dtype=float)
    if not np.isfinite(yields).all() or (yields < 0).any() or yields[0] <= 0:
        raise ValueError('Expected finite nonnegative yields and positive S3 reference')
    changes = (yields / yields[0] - 1) * 100
    reference_colour, biochar_colour, inoculum_colour = '#3569a8', '#43936c', '#d88a32'
    fig, ax = plt.subplots(figsize=(12, 7))
    positions = np.arange(len(ids))
    ax.bar(positions, yields, width=.62,
           color=[reference_colour, biochar_colour, biochar_colour, biochar_colour, inoculum_colour],
           edgecolor='white', zorder=3)
    ax.axhline(yields[0], color=reference_colour, linestyle='--', linewidth=1.5,
               label=f'S3 reference: {yields[0]:.2f} L CH\u2084/kg VS', zorder=4)
    for x, value, change in zip(positions, yields, changes):
        ax.annotate(f'{value:.2f}\n({change:+.3f}% vs S3)', (x, value),
                    xytext=(0, 8), textcoords='offset points', ha='center',
                    va='bottom', fontsize=11)
    ax.set_xticks(positions, ids)
    ax.set_xlabel('Scenario ID', fontsize=12)
    ax.set_ylabel('Adjusted 25-Day Methane Yield (L CH\u2084/kg VS)', fontsize=12)
    fig.suptitle('Predicted Methane Yield Comparison (S3 vs. S21\u2013S24)', fontsize=16, y=.97)
    ax.set_title('Exploratory simulation results (uncalibrated)', fontsize=11, pad=15)
    ax.set_ylim(0, yields.max() * 1.20)
    ax.set_axisbelow(True)
    ax.grid(axis='y', linestyle='--', alpha=.35)
    handles = [Patch(facecolor=reference_colour, label='S3: no biochar, S:I = 1'),
               Patch(facecolor=biochar_colour, label='S21\u2013S23: biochar 5, 10, 15 g/L'),
               Patch(facecolor=inoculum_colour, label=f'S24: S:I = {frame.loc["S24", "S:I (gVS/gVS)"]:g}'),
               ax.lines[0]]
    ax.legend(handles=handles, loc='upper center', bbox_to_anchor=(.5, -.13),
              ncol=2, frameon=False, fontsize=10)
    fig.tight_layout(rect=(0, .03, 1, .94))
    destination = out / 's21_s24_methane_yield_comparison.png'
    fig.savefig(destination, dpi=200, bbox_inches='tight')
    plt.close(fig)
    return destination


def plot_cumulative_methane_comparison(output_dir='output/s21_s24'):
    """Presentation curves read exclusively from saved stability-adjusted data."""
    out = Path(output_dir)
    saved = pd.read_csv(out / 'supporting' / 'biochar_inoculum_timeseries.csv')
    ids = ['S3', 'S21', 'S22', 'S23', 'S24']
    column = 'Adjusted cumulative CH4 (Nm3)'
    # Same Matplotlib colour-cycle order as the original five curves.
    colours = plt.rcParams['axes.prop_cycle'].by_key()['color']
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
        colour = colours[index % len(colours)]
        ax.plot(data['Day'], values, color=colour, label=sid, linewidth=2, zorder=3)
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
    presentation = out / 'biochar_inoculum_gompertz_curve_presentation.png'
    fig.savefig(standard, dpi=180)
    fig.savefig(presentation, dpi=300)
    plt.close(fig)
    return standard, presentation
