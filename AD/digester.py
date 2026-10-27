from typing import Dict
import numpy as np
from data.config import *

"""
Formulas presented in Digester class: 15, 16, 19, 20, 21, 22, 23, 24, 26, [30, 31, 32], [33, 34, 35, 36, 37]
"""

class Digester:
    """
    Evaluates biomethane production (Section G), kinetic modifications (Sections E & F), 
    and energy recovery (Section J) based on feedstock and pretreatment inputs.
    """
    def __init__(self, feedstock, pretreatment, config: Dict):
        self.feedstock = feedstock
        self.pretreatment = pretreatment

        self.calib = config["DIGESTER_CALIBRATION"]
        self.baselines = config["DIGESTER_BASELINES"]
        self.bmp_constants = config["BMP_CONSTANTS"]

        self.organic_classes = ["carb", "protein", "lipid", "inert"]

        self.modified_kinetics = self._calculate_modified_kinetics()
        self.b_treated = self._calculate_treated_biodegradability()
        self.y_ch4_control = self._calculate_baseline_yield()
        self.y_ch4_treated = self._calculate_treated_yield()
        # self.biogas_profile = self._calculate_biogas_profile()
        self.biogas_profile = {}
        
        self.yield_improvement = self._calculate_improvement(self.y_ch4_control, self.y_ch4_treated)
        self.energy = self._calculate_energy()


    def _calculate_modified_kinetics(self) -> Dict[str, float]:
        """calculates modified SCOD, hydrolysis rate, and lag phase"""
        fpsi = self.pretreatment.fpsi
        scod_control = self.baselines['scod']

        # formula 16: SCOD_pretreated = SCOD_control * (1 + alpha_SCOD * FPSI)
        # where alpha_scod = calibration coefficient linking fungal pretreatment to SCOD increase
        scod_treated = scod_control * (1.0 + (self.calib["alpha_SCOD"] * fpsi))
        # formul 15: SCOD increase percentage
        scod_increase_pct = ((scod_treated - scod_control) / scod_control) * 100.0

        # formula 19: k_hyd_modified = k_hyd_base * (1 + alpha_hyd * FPSI)
        k_hyd_modified = self.baselines['k_hyd'] * (1.0 + (self.calib["alpha_hyd"] * fpsi))
        # formula 20: lambda_modified = lambda_base * (1 - alpha_lambda * FPSI)
        lag_modified = self.baselines['lag_phase'] * (1.0 - (self.calib["alpha_lambda"] * fpsi))
        # ensure lag phase doesn't drop below zero numerically
        lag_modified = max(0.0, lag_modified)

        return {
            'scod_treated': scod_treated,
            'scod_increase_pct': scod_increase_pct,
            'k_hyd_modified': k_hyd_modified,
            'lag_modified': lag_modified
        }


    def _calculate_treated_biodegradability(self) -> Dict[str, float]:
        """calculates biodegradability after fungal pretreatment (if each substrate class i)"""
        
        b_treated = {}
        for i in self.organic_classes:
            b_control = self.baselines["b_control"].get(i, 0.0)
            A_i = self.pretreatment.A.get(i, 0.0)

            # formula 21: B_{i,treated} = B_{i,control} + (1 - B_{i,control}) * A_i
            b_treated[i] = b_control + ((1.0 - b_control) * A_i)

        return b_treated

       
    def _calculate_baseline_yield(self) -> float:
        """calculate baseline methane yield without pretreatment"""
        y_control = 0.0
        for i in self.organic_classes:
            M_i = self.feedstock.component_masses.get(i, 0.0)
            BMP_i = self.bmp_constants.get(i, 0.0)
            B_control = self.baselines["b_control"].get(i, 0.0) # * NO PRETREATMENT APPLIED
            
            # formula 22(a): Y_CH4_i = M_i * BMP_i * B_i and formula 23
            y_control += (M_i * BMP_i * B_control)
            
        return y_control

    def _calculate_treated_yield(self) -> float:
        """calculates total methane yield after pretreatment"""
        y_treated = 0.0
        for i in self.organic_classes:
            M_i = self.feedstock.component_masses.get(i, 0.0)
            BMP_i = self.bmp_constants.get(i, 0.0)
            B_treated = self.b_treated.get(i, 0.0) # difference

            # formula 22(b): Y_CH4_i = M_i * BMP_i * B_i and formula 23
            y_treated += (M_i * BMP_i * B_treated)
            
        return y_treated

    def _calculate_improvement(self, control: float, treated: float) -> float:
        """calculates mathane improvement from fungal pretreatment (will likely be the same for other treatment types too)"""
        if control == 0:
            return 0.0

        # formula 24: Improvement(%) = ((Y_treated - Y_control) / Y_control) * 100
        return ((treated - control) / control) * 100.0

    def _calculate_energy(self) -> Dict[str, float]:
        """calculate energy recovery and electricity potential - for BOTH control and treated"""
        lhv = self.calib["LHV_CH4"] # 35.8 MJ/m^3 - constant
        eta = self.calib["ETA_CHP"] # n_CHP = electrical conversion efficiency

        # formula 30: E_CH4 = V_CH4 * LHV_CH4
        # ! IMPORTANT: MAKE SURE THIS IS IN CUBIC METRES (m^3), else divide by 1000
        e_control = self.y_ch4_control * lhv
        e_treated = self.y_ch4_treated * lhv

        # formula 31: E_electricity = E_CH4 * n_CHP
        e_electricity_treated = e_treated * eta
        # formula 32: Energy Improvement (%) = ((E_treated - E_control) / E_control) * 100
        energy_improvement = self._calculate_improvement(e_control, e_treated)
        
        return {
            "E_CH4_control": e_control,
            "E_CH4_treated": e_treated,
            "E_electricity": e_electricity_treated,
            "improvement_percent": energy_improvement
        }

    def _calculate_stability_risks(self, current_olr: float, config: dict) -> dict:
        """calculates stability and inhibition indicators (formulas 18, 33-37)"""
        thresholds = config["RISK_THRESHOLDS"]
        weights = config["STABILITY_WEIGHTS"]
        conditions = config["DIGESTER_CONDITIONS"]
        calib = config["DIGESTER_CALIBRATION"]

        olr_scaling_factor = current_olr / 2.5 # NOTE 2.5 IS THE OLR FOR BASELINE (S1)
        base_fan = conditions["fan_actual"] * olr_scaling_factor
        
        # Formula 18: FAN_pretreated = FAN_control * (1 + alpha_FAN * A_protein)
        a_protein = self.pretreatment.A.get("protein", 0.0)
        # ! ASSUMED VALUE
        fan_treated = base_fan * (1.0 + (calib["alpha_FAN"] * a_protein))
        # print(calib["alpha_FAN"])
        
        # formula 33 & 34: VFA and ammonia risk
        r_vfa = (conditions["vfa_actual"] * olr_scaling_factor) / thresholds['vfa_crit']
        r_nh3 = fan_treated / thresholds["fan_crit"]
        # formula 35 & 36: pH and OLR risk
        r_ph = abs(conditions["ph_actual"] - thresholds["ph_opt"]) / thresholds["ph_opt"]
        r_olr = current_olr / thresholds["olr_crit"]
        
        # formula 37: combined stability score
        total_risk = (weights['w_vfa'] * r_vfa) + (weights['w_nh3'] * r_nh3) + (weights['w_ph'] * r_ph) + (weights['w_olr'] * r_olr)
                     
        # stability must be constrained between 0 and 1
        stability_score = max(0.0, min(1.0, 1.0 - total_risk))
        
        return {
            "R_total": total_risk,
            "Stability": stability_score
        }

    def _calculate_biogas_profile(self, r_total: float) -> dict:
        """calculates ch4 percentage and biogas volume"""
        fpsi = self.pretreatment.fpsi
        f_scg = self.feedstock.mixture_ratios.get("SCG", 0.0)

        # formula 33
        f_ch4 = 0.58 + (0.08 * fpsi) - (0.05 * r_total) - (0.03 * f_scg)
        # constrain to the stated screening range (0.50 - 0.70)
        f_ch4 = max(0.50, min(0.70, f_ch4))
        
        # formula 35: total biogas volume
        biogas_volume = self.y_ch4_treated / f_ch4
        # formula 36: V_CO2
        v_co2 = biogas_volume - self.y_ch4_treated
        
        return {
            'ch4_fraction_pct': f_ch4 * 100.0,
            'biogas_volume_m3': biogas_volume,
            'co2_volume_m3': v_co2
        }

    def get_practical_yields(self, current_olr: float, config: dict) -> dict:
        """applies the stability penalty to calculate practical yields and specific efficiency - no formula applies"""
        risks = self._calculate_stability_risks(current_olr, config)
        # apply the stability inhibition multiplier to the theoretical treated yield
        practical_yield_nm3 = self.y_ch4_treated * risks['Stability']
        
        # calculate specific yield: (Liters of CH4) / (kg VS added)
        # 1 Nm3 = 1000 Liters - current_olr represents the kg VS added per m3.
        specific_yield_L_kgvs = (practical_yield_nm3 * 1000) / current_olr
        self.biogas_profile = self._calculate_biogas_profile(risks['R_total'])
        
        return {
            "R_total": risks["R_total"],
            "Stability": risks["Stability"],
            "Practical_Yield_Nm3": practical_yield_nm3,
            "Specific_Yield_L_kgVS": specific_yield_L_kgvs
        }

    def calculate_gompertz_curve(self, time_array: np.ndarray, is_treated: bool = True) -> np.ndarray:
        """calculates Modified Gompertz model for cumulative methane over time"""
        # select parameters based on whether we are plotting the control or treated curve
        # ! NOTE: LAG AND KINETICS ARE ASSUMED AS OF RIGHT NOW
        if is_treated:
            ch4_max = self.y_ch4_treated
            lag = self.modified_kinetics['lag_modified'] # lag phase
            k_hyd = self.modified_kinetics['k_hyd_modified']
        else:
            ch4_max = self.y_ch4_control
            lag = self.baselines['lag_phase']
            k_hyd = self.baselines['k_hyd']
            
        # approximate R_max (Maximum production rate) if not explicitly defined in config
        r_max = (ch4_max * k_hyd) / np.e 
        # formula 26: CH4(t) = CH4,max * exp{-exp[(R_max * e / CH4,max) * (lambda - t) + 1]}
        exponent_term = ((r_max * np.e) / ch4_max) * (lag - time_array) + 1.0
        cumulative_methane = ch4_max * np.exp(-np.exp(exponent_term))
        
        # zero out any negative initial values caused by the lag phase mathematics
        cumulative_methane = np.maximum(0, cumulative_methane)
        
        return cumulative_methane