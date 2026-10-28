"""Feedstock composition and mass-basis calculations."""

from __future__ import annotations

import math
from typing import Dict, Mapping, Tuple


class Feedstock:
    """
    Defines what and how much of each feedstock exists.
    Returns component masses, theoretical BMP mix
    """
    # def __init__(self, m_wet: float, f_ts: float, f_vs_ts: float, f_scg: float, 
    #              fw_fractions: Dict[str, float], scg_fractions: Dict[str, float]):
    def __init__(self, m_wet: float, f_ts: float, f_vs_ts: float, 
                 mixture_ratios: Dict[str, float], 
                 profiles: Dict[str, Dict[str, float]]):
        
        self.m_wet = m_wet                  # wet mass of food waste 
        self.f_ts = f_ts                    # total solids fraction
        self.f_vs_ts = f_vs_ts              # volatile solids fraction of total solids
        # self.f_scg = f_scg                  # SCG ratio, for example 0, 0.10, 0.20 or 0.30 
        # self.fw_fractions = fw_fractions    # organic-matter fraction - Dict for carb, protein, lipid, and inert
        # self.scg_fractions = scg_fractions  # builds composition of SCG 


        self.mixture_ratios = mixture_ratios  # x_j: Fraction of each feedstock j
        self.profiles = profiles              # f_{i,j}: Organic fractions within each feedstock

        self.organic_classes = ["carb", "protein", "lipid", "inert"]

        self._validate_fractions()
        self.m_ts, self.m_vs = self._calculate_solids() # returns total and volitile solids
        
        self.mixed_fractions = self._calculate_mixed_fractions()
        self.component_masses = self._calculate_component_mass()
        self.source_contributions = self._calculate_source_contributions()

    def _validate_fractions(self) -> None:
        """Formula: f_carb + f_protein + f_lipid + f_inert = 1"""
        if not math.isclose(sum(self.mixture_ratios.values()), 1.0, rel_tol=1e-5):
            raise ValueError("Mixture ratios (x_j) must sum to 1.0")
        for name, profile in self.profiles.items():
            if not math.isclose(sum(profile.values()), 1.0, rel_tol=1e-5):
                raise ValueError(f"Organic fractions for {name} must sum to 1.0")

    def _calculate_solids(self) -> Tuple[float, float]:
        """Return total-solids and volatile-solids masses in kg."""
        m_ts = self.m_wet * self.f_ts
        m_vs = m_ts * self.f_vs_ts
        return m_ts, m_vs

    def _calculate_mixed_fractions(self) -> None:
        """gives back mixed substrate composition
        REFACTOR: formula 60 opposed to formula 7 (new list)
        """
        # mixed_dict = {}
        # for i in self.organic_classes:
        #     f_i_fw = self.fw_fractions.get(i, 0.0) # get(key, default_value)
        #     f_i_scg = self.scg_fractions.get(i, 0.0)
        #     # Formula: f_{i,mix} = (1 - f_SCG)*f_{i,FW} + f_SCG * f_{i,SCG}
        #     mixed_dict[i] = ((1.0 - self.f_scg) * f_i_fw) + (self.f_scg * f_i_scg)
        # return mixed_dict

        # Formula 60: f_{i,mix} = sum(x_j * f_{i,j})
        mixed_dict = {i: 0.0 for i in self.organic_classes}
        
        for j_name, x_j in self.mixture_ratios.items():
            f_j = self.profiles[j_name]
            for i in self.organic_classes:
                mixed_dict[i] += x_j * f_j.get(i, 0.0)
                
        return mixed_dict

    def _calculate_component_mass(self) -> Dict[str, float]:
        """gives back mass of each organic-matter class"""
        mass_dict = {}
        for i in self.organic_classes:
            mass_dict[i] = self.m_vs * self.mixed_fractions[i]

        return mass_dict
        
    def calculate_theoretical_bmp(self, bmp_constants: Dict[str, float]) -> float:
        """gives back theoretical BMP from organic-matter classes"""
        bmp_mix = 0.0
        # formula 8: BMP_mix
        for i in ["carb", "protein", "lipid"]:
            f_i = self.mixed_fractions.get(i, 0.0)
            bmp_i = bmp_constants.get(i, 0.0)
            bmp_mix += (f_i * bmp_i)

        return bmp_mix

    def _calculate_source_contributions(self) -> Dict[str, Dict[str, float]]:
        """calculates the contribution of feedstock j to biochemical class i"""
        # formula 62: M_{i,j} = M_{VS,total} * x_j * f_{i,j} - j is feedstock and i is component
        contributions = {}
        for j_name, x_j in self.mixture_ratios.items():
            contributions[j_name] = {}
            f_j = self.profiles[j_name]
            for i in self.organic_classes:
                contributions[j_name][i] = self.m_vs * x_j * f_j.get(i, 0.0)
        return contributions

    def calculate_inoculum_mass(self, s_i_ratio: float) -> float:
        """calculates required inoculum VS mass based on the substrate VS"""
        # formula 89: S/I = M_{VS,substrate} / M_{VS,inoculum} - to be used for S24
        if not math.isfinite(s_i_ratio) or s_i_ratio <= 0:
            raise ValueError("S/I ratio must be greater than zero.")
        
        # rearranged formula 89: M_{VS,inoculum} = M_{VS,substrate} / (S/I)
        m_vs_inoculum = self.m_vs / s_i_ratio
        return m_vs_inoculum