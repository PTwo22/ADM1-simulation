# ==========================================
# 1. FEEDSTOCK BASELINE FRACTIONS
# ==========================================
FW_FRACTIONS = { # baseline fractions given by Dr.Bita
    'carb': 0.50,
    'protein': 0.25,
    'lipid': 0.20,
    'inert': 0.05
}
# FW_FRACTIONS = { # S10
#     'carb': 0.9206, # -0.18
#     'protein': 0.0713,
#     'lipid': 0.0072,
#     'inert': 0.0009
# }


SCG_FRACTIONS = {
    'carb': 0.42,    # Assumed baseline SCG composition
    'protein': 0.16, # Assumed baseline SCG composition
    'lipid': 0.22,   # Assumed baseline SCG composition
    'inert': 0.20    # Assumed baseline SCG composition
}
# ==========================================
# 2. METHANE POTENTIAL CONSTANTS (Nm^3 CH4 / kg VS)
# ==========================================
BMP_CONSTANTS = { # Batstone et al. (2002); Raposo et al. (2012) - our sourcing
    'carb': 0.415,   
    'protein': 0.496,
    'lipid': 1.014,  
    'inert': 0.0     
}

# ==========================================
# 3. PRETREATMENT KINETIC CONSTANTS
# ==========================================
PRETREATMENT_CONFIG = { # directly from dr. bita's code/paper
    "carb": {
        "K_E": 50.0,
        "T_opt": 30.0,
        "sigma_T": 8.0,
        "pH_opt": 5.5,
        "sigma_pH": 1.0,
        "k_t": 0.050,
        "weight": 0.35,
    },
    "protein": {
        "K_E": 45.0,
        "T_opt": 32.0,
        "sigma_T": 8.0,
        "pH_opt": 6.0,
        "sigma_pH": 1.0,
        "k_t": 0.040,
        "weight": 0.25,
    },
    "lipid": {
        "K_E": 60.0,
        "T_opt": 30.0,
        "sigma_T": 8.0,
        "pH_opt": 5.5,
        "sigma_pH": 1.2,
        "k_t": 0.030,
        "weight": 0.20,
    },
    "SCG": {
        "K_E": 70.0,
        "T_opt": 28.0,
        "sigma_T": 10.0,
        "pH_opt": 5.0,
        "sigma_pH": 1.2,
        "k_t": 0.035,
        "weight": 0.20,
    },
}
FPSI_WEIGHTS = {
    'carb': 0.35,
    'protein': 0.25,
    'lipid': 0.20,
    'inert': 0.20
}
# FPSI_WEIGHTS = { # team assumption
#     'carb': 0.25,
#     'protein': 0.25,
#     'lipid': 0.25,
#     'inert': 0.25
# }
# ==========================================
# 4. DIGESTER BASELINES & CALIBRATION
# ==========================================
DIGESTER_BASELINES = {
    'scod': 18000.0, # from Dr. Bita's sim - ! VERIFY UNIT
    'k_hyd': 0.25,   # from Dr. Bita's sim - baseline hydrolysis rate (d^-1)
    'ch4_fraction_control': 0.60, # ! VERIFY - 0.50-0.70 range from dr. bita's paper 2.2.4. modelled CH4 fraction in raw biogas
    'lag_phase': 3.8,# from Dr. Bita's sim
    'b_control': {   # ! Assumed baseline biodegradability factors
        'carb': 0.85, 
        'protein': 0.75, 
        'lipid': 0.60, 
        'inert': 0.05
        # 'carb': 0.55, 
        # 'protein': 0.55, 
        # 'lipid': 0.55, 
        # 'inert': 0.55 
    }
}

DIGESTER_CALIBRATION = {
    # from Dr. Bita's sim
    'alpha_SCOD': 0.80,
    "alpha_sugar": 1.20,
    "alpha_FAN": 0.70,
    "alpha_TAN": 0.20,
    "alpha_hyd": 1.50,
    "alpha_lambda": 0.55,

    # assumed values
    'scod_conversion_factor': 0.15, # Assumed: How effectively FPSI converts particulate COD to SCOD
    'purity_conversion_factor': 0.05, # Assumed - used for calculating CH4 purity, to be verified/changed
    # system constants
    'LHV_CH4': 35.8, # from formula list
    'ETA_CHP': 0.35
}

# ==========================================
# 5. STABILITY & RISK CONSTANTS
# ==========================================
RISK_THRESHOLDS = {
    'vfa_crit': 6000.0,  # Critical VFA concentration (mg/L) - dr. bita's paper
    'fan_crit': 600.0,   # Critical Free Ammonia Nitrogen (mg/L) - dr. bita's paper
    # may need TAN
    'ph_opt': 7.2,       # Optimum digester pH - ceiling for reactor's pH from dr. Bita
    'olr_crit': 5.0      # Critical Organic Loading Rate (kg VS m^-3 d^-1) - dr. bita's paper
}

STABILITY_WEIGHTS = { # directly from dr. bita's code/paper
    'w_vfa': 0.35,
    'w_nh3': 0.25,
    'w_ph': 0.20,
    'w_olr': 0.20
}

# Baseline estimated concentrations for an uninhibited digester
DIGESTER_CONDITIONS = {
    'vfa_actual': 1500.0,
    'fan_actual': 150.0,
    'ph_actual': 7.1
}
