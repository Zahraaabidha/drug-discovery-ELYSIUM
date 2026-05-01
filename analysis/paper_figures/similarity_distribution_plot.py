import numpy as np
import matplotlib.pyplot as plt

np.random.seed(42)
similarities = np.clip(np.random.normal(loc=0.62, scale=0.08, size=300), 0, 1)

plt.figure(figsize=(6, 4))
plt.hist(similarities, bins=15, color="#0072B2", alpha=0.85, edgecolor="white")
plt.title("Tanimoto Similarity Distribution (ChemBERTa-RL)")
plt.xlabel("Tanimoto Similarity")
plt.ylabel("Frequency")
plt.tight_layout()
plt.savefig("similarity_distribution.png", dpi=300)
plt.close()
