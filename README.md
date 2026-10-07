# ADM1 Food-Waste Simulation

Python simulation of anaerobic digestion for food waste and spent coffee
grounds (SCG). It compares treatment and operating scenarios and predicts
methane production, energy recovery and digester conditions over time.

The simulation is separate from the user interface so it can be connected to
another application through its Python API.

## What the model includes

- Dynamic ADM1 reactor calculations
- Food-waste and SCG feed calculations
- Fungal-enzyme pretreatment
- CaO chemical-pretreatment screening case
- CSTR mass balances and biological reactions
- pH, VFA, TAN and FAN calculations
- Methane, carbon dioxide and energy outputs
- One-input-at-a-time sensitivity testing
- JSON-ready outputs for the UI

> The model runs successfully, but some feed and pretreatment parameters are
> provisional. Experimental data are still needed for final calibration.

## Install

From the project folder:

```bash
python -m pip install -r requirements.txt
```

## Run

```bash
python run_adm1.py
```

The program displays this menu:

```text
1. Compare priority scenarios (S1, S3, S6)
2. Show all scenarios
3. Choose specific scenario(s)
4. Test the effect of one input
5. Print S1-S9 comparison table
6. Run ADM1 with Dr Bita inputs and create graphs
7. Exit
```

Options 3 and 4 allow another selection without restarting the program:

- Enter another number to run the next selection.
- Enter `M` to return to the main menu.
- Enter `0` to exit.

## Direct commands

```bash
# Compare the priority scenarios
python run_adm1.py S1 S3 S6

# Run every implemented scenario
python run_adm1.py --all

# Run selected scenarios
python run_adm1.py S1 S4 S6

# Test one input around Scenario S3
python run_adm1.py --sensitivity olr
python run_adm1.py --sensitivity hrt
python run_adm1.py --sensitivity pretreatment_time

# Run S1-S9 with the same shared inputs as Dr Bita's screening model
python run_adm1.py --bita-validation
```

The validation command writes only one ADM1 methane-yield graph to
`validation_outputs/`. It does not combine or compare Dr Bita's output values;
those can be compared separately.

## Scenarios

| ID | Description |
|---|---|
| S1 | Control food waste with no pretreatment |
| S2 | Low fungal-enzyme pretreatment |
| S3 | Moderate fungal-enzyme pretreatment for 24 hours |
| S4 | High fungal-enzyme pretreatment |
| S5 | Extended fungal-enzyme pretreatment for 72 hours |
| S6 | Moderate pretreatment with 10% SCG |
| S7 | Moderate pretreatment with 20% SCG |
| S8 | Moderate pretreatment with 30% SCG |
| S9 | S6 with a higher organic loading rate |
| C1 | 1% CaO chemical-pretreatment screening case |

S1 is the untreated control. It is automatically included when another
scenario is selected so the program can calculate improvement against the
control.

## Main inputs

- Wet feed mass
- Total solids and volatile solids
- Food-waste and SCG composition
- Pretreatment dose and duration
- Organic loading rate (OLR)
- Hydraulic retention time (HRT)
- Influent pH and digester temperature
- Reactor liquid and gas volumes
- Simulation duration

Starting values are stored in `data/config.py` and `data/adm1_config.py`. The
original team datasets are also stored in `data/`.

## Main outputs

- Methane yield in L CH4/kg VS
- Methane, carbon dioxide, hydrogen and total-biogas rates
- Methane percentage in dry biogas
- Gross methane energy in kWh
- pH
- Volatile fatty acids (VFA)
- Total ammonia nitrogen (TAN)
- Free ammonia nitrogen (FAN)
- Time-series results
- COD, carbon and nitrogen mass-balance checks

The model provides raw pH, VFA, TAN and FAN values. Stability scoring is not
applied because approved limits and scoring rules have not been provided.

## Project structure

```text
ADM1-simulation/
├── AD/adm1/          ADM1 equations, chemistry and solver
├── AD/feedstock.py   Food-waste and SCG calculations
├── data/             Input values and supplied CSV datasets
├── model_analysis/   Sensitivity, calibration and validation tools
├── pretreatment/     Fungal pretreatment and FPSI calculations
├── scenarios/        Scenario definitions and simulation API
├── tests/            Automated tests
└── run_adm1.py       Command-line program
```

## Connect a user interface

```python
from scenarios import SimulationInputs, run_scenario, run_scenario_set

inputs = SimulationInputs(
    wet_feed_mass_kg=1.0,
    influent_pH=7.2,
    duration_d=100.0,
)

result = run_scenario("S3", inputs=inputs)
summary = result.summary()
time_series = result.time_records()
ui_payload = result.to_payload()

comparison = run_scenario_set(("S1", "S3", "S6"), inputs=inputs)
comparison_payload = comparison.to_payload()
```

The returned data are JSON-ready. The UI does not need to access or modify the
ADM1 equations.

## Test

```bash
python -m unittest discover -s tests -v
```

A successful test run ends with:

```text
Ran 35 tests
OK
```

## Current limitations

- Experimental time-series data are still required for calibration.
- Stability scoring is outside the current model scope.
- Algae, archaea and hybrid-treatment scenarios require compatible parameters.
- Economic, recovery and user-interface calculations are outside this model.
