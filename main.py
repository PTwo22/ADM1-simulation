import os
import pandas as pd
import matplotlib.pyplot as plt

from data.config import *

from AD.feedstock import Feedstock
from pretreatment.pretreatment import Pretreatment
from AD.digester import Digester

# create an output directory for CSVs and plots if it doesn't exist
os.makedirs("output", exist_ok=True)

# ==========================================
# Units:
# - enzyme_dose: U g⁻¹ VS
# - t_pre: hours (h)
# - scg: percentage (%)
# - olr: kg VS m⁻³ d⁻¹
# - hrt: days (d)
# ==========================================
scenarios = [
    {"id": "S1", "description": "Control food waste; no pretreatment", "enzyme_dose": 0, "t_pre": 0, "scg": 0.0, "olr": 2.5, "hrt": 25},
    {"id": "S2", "description": "Low fungal pretreatment", "enzyme_dose": 30, "t_pre": 12, "scg": 0.0, "olr": 2.5, "hrt": 25},
    {"id": "S3", "description": "Moderate fungal pretreatment", "enzyme_dose": 60, "t_pre": 24, "scg": 0.0, "olr": 2.5, "hrt": 25},
    {"id": "S4", "description": "High fungal pretreatment", "enzyme_dose": 90, "t_pre": 36, "scg": 0.0, "olr": 2.5, "hrt": 25},
    {"id": "S5", "description": "Extended fungal pretreatment", "enzyme_dose": 90, "t_pre": 72, "scg": 0.0, "olr": 2.5, "hrt": 25},
    {"id": "S6", "description": "Moderate pretreatment + 10% SCG", "enzyme_dose": 60, "t_pre": 24, "scg": 10.0, "olr": 2.5, "hrt": 25},
    {"id": "S7", "description": "Moderate pretreatment + 20% SCG", "enzyme_dose": 60, "t_pre": 24, "scg": 20.0, "olr": 2.5, "hrt": 25},
    {"id": "S8", "description": "Moderate pretreatment + 30% SCG", "enzyme_dose": 60, "t_pre": 24, "scg": 30.0, "olr": 2.5, "hrt": 25},
    {"id": "S9", "description": "Moderate pretreatment + 10% SCG + high OLR", "enzyme_dose": 60, "t_pre": 24, "scg": 10.0, "olr": 4.5, "hrt": 20},
]

# Global/Environmental Assumptions for the pipeline
F_TS = 0.35          # Assumed: 35% Total Solids in raw feed
F_VS_TS = 0.95       # Assumed: 95% Volatile Solids / Total Solids
REACTOR_VOL = 1.0    # Assumed: 1 cubic meter baseline reactor volume
T_PRE = 30.0         # Assumed: Pretreatment operates at 30 deg C
PH_PRE = 5.5         # Assumed: Pretreatment operates at pH 5.5

def main():

    results_summary = []

    # main simulation Loop
    for scenario in scenarios:
        
        # back-calculate Feedstock Wet Mass based on daily OLR. 
        m_vs_daily = scenario["olr"] * REACTOR_VOL
        m_wet_daily = m_vs_daily / (F_TS * F_VS_TS)
        
        # convert SCG percentage (e.g., 10.0) to fractions (e.g., 0.10) for the Feedstock class
        scg_fraction = scenario["scg"] / 100.0
        
        # map the universal enzyme dose from the scenario to all specific classes
        doses = {
            'carb': scenario["enzyme_dose"], 
            'protein': scenario["enzyme_dose"], 
            'lipid': scenario["enzyme_dose"], 
            'inert': scenario["enzyme_dose"]
        }
        
        # instantiate Feedstock
        feedstock = Feedstock(
            m_wet=m_wet_daily,
            f_ts=F_TS,
            f_vs_ts=F_VS_TS,
            f_scg=scg_fraction,
            fw_fractions=FW_FRACTIONS,
            scg_fractions=SCG_FRACTIONS
        )
        
        # instantiate Pretreatment
        config_dict = {
            'DIGESTER_CALIBRATION': DIGESTER_CALIBRATION,
            'DIGESTER_BASELINES': DIGESTER_BASELINES,
            'BMP_CONSTANTS': BMP_CONSTANTS
        }
        
        pretreatment = Pretreatment(
            temp_pre=T_PRE,
            ph_pre=PH_PRE,
            time_pre=scenario["t_pre"],
            enzyme_doses=doses,
            config=PRETREATMENT_CONFIG,
            weights=FPSI_WEIGHTS
        )
        
        # instantiate Digester
        digester = Digester(feedstock=feedstock, pretreatment=pretreatment, config=config_dict)
        
        # extract Data into Dictionary matching your target output structure
        results_summary.append({
            "Scenario ID": scenario["id"],
            "Scenario": scenario["description"],
            "SCG ratio (%)": scenario["scg"],
            "FPSI": round(pretreatment.fpsi, 3),
            "k_hyd modified (1/day)": round(digester.modified_kinetics['k_hyd_modified'], 3),
            "Lag phase modified (days)": round(digester.modified_kinetics['lag_modified'], 3),
            "Control Yield (Nm3/d)": round(digester.y_ch4_control, 3),
            "Treated Yield (Nm3/d)": round(digester.y_ch4_treated, 3),
            "Improvement (%)": round(digester.yield_improvement, 3),
            "Energy CH4 (MJ)": round(digester.energy['E_CH4_treated'], 3),
            "Electricity potential (MJ)": round(digester.energy['E_electricity'], 3)
        })

    # convert to Pandas DataFrame
    df_results = pd.DataFrame(results_summary)

    # print to console
    print("=== SIMULATION RESULTS ===")
    print(df_results.to_string(index=False))

    # ==========================================
    # * OUTPUT GENERATION: CSV & VISUALIZATIONS
    # ==========================================

    # export to CSV
    csv_file_path = os.path.join("output", "scenario_summary.csv")
    df_results.to_csv(csv_file_path, index=False)
    print(f"\n[+] Results successfully saved to {csv_file_path}")

    # generate and Save Bar Chart (Control vs Treated Methane Yield)
    plt.figure(figsize=(14, 7))

    # get bar widths and index positions
    bar_width = 0.35
    indices = range(len(df_results))
    control_bars = [i - bar_width/2 for i in indices]
    treated_bars = [i + bar_width/2 for i in indices]

    # plot the bars
    plt.bar(control_bars, df_results["Control Yield (Nm3/d)"], bar_width, label='Control Yield', color='#1f77b4', edgecolor='black')
    plt.bar(treated_bars, df_results["Treated Yield (Nm3/d)"], bar_width, label='Treated Yield', color='#ff7f0e', edgecolor='black')

    # formatting the plot
    plt.xlabel('Scenario ID', fontsize=12, fontweight='bold')
    plt.ylabel('Methane Yield (Nm³/d)', fontsize=12, fontweight='bold')
    plt.title('Baseline vs. Treated Methane Yield by Scenario', fontsize=14, fontweight='bold')
    plt.xticks(indices, df_results["Scenario ID"])
    plt.legend(fontsize=11)
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    # save the plot
    plot_file_path = os.path.join("output", "methane_yield_comparison.png")
    plt.savefig(plot_file_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[+] Methane yield visualisation successfully saved to {plot_file_path}")

    # generate and save bar chart (Methane Improvement Percentage)
    plt.figure(figsize=(12, 6))
    
    # Exclude Scenario 1 (Baseline) from the improvement plot since it is always 0%
    scenarios_treated = df_results["Scenario ID"]
    improvement_values = df_results["Improvement (%)"]
    
    # Plot the bar chart
    bars = plt.bar(scenarios_treated, improvement_values, color='#2ca02c', edgecolor='black', width=0.5)
    
    # Add percentage labels on top of each bar
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + 0.5, f'{yval}%', ha='center', va='bottom', fontweight='bold')

    # Formatting the plot
    plt.xlabel('Scenario ID', fontsize=12, fontweight='bold')
    plt.ylabel('Improvement Over Baseline (%)', fontsize=12, fontweight='bold')
    plt.title('Methane Yield Improvement from Fungal Pretreatment', fontsize=14, fontweight='bold')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Save the plot
    improvement_plot_path = os.path.join("output", "methane_improvement.png")
    plt.savefig(improvement_plot_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"[+] Methane improvement visualisation successfully saved to {improvement_plot_path}")
    

if __name__ == "__main__":
    main()