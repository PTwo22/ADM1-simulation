# ==========================================
# 1. FEEDSTOCK BASELINE FRACTIONS
# ==========================================
FW_FRACTIONS = { # baseline fractions given by Dr.Bita
    'carb': 0.50,
    'protein': 0.25,
    'lipid': 0.20,
    'inert': 0.05
}

# S10: Cooked Rice (Carbohydrate-rich anchor)
S10_FRACTIONS = {
    'carb': 0.9206, # -0.18
    'protein': 0.0713,
    'lipid': 0.0072,
    'inert': 0.0009
}
# S11: meat waste (protein-rich anchor) - normalised to satisfy constraints of equation 3
S11_FRACTIONS = {
    'carb': 0.083,   # normalised from 3.48%
    'protein': 0.904,# normalised from 37.74%
    'lipid': 0.013,  # normalised from 0.51%
    'inert': 0.000
}
# S12: plant oil (lipid-rich anchor)
# NOTE: carbon is ignored
S12_FRACTIONS = {
    'carb': 0.000,
    'protein': 0.000,
    'lipid': 0.9999, # anchored to 99.99%
    'inert': 0.0001 # to satisfy equation 3
}
# S13: banana peel (fibre-rich anchor)
# total sum is 88.75 - for normalisation
S13_FRACTIONS = { # uses midpoints of all the ranges
    'carb': 0.819,   # normalised from 72.7% - assumption: cellulose (58.9–64%), hemicellulose (3.5–19%)
    'protein': 0.039,# normalised from 3.5% (2–5%)
    'lipid': 0.007,  # normalised from 0.6% (0.2–1%)
    'inert': 0.135   # normalised from 11.95% - lignin (5–18.9%)
}

SCG_FRACTIONS = { # other sim
    'carb': 0.42,
    'protein': 0.16,
    'lipid': 0.22,
    'inert': 0.20
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
# enzyme_split = {
#     "carb": 0.40,
#     "protein": 0.30,
#     "lipid": 0.20,
#     "SCG": 0.10,
# }
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
        # 'carb': 0.85, 
        # 'protein': 0.75, 
        # 'lipid': 0.60, 
        # 'inert': 0.05
        'carb': 0.72, 
        'protein': 0.72, 
        'lipid': 0.72, 
        'inert': 0.72 
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

# baseline estimated concentrations for an uninhibited digester
# ! PRELIMINARY ASSUMED VALUES
DIGESTER_CONDITIONS = {
    'vfa_actual': 1500.0,
    'fan_actual': 150.0,
    'ph_actual': 7.1
}

# * VERIFIED PARAMETERS
MICROBIAL_KINETICS = { # S14-17 - reference: https://peerj.com/articles/16720.pdf
    # S14: hydrolytic/fermentative bacterial activity (sugar degraders)
    "acidogenic": {
        "k_max": 30.0,       # k_m,su (1/d)
        "K_S": 0.5,          # K_S,su (kg COD / m3)
        "Y": 0.10            # Y_su
    },
    # S15: acetogenic/syntrophic bacterial activity (propionate degraders)
    "acetogenic": {
        "k_max": 13.0,       # k_m,pro (1/d)
        "K_S": 0.10,         # K_S,pro (kg COD / m3)
        "Y": 0.04,           # Y_pro
        "K_I_H2": 3.5e-6     # K_I ,H2,pro (kg COD / m3)
    },
    # S16: acetoclastic methanogenic archaea
    # NOTE: pH_LL ~= 6, pH_UP = 7
    "acetoclastic": {
        "k_max": 8.0,        # k_m,ac (1/d)
        "K_S": 0.15,         # K_S,ac (kg COD / m3)
        "Y": 0.05,           # Y_ac
        "K_I_NH3": 0.0018    # unit: M (free ammonia inhibition limit)
    },
    # S17: hydrogenotrophic methanogenic archaea
    # NOTE: pH_LL = 5, pH_UP = 6
    "hydrogenotrophic": {
        "k_max": 35.0,       # k_m,H2 (1/d)
        "K_S": 7e-6,         # K_S,H2 (kg COD / m3)
        "Y": 0.06            # Y_H2
    }
}