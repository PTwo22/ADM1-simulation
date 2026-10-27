import os
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

def generate_all_plots(df_results, scenario_curves, output_dir="output"):
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
        plt.text(bar.get_x() + bar.get_width()/2, yval + 0.5, f'{yval}%', ha='center', va='bottom', fontweight='bold')

    plt.xlabel('Scenario ID', fontsize=12, fontweight='bold')
    plt.ylabel('Improvement Over Baseline (%)', fontsize=12, fontweight='bold')
    plt.title('Methane Yield Improvement from Fungal Pretreatment', fontsize=14, fontweight='bold')
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

    # specific methane yield (L/kgVS)
    plt.figure(figsize=(12, 6))
    scenarios_all = df_results["Scenario ID"]
    specific_yields = df_results["Specific Yield (L/kgVS)"]
    
    bars = plt.bar(scenarios_all, specific_yields, color='#9467bd', edgecolor='black', width=0.5)
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + 5, f'{yval:.1f}', ha='center', va='bottom', fontweight='bold', fontsize=9)

    plt.xlabel('Scenario ID', fontsize=12, fontweight='bold')
    plt.ylabel('Specific Yield (L/kgVS)', fontsize=12, fontweight='bold')
    plt.title('Specific Methane Yield by Scenario (Factoring Stability & OLR)', fontsize=14, fontweight='bold')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    plot4_path = os.path.join(output_dir, "specific_methane_yield.png")
    plt.savefig(plot4_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[+] Visualisation successfully saved to {plot4_path}")

    # practical yield improvement (stability & OLR adjusted)
    plt.figure(figsize=(12, 6))
    
    # extract the baseline specific yield (assumed to be the first row, S1)
    baseline_specific_yield = df_results["Specific Yield (L/kgVS)"].iloc[0]
    # isolate treated scenarios (skip S1)
    scenarios_treated = df_results["Scenario ID"][1:]
    treated_specific_yields = df_results["Specific Yield (L/kgVS)"][1:]
    # calculate practical percentage improvement over S1
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
    plt.ylabel('Practical Improvement Over Baseline (%)', fontsize=12, fontweight='bold')
    plt.title('Stability-Adjusted Specific Yield Improvement (vs S1)', fontsize=14, fontweight='bold')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    plot5_path = os.path.join(output_dir, "practical_yield_improvement.png")
    plt.savefig(plot5_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"[+] Visualization successfully saved to {plot5_path}")

def plot_composition_oat_comparison(df_results, output_dir="output"):
    """
    Compares the S3 reference against composition and NaOH OAT scenarios.
    """
    # filter the dataframe for the relevant scenarios
    target_scenarios = ['S3', 'S10', 'S11', 'S12', 'S13', 'S18', 'S19', 'S20']
    df_filtered = df_results[df_results['Scenario ID'].isin(target_scenarios)]
    
    if df_filtered.empty:
        print("[-] Target scenarios not found in data for OAT comparison.")
        return

    scenarios = df_filtered["Scenario ID"].tolist()
    yields = df_filtered["Specific Yield (L/kgVS)"].tolist()
    
    # calculate percentage difference relative to S3
    s3_yield = df_filtered[df_filtered['Scenario ID'] == 'S3']["Specific Yield (L/kgVS)"].iloc[0]
    
    plt.figure(figsize=(10, 6))
    
    colors = [
        '#1f77b4' if scenario_id == 'S3'
        else '#2ca02c' if scenario_id in {'S18', 'S19', 'S20'}
        else '#ff7f0e'
        for scenario_id in scenarios
    ]
    bars = plt.bar(scenarios, yields, color=colors, edgecolor='black', width=0.6)
    
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
    legend_items = [
        Patch(facecolor='#1f77b4', edgecolor='black', label='S3 reference'),
        Patch(facecolor='#ff7f0e', edgecolor='black', label='Composition scenarios'),
        Patch(facecolor='#2ca02c', edgecolor='black', label='NaOH scenarios'),
    ]
    plt.legend(handles=legend_items)
    plt.title('Composition and NaOH Sensitivities vs. S3 Reference', fontsize=14, fontweight='bold')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    plot_path = os.path.join(output_dir, "oat_composition_comparison.png")
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"[+] OAT Visualization successfully saved to {plot_path}")
