# ADM1 Simulation

Python model for estimating biogas production from food waste and spent coffee
grounds (SCG).

## What it currently does

The model compares:

- **A — No pretreatment**
- **B — Commercial fungal-enzyme pretreatment**

It calculates:

- feedstock TS and VS;
- fungal pretreatment effectiveness (FPSI);
- methane yield and production rate;
- methane energy;
- VS mass balance.

This is a **Phase 1 screening model**, not the complete ADM1 simulation.
Scenarios C–E, dynamic ADM1 reactions, pH, VFA, ammonia, costs and optimisation
still need to be added.

## Main files

- `main.py` — runs Scenarios A and B.
- `AD/feedstock.py` — calculates feedstock composition.
- `AD/digester.py` — calculates methane and energy.
- `pretreatment/pretreatment.py` — calculates fungal pretreatment effects.
- `data/config.py` — contains the input values used by the model.
- `tests/test_model.py` — contains the automated tests.

## Run the model

```bash
python3 main.py
```

## Run the tests

```bash
python3 -m unittest discover -s tests -v
```

Successful tests finish with:

```text
Ran 11 tests
OK
```

## Important note

The parameters are initial values taken from the supplied CSV datasets. Some
values are provisional and will need sensitivity analysis and calibration.
