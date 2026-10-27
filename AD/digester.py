from typing import Dict
import numpy as np
from data.config import *
import numpy as np
from scipy.integrate import solve_ivp

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
        self.microbial_kinetics = config.get("MICROBIAL_KINETICS")
        self.x_baseline = config.get("X_baseline", 1.0) # ! TEMP SOLUTION

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
        scod_control = self.baselines["scod"]

        # formula 16: SCOD_pretreated = SCOD_control * (1 + alpha_SCOD * FPSI)
        # where alpha_scod = calibration coefficient linking fungal pretreatment to SCOD increase
        scod_treated = scod_control * (1.0 + (self.calib["alpha_SCOD"] * fpsi))
        # formul 15: SCOD increase percentage
        scod_increase_pct = ((scod_treated - scod_control) / scod_control) * 100.0

        # formula 19: k_hyd_modified = k_hyd_base * (1 + alpha_hyd * FPSI)
        k_hyd_modified = self.baselines["k_hyd"] * (1.0 + (self.calib["alpha_hyd"] * fpsi))
        # formula 20: lambda_modified = lambda_base * (1 - alpha_lambda * FPSI)
        lag_modified = self.baselines["lag_phase"] * (1.0 - (self.calib["alpha_lambda"] * fpsi))
        # ensure lag phase doesn"t drop below zero numerically
        lag_modified = max(0.0, lag_modified)

        return {
            "scod_treated": scod_treated,
            "scod_increase_pct": scod_increase_pct,
            "k_hyd_modified": k_hyd_modified,
            "lag_modified": lag_modified
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
        r_vfa = (conditions["vfa_actual"] * olr_scaling_factor) / thresholds["vfa_crit"]
        r_nh3 = fan_treated / thresholds["fan_crit"]
        # formula 35 & 36: pH and OLR risk
        r_ph = abs(conditions["ph_actual"] - thresholds["ph_opt"]) / thresholds["ph_opt"]
        r_olr = current_olr / thresholds["olr_crit"]
        
        # formula 37: combined stability score
        total_risk = (weights["w_vfa"] * r_vfa) + (weights["w_nh3"] * r_nh3) + (weights["w_ph"] * r_ph) + (weights["w_olr"] * r_olr)
                     
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
            "ch4_fraction_pct": f_ch4 * 100.0,
            "biogas_volume_m3": biogas_volume,
            "co2_volume_m3": v_co2
        }

    def get_practical_yields(self, current_olr: float, config: dict) -> dict:
        """applies the stability penalty to calculate practical yields and specific efficiency - no formula applies"""
        risks = self._calculate_stability_risks(current_olr, config)
        # apply the stability inhibition multiplier to the theoretical treated yield
        practical_yield_nm3 = self.y_ch4_treated * risks["Stability"]
        
        # calculate specific yield: (Liters of CH4) / (kg VS added)
        # 1 Nm3 = 1000 Liters - current_olr represents the kg VS added per m3.
        specific_yield_L_kgvs = (practical_yield_nm3 * 1000) / current_olr
        self.biogas_profile = self._calculate_biogas_profile(risks["R_total"])
        
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
            lag = self.modified_kinetics["lag_modified"] # lag phase
            k_hyd = self.modified_kinetics["k_hyd_modified"]
        else:
            ch4_max = self.y_ch4_control
            lag = self.baselines["lag_phase"]
            k_hyd = self.baselines["k_hyd"]
            
        # approximate R_max (Maximum production rate) if not explicitly defined in config
        r_max = (ch4_max * k_hyd) / np.e 
        # formula 26: CH4(t) = CH4,max * exp{-exp[(R_max * e / CH4,max) * (lambda - t) + 1]}
        exponent_term = ((r_max * np.e) / ch4_max) * (lag - time_array) + 1.0
        cumulative_methane = ch4_max * np.exp(-np.exp(exponent_term))
        
        # zero out any negative initial values caused by the lag phase mathematics
        cumulative_methane = np.maximum(0, cumulative_methane)
        
        return cumulative_methane

    def _cstr_derivatives(self, t: float, state: list, params: dict) -> list:
        """section 14 & 15: future extensions - hydrolytic, acidogenic and acetogenic bacteria - methanogenic archaea (Equations 67-75, 79)"""
        # P_i: particulate, S_sol: soluble sugars, S_VFA: volatile fatty acids, S_Ac: acetate, S_H2: hydrogen, V_CH4: cumulative methane volume
        # Biomass (X) assumed constant in this simplified step or added to state array
        P_i, S_sol, S_VFA, S_Ac, S_H2, V_CH4 = state

        k_hyd = params["k_hyd"]
        k_kinetics = params["kinetics"]
        hrt = params["hrt"]

        # influent concentration based on formula 78*: S_{VS,in} = OLR * HRT
        P_in = params["olr"] * hrt
        # ! PRELIMINARY VALUES: TO BE CHANGED - initial inhibition factors are 1.0 (no inhibition)
        # I_acid = I_acet = I_Ac = I_H2 = 1.0
        K_I_H2 = k_kinetics['acetogenic'].get('K_I_H2', 3.5e-6)
        I_acet = K_I_H2 / (K_I_H2 + S_H2)
        I_acid = 1.0 
        I_Ac = 1.0
        I_H2 = 1.0
        
        # formula 67: particulate-substrate hydrolysis balance
        # NOTE: Added inflow/outflow based on formula 79 General CSTR mass balance
        r_hyd = k_hyd * P_i
        # formula 69: acidogenic conversion (Soluble -> VFA)
        r_acid = k_kinetics["acidogenic"]["k_max"] * params["X_acid"] * (S_sol / (k_kinetics["acidogenic"]["K_S"] + S_sol)) * I_acid
        # formula 71: acetogenic/syntrophic conversion (VFA -> Acetate + H2)
        r_acet = k_kinetics["acetogenic"]["k_max"] * params["X_acet"] * (S_VFA / (k_kinetics["acetogenic"]["K_S"] + S_VFA)) * I_acet # ! CHECK FOR S_VFA AGAINST S_syn
        # formula 73: acetoclastic methanogenesis (Acetate -> CH4 + CO2)
        r_meth_Ac = k_kinetics["acetoclastic"]["k_max"] * params["X_ac"] * (S_Ac / (k_kinetics["acetoclastic"]["K_S"] + S_Ac)) * I_Ac # ! CHECK FOR K_Ac
        # formula 74: hydrogenotrophic methanogenesis (H2 + CO2 -> CH4)
        r_meth_H2 = k_kinetics["hydrogenotrophic"]["k_max"] * params["X_h2"] * (S_H2 / (k_kinetics["hydrogenotrophic"]["K_S"] + S_H2)) * I_H2
        # formula 75: methane generation rate (Q_CH4)
        q_ch4 = (params["Y_CH4_Ac"] * r_meth_Ac) + (params["Y_CH4_H2"] * r_meth_H2)


        # formula 79: dC_k/dt = (C_k,in - C_k) / HRT + sum(v_kj * r_j) - general CSTR mass balance
        # dynamic state differentials (Equation 79)
        
        dP_dt = ((P_in - P_i) / hrt) - r_hyd
        dS_sol_dt = ((0 - S_sol) / hrt) + r_hyd - r_acid
        dS_VFA_dt = ((0 - S_VFA) / hrt) + ((1 - k_kinetics['acidogenic']['Y']) * r_acid) - r_acet
        dS_Ac_dt = ((0 - S_Ac) / hrt) + ((1 - k_kinetics['acetogenic']['Y']) * r_acet) - r_meth_Ac
        
        # simplified H2 balance (yield from acetogenesis minus consumption)
        # dS_H2_dt = ((0 - S_H2) / hrt) + (params["Y_H2_acet"] * r_acet) - r_meth_H2 # ! CHECK
        # simplified H2 balance (assume ~10% of acetogenic product goes to H2)
        dS_H2_dt = ((0 - S_H2) / hrt) + (0.10 * r_acet) - r_meth_H2

        # formula 82: dynamic methane accumulation rate
        dV_CH4_dt = q_ch4

        return [dP_dt, dS_sol_dt, dS_VFA_dt, dS_Ac_dt, dS_H2_dt, dV_CH4_dt]

    def simulate_dynamic_reactor(self, hrt: float, olr: float) -> dict:
        """Ordinary Differential Equations (ODE) solver over the HRT timeframe"""
        # * DOCUMENTATION FOR ODE: https://jdbburg.com/classes/Sp24Phy5300-JB/notebooks/Reference/ODEs_with_solve_ivp.html

        # integration timeframe
        sim_days = hrt * 10 # arbitrary value to get ODE running
        t_span = (0, sim_days)
        t_eval = np.linspace(0, sim_days, int(sim_days) + 1)
        
        # set initial reactor state [P_i, S_sol, S_VFA, S_Ac, S_H2, V_CH4] - [Particulates, Soluble Sugars, VFAs, Acetate, Hydrogen, Methane Volume]
        # ! ASUMPTION: assuming an active baseline seeded with small intermediate concentrations
        # initial_state = [olr, 0.1, 0.1, 0.1, 1e-5, 0.0]
        initial_state = [olr, 0.0, 0.0, 0.0, 0.0, 0.0]
        
        
        # package biological parameters
        params = {
            'k_hyd': self.modified_kinetics['k_hyd_modified'],
            'kinetics': self.microbial_kinetics,
            'hrt': hrt,
            'olr': olr,
            'X_acid': self.x_baseline, 'X_acet': self.x_baseline, 'X_ac': self.x_baseline, 'X_h2': self.x_baseline,
            # 'X_acid': 1.0, 'X_acet': 1.0, 'X_ac': 1.0, 'X_h2': 1.0,
            # 'X_acid': 0.10, 'X_acet': 0.10, 'X_ac': 0.10, 'X_h2': 0.10,
            # "X_acid": 0.01, "X_acet": 0.01, "X_ac": 0.01, "X_h2": 0.01,
            # yield coefficients for gas conversion - uses PV=nRT
            'Y_CH4_Ac': 395.0,
            'Y_CH4_H2': 395.0,
            # 'Y_CH4_Ac': 1000.0,
            # 'Y_CH4_H2': 1000.0,
        }
        
        # run the ODE solver
        solution = solve_ivp(
            fun=lambda t, y: self._cstr_derivatives(t, y, params),
            t_span=t_span,
            y0=initial_state,
            t_eval=t_eval,
            method="Radau"
        )
        
        # formula 83: extract final cumulative methane
        # cumulative_methane = solution.y[5]
        S_Ac_final = solution.y[3][-1]
        S_H2_final = solution.y[4][-1]

        # re-calculate the steady-state daily methane rate (Q_CH4)
        r_meth_Ac = params['kinetics']['acetoclastic']['k_max'] * params['X_ac'] * (S_Ac_final / (params['kinetics']['acetoclastic']['K_S'] + S_Ac_final))
        r_meth_H2 = params['kinetics']['hydrogenotrophic']['k_max'] * params['X_h2'] * (S_H2_final / (params['kinetics']['hydrogenotrophic']['K_S'] + S_H2_final))
        
        steady_state_daily_yield = (params['Y_CH4_Ac'] * r_meth_Ac) + (params['Y_CH4_H2'] * r_meth_H2)

        # return {
        #     "time": solution.t,
        #     "methane_curve": cumulative_methane,
        #     "final_yield": cumulative_methane[-1]
        # }
    
        return {
            "time": solution.t[:int(hrt)+1], # return just the first HRT for the curve plot
            "methane_curve": solution.y[5][:int(hrt)+1], 
            "final_yield": steady_state_daily_yield # passes back the daily L/m3/d rate
        }
    