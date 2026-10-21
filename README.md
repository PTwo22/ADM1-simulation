# ADM1 Simulation
**Project: Waste-to-Energy Simulation: Biogas Production from Food Waste Using Python**

feed composition → fungal pretreatment → solubilisation/hydrolysis → methane → energy →
risk

## Instructions
1. Install all necessary dependencies
```bash
# Windows instructions
python -m venv env
.\env\Scripts\activate
pip install -r requirements.txt
```

Optional: Install Better Comments extension for VSCode for better reading of codebase
```
Name: Better Comments
Id: aaron-bond.better-comments
Description: Improve your code commenting by annotating with alert, informational, TODOs, and more!
Version: 3.0.2
Publisher: Aaron Bond
VS Marketplace Link: https://marketplace.visualstudio.com/items?itemName=aaron-bond.better-comments
```

## Structure
![High level diagram](high-level-diagram.png)
### CLasses
#### Feedstock
- **Description**: This is where all the materials/feedstocks amount lives before any AD or pretreatment occurs. Transforms operational inputs into volatile solid masses that the bacterial kinetics models require to compute methane generation.
- **Presented Formulas**: 1, 2, 3, 4, 6, 7

#### Pretreatment
- **Description**: Translates physical operational conditions (temperature, pH, reaction time, and enzyme dosage) into a representation of the effectiveness of the degraded waste. Computes 4 specific response factors for each organic matter class.

- **Inputs**: Operational configs and kinetic constants.

- **Outputs**: Fungal Pretreatment Severity Index (FPSI) [ref: formula 14], global effectiveness dictionary (Ai) [ref: formula 13]. Passes FPSI to ```Digester``` class


#### Digester
- **Description**: The main simulation for the CSTR (Continuous Stirred Tank Reactor) to do the AD process where the ```Feedstock``` class' physical mass is combined with the modifications from the Pretreatment class to calculate methane yield, kinetic shifts, and energy recovery.

- **Inputs**: 

- **Outputs**: methane yield, kinetic shifts, and energy recovery

> [!NOTE] Presented formulas refer to the 'Required Formula List for the Simulation' given at the start of this internship



```
/ADM1-simulation
├── AD/
├── data/
├── notebook/
├── pretreatment/
├── main.py
├── README.md
└── requirements.txt
```

S21-S24 biochar/inoculum extension: see [BIOCHAR_INOCULUM.md](BIOCHAR_INOCULUM.md) for assumptions, equations, units, limitations, outputs and execution commands.
