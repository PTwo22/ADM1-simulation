import os
import matplotlib.pyplot as plt

def generate_all_plots(df_results, scenario_curves, output_dir="output", reference_id="S1"):
    """Generates and saves all simulation visualisations to the designated output directory."""
    os.makedirs(output_dir, exist_ok=True)

    # baseline vs. Treated Methane Yield Bar Chart
    plt.figure(figsize=(14, 7))
    bar_width = 0.35
    indices = range(len(df_results))
    control_bars = [i - bar_width/2 for i in indices]
    treated_bars = [i + bar_width/2 for i in indices]

    plt.bar(control_bars, df_results["Control Yield (Nm3/d)"], bar_width, label='Control Yield', color='#1f77b4', edgecolor='black')
    plt.bar(treated_bars, df_results["Treated Yield (Nm3/d)"], bar_width, label='Treated Yield', color='#ff7f0e', edgecolor='black')

    plt.xlabel('Scenario ID', fontsize=12, fontweight='bold')
    plt.ylabel('Methane Yield (Nm³/d)', fontsize=12, fontweight='bold')
    plt.title('Baseline vs. Treated Methane Yield by Scenario', fontsize=14, fontweight='bold')
    plt.xticks(indices, df_results["Scenario ID"])
    plt.legend(fontsize=11)
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    plot1_path = os.path.join(output_dir, "methane_yield_comparison.png")
    plt.savefig(plot1_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[+] Visualisation successfully saved to {plot1_path}")

    # methane Improvement Percentage
    plt.figure(figsize=(12, 6))
    scenarios_treated = df_results["Scenario ID"][1:]
    improvement_values = df_results["Improvement (%)"][1:]
    
    bars = plt.bar(scenarios_treated, improvement_values, color='#2ca02c', edgecolor='black', width=0.5)
    for bar in bars:
        yval = bar.get_height()
        plt.annotate(f'{yval:.1f}%',
                     (bar.get_x() + bar.get_width()/2, yval),
                     xytext=(0, 6), textcoords='offset points',
                     ha='center', va='bottom', fontweight='bold', fontsize=9)

    plt.margins(y=0.15)

    plt.xlabel('Scenario ID', fontsize=12, fontweight='bold')
    plt.ylabel('Improvement Over Untreated Control (%)', fontsize=12, fontweight='bold')
    plt.title('Reported Methane Improvement vs. Untreated Control', fontsize=14, fontweight='bold')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    plot2_path = os.path.join(output_dir, "methane_improvement.png")
    plt.savefig(plot2_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[+] Visualisation successfully saved to {plot2_path}")

    # Gompertz Curves (Time Series)
    plt.figure(figsize=(12, 7))
    for scenario_id, data in scenario_curves.items():
        plt.plot(data["time"], data["methane"], label=f'Scenario {scenario_id}', linewidth=2)

    plt.xlabel('Digestion Time (Days)', fontsize=12, fontweight='bold')
    plt.ylabel('Cumulative Methane (Nm³)', fontsize=12, fontweight='bold')
    plt.title('Daily Cumulative Methane Production (Treated Scenarios)', fontsize=14, fontweight='bold')
    plt.legend(fontsize=10, loc='upper left')
    plt.grid(True, linestyle='--', alpha=0.7)

    plot3_path = os.path.join(output_dir, "all_scenarios_gompertz_curve.png")
    plt.savefig(plot3_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[+] Visualisation successfully saved to {plot3_path}")

    # Reported screening yield: preserve the inherited nominal-loading convention.
    from matplotlib.patches import Patch
    fig, ax = plt.subplots(figsize=(16, 8))
    scenarios_all = df_results["Scenario ID"]
    specific_yields = df_results["Specific Yield (L/kgVS)"]
    reference_yield = df_results.loc[
        df_results['Scenario ID'] == reference_id, 'Specific Yield (L/kgVS)'
    ].iloc[0]
    groups = [
        ('S3 reference' if reference_id == 'S3' else f'{reference_id} reference', '#246f99'),
        ('Feedstock composition', '#df9234'),
        ('Microbial activity (+20%)', '#579bb0'),
        ('NaOH pretreatment', '#37996e'),
        ('Biochar / inoculum', '#8975b5'),
    ]
    def scenario_colour(sid):
        number = int(sid[1:])
        group = 0 if sid == reference_id else 1 if 10 <= number <= 13 else 2 if 14 <= number <= 17 else 3 if 18 <= number <= 20 else 4
        return groups[group][1]
    bars = ax.bar(scenarios_all, specific_yields,
                  color=[scenario_colour(sid) for sid in scenarios_all], width=0.68)
    for sid, bar in zip(scenarios_all, bars):
        yval = bar.get_height()
        centre = bar.get_x() + bar.get_width()/2
        ax.annotate(f'{yval:.1f}', (centre, yval), xytext=(0, 5),
                    textcoords='offset points', ha='center', va='bottom', fontweight='bold', fontsize=10)
        change = (yval / reference_yield - 1) * 100
        label = 'Base' if sid == reference_id else f'{change:+.2f}%' if abs(change) >= 0.005 else '0.00%'
        ax.annotate(label, (centre, yval), xytext=(0, -15),
                    textcoords='offset points', ha='center', va='top',
                    color='white', fontweight='bold', fontsize=8)
    ax.axhline(reference_yield, color='#627581', linestyle='--', linewidth=1.3, zorder=0)
    ax.set_xlabel('Scenario', fontsize=12)
    ax.set_ylabel('Reported methane screening yield (L/kg VS)', fontsize=12)
    ax.set_title(f'Predicted Methane Yield Compared with {reference_id}', fontsize=17, fontweight='bold', pad=18)
    ax.set_ylim(0, specific_yields.max() * 1.17)
    ax.legend(handles=[Patch(color=colour, label=label) for label, colour in groups],
              loc='upper right', frameon=False, fontsize=10)
    ax.grid(axis='y', linestyle=':', alpha=0.25)
    ax.set_axisbelow(True)
    ax.spines[['top', 'right']].set_visible(False)
    fig.tight_layout()
    
    main_results_dir = os.path.join(os.path.dirname(output_dir), "main_results")
    os.makedirs(main_results_dir, exist_ok=True)
    plot4_path = os.path.join(main_results_dir, "01_MAIN_methane_yield_S3_S10-S24.png")
    plt.savefig(plot4_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[+] Visualisation successfully saved to {plot4_path}")

    # practical yield improvement (stability & OLR adjusted)
    plt.figure(figsize=(12, 6))
    
    # Use the explicitly selected reference, not the row position.
    baseline_specific_yield = df_results.loc[
        df_results['Scenario ID'] == reference_id, 'Specific Yield (L/kgVS)'
    ].iloc[0]
    comparison_rows = df_results[df_results['Scenario ID'] != reference_id]
    scenarios_treated = comparison_rows['Scenario ID']
    treated_specific_yields = comparison_rows['Specific Yield (L/kgVS)']
    # Calculate specific-yield percentage differences from the reference.
    practical_improvement = ((treated_specific_yields - baseline_specific_yield) / baseline_specific_yield) * 100.0
    # color bars green if positive, red if negative
    colors = ['#2ca02c' if val >= 0 else '#d62728' for val in practical_improvement]
    
    bars = plt.bar(scenarios_treated, practical_improvement, color=colors, edgecolor='black', width=0.5)
    
    for bar in bars:
        yval = bar.get_height()
        # Adjust text placement based on whether the bar goes up or down
        offset = 1.0 if yval >= 0 else -2.5
        va = 'bottom' if yval >= 0 else 'top'
        plt.text(bar.get_x() + bar.get_width()/2, yval + offset, f'{yval:.1f}%', ha='center', va=va, fontweight='bold', fontsize=9)

    plt.axhline(0, color='black', linewidth=1.2) # baseline reference line
    plt.xlabel('Scenario ID', fontsize=12, fontweight='bold')
    plt.ylabel(f'Practical Improvement Over {reference_id} (%)', fontsize=12, fontweight='bold')
    plt.title(f'Stability-Adjusted Specific Yield Improvement (vs {reference_id})', fontsize=14, fontweight='bold')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    plot5_path = os.path.join(output_dir, "practical_yield_improvement.png")
    plt.savefig(plot5_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"[+] Visualization successfully saved to {plot5_path}")

def plot_composition_oat_comparison(df_results, output_dir="output"):
    """
    Generates a targeted bar chart comparing the S3 reference against 
    the composition OAT scenarios (S10, S11, S12).
    """
    # filter the dataframe for the relevant scenarios
    target_scenarios = ['S3', 'S10', 'S11', 'S12', 'S13']
    df_filtered = df_results[df_results['Scenario ID'].isin(target_scenarios)]
    
    if df_filtered.empty:
        print("[-] Target scenarios not found in data for OAT comparison.")
        return

    scenarios = df_filtered["Scenario ID"].tolist()
    yields = df_filtered["Specific Yield (L/kgVS)"].tolist()
    
    # calculate percentage difference relative to S3
    s3_yield = df_filtered[df_filtered['Scenario ID'] == 'S3']["Specific Yield (L/kgVS)"].iloc[0]
    
    plt.figure(figsize=(10, 6))
    
    # colors = ['#1f77b4' if s == 'S3' else '#ff7f0e' for s in scenarios]
    bars = plt.bar(scenarios, yields, color='#1f77b4', edgecolor='black', width=0.6)
    
    for bar, scenario_id, yval in zip(bars, scenarios, yields):
        # Annotate absolute value
        plt.text(bar.get_x() + bar.get_width()/2, yval + 5, f'{yval:.1f}', 
                 ha='center', va='bottom', fontweight='bold')
        
        # Annotate percentage difference from S3 (Equation 88)
        if scenario_id != 'S3':
            pct_diff = ((yval - s3_yield) / s3_yield) * 100.0
            sign = "+" if pct_diff > 0 else ""
            plt.text(bar.get_x() + bar.get_width()/2, yval / 2, f'{sign}{pct_diff:.1f}%', 
                     ha='center', va='center', color='white', fontweight='bold')

    plt.axhline(s3_yield, color='black', linestyle='--', linewidth=1.2, alpha=0.7)
    plt.xlabel('Scenario ID', fontsize=12, fontweight='bold')
    plt.ylabel('Specific Methane Yield (L/kgVS)', fontsize=12, fontweight='bold')
    plt.title('Food Waste Composition Sensitivities vs. S3 Reference', fontsize=14, fontweight='bold')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    plot_path = os.path.join(output_dir, "oat_composition_comparison.png")
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"[+] OAT Visualization successfully saved to {plot_path}")


def plot_microbial_oat_comparison(df_results, output_dir="output"):
    """Compares microbial kinetic OAT scenarios (S14-S17) against S3 reference."""
    target_scenarios = ['S3', 'S14', 'S15', 'S16', 'S17']
    df_filtered = df_results[df_results['Scenario ID'].isin(target_scenarios)]
    
    if df_filtered.empty:
        return

    scenarios = df_filtered["Scenario ID"].tolist()
    yields = df_filtered["Specific Yield (L/kgVS)"].tolist()
    s3_yield = df_filtered[df_filtered['Scenario ID'] == 'S3']["Specific Yield (L/kgVS)"].iloc[0]
    
    plt.figure(figsize=(10, 6))
    colors = ['#1f77b4' if s == 'S3' else '#9467bd' for s in scenarios]
    bars = plt.bar(scenarios, yields, color=colors, edgecolor='black', width=0.6)
    
    for bar, scenario_id, yval in zip(bars, scenarios, yields):
        plt.text(bar.get_x() + bar.get_width()/2, yval + 5, f'{yval:.1f}', ha='center', va='bottom', fontweight='bold')
        if scenario_id != 'S3':
            pct_diff = ((yval - s3_yield) / s3_yield) * 100.0
            sign = "+" if pct_diff > 0 else ""
            plt.text(bar.get_x() + bar.get_width()/2, yval / 2, f'{sign}{pct_diff:.1f}%', ha='center', va='center', color='white', fontweight='bold')

    plt.axhline(s3_yield, color='black', linestyle='--', linewidth=1.2, alpha=0.7)
    plt.title('Microbial Kinetic Sensitivities vs. S3 Reference', fontsize=14, fontweight='bold')
    plt.savefig(os.path.join(output_dir, "oat_microbial_comparison.png"), dpi=300, bbox_inches='tight')
    plt.close()

def plot_composition_gompertz_curves(scenario_curves, output_dir="output"):
    target_scenarios = ['S3', 'S10', 'S11', 'S12', 'S13']
    
    plt.figure(figsize=(12, 7))
    
    for scenario_id in target_scenarios:
        if scenario_id in scenario_curves:
            data = scenario_curves[scenario_id]
            if scenario_id == 'S3':
                plt.plot(data["time"], data["methane"], label=f'{scenario_id} (Reference)', linewidth=2, linestyle='--', color='black')
            else:
                plt.plot(data["time"], data["methane"], label=f'{scenario_id}', linewidth=2)

    plt.xlabel('Digestion Time (Days)', fontsize=12, fontweight='bold')
    plt.ylabel('Cumulative Methane (Nm³)', fontsize=12, fontweight='bold')
    plt.title('Cumulative Methane Production (Composition OAT vs S3)', fontsize=14, fontweight='bold')
    
    plt.legend(fontsize=10, loc='lower right')
    plt.grid(True, linestyle='--', alpha=0.7)

    plot_path = os.path.join(output_dir, "composition_gompertz_curves.png")
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()


def plot_microbial_ode_curves(scenario_curves, output_dir="output"):
    target_scenarios = ['S3', 'S14', 'S15', 'S16', 'S17']
    plt.figure(figsize=(12, 7))

    for scenario_id in target_scenarios:
        if scenario_id in scenario_curves:
            data = scenario_curves[scenario_id]
            if scenario_id == 'S3':
                # S3 remains the empirical Gompertz reference
                plt.plot(data["time"], data["methane"], label=f'{scenario_id} (Gompertz Baseline)', linewidth=2, linestyle='--', color='black')
            else:
                # S14-S17 are generated by the ADM1 ODE solver
                plt.plot(data["time"], data["methane"], label=f'{scenario_id} (Mechanistic ODE)', linewidth=2)

    plt.xlabel('Digestion Time (Days)', fontsize=12, fontweight='bold')
    plt.ylabel('Cumulative Methane (Nm³)', fontsize=12, fontweight='bold')
    plt.title('Dynamic Methane Production (Microbial Kinetic OAT vs S3)', fontsize=14, fontweight='bold')
    plt.legend(fontsize=10, loc='lower right')
    plt.grid(True, linestyle='--', alpha=0.7)

    plot_path = os.path.join(output_dir, "microbial_ode_curves.png")
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
