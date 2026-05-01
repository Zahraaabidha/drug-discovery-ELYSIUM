"""
Known drug library for ELYSIUM similarity search.
Used by both fingerprint similarity and ChemBERTa semantic similarity.
"""

from typing import List, Dict

DrugRecord = Dict[str, str]

FDA_LIKE_DRUGS: List[DrugRecord] = [
    {"name": "Paracetamol", "smiles": "CC(=O)NC1=CC=C(O)C=C1", "indication": "Pain relief, fever reduction"},
    {"name": "Ibuprofen", "smiles": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O", "indication": "Pain relief, anti-inflammatory"},
    {"name": "Aspirin", "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O", "indication": "Pain relief, anti-inflammatory, antiplatelet"},
    {"name": "Caffeine", "smiles": "Cn1cnc2c1c(=O)n(C)c(=O)n2C", "indication": "Stimulant"},
    {"name": "Lidocaine", "smiles": "CCN(CC)CC(=O)N1CCN(CC1)C2=CC=CC=C2", "indication": "Local anesthetic, antiarrhythmic"},
    {"name": "Propranolol", "smiles": "CC(C)NCC(O)COC1=CC=CC2=CC=CC=C21", "indication": "Beta blocker, hypertension"},
    {"name": "Metoprolol", "smiles": "CC(C)CCOC1=CC=C(C=C1)OCC(N)CO", "indication": "Beta blocker, heart failure"},
    {"name": "Omeprazole", "smiles": "COC1=CC=C(C=C1OCC2=NC(=CS2)NC3=CC=CC(=N3)C)OC", "indication": "Proton pump inhibitor, acid reflux"},
    {"name": "Atorvastatin", "smiles": "CC(C)C1=CC(=O)CC(C1)CC(O)CC(O)CC(=O)O", "indication": "Statin, high cholesterol"},
    {"name": "Metformin", "smiles": "CN(C)C(=N)NC(=N)N", "indication": "Type 2 diabetes"},
    {"name": "Amlodipine", "smiles": "CCOC(=O)C1=C(COCCN)NC(C)=C(C1C2=CC=CC=C2Cl)C(=O)OC", "indication": "Calcium channel blocker, hypertension"},
    {"name": "Fluoxetine", "smiles": "CNCCC(OC1=CC=CC=C1)C2=CC=C(C=C2)C(F)(F)F", "indication": "SSRI antidepressant"},
    {"name": "Sertraline", "smiles": "CNC1CCC2=CC=CC=C2C1C3=CC(Cl)=CC=C3Cl", "indication": "SSRI antidepressant"},
    {"name": "Diazepam", "smiles": "CN1C(=O)CN=C(C2=CC=CC=C21)C3=CC=CC=C3Cl", "indication": "Benzodiazepine, anxiety"},
    {"name": "Ciprofloxacin", "smiles": "OC(=O)C1=CN(C2CC2)C3=CC(=C(C=C13)N4CCNCC4)F", "indication": "Fluoroquinolone antibiotic"},
    {"name": "Amoxicillin", "smiles": "CC1(C)SC2C(NC(=O)C(N)C3=CC=C(O)C=C3)C(=O)N2C1C(=O)O", "indication": "Beta-lactam antibiotic"},
    {"name": "Warfarin", "smiles": "OC(=O)CC(C1=CC=CC=C1)C2=C(O)C3=CC=CC=C3C2=O", "indication": "Anticoagulant"},
    {"name": "Naproxen", "smiles": "COC1=CC2=CC=CC=C2C=C1C(C)C(=O)O", "indication": "NSAID, pain relief"},
    {"name": "Diclofenac", "smiles": "OC(=O)CC1=CC=CC=C1NC2=C(Cl)C=CC=C2Cl", "indication": "NSAID, anti-inflammatory"},
    {"name": "Fluconazole", "smiles": "OC(CN1C=NC=N1)(CN2C=NC=N2)C3=CC=C(F)C=C3F", "indication": "Antifungal"},
    {"name": "Acyclovir", "smiles": "NC1=NC2=C(N=CN2COCCO)C(=O)N1", "indication": "Antiviral, herpes"},
    {"name": "Gefitinib", "smiles": "COC1=CC2=NC=NC(=C2C=C1OCCCN3CCOCC3)NC4=CC=C(F)C(Cl)=C4", "indication": "EGFR inhibitor, lung cancer"},
    {"name": "Erlotinib", "smiles": "COCCOC1=CC2=NC=NC(=C2C=C1OCCOC)NC3=CC=CC(C#C)=C3", "indication": "EGFR inhibitor, lung cancer"},
    {"name": "Tamoxifen", "smiles": "CCN(CC)CCOC1=CC=C(C=C1)C(=C2C=CC=CC2)C3=CC=CC=C3", "indication": "Breast cancer, estrogen receptor"},
    {"name": "Dexamethasone", "smiles": "CC1CC2C3CCC4=CC(=O)C=CC4(C)C3(F)C(O)CC2(C)C1(O)C(=O)CO", "indication": "Corticosteroid, inflammation"},
    {"name": "Theophylline", "smiles": "Cn1cnc2c1c(=O)[nH]c(=O)n2C", "indication": "Bronchodilator, asthma"},
    {"name": "Donepezil", "smiles": "COC1=CC=C(CC2CCN(CC3=CC=CC=C3)CC2)C=C1OC", "indication": "Acetylcholinesterase inhibitor, Alzheimers"},
    {"name": "Levodopa", "smiles": "NC(CC1=CC(O)=C(O)C=C1)C(=O)O", "indication": "Dopamine precursor, Parkinsons"},
    {"name": "Chloroquine", "smiles": "CCN(CC)CCCC(C)NC1=CC=NC2=CC(Cl)=CC=C21", "indication": "Antimalarial"},
    {"name": "Ranitidine", "smiles": "CNC(=NC#N)NCCSCC1=CC=C(CN(C)C)O1", "indication": "H2 blocker, acid reflux"},
]