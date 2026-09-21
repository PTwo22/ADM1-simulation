import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os


class Feedstock:
    def __init__(self, M_wet: float, f_TS: float, f_VS_TS: float, fractions: dict):
        self.m_wet = M_wet
        self.m_ts = self.m_wet * f_TS
        self.m_vs = self.m_ts * f_VS_TS
        assert sum(fractions.values()) == 1.0, "Fractions must sum to 1. Try again."
        self.fractions = fractions

    def __getitem__(self, key):
        pass

    def get_solid_masses(self):
        return {}