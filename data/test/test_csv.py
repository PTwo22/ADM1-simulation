import pandas as pd

# 1. Update fw_adm1_inputs_updated.csv
df_adm1 = pd.read_csv("fw_adm1_inputs_updated.csv")
adm1_updates = {
    "f_TS": 0.25,
    "M_wet": 10.0,
    "OLR": 2.5,
    "HRT": 25.0,
}
for var, val in adm1_updates.items():
    df_adm1.loc[df_adm1["variable"] == var, "baseline_value"] = val
df_adm1.to_csv("fw_adm1_inputs_updated.csv", index=False)

# 2. Update fungal_pretreatment_inputs_updated.csv
df_fungal = pd.read_csv("fungal_pretreatment_inputs_updated.csv")
fungal_updates = {
    "T_pre": 30.0,
    "pH_pre": 5.5,
    "E_i": 60.0,
    "K_E_i": 50.0,
    "T_opt_i": 30.0,
    "sigma_T_i": 8.0,
    "pH_opt_i": 5.5,
    "sigma_pH_i": 1.0,
    "k_t_i": 0.05,
    "w_i": 0.35,
    "SCOD_control": 18.0,
    "alpha_SCOD": 0.80,
    "alpha_hyd": 1.50,
}
for var, val in fungal_updates.items():
    df_fungal.loc[df_fungal["variable"] == var, "baseline_value"] = val
df_fungal.to_csv("fungal_pretreatment_inputs_updated.csv", index=False)

print("Both CSV files updated successfully.")