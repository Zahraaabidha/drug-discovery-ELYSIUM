import matplotlib.pyplot as plt

# Example discovery results (demo values for hackathon)
molecules = [
    "Mol_1",
    "Mol_2",
    "Mol_3",
    "Mol_4",
    "Mol_5"
]

# Predicted binding affinity scores
# (Lower = stronger binding, for illustration)
binding_scores = [
    -8.2,
    -7.5,
    -9.1,
    -6.8,
    -8.7
]

plt.figure(figsize=(8, 5))
plt.bar(molecules, binding_scores)
plt.xlabel("Molecules")
plt.ylabel("Binding Affinity Score")
plt.title("Predicted Binding Affinity vs Molecules")
plt.tight_layout()

# Save image for PPT
plt.savefig("analysis/binding_scores.png")

plt.show()
