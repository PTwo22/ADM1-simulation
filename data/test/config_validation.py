# ==========================================
# 1. FEEDSTOCK BASELINE FRACTIONS
# ==========================================
FW_FRACTIONS = { # baseline fractions given by Dr.Bita
    'carb': 0.50,
    'protein': 0.25,
    'lipid': 0.20,
    'inert': 0.05
}

SCG_FRACTIONS = {
    'carb': 0.42,    # Assumed baseline SCG composition
    'protein': 0.16, # Assumed baseline SCG composition
    'lipid': 0.22,   # Assumed baseline SCG composition
    'inert': 0.20    # Assumed baseline SCG composition
}

# ==========================================
# 2. METHANE POTENTIAL CONSTANTS (Nm^3 CH4 / kg VS)
# ==========================================
BMP_CONSTANTS = {
    'carb': 0.415,   
    'protein': 0.496,
    'lipid': 1.014,  
    'inert': 0.0     
}

# ==========================================
# 3. PRETREATMENT KINETIC CONSTANTS
# ==========================================
PRETREATMENT_CONFIG = {
    'carb': {
        'K_E': 45.0,      # Assumed: Half-saturation at 45 U/g VS to fit 0-90 dose range
        'T_opt': 30.0,    # Assumed: Fungi optimum temperature
        'sigma_T': 5.0,   # Assumed: Temperature tolerance width
        'pH_opt': 5.5,    # Assumed: Fungi optimum pH
        'sigma_pH': 1.0,  # Assumed: pH tolerance width
        'k_t': 0.05       # Assumed: Reaction rate constant (h^-1)
    },
    'protein': {
        'K_E': 50.0,      # Assumed
        'T_opt': 30.0,    # Assumed
        'sigma_T': 5.0,   # Assumed
        'pH_opt': 5.5,    # Assumed
        'sigma_pH': 1.0,  # Assumed
        'k_t': 0.04       # Assumed
    },
    'lipid': {
        'K_E': 60.0,      # Assumed
        'T_opt': 30.0,    # Assumed
        'sigma_T': 5.0,   # Assumed
        'pH_opt': 5.5,    # Assumed
        'sigma_pH': 1.0,  # Assumed
        'k_t': 0.02       # Assumed
    },
    'inert': {
        'K_E': 40.0,      # Assumed: Fungi highly target inerts/lignocellulose
        'T_opt': 30.0,    # Assumed
        'sigma_T': 5.0,   # Assumed
        'pH_opt': 5.5,    # Assumed
        'sigma_pH': 1.0,  # Assumed
        'k_t': 0.06       # Assumed: Fast degradation of structural matter
    }
}

FPSI_WEIGHTS = {
    'carb': 0.40,    # Assumed weight
    'protein': 0.20, # Assumed weight
    'lipid': 0.10,   # Assumed weight
    'inert': 0.30    # Assumed weight
}

# ==========================================
# 4. DIGESTER BASELINES & CALIBRATION
# ==========================================
DIGESTER_BASELINES = {
    'scod': 10000.0, # Assumed baseline soluble COD (mg/L)
    'k_hyd': 0.25,   # Assumed baseline hydrolysis rate (d^-1)
    'lag_phase': 3.0,# Assumed baseline lag phase (days)
    'b_control': {   # Assumed baseline biodegradability factors
        'carb': 0.85, 
        'protein': 0.75, 
        'lipid': 0.60, 
        'inert': 0.05 
    }
}

DIGESTER_CALIBRATION = {
    'alpha_SCOD': 0.50,   # Assumed: FPSI to SCOD multiplier
    'alpha_hyd': 0.30,    # Assumed: FPSI to hydrolysis rate multiplier
    'alpha_lambda': 0.20,  # Assumed: FPSI to lag phase reduction multiplier
    # system constants
    'LHV_CH4': 35.8,
    'ETA_CHP': 0.35
}