#C:\Users\Aabidha\Desktop\PROJECTS\elysium\elysium\backend\app\data\candidate_library.py
"""
Expanded library of drug-like molecules for ELYSIUM to sample from.
50 diverse drug-like SMILES covering multiple therapeutic classes.
"""

from typing import Dict, List

Candidate = Dict[str, str]

CANDIDATE_LIBRARY: List[Candidate] = [
    # Anti-inflammatory / Pain
    {"name": "Paracetamol", "smiles": "CC(=O)NC1=CC=C(O)C=C1"},
    {"name": "Ibuprofen", "smiles": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O"},
    {"name": "Aspirin", "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O"},
    {"name": "Naproxen", "smiles": "COC1=CC2=CC=CC=C2C=C1C(C)C(=O)O"},
    {"name": "Diclofenac", "smiles": "OC(=O)CC1=CC=CC=C1NC2=C(Cl)C=CC=C2Cl"},
    {"name": "Celecoxib", "smiles": "CC1=CC=C(C=C1)C2=CC(=NN2C3=CC=C(C=C3)S(N)(=O)=O)C(F)(F)F"},
    {"name": "Meloxicam", "smiles": "CC1=CN=C(S1)NC(=O)C2=C(O)C3=CC=CC=C3S(=O)(=O)N2C"},
    {"name": "Indomethacin", "smiles": "COC1=CC2=CC=CC=C2C(=C1)CC(=O)N3C=C(C(=O)O)C4=CC=C(Cl)C=C43"},

    # Cardiovascular
    {"name": "Propranolol", "smiles": "CC(C)NCC(O)COC1=CC=CC2=CC=CC=C21"},
    {"name": "Metoprolol", "smiles": "CC(C)CCOC1=CC=C(C=C1)OCC(N)CO"},
    {"name": "Atenolol", "smiles": "CC(C)NCC(O)COC1=CC=C(CC(N)=O)C=C1"},
    {"name": "Amlodipine", "smiles": "CCOC(=O)C1=C(COCCN)NC(C)=C(C1C2=CC=CC=C2Cl)C(=O)OC"},
    {"name": "Lisinopril", "smiles": "OC(=O)C(CCCCN)NC(C(=O)N1CCCC1C(=O)O)CC2=CC=CC=C2"},
    {"name": "Valsartan", "smiles": "CCCCC1=NC2=CC=CC=C2N1CC3=CC=C(C=C3)C4=CC=CC=C4C(=O)O"},
    {"name": "Warfarin", "smiles": "OC(=O)CC(C1=CC=CC=C1)C2=C(O)C3=CC=CC=C3C2=O"},

    # Antibiotics
    {"name": "Amoxicillin", "smiles": "CC1(C)SC2C(NC(=O)C(N)C3=CC=C(O)C=C3)C(=O)N2C1C(=O)O"},
    {"name": "Ciprofloxacin", "smiles": "OC(=O)C1=CN(C2CC2)C3=CC(=C(C=C13)N4CCNCC4)F"},
    {"name": "Metronidazole", "smiles": "CC1=NC=C(CCO)N1CC2=CC=C([N+](=O)[O-])C=C2"},
    {"name": "Doxycycline", "smiles": "OC1=C2CC3CC4C(O)=C(O)C(=O)C(C)(O)C4CC3(O)C2(O)C(=O)C1=O"},
    {"name": "Azithromycin_frag", "smiles": "CC1OC(=O)C2CC(OC3OC(C)C(O)C(OC)C3O)CC2(O)C(C)(O)CC(CC(=O)O)NC1"},

    # CNS / Neurological
    {"name": "Caffeine", "smiles": "Cn1cnc2c1c(=O)n(C)c(=O)n2C"},
    {"name": "Fluoxetine", "smiles": "CNCCC(OC1=CC=CC=C1)C2=CC=C(C=C2)C(F)(F)F"},
    {"name": "Sertraline", "smiles": "CNC1CCC2=CC=CC=C2C1C3=CC(Cl)=CC=C3Cl"},
    {"name": "Diazepam", "smiles": "CN1C(=O)CN=C(C2=CC=CC=C21)C3=CC=CC=C3Cl"},
    {"name": "Levodopa", "smiles": "NC(CC1=CC(O)=C(O)C=C1)C(=O)O"},
    {"name": "Donepezil", "smiles": "COC1=CC=C(CC2CCN(CC3=CC=CC=C3)CC2)C=C1OC"},

    # Antidiabetic
    {"name": "Metformin", "smiles": "CN(C)C(=N)NC(=N)N"},
    {"name": "Glipizide", "smiles": "CC1=CN=C(C=C1)C(=O)NCCC2=CC=C(C=C2)S(=O)(=O)NC(=O)NC3CCCCC3"},
    {"name": "Sitagliptin_frag", "smiles": "FC1=CC=C(CC(N)CC(=O)N2CC3=NN=C(C=C3C2)C(F)(F)F)C=C1F"},

    # Anticancer
    {"name": "Imatinib_frag", "smiles": "CC1=CN=C(NC2=NC=CC(=N2)C3=CC=CN=C3)C=C1NC(=O)C4=CC=C(CN5CCN(C)CC5)C=C4"},
    {"name": "Gefitinib", "smiles": "COC1=CC2=NC=NC(=C2C=C1OCCCN3CCOCC3)NC4=CC=C(F)C(Cl)=C4"},
    {"name": "Erlotinib", "smiles": "COCCOC1=CC2=NC=NC(=C2C=C1OCCOC)NC3=CC=CC(C#C)=C3"},
    {"name": "Tamoxifen", "smiles": "CCN(CC)CCOC1=CC=C(C=C1)C(=C2C=CC=CC2)C3=CC=CC=C3"},

    # GI / Acid
    {"name": "Omeprazole", "smiles": "COC1=CC=C(C=C1OCC2=NC(=CS2)NC3=CC=CC(=N3)C)OC"},
    {"name": "Ranitidine", "smiles": "CNC(=NC#N)NCCSCC1=CC=C(CN(C)C)O1"},
    {"name": "Famotidine", "smiles": "NC(=N)NS(=O)(=O)C1=NC(=CS1)CSCCC(=N)N"},

    # Antifungal / Antiviral
    {"name": "Fluconazole", "smiles": "OC(CN1C=NC=N1)(CN2C=NC=N2)C3=CC=C(F)C=C3F"},
    {"name": "Oseltamivir_frag", "smiles": "CCOC(=O)C1=C(OC(CC)CC)CC(N)CC1N"},
    {"name": "Acyclovir", "smiles": "NC1=NC2=C(N=CN2COCCO)C(=O)N1"},

    # Lipid / Metabolic
    {"name": "Atorvastatin_frag", "smiles": "CC(C)C1=CC(=O)CC(C1)CC(O)CC(O)CC(=O)O"},
    {"name": "Rosuvastatin_frag", "smiles": "CC(C)C1=NC(=NC=C1CC=CC(O)CC(O)CC(=O)O)N(C)S(C)(=O)=O"},
    {"name": "Fenofibrate_frag", "smiles": "CC(C)(OC(=O)C1=CC=C(Cl)C=C1)C(=O)OCC(C)C"},

    # Misc drug-like scaffolds
    {"name": "Lidocaine", "smiles": "CCN(CC)CC(=O)N1CCN(CC1)C2=CC=CC=C2"},
    {"name": "Morphine_frag", "smiles": "OC1=CC2=C(C=C1)C3CC4N(CCC34)CC2"},
    {"name": "Theophylline", "smiles": "Cn1cnc2c1c(=O)[nH]c(=O)n2C"},
    {"name": "Theobromine", "smiles": "Cn1cnc2c1c(=O)[nH]c(=O)n2C"},
    {"name": "Chloroquine_frag", "smiles": "CCN(CC)CCCC(C)NC1=CC=NC2=CC(Cl)=CC=C21"},
    {"name": "Hydroxychloroquine_frag", "smiles": "CCN(CCO)CCCC(C)NC1=CC=NC2=CC(Cl)=CC=C21"},
    {"name": "Dexamethasone_frag", "smiles": "CC1CC2C3CCC4=CC(=O)C=CC4(C)C3(F)C(O)CC2(C)C1(O)C(=O)CO"},
    {"name": "Prednisolone_frag", "smiles": "CC1CC2C3CCC4=CC(=O)C=CC4(C)C3C(O)CC2(C)C1(O)C(=O)CO"},
]