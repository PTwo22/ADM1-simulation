"""Default IWA ADM1 kinetic, stoichiometric and gas-transfer parameters."""

from __future__ import annotations

from dataclasses import dataclass, field
import math


def _carbon_content() -> dict[str, float]:
    # kmol C per kg COD
    return {
        "S_su": 0.0313,
        "S_aa": 0.0300,
        "S_fa": 0.0217,
        "S_va": 0.0240,
        "S_bu": 0.0250,
        "S_pro": 0.0268,
        "S_ac": 0.0313,
        "S_h2": 0.0,
        # One kmol CH4 represents 64 kg COD and contains one kmol C.
        "S_ch4": 1.0 / 64.0,
        "S_I": 0.0300,
        "X_c": 0.02786,
        "X_ch": 0.0313,
        "X_pr": 0.0300,
        "X_li": 0.0220,
        "X_su": 0.0313,
        "X_aa": 0.0313,
        "X_fa": 0.0313,
        "X_c4": 0.0313,
        "X_pro": 0.0313,
        "X_ac": 0.0313,
        "X_h2": 0.0313,
        "X_I": 0.0300,
    }


def _nitrogen_content() -> dict[str, float]:
    # kmol N per kg COD. Non-listed organic states contain no nitrogen.
    values = {name: 0.0 for name in _carbon_content()}
    values.update(
        {
            "S_aa": 0.007,
            "X_pr": 0.007,
            "S_I": 0.06 / 14.0,
            "X_I": 0.06 / 14.0,
            "X_c": 0.0376 / 14.0,
            "X_su": 0.08 / 14.0,
            "X_aa": 0.08 / 14.0,
            "X_fa": 0.08 / 14.0,
            "X_c4": 0.08 / 14.0,
            "X_pro": 0.08 / 14.0,
            "X_ac": 0.08 / 14.0,
            "X_h2": 0.08 / 14.0,
        }
    )
    return values


@dataclass(frozen=True)
class ADM1Parameters:
    """Parameter set for the standard 19-process ADM1 model.

    Rates are per day, COD concentrations are kg COD m-3 and inorganic
    carbon/nitrogen concentrations are kmol m-3.
    """

    # Composite disintegration fractions
    f_sI_xc: float = 0.10
    f_xI_xc: float = 0.20
    f_ch_xc: float = 0.20
    f_pr_xc: float = 0.20
    f_li_xc: float = 0.30

    # Fermentation product fractions
    f_fa_li: float = 0.95
    f_h2_su: float = 0.19
    f_bu_su: float = 0.13
    f_pro_su: float = 0.27
    f_ac_su: float = 0.41
    f_h2_aa: float = 0.06
    f_va_aa: float = 0.23
    f_bu_aa: float = 0.26
    f_pro_aa: float = 0.05
    f_ac_aa: float = 0.40

    # Biomass yields (kg COD biomass per kg COD substrate)
    Y_su: float = 0.10
    Y_aa: float = 0.08
    Y_fa: float = 0.06
    Y_c4: float = 0.06
    Y_pro: float = 0.04
    Y_ac: float = 0.05
    Y_h2: float = 0.06

    # Disintegration and hydrolysis
    k_dis: float = 0.50
    k_hyd_ch: float = 0.25
    k_hyd_pr: float = 0.20
    k_hyd_li: float = 0.10

    # Maximum uptake and half-saturation parameters
    k_m_su: float = 30.0
    K_S_su: float = 0.50
    k_m_aa: float = 50.0
    K_S_aa: float = 0.30
    k_m_fa: float = 6.0
    K_S_fa: float = 0.40
    k_m_c4: float = 20.0
    K_S_c4: float = 0.20
    k_m_pro: float = 13.0
    K_S_pro: float = 0.10
    k_m_ac: float = 8.0
    K_S_ac: float = 0.15
    k_m_h2: float = 35.0
    K_S_h2: float = 7e-6
    K_S_IN: float = 1e-4

    # Inhibition and decay
    K_I_h2_fa: float = 5e-6
    K_I_h2_c4: float = 1e-5
    K_I_h2_pro: float = 3.5e-6
    K_I_nh3: float = 0.0018
    k_dec: float = 0.02
    pH_UL_aa: float = 5.5
    pH_LL_aa: float = 4.0
    pH_UL_ac: float = 7.0
    pH_LL_ac: float = 6.0
    pH_UL_h2: float = 6.0
    pH_LL_h2: float = 5.0

    # Acid-base constants at the reference temperature
    pK_w: float = 14.0
    pK_a_va: float = 4.86
    pK_a_bu: float = 4.82
    pK_a_pro: float = 4.88
    pK_a_ac: float = 4.76
    pK_a_co2: float = 6.35
    pK_a_IN: float = 9.25
    temperature_ref_k: float = 298.15

    # Gas transfer. Henry constants use kmol m-3 bar-1.
    k_la_per_d: float = 200.0
    k_p_m3_per_d_bar: float = 5.0e4
    atmospheric_pressure_bar: float = 1.013
    water_vapour_pressure_ref_bar: float = 0.0313
    K_H_h2: float = 7.8e-4
    K_H_ch4: float = 1.4e-3
    K_H_co2: float = 3.5e-2
    gas_constant_bar_m3_per_kmol_k: float = 0.083145
    normal_m3_per_kmol: float = 22.414
    cod_per_kmol_h2: float = 16.0
    cod_per_kmol_ch4: float = 64.0

    carbon_content: dict[str, float] = field(default_factory=_carbon_content)
    nitrogen_content: dict[str, float] = field(default_factory=_nitrogen_content)

    def _temperature_factor(self, temperature_c: float) -> float:
        temperature_k = temperature_c + 273.15
        if temperature_k <= 0:
            raise ValueError("Absolute temperature must be positive")
        return (1.0 / self.temperature_ref_k - 1.0 / temperature_k) / (
            100.0 * self.gas_constant_bar_m3_per_kmol_k
        )

    def equilibrium_constants(self, temperature_c: float) -> dict[str, float]:
        """Return BSM2 temperature-adjusted acid-base constants."""
        factor = self._temperature_factor(temperature_c)
        return {
            "water": 10.0 ** (-self.pK_w) * math.exp(55900.0 * factor),
            "co2": 10.0 ** (-self.pK_a_co2) * math.exp(7646.0 * factor),
            "in": 10.0 ** (-self.pK_a_IN) * math.exp(51965.0 * factor),
            "S_va": 10.0 ** (-self.pK_a_va),
            "S_bu": 10.0 ** (-self.pK_a_bu),
            "S_pro": 10.0 ** (-self.pK_a_pro),
            "S_ac": 10.0 ** (-self.pK_a_ac),
        }

    def henry_constants(self, temperature_c: float) -> dict[str, float]:
        """Return BSM2 temperature-adjusted Henry constants."""
        factor = self._temperature_factor(temperature_c)
        return {
            "h2": self.K_H_h2 * math.exp(-4180.0 * factor),
            "ch4": self.K_H_ch4 * math.exp(-14240.0 * factor),
            "co2": self.K_H_co2 * math.exp(-19410.0 * factor),
        }

    def water_vapour_pressure(self, temperature_c: float) -> float:
        """Return saturated water-vapour pressure using the BSM2 correction."""
        temperature_k = temperature_c + 273.15
        if temperature_k <= 0:
            raise ValueError("Absolute temperature must be positive")
        return self.water_vapour_pressure_ref_bar * math.exp(
            5290.0 * (1.0 / self.temperature_ref_k - 1.0 / temperature_k)
        )

    def validate(self) -> None:
        """Reject internally inconsistent parameter sets."""
        xc_sum = self.f_sI_xc + self.f_xI_xc + self.f_ch_xc + self.f_pr_xc + self.f_li_xc
        if abs(xc_sum - 1.0) > 1e-9:
            raise ValueError("Composite disintegration fractions must sum to 1")
        sugar_sum = self.f_h2_su + self.f_bu_su + self.f_pro_su + self.f_ac_su
        amino_sum = (
            self.f_h2_aa
            + self.f_va_aa
            + self.f_bu_aa
            + self.f_pro_aa
            + self.f_ac_aa
        )
        if abs(sugar_sum - 1.0) > 1e-9 or abs(amino_sum - 1.0) > 1e-9:
            raise ValueError("Fermentation product fractions must sum to 1")
        if self.k_la_per_d <= 0 or self.k_p_m3_per_d_bar <= 0:
            raise ValueError("Gas-transfer parameters must be positive")
        if self.temperature_ref_k <= 0 or self.water_vapour_pressure_ref_bar <= 0:
            raise ValueError("Reference temperature and water-vapour pressure must be positive")
        for lower, upper in (
            (self.pH_LL_aa, self.pH_UL_aa),
            (self.pH_LL_ac, self.pH_UL_ac),
            (self.pH_LL_h2, self.pH_UL_h2),
        ):
            if upper <= lower:
                raise ValueError("Each upper pH limit must exceed its lower limit")
