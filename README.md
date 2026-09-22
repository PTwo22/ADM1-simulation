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
```bash
Name: Better Comments
Id: aaron-bond.better-comments
Description: Improve your code commenting by annotating with alert, informational, TODOs, and more!
Version: 3.0.2
Publisher: Aaron Bond
VS Marketplace Link: https://marketplace.visualstudio.com/items?itemName=aaron-bond.better-comments
```

## Structure
![High level diagra](high-level-diagram.png)
### CLasses
#### Feedstock
- **Description**:

- **Inputs**:

- **Output**:

#### Pretreatment
- **Description**: Translates physical operational conditions (temperature, pH, reaction time, and enzyme dosage) into a representation of the effectiveness of the degraded waste. Computes 4 specific response factors for each organic matter class.

- **Inputs**: Operational configs and kinetic constants.

- **Outputs**: Fungal Pretreatment Severity Index (FPSI) [ref: formula 14], global effectiveness dictionary (Ai) [ref: formula 13]. Passes FPSI to ```Digester``` class


#### Digester
- **Description**:

- **Inputs**:

- **Output**:


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