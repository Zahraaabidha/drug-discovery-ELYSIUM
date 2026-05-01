import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from app.db import SessionLocal
from app.models import DiscoveryRun, MoleculeRecord

db = SessionLocal()
runs = db.query(DiscoveryRun).all()

target_scores = {}
for run in runs:
    t = run.target_id
    if t not in target_scores:
        target_scores[t] = []
    for m in run.molecules:
        if m.score:
            target_scores[t].append(m.score)

fig, ax = plt.subplots(figsize=(10, 6))
colors = ['#2563eb', '#16a34a', '#dc2626', '#d97706', '#7c3aed']

for i, (target, scores) in enumerate(target_scores.items()):
    x = range(len(scores))
    ax.scatter(x, sorted(scores, reverse=True),
               label=target, color=colors[i % len(colors)], alpha=0.7, s=60)

ax.set_xlabel('Molecule Rank', fontsize=12)
ax.set_ylabel('Predicted Binding Score', fontsize=12)
ax.set_title('ELYSIUM — Predicted Binding Affinity Scores by Target', fontsize=14)
ax.legend()
ax.grid(True, alpha=0.3)
ax.set_ylim(0, 1.1)

os.makedirs('analysis', exist_ok=True)
plt.tight_layout()
plt.savefig('analysis/binding_scores.png', dpi=150)
print('Saved analysis/binding_scores.png')
db.close()