import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

from data.config import *
from AD.feedstock import Feedstock
from pretreatment.pretreatment import Pretreatment
from AD.digester import Digester

from utils.visualisations import generate_all_plots

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
    # {"id": "S10", "description": "Carbohydrate-rich food-waste composition.", "enzyme_dose": 60, "t_pre": 24, "scg": 10.0, "olr": 4.5, "hrt": 20},
]

# Global/Environmental Assumptions for the pipeline
F_TS = 0.25          # published sim variable
F_VS_TS = 0.90       # published sim variable
REACTOR_VOL = 1.0    # Assumed: 1 cubic meter baseline reactor volume
T_PRE = 30.0         # published sim variable
PH_PRE = 5.5         # published sim variable

def main():

    results_summary = []
    scenario_curves = {}

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
        
        config_dict = {
            'DIGESTER_CALIBRATION': DIGESTER_CALIBRATION,
            'DIGESTER_BASELINES': DIGESTER_BASELINES,
            'BMP_CONSTANTS': BMP_CONSTANTS,
            'RISK_THRESHOLDS': RISK_THRESHOLDS,
            'STABILITY_WEIGHTS': STABILITY_WEIGHTS,
            'DIGESTER_CONDITIONS': DIGESTER_CONDITIONS
        }
        # instantiate Pretreatment
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
            "Electricity potential (MJ)": round(digester.energy['E_electricity'], 3),
            "R_total": round(practical_data['R_total'], 3), # total risk
            "Stability score": round(practical_data['Stability'], 3),
            "Specific Yield (L/kgVS)": round(practical_data['Specific_Yield_L_kgVS'], 3),
            "SCOD increase (%)": round(digester.modified_kinetics["scod_increase_pct"], 3),
            "Predicted CH4 fraction in raw biogas (%)": round(digester.biogas_profile['ch4_fraction_pct'], 3),
            "Biogas volume (m3)": round(digester.biogas_profile['biogas_volume_m3'], 3),
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

    generate_all_plots(df_results, scenario_curves, output_dir="output")


if __name__ == "__main__":
    main()