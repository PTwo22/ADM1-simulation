import os
import pandas as pd
import numpy as np
from scipy.optimize import minimize_scalar

from data.config import *
from data.chemical_config import CHEMICAL_PRETREATMENT_CONFIG
from AD.feedstock import Feedstock
from pretreatment.pretreatment import Pretreatment
from pretreatment.chemical_pretreatment import ChemicalPretreatment
from AD.digester import Digester
from AD.chemical_digester import ChemicalDigester
from AD.biochar_inoculum import evaluate_batch

from utils.visualisations import generate_all_plots, plot_composition_oat_comparison, plot_microbial_oat_comparison, plot_composition_gompertz_curves, plot_microbial_ode_curves

# create an output directory for CSVs and plots if it doesn't exist
os.makedirs("output/other_graphs", exist_ok=True)
os.makedirs("output/tables", exist_ok=True)
os.makedirs("output/main_results", exist_ok=True)

# ==========================================
# Units:
# - enzyme_dose: U g⁻¹ VS
# - t_pre: hours (h)
# - scg: percentage (%)
# - olr: kg VS m⁻³ d⁻¹
# - hrt: days (d)
# ==========================================
MODIFIER = 1.2

scenarios = [
    # S1-S9
    {"id": "S1", "description": "Control food waste", "enzyme_dose": 0, "t_pre": 0, "mixture_ratios": {"FW": 1.0}, "profiles": {"FW": FW_FRACTIONS}, "olr": 2.5, "hrt": 25},
    {"id": "S2", "description": "Low fungal pretreatment", "enzyme_dose": 30, "t_pre": 12, "mixture_ratios": {"FW": 1.0}, "profiles": {"FW": FW_FRACTIONS}, "olr": 2.5, "hrt": 25},
    {"id": "S3", "description": "Moderate fungal pretreatment", "enzyme_dose": 60, "t_pre": 24, "mixture_ratios": {"FW": 1.0}, "profiles": {"FW": FW_FRACTIONS}, "olr": 2.5, "hrt": 25, "biochar_g_L": 0.0, "si_ratio": 1.0},
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
    {"id": "S13", "description": "Fibre-rich (Banana Peel)", "enzyme_dose": 60, "t_pre": 24, "mixture_ratios": {"Peel": 1.0}, "profiles": {"Peel": S13_FRACTIONS}, "olr": 2.5, "hrt": 25},

    # S14-S17
    {"id": "S14", "description": "Acidogenic Bacterial Activity (+20%)", "enzyme_dose": 60, "t_pre": 24, "mixture_ratios": {"FW": 1.0}, "profiles": {"FW": FW_FRACTIONS}, "olr": 2.5, "hrt": 25, "target_microbe": "acidogenic", "target_param": "k_max", "modifier": MODIFIER},
    {"id": "S15", "description": "Acetogenic Bacterial Activity (+20%)", "enzyme_dose": 60, "t_pre": 24, "mixture_ratios": {"FW": 1.0}, "profiles": {"FW": FW_FRACTIONS}, "olr": 2.5, "hrt": 25, "target_microbe": "acetogenic", "target_param": "k_max", "modifier": MODIFIER},
    {"id": "S16", "description": "Acetoclastic Methanogenic Archaea (+20%)", "enzyme_dose": 60, "t_pre": 24, "mixture_ratios": {"FW": 1.0}, "profiles": {"FW": FW_FRACTIONS}, "olr": 2.5, "hrt": 25, "target_microbe": "acetoclastic", "target_param": "k_max", "modifier": MODIFIER},
    {"id": "S17", "description": "Hydrogenotrophic Methanogenic Archaea (+20%)", "enzyme_dose": 60, "t_pre": 24, "mixture_ratios": {"FW": 1.0}, "profiles": {"FW": FW_FRACTIONS}, "olr": 2.5, "hrt": 25, "target_microbe": "hydrogenotrophic", "target_param": "k_max", "modifier": MODIFIER},
    # S18-S20
    {"id": "S18", "description": "Chemical pretreatment (1 wt% NaOH)", "naoh_wt_percent": 1.0, "enzyme_dose": 0, "t_pre": 24, "mixture_ratios": {"FW": 1.0}, "profiles": {"FW": FW_FRACTIONS}, "olr": 2.5, "hrt": 25},
    {"id": "S19", "description": "Chemical pretreatment (2 wt% NaOH)", "naoh_wt_percent": 2.0, "enzyme_dose": 0, "t_pre": 24, "mixture_ratios": {"FW": 1.0}, "profiles": {"FW": FW_FRACTIONS}, "olr": 2.5, "hrt": 25},
    {"id": "S20", "description": "Chemical pretreatment (3 wt% NaOH)", "naoh_wt_percent": 3.0, "enzyme_dose": 0, "t_pre": 24, "mixture_ratios": {"FW": 1.0}, "profiles": {"FW": FW_FRACTIONS}, "olr": 2.5, "hrt": 25},

    # S21-S24
    {"id": "S21", "description": "Low biochar addition", "enzyme_dose": 60, "t_pre": 24, "mixture_ratios": {"FW": 1.0}, "profiles": {"FW": FW_FRACTIONS}, "olr": 2.5, "hrt": 25, "biochar_g_L": 5.0, "si_ratio": 1.0},
    {"id": "S22", "description": "Moderate biochar addition", "enzyme_dose": 60, "t_pre": 24, "mixture_ratios": {"FW": 1.0}, "profiles": {"FW": FW_FRACTIONS}, "olr": 2.5, "hrt": 25, "biochar_g_L": 10.0, "si_ratio": 1.0},
    {"id": "S23", "description": "High biochar addition", "enzyme_dose": 60, "t_pre": 24, "mixture_ratios": {"FW": 1.0}, "profiles": {"FW": FW_FRACTIONS}, "olr": 2.5, "hrt": 25, "biochar_g_L": 15.0, "si_ratio": 1.0},
    {"id": "S24", "description": "Literature-anchor inoculum: S:I = 0.33", "enzyme_dose": 60, "t_pre": 24, "mixture_ratios": {"FW": 1.0}, "profiles": {"FW": FW_FRACTIONS}, "olr": 2.5, "hrt": 25, "biochar_g_L": 0.0, "si_ratio": 0.33},
]

# Global/Environmental Assumptions for the pipeline
F_TS = 0.25          # published sim variable
F_VS_TS = 0.90       # published sim variable
REACTOR_VOL = 1.0    # assumed: 1 cubic meter baseline reactor volume -
T_PRE = 30.0         # published sim variable
PH_PRE = 5.5         # published sim variable


def run_scenario(scenario):
    """Construct the fungal screening reference for biochar/inoculum analysis."""
    m_wet = 10.0 if scenario['olr'] <= 2.5 else scenario['olr'] * REACTOR_VOL / (F_TS * F_VS_TS)
    feedstock = Feedstock(m_wet, F_TS, F_VS_TS, scenario['mixture_ratios'], scenario['profiles'])
    doses = {i: scenario['enzyme_dose'] for i in ('carb', 'protein', 'lipid', 'inert')}
    pretreatment = Pretreatment(T_PRE, PH_PRE, scenario['t_pre'], doses, PRETREATMENT_CONFIG, FPSI_WEIGHTS)
    config = {k: globals()[k] for k in ('DIGESTER_CALIBRATION', 'DIGESTER_BASELINES', 'BMP_CONSTANTS',
                                     'RISK_THRESHOLDS', 'STABILITY_WEIGHTS', 'DIGESTER_CONDITIONS')}
    return feedstock, pretreatment, Digester(feedstock, pretreatment, config), config

def find_baseline_biomass(digester, hrt, olr, target_yield_m3):
    """finds X value for ODE solver - used to calibrate for S14-S17"""
    def objective(X_guess):
        digester.x_baseline = X_guess
        result = digester.simulate_dynamic_reactor(hrt, olr)
        ode_yield = result["final_yield"] / 1000.0
        return abs(ode_yield - target_yield_m3)

    res = minimize_scalar(objective, bounds=(0.001, 5.0), method='bounded')
    return res.x


def main():

    results_summary = []
    scenario_curves = {}
    batch_curves = {}

    optimal_biomass_x = 1.0

    # main simulation Loop
    for scenario in scenarios:

        m_wet_daily = 10.0
        m_vs_daily = m_wet_daily * F_TS * F_VS_TS

        # calculate the true OLR based on the fixed wet mass
        # 10.0 * 0.25 * 0.90 = 2.25 kg VS per day
        current_olr = m_vs_daily / REACTOR_VOL

        # EXCEPTION: If the scenario explicitly calls for a high OLR
        if scenario["olr"] > 2.5: # change value if OLR changes
            current_olr = scenario["olr"]
            m_vs_daily = current_olr * REACTOR_VOL
            m_wet_daily = m_vs_daily / (F_TS * F_VS_TS)


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
            mixture_ratios=scenario["mixture_ratios"],
            profiles=scenario["profiles"]
        )
        # instantiate Pretreatment
        if "naoh_wt_percent" in scenario:
            pretreatment = ChemicalPretreatment(
                concentration_wt_percent=scenario["naoh_wt_percent"],
                wet_feed_mass_kg=m_wet_daily,
                config=CHEMICAL_PRETREATMENT_CONFIG,
            )
        else:
            pretreatment = Pretreatment(
                temp_pre=T_PRE,
                ph_pre=PH_PRE,
                time_pre=scenario["t_pre"],
                enzyme_doses=doses,
                config=PRETREATMENT_CONFIG,
                weights=FPSI_WEIGHTS
            )
        config_dict = {
            'DIGESTER_CALIBRATION': DIGESTER_CALIBRATION,
            'DIGESTER_BASELINES': DIGESTER_BASELINES,
            'BMP_CONSTANTS': BMP_CONSTANTS,
            'RISK_THRESHOLDS': RISK_THRESHOLDS,
            'STABILITY_WEIGHTS': STABILITY_WEIGHTS,
            'DIGESTER_CONDITIONS': DIGESTER_CONDITIONS,
            'MICROBIAL_KINETICS': MICROBIAL_KINETICS,
            'X_baseline': optimal_biomass_x
        }

        # TEMPORARY KINETIC MODIFICATION (For S14-S17)
        if "target_microbe" in scenario:
            target = scenario["target_microbe"]
            param = scenario["target_param"]
            config_dict['MICROBIAL_KINETICS'][target][param] *= scenario["modifier"]

        # instantiate Digester
        digester_class = ChemicalDigester if "naoh_wt_percent" in scenario else Digester
        digester = digester_class(feedstock=feedstock, pretreatment=pretreatment, config=config_dict)
        # run appropriate curve model
        time_array = np.linspace(0, scenario["hrt"], num=scenario["hrt"] + 1)

        cod_vs_ratio = (
            (feedstock.mixed_fractions["carb"] * 1.067) + # C6H12O6 + 6 02 -> 6 CO2 + 6 H20
            (feedstock.mixed_fractions["protein"] * 1.415) + # C5H7O2N + 5 02 -> 5 CO2 + 2 H20 + NH3
            (feedstock.mixed_fractions["lipid"] * 2.895) # C57H104O6 + 80 02 -> 57 CO2 + 52 H20
        )

        current_olr_cod = current_olr * cod_vs_ratio

        if "target_microbe" in scenario:
            dynamic_results = digester.simulate_dynamic_reactor(scenario["hrt"], current_olr_cod)
            # Divide the entire cumulative curve array by 1000 to convert Liters to Nm3
            treated_curve = dynamic_results["methane_curve"] / 1000.0
            digester.y_ch4_treated = dynamic_results["final_yield"] / 1000.0
        else:
            treated_curve = digester.calculate_gompertz_curve(time_array, is_treated=True)

            if scenario["id"] == "S3":
                target_yield = digester.y_ch4_treated
                print(f"[*] Calibrating ODE solver to S3 target yield: {target_yield:.3f} Nm3/d")
                # Pass the COD-converted OLR to the optimizer
                optimal_biomass_x = find_baseline_biomass(digester, scenario["hrt"], current_olr_cod, target_yield)
                print(f"[+] Calibration complete. Optimized biomass (X): {optimal_biomass_x:.4f} kg COD/m3")

        # store the curve to plot later
        scenario_curves[scenario["id"]] = {
            "time": time_array,
            "methane": treated_curve
        }


        # calculate risks and practical yields
        practical_data = digester.get_practical_yields(scenario["olr"], config_dict)

        batch_row = {}
        if scenario['id'] in ('S3', 'S21', 'S22', 'S23', 'S24'):
            batch_row, batch_curves[scenario['id']] = evaluate_batch(
                digester, scenario, config_dict, REACTOR_VOL)
            # Keep the original S3 curve for the existing scenario comparisons.
            # The separate batch comparison uses the same normalisation for all five cases.
            if scenario['id'] != 'S3':
                scenario_curves[scenario['id']] = batch_curves[scenario['id']]

        # generate a string showing the feed composition (e.g. "FW: 100.0%")
        mixture_str = ", ".join([f"{k}: {v*100}%" for k, v in scenario["mixture_ratios"].items()])

        results_summary.append({
            **batch_row,
            "Scenario ID": scenario["id"],
            "Scenario": scenario["description"],
            "Feedstock Mixture": mixture_str,
            "FPSI": "N/A" if "naoh_wt_percent" in scenario else round(pretreatment.fpsi, 3),
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

    # Keep S3 as the reference and display/export the extended scenarios only.
    comparison_ids = ['S3'] + [f'S{i}' for i in range(10, 25)]
    df_results = df_results.set_index('Scenario ID').loc[comparison_ids].reset_index()
    comparison_curves = {key: scenario_curves[key] for key in comparison_ids}

    # print to console
    print("=== SIMULATION RESULTS ===")
    print(df_results.to_string(index=False))

    # ==========================================
    # * OUTPUT GENERATION: CSV & VISUALIZATIONS
    # ==========================================

    # export to CSV
    csv_file_path = os.path.join("output", "main_results", "scenario_summary.csv")
    df_results.to_csv(csv_file_path, index=False)
    print(f"\n[+] Results successfully saved to {csv_file_path}")

    # Combined plots for S3 and S10-S24; calculation order remains unchanged.
    generate_all_plots(df_results, comparison_curves, output_dir="output/other_graphs", reference_id="S3")
    # OAT composition comparison plot for S10-13
    plot_composition_oat_comparison(df_results, output_dir="output/other_graphs")
    # OAT microbial kinetic comparison plot (S3 vs S14-S17)
    plot_microbial_oat_comparison(df_results, output_dir="output/other_graphs")
    plot_composition_gompertz_curves(scenario_curves, output_dir="output/other_graphs")
    plot_microbial_ode_curves(scenario_curves, output_dir="output/other_graphs")


if __name__ == "__main__":
    main()
