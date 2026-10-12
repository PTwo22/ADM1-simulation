from typing import Dict
from data.config import *

"""
Formulas presented in Digester class: 16, 19, 20, 21, 22, 23, 24, [30, 31, 32]
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
        
        self.yield_improvement = self._calculate_improvement(self.y_ch4_control, self.y_ch4_treated)
        self.energy = self._calculate_energy()


    def _calculate_modified_kinetics(self) -> Dict[str, float]:
        """calculates modified SCOD, hydrolysis rate, and lag phase"""
        fpsi = self.pretreatment.fpsi

        # formula 16: SCOD_pretreated = SCOD_control * (1 + alpha_SCOD * FPSI)
        # where alpha_scod = calibration coefficient linking fungal pretreatment to SCOD increase
        scod_treated = self.baselines['scod'] * (1.0 + (self.calib["alpha_SCOD"] * fpsi))
        # formula 17: k_hyd_modified = k_hyd_base * (1 + alpha_hyd * FPSI)
        k_hyd_modified = self.baselines['k_hyd'] * (1.0 + (self.calib["alpha_hyd"] * fpsi))
        # formula 20: lambda_modified = lambda_base * (1 - alpha_lambda * FPSI)
        lag_modified = self.baselines['lag_phase'] * (1.0 - (self.calib["alpha_lambda"] * fpsi))
        
        # ensure lag phase doesn't drop below zero numerically
        lag_modified = max(0.0, lag_modified)

        return {
            'scod_treated': scod_treated,
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