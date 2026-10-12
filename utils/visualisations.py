import os
import matplotlib.pyplot as plt

def generate_all_plots(df_results, scenario_curves, output_dir="output"):
    """Generates and saves all simulation visualisations to the designated output directory."""
    os.makedirs(output_dir, exist_ok=True)

    # 1. Baseline vs. Treated Methane Yield Bar Chart
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

    # 2. Methane Improvement Percentage
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

    # 3. Gompertz Curves (Time Series)
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

    # 4. Specific Methane Yield (L/kgVS)
    plt.figure(figsize=(12, 6))
    scenarios_all = df_results["Scenario ID"]
    specific_yields = df_results["Specific Yield (L/kgVS)"]
    
    bars = plt.bar(scenarios_all, specific_yields, color='#9467bd', edgecolor='black', width=0.5)
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + 5, f'{yval:.1f}', ha='center', va='bottom', fontweight='bold', fontsize=9)

    plt.xlabel('Scenario ID', fontsize=12, fontweight='bold')
    plt.ylabel('Specific Yield (L/kgVS)', fontsize=12, fontweight='bold')
    plt.title('Specific Methane Yield by Scenario (Factoring Risk & OLR)', fontsize=14, fontweight='bold')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    plot4_path = os.path.join(output_dir, "specific_methane_yield.png")
    plt.savefig(plot4_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[+] Visualisation successfully saved to {plot4_path}")