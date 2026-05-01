import matplotlib.pyplot as plt

models = ["Random", "VAE", "GCPN", "ChemBERTa-RL"]
validity_percent = [55, 72, 88, 94]
colors = ["#999999", "#56B4E9", "#E69F00", "#0072B2"]

plt.figure(figsize=(6, 4))
bars = plt.bar(models, validity_percent, color=colors)
plt.title("Validity Rate of Generated Molecules")
plt.ylabel("Validity (%)")
plt.ylim(0, 100)

for bar, value in zip(bars, validity_percent):
    plt.text(bar.get_x() + bar.get_width() / 2, value + 1.5, f"{value}%", ha="center", va="bottom", fontsize=9)

plt.tight_layout()
plt.savefig("validity_comparison.png", dpi=300)
plt.close()
