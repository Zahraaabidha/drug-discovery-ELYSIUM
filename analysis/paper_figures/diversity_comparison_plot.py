import matplotlib.pyplot as plt

models = ["Random", "VAE", "GCPN", "ChemBERTa-RL"]
internal_diversity = [0.80, 0.74, 0.70, 0.76]
colors = ["#999999", "#56B4E9", "#E69F00", "#0072B2"]

plt.figure(figsize=(6, 4))
bars = plt.bar(models, internal_diversity, color=colors)
plt.title("Internal Diversity (1 - Tanimoto Similarity)")
plt.ylabel("Average Pairwise Distance")
plt.ylim(0, 1)

for bar, value in zip(bars, internal_diversity):
    plt.text(bar.get_x() + bar.get_width() / 2, value + 0.02, f"{value:.2f}", ha="center", va="bottom", fontsize=9)

plt.tight_layout()
plt.savefig("diversity_comparison.png", dpi=300)
plt.close()
