import matplotlib.pyplot as plt

models = ["Random", "VAE", "GCPN", "ChemBERTa-RL"]
avg_qed = [0.42, 0.55, 0.68, 0.78]
colors = ["#999999", "#56B4E9", "#E69F00", "#0072B2"]

plt.figure(figsize=(6, 4))
bars = plt.bar(models, avg_qed, color=colors)
plt.title("Average QED Score Comparison")
plt.ylabel("QED Score")
plt.ylim(0, 1)

for bar, value in zip(bars, avg_qed):
    plt.text(bar.get_x() + bar.get_width() / 2, value + 0.02, f"{value:.2f}", ha="center", va="bottom", fontsize=9)

plt.tight_layout()
plt.savefig("qed_comparison.png", dpi=300)
plt.close()
