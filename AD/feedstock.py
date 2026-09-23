import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, Tuple
import math
import os

"""
Formulas presented in Feedstock class: 1, 2, 3, 4, 6, 7
"""

class Feedstock:
    """
    Defines what and how much of each feedstock exists.
    Returns component masses, theoretical BMP mix
    """
    def __init__(self, m_wet: float, f_ts: float, f_vs_ts: float, f_scg: float, 
                 fw_fractions: Dict[str, float], scg_fractions: Dict[str, float]):
        
        self.m_wet = m_wet                  # wet mass of food waste 
        self.f_ts = f_ts                    # total solids fraction
        self.f_vs_ts = f_vs_ts              # volatile solids fraction of total solids
        self.f_scg = f_scg                  # SCG ratio, for example 0, 0.10, 0.20 or 0.30 
        self.fw_fractions = fw_fractions    # organic-matter fraction - Dict for carb, protein, lipid, and inert
        self.scg_fractions = scg_fractions  # builds composition of SCG 

        self.organic_classes = ["carb", "protein", "lipid", "inert"]
        self._validate_fractions()

        self.m_ts, self.m_vs = self._calculate_solids() # returns total and volitile solids
        self.mixed_fractions = self._calculate_mixed_fractions()
        self.component_masses = self._calculate_component_mass()

    def _validate_fractions(self) -> None:
        """Formula: f_carb + f_protein + f_lipid + f_inert = 1"""
        # NOTE add rel_tol=[value] for minor discrepecies
        if not math.isclose(sum(self.fw_fractions.values(), 1.0)):
            raise ValueError("FW fractions must sum to 1.0")
        if not math.isclose(sum(self.scg_fractions.values(), 1.0)):
            raise ValueError("SCG fractions must sum to 1.0")

    def _calculate_solids(self) -> None:
        """gives back total solids (TS) and volitile solids (VS)"""
        m_ts = self.m_wet * self.f_ts
        m_vs = m_ts * self.f_vs_ts
        return m_ts, m_vs

    def _calculate_mixed_fractions(self) -> None:
        """gives back mixed substrate composition"""
        mixed_dict = {}
        for i in self.organic_classes:
            f_i_fw = self.fw_fractions.get(i, 0.0) # get(key, default_value)
            f_i_scg = self.scg_fractions.get(i, 0.0)

            # Formula: f_{i,mix} = (1 - f_SCG)*f_{i,FW} + f_SCG * f_{i,SCG}
            mixed_dict[i] = ((1.0 - self.f_scg) * f_i_fw) + (self.f_scg * f_i_scg)

        return mixed_dict

    def _calculate_component_mass(self) -> None:
        """gives back mass of each organic-matter class"""
        mass_dict = {}
        for i in self.organic_classes:
            mass_dict[i] = self.m_vs * self.mixed_fractions[i]

        return mass_dict

    def calculate_theoretical_bmp(self, bmp_constants: Dict[str, float]) -> float:
        """gives back theoretical BMP from organic-matter classes"""
        bmp_mix = 0.0
        for i in ["carb", "protein", "lipid"]:
            f_i = self.mixed_fractions.get(i, 0.0)
            bmp_i = bmp_constants.get(i, 0.0)
            bmp_mix += (f_i * bmp_i)

        return bmp_mix