"""Run the Phase 1 untreated and commercial-enzyme screening scenarios."""

from __future__ import annotations

from AD import Digester, Feedstock
from data.config import (
    ENZYME_DOSES,
    FEEDSTOCK_BASELINE,
    FPSI_WEIGHTS,
    FW_FRACTIONS,
    MODEL_CONFIG,
    PRETREATMENT_BASELINE,
    PRETREATMENT_CONFIG,
    SCG_FRACTIONS,
)
from pretreatment import NoPretreatment, Pretreatment


def build_feedstock() -> Feedstock:
    scg_fraction = Feedstock.scg_fraction_from_fw_ratio(
        FEEDSTOCK_BASELINE["r_scg_to_fw"]
    )
    return Feedstock(
        m_wet=FEEDSTOCK_BASELINE["m_wet"],
        f_ts=FEEDSTOCK_BASELINE["f_ts"],
        f_vs_ts=FEEDSTOCK_BASELINE["f_vs_ts"],
        f_scg=scg_fraction,
        fw_fractions=FW_FRACTIONS,
        scg_fractions=SCG_FRACTIONS,
    )


def run_scenarios():
    feedstock = build_feedstock()

    control_model = Digester(feedstock, NoPretreatment(), MODEL_CONFIG)
    control = control_model.simulate("A - No pretreatment")

    enzyme_treatment = Pretreatment(
        temp_pre=PRETREATMENT_BASELINE["temperature_c"],
        ph_pre=PRETREATMENT_BASELINE["pH"],
        time_pre=PRETREATMENT_BASELINE["time_h"],
        enzyme_doses=ENZYME_DOSES,
        config=PRETREATMENT_CONFIG,
        weights=FPSI_WEIGHTS,
    )
    treated_model = Digester(feedstock, enzyme_treatment, MODEL_CONFIG)
    treated = treated_model.simulate(
        "B - Commercial fungal enzymes",
        control_yield=control.methane_yield_nm3_per_kg_vs,
    )
    return control, treated


def _print_result(result) -> None:
    print(f"\n{result.scenario}")
    print(f"  FPSI: {result.fpsi:.4f}")
    print(
        "  Methane yield: "
        f"{result.methane_yield_nm3_per_kg_vs:.4f} Nm3 CH4/kg VS"
    )
    print(
        "  Methane rate: "
        f"{result.methane_rate_nm3_per_m3_d:.4f} Nm3 CH4/m3 reactor/d"
    )
    print(f"  Improvement vs control: {result.improvement_pct_vs_control:.2f}%")
    print(f"  Recoverable methane energy: {result.energy_mj_per_m3_d:.2f} MJ/m3/d")
    print(f"  VS mass-balance error: {result.mass_balance_error_kg_vs:.3e} kg")


def main() -> None:
    for result in run_scenarios():
        _print_result(result)


if __name__ == "__main__":
    main()
