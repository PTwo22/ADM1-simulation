"""Finite batch kinetic sensitivity layered over the existing Digester.
No biochar carbon or inoculum endogenous methane is credited.
"""
import math
import numpy as np
from data.biochar_config import BIOCHAR_MODEL, REFERENCE_SI


def kinetic_factors(biochar_g_L, si_ratio, parameters=None):
    p = BIOCHAR_MODEL if parameters is None else parameters
    values = (biochar_g_L, si_ratio, *p.values())
    if not all(math.isfinite(float(v)) for v in values):
        raise ValueError("Inputs and coefficients must be finite")
    if biochar_g_L < 0 or si_ratio <= 0:
        raise ValueError("Biochar must be nonnegative and S:I positive")
    a, half, inhibition = (p[k] for k in (
        "benefit_amplitude", "half_saturation_g_L", "inhibition_scale_g_L"))
    if a < 0 or half <= 0 or inhibition <= 0:
        raise ValueError("Invalid biochar coefficients")
    # Saturating facilitation and high-dose attenuation; exploratory only.
    biochar = (1 + a * biochar_g_L / (half + biochar_g_L)) / (1 + (biochar_g_L / inhibition)**2)
    # Constant active fraction assumed: X/Xref = (S:I)ref / (S:I).
    # Saturating conversion-capacity proxy, normalised to 1 at reference biomass.
    relative_biomass = REFERENCE_SI / si_ratio
    capacity = 2 * relative_biomass / (1 + relative_biomass)
    return biochar, capacity


def evaluate_batch(digester, scenario, config, reactor_volume_m3=1.0):
    dose, ratio = scenario['biochar_g_L'], scenario['si_ratio']
    biochar, capacity = kinetic_factors(dose, ratio)
    if reactor_volume_m3 <= 0 or not math.isfinite(reactor_volume_m3):
        raise ValueError("Reactor volume must be finite and positive")
    # Reuse inherited pretreatment k as an apparent Gompertz rate proxy.
    # This is not a mechanistic change to first-order hydrolysis.
    kinetics = dict(digester.modified_kinetics)
    kinetics['k_hyd_modified'] *= biochar * capacity
    kinetics['lag_modified'] /= biochar * capacity
    # Reuse Gompertz implementation without mutating the original digester.
    from copy import copy
    batch = copy(digester)
    batch.modified_kinetics = kinetics
    time = np.arange(scenario['hrt'] + 1, dtype=float)
    raw = batch.calculate_gompertz_curve(time)
    # Origin-normalised finite-charge curve: C(0)=0, same asymptote P.
    potential = digester.y_ch4_treated  # Nm3 for this single feed charge
    cumulative = potential * (raw - raw[0]) / (potential - raw[0])
    cumulative = np.clip(cumulative, 0, potential)
    daily = np.diff(cumulative)  # Nm3 / each one-day interval
    risks = digester.get_practical_yields(scenario['olr'], config)
    adjusted = cumulative * risks['Stability']
    mass_vs = digester.feedstock.m_vs
    theoretical = mass_vs * digester.feedstock.calculate_theoretical_bmp(digester.bmp_constants)
    row = {
        'Biochar (g/L)': dose, 'S:I (gVS/gVS)': ratio,
        'Model status': 'Exploratory kinetic sensitivity; uncalibrated',
        'Substrate charge VS (kg)': mass_vs,
        'Inoculum VS (kg)': digester.feedstock.calculate_inoculum_mass(ratio),
        'Inoculum VS concentration (kg/m3)': mass_vs / ratio / reactor_volume_m3,
        'Biochar mass (kg)': dose * reactor_volume_m3,
        'Biochar kinetic factor': biochar, 'Inoculum capacity factor': capacity,
        'Apparent conversion rate (1/day)': kinetics['k_hyd_modified'],
        'Batch lag (days)': kinetics['lag_modified'],
        'Theoretical charge BMP (Nm3)': theoretical,
        'Treated charge potential (Nm3)': potential,
        'Batch cumulative CH4 at 25d (Nm3)': cumulative[-1],
        'Adjusted batch cumulative CH4 at 25d (Nm3)': adjusted[-1],
        'Batch mean CH4 production (Nm3/day)': cumulative[-1] / scenario['hrt'],
        'Batch specific CH4 at 25d (L/kgVS)': cumulative[-1] * 1000 / mass_vs,
        'Adjusted batch specific CH4 at 25d (L/kgVS)': adjusted[-1] * 1000 / mass_vs,
        'Batch gross CH4 energy at 25d (MJ)': cumulative[-1] * digester.calib['LHV_CH4'],
        'Batch electricity at 25d (MJ)': cumulative[-1] * digester.calib['LHV_CH4'] * digester.calib['ETA_CHP'],
    }
    return row, {'time': time, 'methane': cumulative, 'adjusted': adjusted, 'daily': daily}
