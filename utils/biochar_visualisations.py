"""Exports use the same finite-charge, stability-adjusted 25-day metric."""
from copy import deepcopy
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from AD.biochar_inoculum import evaluate_batch
from data.biochar_config import SI_LEVELS

YIELD = 'Adjusted batch specific CH4 at 25d (L/kgVS)'
CHANGE = 'Adjusted batch yield change vs S3 (%)'


def export_biochar_analysis(results, curves, scenarios, run_scenario, volume):
    out = Path('output')
    out.mkdir(exist_ok=True)
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
    pd.DataFrame(daily_rows).to_csv(out / 'biochar_inoculum_timeseries.csv', index=False)

    def save(name, ylabel):
        plt.ylabel(ylabel)
        plt.title('Exploratory sensitivity (uncalibrated)')
        plt.grid(axis='y', linestyle='--', alpha=.4)
        plt.tight_layout()
        plt.savefig(out / name, dpi=180)
        plt.close()

    def bars(frame, column, filename):
        plt.figure(figsize=(10, 6))
        positions = np.arange(len(frame))
        plt.bar(positions, frame[column])
        plt.xticks(positions, frame['Scenario ID'])
        for x, (_, row) in zip(positions, frame.iterrows()):
            plt.annotate(f"{row[column]:.2f} ({row[CHANGE]:+.2f}%)" if column == YIELD else f"{row[column]:+.2f}%",
                         (x, row[column]), xytext=(0, 5), textcoords='offset points', ha='center')
        plt.margins(y=.2)
        plt.xlabel('Scenario ID')
        save(filename, column)

    bars(selected[selected['Scenario ID'] != 'S24'], YIELD, 'biochar_methane_yield.png')
    plt.figure(figsize=(10, 6))
    for sid in ids:
        plt.plot(curves[sid]['time'], curves[sid]['methane'], label=sid)
    plt.xlabel('Digestion time (days); single fixed substrate charge')
    plt.legend()
    save('biochar_inoculum_gompertz_curve.png', 'Cumulative treated CH4 (Nm3), before stability penalty')

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

    doses = sensitivity('biochar_g_L', np.linspace(0, 30, 61))
    doses.to_csv(out / 'biochar_dose_sensitivity.csv', index=False)
    plt.figure(figsize=(10, 6))
    plt.plot(doses['Biochar (g/L)'], doses[YIELD], label='Assumed kinetic response')
    official = selected[selected['Scenario ID'] != 'S24']
    plt.scatter(official['Biochar (g/L)'], official[YIELD], label='Official cases')
    plt.xlabel('RHB550 biochar concentration (g/L)')
    plt.legend()
    save('biochar_dose_response.png', YIELD)

    ratios = sensitivity('si_ratio', SI_LEVELS)
    ratios['Role'] = ['Official S24' if r == 2 else 'S3 reference' if r == 1 else 'Additional sensitivity' for r in SI_LEVELS]
    ratios.to_csv(out / 'inoculum_ratio_sensitivity.csv', index=False)
    plt.figure(figsize=(10, 6))
    plt.plot(ratios['S:I (gVS/gVS)'], ratios[YIELD], marker='o', label='Sensitivity')
    for ratio, label in ((1, 'S3 reference'), (2, 'Official S24')):
        row = ratios[ratios['S:I (gVS/gVS)'] == ratio].iloc[0]
        plt.scatter([ratio], [row[YIELD]], s=80, label=label)
    plt.xlabel('S:I (g substrate VS / g inoculum VS)')
    plt.legend()
    save('inoculum_ratio_sensitivity.png', YIELD)
    bars(selected[selected['Scenario ID'] != 'S3'], CHANGE, 'biochar_inoculum_improvement.png')


def plot_combined_methane_yield(output_dir='output'):
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
               Patch(facecolor=inoculum_colour, label='S24: S:I = 2'),
               ax.lines[0]]
    ax.legend(handles=handles, loc='upper center', bbox_to_anchor=(.5, -.13),
              ncol=2, frameon=False, fontsize=10)
    fig.tight_layout(rect=(0, .03, 1, .94))
    destination = out / 's21_s24_methane_yield_comparison.png'
    fig.savefig(destination, dpi=200, bbox_inches='tight')
    plt.close(fig)
    return destination
