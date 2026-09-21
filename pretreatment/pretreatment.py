import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

"""
BASELINE:
- Carbohydrates: 40-70% of VS, with 50% as our current baseline
- Protein: 10-30% of VS, with 25% as the baseline
- Lipids: 5-30% of VS, with 20% as the baseline
- Inert fraction: approximately 5% in our baseline food-waste case
"""

# * ================================================
# * A. FEEDSTOCK AND ORGANIC-MATTER COMPOSITION
# * ================================================


def calculate_total_solids(M_wet, f_TS):
    """total solids (TS)"""
    M_TS = M_wet * f_TS
    return M_TS

def calculate_volatile_solids(M_TS, f_vs_ts):
    """volatile solids (VS)"""
    M_VS = M_TS * f_vs_ts
    return M_VS
    

def calculate_mass_of_organic_matter_class(M_VS, fractions):
    """mass of each organic matter class
    M_carb = M_VS * f_carb and so on
    RETURN DICT
    """
    pass


# * ================================================
# * B. SCG co-substrate composition
# * ================================================

def calculate_scg_food_waste_mass_split():
    """SCG co-substrate composition
    RETURN DICT
    """
    pass

def calculate_mixed_substrate_composition(f_i_mixed, f_i_FW, f_i_SCG):
    """mixed substrate composition
    i = carbohydrate, protein, lipid or inert -> iterate through a list/dict
    RETURN DICT
    """
    
    pass

# * ================================================
# * C. Baseline methane potential
# * ================================================

def calculate_theoretical_bmp(fractions, BMP_mix):
    """theoretical BMP from organic-matter class
    Unit: Nm^3 CH4/kgVS
    """
    
    pass

def calculate_baseline_methane_yield():
    """baseline methane yield with biodegradability"""
    pass

# * ================================================
# * D. Fungal pretreatment severity
# * ================================================

def calculate_enzyme_dose_response():
    pass

def calculate_temperature_response():
    pass

def calculate_ph_response():
    pass

def calculate_time_response():
    pass

def calculate_fungal_pretreatment_effectiveness():
    """Fungal pretreatment effectiveness for each organic-matter class"""
    pass

def calculate_fungal_pretreatment_severity_index():
    """FPSI"""
    pass

# * ================================================
# * E. Pretreatment effect on substrate solubilisation
# * ================================================

def calculate_scod_increase():
    pass

def calculate_estimated_scod():
    """SCOD after pretreatment"""
    pass

def calculate_soluble_sugar_release():
    pass

def calculate_fan_tan_change():
    pass

# * ================================================
# * F. Hydrolysis and lag-phase modification
# * ================================================

def calculate_modified_hydrolysis_rate():
    pass

def calculate_lag_phase_reduction():
    pass

