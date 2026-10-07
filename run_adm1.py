"""Command-line entry point for the dynamic ADM1 scenarios."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import tempfile

from model_analysis.sensitivity import OAT_FACTORS, run_oat_sensitivity
from model_analysis.stability import (
    StabilityConfig,
    calculate_practical_yield_stability,
    load_stability_config,
)
from scenarios import (
    SCENARIOS,
    SimulationInputs,
    list_scenarios,
    run_scenario_set,
)


PRIORITY_SCENARIOS = ("S1", "S3", "S6")
COMPARISON_SCENARIOS = tuple(f"S{number}" for number in range(1, 10))
ALL_SCENARIOS = tuple(SCENARIOS)


@dataclass(frozen=True)
class BitaInputRunReport:
    rows: tuple[dict[str, object], ...]
    graph_paths: tuple[Path, ...]


BITA_SCENARIOS = tuple(SCENARIOS[scenario_id] for scenario_id in COMPARISON_SCENARIOS)


def bita_common_inputs(*, duration_d: float = 100.0, output_points: int = 201) -> SimulationInputs:
    """Return the global inputs, now aligned with Dr Bita's GitHub model."""
    return SimulationInputs(duration_d=duration_d, output_points=output_points)


def run_bita_input_scenarios(
    *,
    output_directory: str | Path = "validation_outputs",
    duration_d: float = 100.0,
    output_points: int = 201,
) -> BitaInputRunReport:
    settings = bita_common_inputs(duration_d=duration_d, output_points=output_points)
    rows: list[dict[str, object]] = []
    comparison = run_scenario_set(COMPARISON_SCENARIOS, inputs=settings)
    for case, result in zip(BITA_SCENARIOS, comparison.results):
        effectiveness = result.metadata.get("pretreatment_effectiveness", {})
        protein_effectiveness = float(effectiveness.get("protein", 0.0))
        stability = calculate_practical_yield_stability(
            fpsi=result.fpsi,
            protein_effectiveness=protein_effectiveness,
            olr_kg_vs_m3_d=case.olr_kg_vs_m3_d,
        )
        raw_yield = result.methane_yield_l_per_kg_vs
        practical_yield = raw_yield * stability.score
        rows.append(
            {
                "scenario_id": case.scenario_id,
                "enzyme_dose_u_g_vs": case.enzyme_dose_u_g,
                "pretreatment_time_h": case.pretreatment_time_h,
                "scg_fraction_vs": case.scg_fraction_vs,
                "olr_kg_vs_m3_d": case.olr_kg_vs_m3_d,
                "hrt_d": case.hrt_d,
                "raw_adm1_methane_yield_l_per_kg_vs": raw_yield,
                "stability_score": stability.score,
                "stability_risk": stability.total_risk,
                "methane_yield_l_per_kg_vs": practical_yield,
                "improvement_pct_vs_s1": 0.0,
                "methane_fraction": result.final_methane_fraction,
            }
        )
    control_yield = float(rows[0]["methane_yield_l_per_kg_vs"])
    for row in rows:
        row["improvement_pct_vs_s1"] = (
            (float(row["methane_yield_l_per_kg_vs"]) - control_yield)
            / control_yield
            * 100.0
        )

    output_path = Path(output_directory).resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    graph_path = output_path / "adm1_methane_yield.png"
    cache_path = Path(tempfile.gettempdir()) / "adm1-simulation-matplotlib-cache"
    cache_path.mkdir(exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(cache_path / "matplotlib"))
    os.environ.setdefault("XDG_CACHE_HOME", str(cache_path))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axis = plt.subplots(figsize=(11, 5.5))
    axis.bar(
        [str(row["scenario_id"]) for row in rows],
        [float(row["methane_yield_l_per_kg_vs"]) for row in rows],
        color="#2a78b2",
    )
    axis.set_ylabel("Methane yield (L CH4/kg VS)")
    axis.set_title("ADM1 Practical Methane Yield Across Scenarios")
    axis.set_ylim(0.0, 300.0)
    axis.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(graph_path, dpi=180)
    plt.close(fig)
    return BitaInputRunReport(rows=tuple(rows), graph_paths=(graph_path,))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run food-waste ADM1 scenarios")
    parser.add_argument(
        "scenarios",
        nargs="*",
        help="Scenario IDs to run; omit them to open the selection menu",
    )
    parser.add_argument("--all", action="store_true", help="Run every implemented scenario")
    parser.add_argument("--days", type=float, default=100.0)
    parser.add_argument("--points", type=int, default=201)
    parser.add_argument(
        "--stability-config",
        help="JSON file overriding the documented literature screening profile",
    )
    parser.add_argument(
        "--sensitivity",
        choices=tuple(OAT_FACTORS),
        help="Run one-factor-at-a-time analysis around S3",
    )
    parser.add_argument(
        "--bita-validation",
        action="store_true",
        help="Run ADM1 S1-S9 with Dr Bita's inputs and create ADM1 graphs",
    )
    return parser


def _parse_scenario_ids(value: str) -> tuple[str, ...]:
    """Parse comma- or space-separated S1-S9 identifiers."""
    scenario_ids = tuple(
        f"S{item}" if item.isdigit() else item.upper()
        for item in value.replace(",", " ").split()
        if item.strip()
    )
    if not scenario_ids:
        raise ValueError("Enter at least one scenario")
    invalid = [item for item in scenario_ids if item not in SCENARIOS]
    if invalid:
        raise ValueError(f"Unknown scenario(s): {', '.join(invalid)}")
    return tuple(dict.fromkeys(scenario_ids))


def _parse_sensitivity_factor(value: str) -> str:
    """Convert a menu number or input key into a sensitivity-factor key."""

    factors = tuple(OAT_FACTORS)
    selected = value.strip().lower()
    if selected.isdigit():
        index = int(selected) - 1
        if 0 <= index < len(factors):
            return factors[index]
    elif selected in OAT_FACTORS:
        return selected
    raise ValueError(f"Choose an input from 1 to {len(factors)}")


def _choose_sensitivity_factor() -> str | None:
    factors = tuple(OAT_FACTORS)
    print("\nInputs available for testing")
    for number, factor_name in enumerate(factors, start=1):
        factor = OAT_FACTORS[factor_name]
        print(f"  {number}. {factor.label} ({factor.unit})")
    try:
        selected = input("\nSelect an input, or 0 to go back: ").strip()
    except EOFError:
        return None
    if selected == "0":
        return None
    try:
        return _parse_sensitivity_factor(selected)
    except ValueError as error:
        print(f"Invalid input: {error}.")
        return None


def _interactive_selection() -> tuple[str, ...] | str | None:
    """Let a terminal user choose scenarios without remembering commands."""
    while True:
        print("\nADM1 Simulation")
        print("=" * 42)
        print("1. Compare priority scenarios (S1, S3, S6)")
        print("2. Show all scenarios")
        print("3. Choose specific scenario(s)")
        print("4. Test the effect of one input")
        print("5. Print S1-S9 comparison table")
        print("6. Run ADM1 with Dr Bita inputs and create graphs")
        print("7. Exit")
        try:
            choice = input("\nSelect an option [1]: ").strip()
        except EOFError:
            print("\nNo interactive input detected; running S1, S3 and S6.")
            return PRIORITY_SCENARIOS

        if choice in {"", "1"}:
            return PRIORITY_SCENARIOS
        if choice == "2":
            return ALL_SCENARIOS
        if choice == "5":
            return "comparison"
        if choice == "6":
            return "bita_validation"
        if choice == "7":
            print("Simulation closed.")
            return None
        if choice == "3":
            print("\nAvailable scenarios")
            for scenario in list_scenarios():
                print(f"  {scenario['scenario_id']}: {scenario['name']}")
            try:
                selected = input(
                    "\nEnter IDs separated by spaces or commas (example: S1 S3 S6): "
                )
                chosen = _parse_scenario_ids(selected)
                return f"specific:{' '.join(chosen)}"
            except ValueError as error:
                print(f"\nInvalid selection: {error}")
                continue
        if choice == "4":
            factor = _choose_sensitivity_factor()
            if factor is not None:
                return f"sensitivity:{factor}"
            continue
        print("\nInvalid option. Choose 1, 2, 3, 4, 5, 6 or 7.")


def _run_and_print_sensitivity(
    factor_name: str,
    *,
    duration_d: float,
    output_points: int,
    stability_config: StabilityConfig | None,
) -> None:
    report = run_oat_sensitivity(
        factor_name,
        duration_d=duration_d,
        output_points=output_points,
        stability_config=stability_config,
    )
    print(f"\nTesting One Input: {report.factor.label}")
    print("=" * 96)
    print(
        f"{'Value':>10} {'Unit':<14} {'CH4 (L/kgVS)':>14} {'CH4%':>8} "
        f"{'pH':>7} {'VFA':>9} {'FAN':>9} {'Stability':>18}"
    )
    for row in report.rows:
        stability = (
            f"{row['stability_status']} ({row['stability_risk_index']:.3f})"
            if row["stability_risk_index"] is not None
            else "Not validated"
        )
        print(
            f"{row['value']:>10.3f} {row['unit']:<14.14} "
            f"{row['methane_yield_l_per_kg_vs']:>14.2f} "
            f"{100.0 * row['methane_fraction']:>8.2f} {row['pH']:>7.3f} "
            f"{row['vfa_kg_cod_m3']:>9.3f} "
            f"{row['free_ammonia_kg_n_m3']:>9.4f} {stability:>18.18}"
        )
    stats = report.to_payload()["statistics"]
    print(
        "\nMethane-yield range: "
        f"{stats['methane_yield_min_l_per_kg_vs']:.2f}-"
        f"{stats['methane_yield_max_l_per_kg_vs']:.2f} L CH4/kg VS"
    )
    print("Only one input changed in each run; this is screening, not calibration.")


def _run_sensitivity_loop(
    first_factor: str,
    *,
    duration_d: float,
    output_points: int,
    stability_config: StabilityConfig | None,
) -> bool:
    """Test inputs repeatedly without returning to the main menu."""

    factor = first_factor
    while True:
        _run_and_print_sensitivity(
            factor,
            duration_d=duration_d,
            output_points=output_points,
            stability_config=stability_config,
        )
        try:
            next_value = input(
                "\nEnter the next input number (1-5), "
                "M for main menu, or 0 to exit: "
            ).strip()
        except EOFError:
            print()
            return False
        if next_value == "0":
            print("Simulation closed.")
            return False
        if next_value.upper() in {"", "M", "MENU"}:
            return True
        try:
            factor = _parse_sensitivity_factor(next_value)
        except ValueError as error:
            print(f"Invalid input: {error}.")


def _run_and_print(
    scenario_ids: tuple[str, ...],
    *,
    duration_d: float,
    output_points: int,
    stability_config: StabilityConfig | None = None,
) -> None:
    """Run one selection and print its summary tables."""
    comparison = run_scenario_set(
        scenario_ids,
        duration_d=duration_d,
        output_points=output_points,
        stability_config=stability_config,
    )
    rows = comparison.summaries()

    print("\nADM1 Scenario Summary")
    print("=" * 132)
    print(
        f"{'ID':<4} {'Definition':<50} {'FPSI':>7} "
        f"{'CH4 (L/kgVS)':>14} {'Energy (kWh)':>14} "
        f"{'Stability':>14} {'vs S1%':>9}"
    )
    for row in rows:
        marker = "*" if row["is_best"] else " "
        stability = (
            f"{row['stability_status']} {row['stability_risk_index']:.3f}"
            if row["stability_risk_index"] is not None
            else "Not validated"
        )
        fpsi = f"{row['fpsi']:.3f}" if row["fpsi_applicable"] else "N/A"
        print(
            f"{row['scenario_id'] + marker:<4} "
            f"{row['scenario_name']:<50.50} "
            f"{fpsi:>7} "
            f"{row['methane_yield_l_per_kg_vs']:>14.2f} "
            f"{row['gross_energy_kwh_for_2_25kg_vs']:>14.2f} "
            f"{stability:>14} "
            f"{row['improvement_pct_vs_control']:>9.2f}"
        )

    print("\nOperating Conditions and Process Indicators")
    print("=" * 127)
    print(
        f"{'ID':<4} {'SCG%':>7} {'OLR':>7} {'HRT':>7} {'CH4%':>8} "
        f"{'pH':>7} {'VFA kgCOD/m3':>14} {'TAN kgN/m3':>12} {'FAN kgN/m3':>12}"
    )
    for row in rows:
        marker = "*" if row["is_best"] else " "
        print(
            f"{row['scenario_id'] + marker:<4} "
            f"{100.0 * row['scg_fraction_vs']:>7.1f} "
            f"{row['olr_kg_vs_m3_d']:>7.2f} "
            f"{row['hrt_d']:>7.1f} "
            f"{100.0 * row['methane_fraction']:>8.2f} "
            f"{row['pH']:>7.3f} "
            f"{row['vfa_kg_cod_m3']:>14.3f} "
            f"{row['tan_kg_n_m3']:>12.3f} "
            f"{row['free_ammonia_kg_n_m3']:>12.4f}"
        )
    print(f"\n* Highest predicted methane yield: {comparison.best_scenario_id}")


def _run_and_print_comparison(
    *,
    duration_d: float,
    output_points: int,
    stability_config: StabilityConfig | None = None,
) -> None:
    """Print S1-S9 inputs and outputs in one compact comparison table."""

    comparison = run_scenario_set(
        COMPARISON_SCENARIOS,
        duration_d=duration_d,
        output_points=output_points,
        stability_config=stability_config,
    )
    summaries = {
        row["scenario_id"]: row for row in comparison.summaries()
    }

    print("\nS1-S9 Pretreatment and Output Comparison")
    print("=" * 142)
    print(
        f"{'ID':<4} {'Dose':>6} {'Dose basis':<13} {'Time h':>7} "
        f"{'Pre C':>7} {'Pre pH':>7} {'SCG%':>6} {'OLR':>6} {'HRT':>6} "
        f"{'CH4 L/kgVS':>12} {'vs S1%':>8} {'CH4%':>7} {'Final pH':>9} "
        f"{'VFA kgCOD/m3':>14}"
    )
    for result in comparison.results:
        row = summaries[result.scenario_id]
        metadata = result.metadata
        fungal = metadata["pretreatment_kind"] == "fungal_enzyme_proxy"
        dose = f"{metadata['enzyme_dose_u_g']:.1f}" if fungal else "-"
        basis = (
            "U/g VS"
            if metadata["enzyme_dose_basis"] == "U/g VS"
            else "U/g dry FW"
        ) if fungal else "-"
        time_h = f"{metadata['pretreatment_time_h']:.0f}" if fungal else "-"
        pre_c = (
            f"{metadata['pretreatment_temperature_c']:.1f}" if fungal else "-"
        )
        pre_ph = f"{metadata['pretreatment_pH']:.1f}" if fungal else "-"
        print(
            f"{result.scenario_id:<4} {dose:>6} {basis:<13.13} {time_h:>7} "
            f"{pre_c:>7} {pre_ph:>7} {100.0 * result.scg_fraction_vs:>6.1f} "
            f"{result.olr_kg_vs_m3_d:>6.2f} {result.hrt_d:>6.1f} "
            f"{result.methane_yield_l_per_kg_vs:>12.2f} "
            f"{row['improvement_pct_vs_control']:>8.2f} "
            f"{100.0 * result.methane_fraction[-1]:>7.2f} "
            f"{result.final_pH:>9.3f} {result.vfa_kg_cod_m3[-1]:>14.3f}"
        )
    print("\nUnits: dose is shown using each scenario's stated basis; OLR is kg VS/m3/day;")
    print("HRT is days; methane yield is L CH4/kg VS.")


def _run_and_print_bita_validation(
    *, duration_d: float, output_points: int
) -> None:
    """Run ADM1 inputs and apply the practical-yield stability adjustment."""

    report = run_bita_input_scenarios(
        duration_d=duration_d,
        output_points=output_points,
    )
    print("\nADM1 Results with Practical-Yield Stability Adjustment")
    print("=" * 126)
    print(
        f"{'ID':<4} {'Dose U/gVS':>11} {'Time h':>8} {'SCG%':>7} "
        f"{'OLR':>6} {'HRT':>6} {'ADM1 raw':>11} {'Stability':>10} "
        f"{'Practical':>11} {'vs S1%':>9} {'CH4%':>8}"
    )
    for row in report.rows:
        print(
            f"{row['scenario_id']:<4} "
            f"{row['enzyme_dose_u_g_vs']:>11.1f} "
            f"{row['pretreatment_time_h']:>8.0f} "
            f"{100.0 * row['scg_fraction_vs']:>7.1f} "
            f"{row['olr_kg_vs_m3_d']:>6.2f} "
            f"{row['hrt_d']:>6.1f} "
            f"{row['raw_adm1_methane_yield_l_per_kg_vs']:>11.2f} "
            f"{row['stability_score']:>10.3f} "
            f"{row['methane_yield_l_per_kg_vs']:>12.2f} "
            f"{row['improvement_pct_vs_s1']:>9.2f} "
            f"{100.0 * row['methane_fraction']:>8.2f}"
        )
    print("\nCommon feed: 10 kg wet mass, 25% TS, 90% VS/TS; digester: 35 C.")
    print("Pretreatment temperature is 30 C and pH is 5.5 for S1-S9 inputs.")
    print("Practical yield = raw ADM1 yield x stability score.")
    print("The ADM1 calculation itself is unchanged; the penalty is post-processing.")
    print("\nADM1 practical methane-yield graph:")
    for path in report.graph_paths:
        print(f"  {path}")


def _run_specific_scenario_loop(
    first_selection: tuple[str, ...],
    *,
    duration_d: float,
    output_points: int,
    stability_config: StabilityConfig | None,
) -> bool:
    """Run selected scenarios repeatedly without returning to the main menu.

    Returns ``True`` when the user requests the main menu and ``False`` when
    the user exits the program.
    """

    selected = first_selection
    while True:
        _run_and_print(
            selected,
            duration_d=duration_d,
            output_points=output_points,
            stability_config=stability_config,
        )
        try:
            next_value = input(
                "\nEnter the next scenario (example: 2 or S2), "
                "M for main menu, or 0 to exit: "
            ).strip()
        except EOFError:
            print()
            return False
        if next_value == "0":
            print("Simulation closed.")
            return False
        if next_value.upper() in {"", "M", "MENU"}:
            return True
        try:
            selected = _parse_scenario_ids(next_value)
        except ValueError as error:
            print(f"Invalid selection: {error}")


def main() -> None:
    args = _parser().parse_args()
    try:
        stability_config = (
            load_stability_config(args.stability_config)
            if args.stability_config
            else None
        )
    except (OSError, ValueError) as error:
        raise SystemExit(f"Cannot load stability configuration: {error}") from error
    if args.sensitivity:
        _run_and_print_sensitivity(
            args.sensitivity,
            duration_d=args.days,
            output_points=args.points,
            stability_config=stability_config,
        )
        return
    if args.bita_validation:
        _run_and_print_bita_validation(
            duration_d=args.days,
            output_points=args.points,
        )
        return
    if args.all:
        _run_and_print(
            ALL_SCENARIOS,
            duration_d=args.days,
            output_points=args.points,
            stability_config=stability_config,
        )
        return

    if args.scenarios:
        try:
            scenario_ids = _parse_scenario_ids(" ".join(args.scenarios))
        except ValueError as error:
            raise SystemExit(str(error)) from error
        _run_and_print(
            scenario_ids,
            duration_d=args.days,
            output_points=args.points,
            stability_config=stability_config,
        )
        return

    while True:
        scenario_ids = _interactive_selection()
        if scenario_ids is None:
            return
        if isinstance(scenario_ids, str) and scenario_ids.startswith("specific:"):
            first_selection = _parse_scenario_ids(scenario_ids.split(":", 1)[1])
            return_to_menu = _run_specific_scenario_loop(
                first_selection,
                duration_d=args.days,
                output_points=args.points,
                stability_config=stability_config,
            )
            if not return_to_menu:
                return
            continue
        elif isinstance(scenario_ids, str) and scenario_ids.startswith("sensitivity:"):
            return_to_menu = _run_sensitivity_loop(
                scenario_ids.split(":", 1)[1],
                duration_d=args.days,
                output_points=args.points,
                stability_config=stability_config,
            )
            if not return_to_menu:
                return
            continue
        elif scenario_ids == "comparison":
            _run_and_print_comparison(
                duration_d=args.days,
                output_points=args.points,
                stability_config=stability_config,
            )
        elif scenario_ids == "bita_validation":
            _run_and_print_bita_validation(
                duration_d=args.days,
                output_points=args.points,
            )
        else:
            _run_and_print(
                scenario_ids,
                duration_d=args.days,
                output_points=args.points,
                stability_config=stability_config,
            )
        try:
            next_action = input(
                "\nPress Enter to choose another option, or enter 0 to exit: "
            ).strip()
        except EOFError:
            print()
            return
        if next_action == "0":
            print("Simulation closed.")
            return


if __name__ == "__main__":
    main()
