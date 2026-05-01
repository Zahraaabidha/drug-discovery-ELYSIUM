import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from app.db import SessionLocal
from app.models import DiscoveryRun, MoleculeRecord

db = SessionLocal()
runs = db.query(DiscoveryRun).all()

target_data = {}
for run in runs:
    t = run.target_id
    if t not in target_data:
        target_data[t] = []
    for m in run.molecules:
        if m.score:
            target_data[t].append(m.score)

targets = list(target_data.keys())
avg_scores = [sum(target_data[t])/len(target_data[t]) for t in targets]
max_scores = [max(target_data[t]) for t in targets]
counts = [len(target_data[t]) for t in targets]

fig, axes = plt.subplots(1, 3, figsize=(14, 5))

colors = ['#2563eb', '#16a34a', '#dc2626', '#d97706']

axes[0].bar(targets, avg_scores, color=colors[:len(targets)], alpha=0.85, edgecolor='black')
axes[0].set_title('Average Binding Score by Target', fontsize=12)
axes[0].set_ylabel('Avg Predicted Binding Score')
axes[0].set_ylim(0, 1.1)
for i, v in enumerate(avg_scores):
    axes[0].text(i, v + 0.02, str(round(v, 3)), ha='center', fontsize=10)

axes[1].bar(targets, max_scores, color=colors[:len(targets)], alpha=0.85, edgecolor='black')
axes[1].set_title('Max Binding Score by Target', fontsize=12)
axes[1].set_ylabel('Max Predicted Binding Score')
axes[1].set_ylim(0, 1.1)
for i, v in enumerate(max_scores):
    axes[1].text(i, v + 0.02, str(round(v, 3)), ha='center', fontsize=10)

axes[2].bar(targets, counts, color=colors[:len(targets)], alpha=0.85, edgecolor='black')
axes[2].set_title('Molecules Generated per Target', fontsize=12)
axes[2].set_ylabel('Number of Molecules')
for i, v in enumerate(counts):
    axes[2].text(i, v + 0.5, str(v), ha='center', fontsize=10)

plt.suptitle('ELYSIUM — Per-Target Discovery Summary', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig('analysis/score_comparison.png', dpi=150)
print('Saved analysis/score_comparison.png')
db.close()