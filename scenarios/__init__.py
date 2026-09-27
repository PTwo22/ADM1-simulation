"""Scenario definitions and reusable runner API."""

from scenarios.definitions import (
    SCENARIOS,
    UNPARAMETERIZED_TREATMENTS,
    ScenarioSpec,
    get_scenario,
    make_custom_scenario,
)
from scenarios.inputs import SimulationInputs, input_schema
from scenarios.runner import (
    ScenarioComparison,
    list_scenarios,
    run_scenario,
    run_scenario_set,
)

__all__ = [
    "SCENARIOS",
    "UNPARAMETERIZED_TREATMENTS",
    "ScenarioComparison",
    "ScenarioSpec",
    "SimulationInputs",
    "get_scenario",
    "input_schema",
    "list_scenarios",
    "make_custom_scenario",
    "run_scenario",
    "run_scenario_set",
]
