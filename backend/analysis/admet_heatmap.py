import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from app.db import SessionLocal
from app.models import DiscoveryRun, MoleculeRecord

db = SessionLocal()
runs = db.query(DiscoveryRun).all()

target_data = {}
for run in runs:
    t = run.target_id
    if t not in target_data:
        target_data[t] = {'mw': [], 'logp': [], 'tpsa': [], 'hbd': [], 'hba': [], 'pass': 0, 'total': 0}
    for m in run.molecules:
        target_data[t]['total'] += 1
        if m.admet_lipinski_pass:
            target_data[t]['pass'] += 1
        if m.admet_mw: target_data[t]['mw'].append(m.admet_mw)
        if m.admet_logp: target_data[t]['logp'].append(m.admet_logp)
        if m.admet_tpsa: target_data[t]['tpsa'].append(m.admet_tpsa)
        if m.admet_hbd: target_data[t]['hbd'].append(m.admet_hbd)
        if m.admet_hba: target_data[t]['hba'].append(m.admet_hba)

targets = list(target_data.keys())
props = ['Avg MW', 'Avg LogP', 'Avg TPSA', 'Lipinski Pass%']

matrix = []
for t in targets:
    d = target_data[t]
    row = [
        round(sum(d['mw'])/len(d['mw']), 1) if d['mw'] else 0,
        round(sum(d['logp'])/len(d['logp']), 2) if d['logp'] else 0,
        round(sum(d['tpsa'])/len(d['tpsa']), 1) if d['tpsa'] else 0,
        round(d['pass']/d['total']*100, 1) if d['total'] else 0,
    ]
    matrix.append(row)

matrix = np.array(matrix)
norm_matrix = (matrix - matrix.min(axis=0)) / (matrix.max(axis=0) - matrix.min(axis=0) + 1e-8)

fig, ax = plt.subplots(figsize=(8, max(4, len(targets) * 1.2)))
im = ax.imshow(norm_matrix, cmap='YlOrRd', aspect='auto')

ax.set_xticks(range(len(props)))
ax.set_xticklabels(props, fontsize=11)
ax.set_yticks(range(len(targets)))
ax.set_yticklabels(targets, fontsize=11)

for i in range(len(targets)):
    for j in range(len(props)):
        ax.text(j, i, str(matrix[i, j]), ha='center', va='center',
                fontsize=10, color='black')

ax.set_title('ELYSIUM — ADMET Property Heatmap by Target', fontsize=13)
plt.colorbar(im, ax=ax, label='Normalized value')
plt.tight_layout()

os.makedirs('analysis', exist_ok=True)
plt.savefig('analysis/admet_heatmap.png', dpi=150)
print('Saved analysis/admet_heatmap.png')
db.close()