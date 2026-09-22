# ADM1 Simulation

**Project:** Waste-to-Energy Simulation: Biogas Production from Food Waste Using Python

This repository contains the Phase 1 screening model for food-waste and spent
coffee-ground digestion with fungal pretreatment. The current executable model
compares:

- **A — No pretreatment**
- **B — Commercial fungal-enzyme pretreatment**

Scenarios for in-situ solid-state fermentation, fungal consortia and hybrid
biological/chemical treatment require additional process-specific kinetics and
are not represented by the commercial-enzyme model.

## Current model scope

The code implements three collaborating model objects:

1. `Feedstock` — validates the food-waste/SCG composition and calculates TS,
   VS, component masses and theoretical BMP.
2. `Pretreatment` — converts enzyme dose, temperature, pH and time into
   substrate-specific effectiveness values and an aggregate FPSI.
3. `Digester` — applies first-order hydrolysis and a steady-state CSTR
   screening calculation to estimate methane yield, methane rate and energy.

The CSTR conversion used for each component is:

```text
conversion_i = k_i * HRT / (1 + k_i * HRT)
```

The realised methane yield is:

```text
Y_CH4 = sum(f_i * BMP_i * B_i * conversion_i)
```

This is an **ADM1-inspired screening model**, not yet the complete IWA ADM1.
A full ADM1 implementation will require soluble and particulate state vectors,
stoichiometric process rates, inhibition, acid-base chemistry, gas transfer and
dynamic mass balances.

## Run the model

From the repository root:

```bash
python3 main.py
```

The program prints the methane yield, volumetric methane rate, improvement over
the untreated control, methane energy and VS mass-balance residual for both
implemented scenarios.

## Run the tests

```bash
python3 -m unittest discover -s tests -v
```

The tests cover input validation, SCG ratio conversion, solids calculations,
theoretical BMP, FPSI, CSTR output bounds, energy units and mass balance.

## Parameter status

The current values in `data/config.py` come from the supplied Phase 1 datasets.
Several fungal-response, solubilisation, hydrolysis and biodegradability values
are provisional. They must be evaluated through sensitivity analysis and
calibrated against compatible experimental data before predictive use.

The value `r_scg_to_fw = 0.04` is a ratio of SCG VS to food-waste VS. The
`Feedstock` class converts it to the corresponding fraction of total mixture VS
before composition mixing.

## Structure

```text
ADM1-simulation/
├── AD/
│   ├── digester.py
│   ├── feedstock.py
│   └── results.py
├── data/
│   ├── config.py
│   ├── fungal_pretreatment_inputs_updated.csv
│   └── fw_adm1_inputs_updated.csv
├── notebook/
├── pretreatment/
│   └── pretreatment.py
├── tests/
│   └── test_model.py
├── main.py
├── README.md
└── requirements.txt
```
