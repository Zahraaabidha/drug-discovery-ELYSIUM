import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# Example ADMET scores (0 = poor, 1 = excellent)
data = {
    "Absorption": [0.85, 0.70, 0.90, 0.60, 0.88],
    "Distribution": [0.78, 0.65, 0.82, 0.55, 0.80],
    "Metabolism": [0.80, 0.72, 0.88, 0.60, 0.83],
    "Excretion": [0.75, 0.68, 0.85, 0.58, 0.79],
    "Toxicity": [0.90, 0.85, 0.92, 0.70, 0.88]
}

molecules = ["Mol_1", "Mol_2", "Mol_3", "Mol_4", "Mol_5"]

df = pd.DataFrame(data, index=molecules)

plt.figure(figsize=(9, 5))
sns.heatmap(
    df,
    annot=True,
    cmap="YlGn",
    linewidths=0.5,
    cbar_kws={"label": "ADMET Score"}
)

plt.title("ADMET Profile Heatmap for Candidate Molecules")
plt.ylabel("Molecules")
plt.xlabel("ADMET Properties")
plt.tight_layout()

# Save image for PPT
plt.savefig("analysis/admet_heatmap.png")

plt.show()
