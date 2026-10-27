"""Equation-register functions and explicitly exploratory finite-charge kinetics.
No active ADM1 methanogen state, DIET, adsorption or acid-base model is solved.
"""
import math
import numpy as np
from data.biochar_config import BIOCHAR_MODEL, REFERENCE_SI, EXPLORATORY_OPTIONS, BIOCHAR_MATERIAL


def _finite(value, name, positive=False):
    if not math.isfinite(value) or (value <= 0 if positive else value < 0):
        raise ValueError(f"{name} must be finite and {'positive' if positive else 'nonnegative'}")


def _hill(concentration, half, exponent):
    # log-domain evaluation avoids C**n overflow, including large finite doses.
    _finite(concentration, 'concentration')
    _finite(half, 'half-response', True)
    _finite(exponent, 'exponent', True)
    if concentration == 0:
        return 0.0
    z = exponent * (math.log(concentration) - math.log(half))
    if z >= 0:
        return 1 / (1 + math.exp(-z))
    e = math.exp(z)
    return e / (1 + e)


def additive_response(concentration_g_L, half_response_g_L, exponent=1.0):
    """Eq.84: C**n/(K**n+C**n); C and K must use the same g/L basis."""
    return _hill(concentration_g_L, half_response_g_L, exponent)


def additive_inhibition(concentration_g_L, inhibition_g_L, exponent=2.0, enabled=False):
    """Eq.86: 1/(1+(C/KI)**m); optional and disabled by default."""
    _finite(concentration_g_L, 'concentration')
    _finite(inhibition_g_L, 'inhibition concentration', True)
    _finite(exponent, 'inhibition exponent', True)
    if not enabled or concentration_g_L == 0:
        return 1.0
    # Complement expressed independently so high-dose attenuation stays stable.
    z = exponent * (math.log(concentration_g_L) - math.log(inhibition_g_L))
    if z >= 0:
        e = math.exp(-z)
        return e / (1 + e)
    return 1 / (1 + math.exp(z))


def additive_modified_coefficient(baseline, alpha, response, inhibition=1.0):
    """Eq.85 algebra only. Does not create a mechanistic methanogen state.
    The coefficient retains the units of baseline; use requires calibration.
    """
    _finite(baseline, 'baseline coefficient')
    _finite(alpha, 'benefit coefficient')
    if not (math.isfinite(response) and 0 <= response <= 1 and
            math.isfinite(inhibition) and 0 <= inhibition <= 1):
        raise ValueError('Response and inhibition must lie in [0,1]')
    result = baseline * (1 + alpha * response) * inhibition
    if not math.isfinite(result):
        raise ValueError('Modified coefficient overflow')
    return result


def inoculum_capacity(si_ratio, half_capacity=1.0):
    """Unverified empirical proxy, NOT Eq.89 or an active biomass balance."""
    _finite(si_ratio, 'S:I', True)
    _finite(half_capacity, 'capacity half-response', True)
    # Equivalent to (1+h)*x/(h+x), x=SIref/SI; avoids inverse-ratio overflow.
    return (1 + half_capacity) / (1 + half_capacity * si_ratio / REFERENCE_SI)


def kinetic_factors(biochar_g_L, si_ratio, parameters=None, options=None):
    p = {**BIOCHAR_MODEL, **(parameters or {})}
    opt = {**EXPLORATORY_OPTIONS, **(options or {})}
    response = additive_response(biochar_g_L, p['half_saturation_g_L'], p['response_exponent'])
    inhibition = additive_inhibition(biochar_g_L, p['inhibition_scale_g_L'],
                                    p['inhibition_exponent'], p['inhibition_enabled'])
    biochar = additive_modified_coefficient(1.0, p['benefit_amplitude'], response, inhibition)
    capacity = inoculum_capacity(si_ratio, opt['inoculum_half_capacity'])
    return (biochar if opt['biochar_response_enabled'] else 1.0,
            capacity if opt['inoculum_response_enabled'] else 1.0)


def finite_charge_curve(potential, rate_proxy, lag, time):
    """Origin-normalised Gompertz curve; rate_proxy=Rmax*e/P, not ADM1 k_meth.
    Algebraically equivalent to the legacy curve at reference settings.
    """
    for name, value in [('potential', potential), ('rate', rate_proxy), ('lag', lag)]:
        _finite(value, name)
    time = np.asarray(time, dtype=float)
    if not np.isfinite(time).all() or (time < 0).any() or (np.diff(time) < 0).any():
        raise ValueError('Times must be finite, nonnegative and ordered')
    if potential == 0 or rate_proxy == 0:
        return np.zeros_like(time)
    q0 = np.exp(np.clip(1 + rate_proxy * lag, -745, 700))
    qt = np.exp(np.clip(1 + rate_proxy * (lag - time), -745, 700))
    # Stable evaluation of [exp(-qt)-exp(-q0)]/[1-exp(-q0)].
    curve = potential * np.exp(-qt) * (-np.expm1(-(q0 - qt))) / (-np.expm1(-q0))
    return np.clip(curve, 0, potential)


def evaluate_batch(digester, scenario, config, reactor_volume_m3=1.0, parameters=None, options=None):
    p = {**BIOCHAR_MODEL, **(parameters or {})}
    opt = {**EXPLORATORY_OPTIONS, **(options or {})}
    dose, ratio = scenario['biochar_g_L'], scenario['si_ratio']
    biochar, capacity = kinetic_factors(dose, ratio, p, opt)
    _finite(reactor_volume_m3, 'reactor volume', True)
    _finite(opt['empirical_rate_scale'], 'empirical rate scale', True)
    if scenario['hrt'] != 25:
        raise ValueError('This analysis exports explicitly labelled 25-day batch metrics')
    potential = digester.y_ch4_treated  # Nm3 from ONE substrate charge
    base_rate = digester.modified_kinetics['k_hyd_modified']
    rate = base_rate * biochar * capacity * opt['empirical_rate_scale']
    lag = digester.modified_kinetics['lag_modified']  # no unsupported additive/inoculum lag scaling
    time = np.arange(26, dtype=float)
    cumulative = finite_charge_curve(potential, rate, lag, time)
    daily = np.diff(cumulative)
    risks = digester.get_practical_yields(scenario['olr'], config)
    adjusted = cumulative * risks['Stability']
    mass_vs = digester.feedstock.m_vs
    _finite(mass_vs, 'substrate VS', True)
    theoretical = mass_vs * digester.feedstock.calculate_theoretical_bmp(digester.bmp_constants)
    row = {
        'Biochar (g/L)': dose, 'S:I (gVS/gVS)': ratio,
        'Biochar material': BIOCHAR_MATERIAL,
        'Model status': 'Exploratory empirical Gompertz sensitivity; uncalibrated; not ADM1 k_meth',
        'Biochar response enabled': opt['biochar_response_enabled'],
        'Inoculum response enabled': opt['inoculum_response_enabled'],
        'High-dose inhibition enabled': p['inhibition_enabled'],
        'Additive response R_add': additive_response(dose, p['half_saturation_g_L'], p['response_exponent']),
        'Additive inhibition I_add': additive_inhibition(dose, p['inhibition_scale_g_L'], p['inhibition_exponent'], p['inhibition_enabled']),
        'Substrate charge VS (kg)': mass_vs,
        'Inoculum VS (kg)': digester.feedstock.calculate_inoculum_mass(ratio),
        'Inoculum VS concentration (kg/m3)': mass_vs / ratio / reactor_volume_m3,
        'Biochar mass (kg)': dose * reactor_volume_m3,
        'Biochar kinetic factor': biochar, 'Inoculum capacity factor': capacity,
        'Apparent conversion rate (1/day)': rate,
        'Empirical Gompertz Rmax (Nm3/day)': potential * rate / np.e,
        'Batch lag (days)': lag,
        'Theoretical charge BMP (Nm3)': theoretical,
        'Treated charge potential (Nm3)': potential,
        'Batch cumulative CH4 at 25d (Nm3)': cumulative[-1],
        'Adjusted batch cumulative CH4 at 25d (Nm3)': adjusted[-1],
        'Batch mean CH4 production (Nm3/day)': cumulative[-1] / 25,
        'Batch specific CH4 at 25d (L/kgVS)': cumulative[-1] * 1000 / mass_vs,
        'Adjusted batch specific CH4 at 25d (L/kgVS)': adjusted[-1] * 1000 / mass_vs,
        'Batch gross CH4 energy at 25d (MJ)': cumulative[-1] * digester.calib['LHV_CH4'],
        'Batch electricity at 25d (MJ)': cumulative[-1] * digester.calib['LHV_CH4'] * digester.calib['ETA_CHP'],
    }
    return row, {'time': time, 'methane': cumulative, 'adjusted': adjusted, 'daily': daily}
