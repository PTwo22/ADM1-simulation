# ADM1 Simulation
**Project: Waste-to-Energy Simulation: Biogas Production from Food Waste Using Python**
```
feed composition → fungal pretreatment → solubilisation/hydrolysis → methane → energy →
risk
```
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

## Structure
![High level diagram](high-level-diagram.png)

```
/ADM1-simulation
├── AD/
├── data/
├── notebook/
├── pretreatment/
├── main.py
├── README.md
├── .gitignore
└── requirements.txt
```

### CLasses
#### Feedstock
- **Description**: This is where all the materials/feedstocks amount lives before any AD or pretreatment occurs. Transforms operational inputs into volatile solid masses that the bacterial kinetics models require to compute methane generation.

- **Inputs**: 

- **Outputs**: 


#### Pretreatment
- **Description**: Translates physical operational conditions (temperature, pH, reaction time, and enzyme dosage) into a representation of the effectiveness of the degraded waste. Computes 4 specific response factors for each organic matter class.

- **Inputs**: Operational configs and kinetic constants.

- **Outputs**: Fungal Pretreatment Severity Index (FPSI) [ref: formula 14], global effectiveness dictionary (Ai) [ref: formula 13]. Passes FPSI to ```Digester``` class


#### Digester
- **Description**: The main simulation for the CSTR (Continuous Stirred Tank Reactor) to do the AD process where the ```Feedstock``` class' physical mass is combined with the modifications from the Pretreatment class to calculate methane yield, kinetic shifts, and energy recovery.

- **Inputs**: 

- **Outputs**: methane yield, kinetic shifts, and energy recovery

### Main files

- `main.py` — runs Scenarios A and B.
- `AD/feedstock.py` — calculates feedstock composition.
- `AD/digester.py` — calculates methane and energy.
- `pretreatment/pretreatment.py` — calculates fungal pretreatment effects.
- `data/config.py` — contains the input values used by the model.
- `tests/test_model.py` — contains the automated tests.

## Instructions

1. Run the main program
```bash
python3 main.py
```

2. Run the tests
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
