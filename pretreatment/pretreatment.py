import math
from typing import Dict

"""
Formulas presented in Pretreatment class: 9, 10, 11, 12, 13, 14
"""

class Pretreatment:
    """Returns FPSI and fungal pretreatment effectiveness for each organic-matter class"""
    def __init__(self, temp_pre: float, ph_pre: float, time_pre: float, 
                 enzyme_doses: Dict[str, float], config: Dict[str, Dict[str, float]], 
                 weights: Dict[str, float]):
        self.temp_pre = temp_pre                # temperature
        self.ph_pre = ph_pre                    # pH
        self.time_pre = time_pre                # pretreatment duration
        self.enzyme_doses = enzyme_doses        # enzyme_doses

        # parameters: K_E, T_opt, sigma_T, pH_opt, sigma_pH, k_t
        self.config = config

        self.weights = weights
        self.organic_classes = ["carb", "protein", "lipid", "inert"]

        self.A = self._calculate_effectiveness() # formula 13
        self.fpsi = self._calculate_fpsi()       # formula 14

    def _calculate_dose_response(self, i) -> float:
        """returns enzyme does response term"""
        E_i = self.enzyme_doses.get(i, 0.0)     # enzyme dose or activity for organic-matter class i
        K_E_i = self.config[i]["K_E"]           # half-saturation enzyme constant

        # Formula 9: D_i = E_i / (K_E_i + E_i)
        return E_i / (K_E_i + E_i) if (K_E_i + E_i) > 0 else 0.0

    def _calculate_temp_response(self, i) -> float:
        """returns temperature response"""
        T_opt_i = self.config[i]["T_opt"]       #  optimum temperature for enzyme group i
        sigma_T_i = self.config[i]["sigma_T"]   # temperature tolerance width

        # Formula 10: T_i = exp(-((T_pre - T_opt_i) / sigma_T_i)^2)
        return math.exp(-((self.temp_pre - T_opt_i) / sigma_T_i) ** 2) if sigma_T_i > 0 else 0.0

    def _calculate_ph_response(self, i) -> float:
        """returns pH response"""
        ph_opt_i = self.config[i]["pH_opt"]     # optimum pH for enzyme group i
        alpha_ph_i = self.config[i]["alpha_pH"] # pH tolerance width

        # Formula 11: P_i = exp(-((ph_pre - ph_opt_i) / alpha_ph_i)^2)
        return math.exp(-((self.ph_pre - ph_opt_i) / alpha_ph_i)**2) if alpha_ph_i > 0 else 0.0

    def _calculate_time_response(self, i) -> float:
        """returns time response"""
        k_t_i = self.config[i]["k_t"]           # time-response coefficient

        # Formula 12: R_i = 1 - e^(-k_t_i*t_pre)
        return 1.0 - math.exp(-k_t_i * self.time_pre)

    def _calculate_effectiveness(self) -> Dict[str, float]:
        """Fungal effectiveness for each class i. Useful as it prevents enzyme 
        dose alone from directly predicting methane. The enzyme first changes 
        substrate accessibility and biodegradability.
        """
        a_dict = {}                             # A_i = fungal enzyme effectiveness for substrate class i
        for i in self.organic_classes:
            if i not in self.config:
                a_dict[i] = 0.0
                continue

            D_i = self._calculate_dose_response(i)
            T_i = self._calculate_temp_response(i)
            P_i = self._calculate_ph_response(i)
            R_i = self._calculate_time_response(i)

            # Formula 13: A_i = D_i * T_i * P_i * R_i
            a_dict[i] = D_i * T_i * P_i * R_i

        return a_dict

    def _calculate_fpsi(self, i) -> float:
        """returns overall fungal pretreatment severity index (FPSI)"""
        fpsi = 0.0
        for i in self.organic_classes:
            w_i = self.weights.get(i, 0.0)

            # Formula 14: FPSI = w_carb*A_carb + w_protein*A_protein + w_lipid*A_lipd + w_scg*A_scg
            fpsi += w_i * self.A[i]

        return fpsi


