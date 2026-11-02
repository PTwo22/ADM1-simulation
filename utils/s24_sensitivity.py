"""S24 OAT sweep; reuse the existing model without changing scenario settings."""
from copy import deepcopy
from pathlib import Path
import pandas as pd
from AD.biochar_inoculum import evaluate_batch

RATIOS = (0.33, 0.5, 1.0, 1.5, 2.0)

def calculate_sweep(base, run_scenario, volume):
    rows=[]
    for ratio in RATIOS:
        case=deepcopy(base)
        case['si_ratio']=ratio
        assert all(case[k]==v for k,v in base.items() if k!='si_ratio')
        _,_,digester,config=run_scenario(case)
        row,_=evaluate_batch(digester,case,config,volume)
        rows.append(row)
    frame=pd.DataFrame(rows)
    ref=frame.loc[frame['S:I (gVS/gVS)']==1].iloc[0]
    for day in (10,25):
        col=f'Day-{day} legacy comparison metric'
        frame[col]=1000*frame[f'Adjusted batch cumulative CH4 at {day}d (Nm3)']/frame['Screening nominal loading (kgVS/m3/day)']
        baseline=1000*ref[f'Adjusted batch cumulative CH4 at {day}d (Nm3)']/ref['Screening nominal loading (kgVS/m3/day)']
        frame[f'Day-{day} change vs S3 (%)']=(frame[col]/baseline-1)*100
    return frame

def export_s24_sensitivity(base,run_scenario,volume,output_dir='output/s21_s24'):
    frame=calculate_sweep(base,run_scenario,volume)
    out=Path(output_dir)
    out.mkdir(parents=True,exist_ok=True)
    support=out/'supporting'
    support.mkdir(exist_ok=True)
    frame.to_csv(support/'s24_ratio_sensitivity.csv',index=False)
    return frame

if __name__=='__main__':
    import main
    base=next(s for s in main.scenarios if s['id']=='S3')
    print(export_s24_sensitivity(base,main.run_scenario,main.REACTOR_VOL)[['S:I (gVS/gVS)','Inoculum VS (kg)','Day-10 legacy comparison metric','Day-25 legacy comparison metric','Day-10 change vs S3 (%)','Day-25 change vs S3 (%)']].to_string(index=False))
