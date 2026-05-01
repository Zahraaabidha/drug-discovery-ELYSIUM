import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.db import SessionLocal
from app.models import DiscoveryRun, MoleculeRecord
db = SessionLocal()
runs = db.query(DiscoveryRun).all()
mols = db.query(MoleculeRecord).all()
total_runs = len(runs)
total_mols = len(mols)
lipinski_pass = sum(1 for m in mols if m.admet_lipinski_pass)
scores = [m.score for m in mols if m.score]
mws = [m.admet_mw for m in mols if m.admet_mw]
logps = [m.admet_logp for m in mols if m.admet_logp]
tpsas = [m.admet_tpsa for m in mols if m.admet_tpsa]

print(f'Total runs: {total_runs}')
print(f'Total molecules: {total_mols}')
print(f'Lipinski pass: {lipinski_pass}')
print(f'Lipinski pass rate: {round(lipinski_pass/total_mols*100,1)}%')
print(f'Avg score: {round(sum(scores)/len(scores),3)}')
print(f'Max score: {max(scores)}')
print(f'Avg MW: {round(sum(mws)/len(mws),2)}')
print(f'Avg logP: {round(sum(logps)/len(logps),2)}')
print(f'Avg TPSA: {round(sum(tpsas)/len(tpsas),2)}')

print()
print('Per target breakdown:')
for target in ['EGFR', 'BRAF', 'KRAS']:
    target_runs = [r for r in runs if r.target_id == target]
    target_mols = []
    for r in target_runs:
        target_mols.extend(r.molecules)
    if target_mols:
        lp = sum(1 for m in target_mols if m.admet_lipinski_pass)
        sc = [m.score for m in target_mols]
        mw = [m.admet_mw for m in target_mols if m.admet_mw]
        print(f'{target}: {len(target_mols)} molecules, {lp} Lipinski pass ({round(lp/len(target_mols)*100,1)}%), avg score {round(sum(sc)/len(sc),3)}, avg MW {round(sum(mw)/len(mw),2)}')

db.close()