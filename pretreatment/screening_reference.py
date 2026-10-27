"""Compatibility for main.py's historical screening reference only.
The newer shared Pretreatment validates inert parameters and uses Gaussian
exp(-0.5*z**2). This adapter preserves the archived S3 exp(-z**2) response
and the historical zero response of the unconfigured inert pool.
It does not change the shared class or run_adm1.py.
"""
import math
from pretreatment.pretreatment import Pretreatment


class ScreeningReferencePretreatment(Pretreatment):
    organic_classes = ('carb', 'protein', 'lipid')

    def _calculate_temp_response(self, name):
        values = self.config[name]
        z = (self.temp_pre - values['T_opt']) / values['sigma_T']
        return math.exp(-z**2)

    def _calculate_ph_response(self, name):
        values = self.config[name]
        z = (self.ph_pre - values['pH_opt']) / values['sigma_pH']
        return math.exp(-z**2)

    def _calculate_effectiveness(self):
        return {**super()._calculate_effectiveness(), 'inert': 0.0}
