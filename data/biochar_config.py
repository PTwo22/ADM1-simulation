"""Exploratory assumptions, NOT fitted RHB550 kinetic measurements."""
REFERENCE_SI = 1.0  # assumed g substrate VS / g inoculum VS
OFFICIAL_S24_SI = 0.33  # formula-register literature anchor; 2 remains a sensitivity case
BIOCHAR_MATERIAL = "Rice-husk biochar RHB550 (550 C); uncharacterised batch"
BIOCHAR_MODEL = {
    "response_exponent": 1.0,  # assumed Hill shape, unverified
    "inhibition_exponent": 2.0,  # assumed shape; inactive by default
    "inhibition_enabled": False,
    "benefit_amplitude": 0.5,  # assumed dimensionless kinetic response
    "half_saturation_g_L": 5.0,  # assumed, not measured
    "inhibition_scale_g_L": 30.0,  # assumed, not a measured toxicity threshold
}
# Explicit empirical options; neither represents a mechanistic ADM1 constant.
EXPLORATORY_OPTIONS = {
    "biochar_response_enabled": True,
    "inoculum_response_enabled": True,
    "inoculum_half_capacity": 1.0,  # unverified relative-biomass half-response
    "empirical_rate_scale": 1.0,  # diagnostic scale, not a fitted parameter
}
SI_LEVELS = (0.33, 0.5, 1.0, 2.0, 4.0)
