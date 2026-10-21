import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

from data.config import *
from AD.feedstock import Feedstock
from pretreatment.pretreatment import Pretreatment
from AD.digester import Digester

from utils.visualisations import generate_all_plots, plot_composition_oat_comparison

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
# scenarios = [
#     {"id": "S1", "description": "Control food waste; no pretreatment", "enzyme_dose": 0, "t_pre": 0, "scg": 0.0, "olr": 2.5, "hrt": 25},
#     {"id": "S2", "description": "Low fungal pretreatment", "enzyme_dose": 30, "t_pre": 12, "scg": 0.0, "olr": 2.5, "hrt": 25},
#     {"id": "S3", "description": "Moderate fungal pretreatment", "enzyme_dose": 60, "t_pre": 24, "scg": 0.0, "olr": 2.5, "hrt": 25},
#     {"id": "S4", "description": "High fungal pretreatment", "enzyme_dose": 90, "t_pre": 36, "scg": 0.0, "olr": 2.5, "hrt": 25},
#     {"id": "S5", "description": "Extended fungal pretreatment", "enzyme_dose": 90, "t_pre": 72, "scg": 0.0, "olr": 2.5, "hrt": 25},
#     {"id": "S6", "description": "Moderate pretreatment + 10% SCG", "enzyme_dose": 60, "t_pre": 24, "scg": 10.0, "olr": 2.5, "hrt": 25},
#     {"id": "S7", "description": "Moderate pretreatment + 20% SCG", "enzyme_dose": 60, "t_pre": 24, "scg": 20.0, "olr": 2.5, "hrt": 25},
#     {"id": "S8", "description": "Moderate pretreatment + 30% SCG", "enzyme_dose": 60, "t_pre": 24, "scg": 30.0, "olr": 2.5, "hrt": 25},
#     {"id": "S9", "description": "Moderate pretreatment + 10% SCG + high OLR", "enzyme_dose": 60, "t_pre": 24, "scg": 10.0, "olr": 4.5, "hrt": 20},
# ]

scenarios = [
    # S1-S9
    {"id": "S1", "description": "Control food waste", "enzyme_dose": 0, "t_pre": 0, "mixture_ratios": {"FW": 1.0}, "profiles": {"FW": FW_FRACTIONS}, "olr": 2.5, "hrt": 25},
    {"id": "S2", "description": "Low fungal pretreatment", "enzyme_dose": 30, "t_pre": 12, "mixture_ratios": {"FW": 1.0}, "profiles": {"FW": FW_FRACTIONS}, "olr": 2.5, "hrt": 25},
    {"id": "S3", "description": "Moderate fungal pretreatment (Reference)", "enzyme_dose": 60, "t_pre": 24, "mixture_ratios": {"FW": 1.0}, "profiles": {"FW": FW_FRACTIONS}, "olr": 2.5, "hrt": 25},
    {"id": "S4", "description": "High fungal pretreatment", "enzyme_dose": 90, "t_pre": 36, "mixture_ratios": {"FW": 1.0}, "profiles": {"FW": FW_FRACTIONS}, "olr": 2.5, "hrt": 25},
    {"id": "S5", "description": "Extended fungal pretreatment", "enzyme_dose": 90, "t_pre": 72, "mixture_ratios": {"FW": 1.0}, "profiles": {"FW": FW_FRACTIONS}, "olr": 2.5, "hrt": 25},
    {"id": "S6", "description": "Moderate pretreatment + 10% SCG", "enzyme_dose": 60, "t_pre": 24, "mixture_ratios": {"FW": 0.90, "SCG": 0.10}, "profiles": {"FW": FW_FRACTIONS, "SCG": SCG_FRACTIONS}, "olr": 2.5, "hrt": 25},
    {"id": "S7", "description": "Moderate pretreatment + 20% SCG", "enzyme_dose": 60, "t_pre": 24, "mixture_ratios": {"FW": 0.80, "SCG": 0.20}, "profiles": {"FW": FW_FRACTIONS, "SCG": SCG_FRACTIONS}, "olr": 2.5, "hrt": 25},
    {"id": "S8", "description": "Moderate pretreatment + 30% SCG", "enzyme_dose": 60, "t_pre": 24, "mixture_ratios": {"FW": 0.70, "SCG": 0.30}, "profiles": {"FW": FW_FRACTIONS, "SCG": SCG_FRACTIONS}, "olr": 2.5, "hrt": 25},
    {"id": "S9", "description": "Moderate pretreatment + 10% SCG + high OLR", "enzyme_dose": 60, "t_pre": 24, "mixture_ratios": {"FW": 0.90, "SCG": 0.10}, "profiles": {"FW": FW_FRACTIONS, "SCG": SCG_FRACTIONS}, "olr": 4.5, "hrt": 20},
    
    # S10-S13
    {"id": "S10", "description": "Carbohydrate-rich (Cooked Rice)", "enzyme_dose": 60, "t_pre": 24, "mixture_ratios": {"Rice": 1.0}, "profiles": {"Rice": S10_FRACTIONS}, "olr": 2.5, "hrt": 25},
    {"id": "S11", "description": "Protein-rich (Meat Waste)", "enzyme_dose": 60, "t_pre": 24, "mixture_ratios": {"Meat": 1.0}, "profiles": {"Meat": S11_FRACTIONS}, "olr": 2.5, "hrt": 25},
    {"id": "S12", "description": "Lipid-rich (Plant Oil)", "enzyme_dose": 60, "t_pre": 24, "mixture_ratios": {"Oil": 1.0}, "profiles": {"Oil": S12_FRACTIONS}, "olr": 2.5, "hrt": 25},
    {"id": "S13", "description": "Fibre-rich (Banana Peel)", "enzyme_dose": 60, "t_pre": 24, "mixture_ratios": {"Peel": 1.0}, "profiles": {"Peel": S13_FRACTIONS}, "olr": 2.5, "hrt": 25}
]

# Global/Environmental Assumptions for the pipeline
F_TS = 0.25          # published sim variable
F_VS_TS = 0.90       # published sim variable
REACTOR_VOL = 1.0    # assumed: 1 cubic meter baseline reactor volume - 
T_PRE = 30.0         # published sim variable
PH_PRE = 5.5         # published sim variable

from data.biochar_config import extend_scenarios
from AD.biochar_inoculum import evaluate_batch

scenarios.extend(extend_scenarios(scenarios))


def run_scenario(scenario):
    """Shared construction for legacy scenarios and OAT sensitivity runs."""
    m_wet = 10.0 if scenario['olr'] <= 2.5 else scenario['olr'] * REACTOR_VOL / (F_TS * F_VS_TS)
    feedstock = Feedstock(m_wet, F_TS, F_VS_TS, scenario['mixture_ratios'], scenario['profiles'])
    doses = {i: scenario['enzyme_dose'] for i in ('carb', 'protein', 'lipid', 'inert')}
    pretreatment = Pretreatment(T_PRE, PH_PRE, scenario['t_pre'], doses, PRETREATMENT_CONFIG, FPSI_WEIGHTS)
    config = {k: globals()[k] for k in ('DIGESTER_CALIBRATION', 'DIGESTER_BASELINES', 'BMP_CONSTANTS',
                                     'RISK_THRESHOLDS', 'STABILITY_WEIGHTS', 'DIGESTER_CONDITIONS')}
    return feedstock, pretreatment, Digester(feedstock, pretreatment, config), config


def main(scenario_ids=None):

    results_summary = []
    scenario_curves = {}
    batch_curves = {}

    # main simulation Loop
    for scenario in scenarios:
        
        if scenario_ids is not None and scenario["id"] not in scenario_ids:
            continue
        feedstock, pretreatment, digester, config_dict = run_scenario(scenario)
        # calculate the Gompertz curve for all
        time_array = np.linspace(0, scenario["hrt"], num=scenario["hrt"] + 1)
        treated_curve = digester.calculate_gompertz_curve(time_array, is_treated=True)

        # store the curve to plot later
        scenario_curves[scenario["id"]] = {
            "time": time_array,
            "methane": treated_curve
        }
        # calculate risks and practical yields
        practical_data = digester.get_practical_yields(scenario["olr"], config_dict)

        # generate a string showing the feed composition (e.g. "FW: 100.0%")
        mixture_str = ", ".join([f"{k}: {v*100}%" for k, v in scenario["mixture_ratios"].items()])
        
        batch_row = {}
        if scenario['id'] in ('S3', 'S21', 'S22', 'S23', 'S24'):
            batch_row, batch_curves[scenario['id']] = evaluate_batch(digester, scenario, config_dict, REACTOR_VOL)

        results_summary.append({
            **batch_row,
            "Scenario ID": scenario["id"],
            "Scenario": scenario["description"],
            "Feedstock Mixture": mixture_str,
            "FPSI": round(pretreatment.fpsi, 3),
            "k_hyd modified (1/day)": round(digester.modified_kinetics['k_hyd_modified'], 3),
            "Lag phase modified (days)": round(digester.modified_kinetics['lag_modified'], 3),
            "Control Yield (Nm3/d)": round(digester.y_ch4_control, 3),
            "Treated Yield (Nm3/d)": round(digester.y_ch4_treated, 3),
            "Improvement (%)": round(digester.yield_improvement, 3),
            "Energy CH4 (MJ)": round(digester.energy['E_CH4_treated'], 3),
            "Electricity potential (MJ)": round(digester.energy['E_electricity'], 3),
            "R_total": round(practical_data['R_total'], 3),
            "Stability score": round(practical_data['Stability'], 3),
            "Specific Yield (L/kgVS)": round(practical_data['Specific_Yield_L_kgVS'], 3),
            "SCOD increase (%)": round(digester.modified_kinetics["scod_increase_pct"], 3),
            "Predicted CH4 fraction in raw biogas (%)": round(digester.biogas_profile['ch4_fraction_pct'], 3),
            "CO2 volume (m3)": round(digester.biogas_profile['co2_volume_m3'], 3),
            "Biogas volume (m3)": round(digester.biogas_profile['biogas_volume_m3'], 3),
        })

    # convert to Pandas DataFrame
    df_results = pd.DataFrame(results_summary)

    from utils.biochar_visualisations import export_biochar_analysis
    export_biochar_analysis(df_results, batch_curves, scenarios, run_scenario, REACTOR_VOL)

    # print to console
    print("=== SIMULATION RESULTS ===")
    print(df_results.to_string(index=False))

    # ==========================================
    # * OUTPUT GENERATION: CSV & VISUALIZATIONS
    # ==========================================

    # export to CSV
    csv_file_path = os.path.join("output", "scenario_summary.csv")
    if scenario_ids is not None and os.path.exists(csv_file_path):
        previous = pd.read_csv(csv_file_path)
        previous = previous[~previous['Scenario ID'].isin(df_results['Scenario ID'])]
        pd.concat([previous, df_results], ignore_index=True).to_csv(csv_file_path, index=False)
    else:
        df_results.to_csv(csv_file_path, index=False)
    print(f"\n[+] Results successfully saved to {csv_file_path}")

    # S1-S9
    s1_to_s9_ids = [f"S{i}" for i in range(1, 10)]
    df_s1_to_s9 = df_results[df_results["Scenario ID"].isin(s1_to_s9_ids)]
    curves_s1_to_s9 = {k: v for k, v in scenario_curves.items() if k in s1_to_s9_ids}

    # standard plots for S1-S9
    if scenario_ids is None:
        generate_all_plots(df_s1_to_s9, curves_s1_to_s9, output_dir="output")
    
    # OAT composition comparison plot
    if scenario_ids is None:
        plot_composition_oat_comparison(df_results, output_dir="output")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--biochar-only', action='store_true', help='Run S3 and S21-S24; preserve legacy plots')
    args = parser.parse_args()
    main({'S3', 'S21', 'S22', 'S23', 'S24'} if args.biochar_only else None)