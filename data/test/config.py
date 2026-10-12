"""
config.py
Centralized parameters and constants for the custom AD simulation.
"""

# ==========================================
# 1. FEEDSTOCK BASELINE FRACTIONS
# ==========================================
FW_FRACTIONS = { # NOTE these values were given by Dr.Bita

}

# Provisional composition constraints for Spent Coffee Grounds (SCG)
SCG_FRACTIONS = {

}

# ==========================================
# 2. METHANE POTENTIAL CONSTANTS (Nm^3 CH4 / kg VS)
# ==========================================
# Theoretical BMP values for each organic-matter class
BMP_CONSTANTS = {

}
# ==========================================
# 3. PRETREATMENT KINETIC CONSTANTS
# ==========================================
# Environmental response parameters for fungal enzymes
PRETREATMENT_CONFIG = {

}

# Weighting factors for the Overall Fungal Pretreatment Severity Index (FPSI)
FPSI_WEIGHTS = {

}

# ==========================================
# 4. DIGESTER CALIBRATION COEFFICIENTS
# ==========================================
DIGESTER_CALIBRATION = {

}

# ==========================================
# 5. ENERGY & SYSTEM CONSTANTS
# ==========================================
LHV_CH4 = 35.8  # Lower Heating Value of Methane (MJ/m^3)
ETA_CHP = 0.35  # Electrical conversion efficiency (CHP)