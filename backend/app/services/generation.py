"""Molecule generation.

MutationGenerator builds NEW structures from seed molecules with RDKit (functional-group edits
and BRICS fragment recombination). Every returned molecule has been validated, standardised,
de-duplicated and checked against the known-compound set, so reference compounds are never
returned as "generated". If fewer than the requested number of novel molecules can be found
the generator returns fewer - it never pads with library molecules.
"""
from __future__ import annotations

import logging
import random
import threading
from dataclasses import dataclass, field, asdict
from typing import Dict, Iterable, List, Optional, Sequence, Set

from rdkit import Chem
from rdkit.Chem import AllChem, BRICS, Descriptors

from . import chem

log = logging.getLogger(__name__)
_GLOBAL_RANDOM_LOCK = threading.Lock()   # BRICSBuild shuffles with the global `random` module

METHOD_NAME = "rdkit_mutation_brics"


@dataclass
class GenerationStats:
    method: str = METHOD_NAME
    requested: int = 0
    attempted: int = 0          # candidate strings produced
    valid: int = 0              # parsed + standardised
    filtered_size: int = 0      # valid but outside the MW window
    unique: int = 0             # distinct InChIKeys among accepted-valid
    novel: int = 0              # unique and absent from the known-compound set
    returned: int = 0
    exhausted: bool = False     # stopped at the attempt cap before reaching `requested`

    @property
    def validity(self) -> Optional[float]:
        return self.valid / self.attempted if self.attempted else None

    @property
    def uniqueness(self) -> Optional[float]:
        return self.unique / self.valid if self.valid else None

    @property
    def novelty(self) -> Optional[float]:
        return self.novel / self.unique if self.unique else None

    def as_dict(self) -> Dict:
        d = asdict(self)
        d.update(validity=self.validity, uniqueness=self.uniqueness, novelty=self.novelty)
        return d


@dataclass
class GenerationResult:
    smiles: List[str]
    stats: GenerationStats
    params: Dict = field(default_factory=dict)


class GeneratorBackend:
    method = METHOD_NAME

    def generate(self, target_id: str, num_molecules: int, **kwargs) -> GenerationResult:  # pragma: no cover
        raise NotImplementedError


class MutationGenerator(GeneratorBackend):
    _EDITS = [
        "[c:1][H]>>[c:1]F",
        "[c:1][H]>>[c:1]Cl",
        "[c:1][H]>>[c:1]C",
        "[c:1][H]>>[c:1]O",
        "[c:1][H]>>[c:1]N",
        "[CH3:1]>>[CH2:1]F",
        "[F:1]>>[Cl:1]",
        "[Cl:1]>>[F:1]",
        "[c:1]-[OH:2]>>[c:1]-[O:2]C",
        "[nH:1]>>[n:1]C",
        "[NH2:1]>>[NH:1]C",
    ]

    def __init__(self, seed_smiles: Optional[Sequence[str]] = None, mw_min: float = 150, mw_max: float = 650) -> None:
        self.mw_min, self.mw_max = mw_min, mw_max
        self._rxns = [AllChem.ReactionFromSmarts(e) for e in self._EDITS]
        self.set_seeds(seed_smiles or [])

    def set_seeds(self, seed_smiles: Iterable[str]) -> None:
        self._seeds = [s for s in seed_smiles if chem.is_valid(s)]
        frags: Set[str] = set()
        for smi in self._seeds:
            mol = Chem.MolFromSmiles(smi)
            if mol is not None:
                frags.update(BRICS.BRICSDecompose(mol, minFragmentSize=3))
        self._frag_mols = [x for x in (Chem.MolFromSmiles(f) for f in sorted(frags)) if x is not None]

    # ── operators ──────────────────────────────────────────────────────
    def _mutate(self, smi: str, rng: random.Random) -> Optional[str]:
        mol = Chem.AddHs(Chem.MolFromSmiles(smi))
        rxn = rng.choice(self._rxns)
        try:
            products = rxn.RunReactants((mol,))
        except Exception:
            return None
        if not products:
            return None
        prod = rng.choice(products)[0]
        try:
            prod = Chem.RemoveHs(prod)
            Chem.SanitizeMol(prod)
            return Chem.MolToSmiles(prod)
        except Exception:
            return None

    def _recombine(self, count: int, rng: random.Random) -> List[str]:
        out: List[str] = []
        if len(self._frag_mols) < 2:
            return out
        seeds = rng.sample(self._frag_mols, k=min(len(self._frag_mols), 30))
        try:
            for mol in BRICS.BRICSBuild(seeds, maxDepth=1, scrambleReagents=True):
                try:
                    Chem.SanitizeMol(mol)
                    out.append(Chem.MolToSmiles(mol))
                except Exception:
                    out.append("")   # counted as an invalid attempt
                if len(out) >= count:
                    break
        except Exception:
            pass
        return out

    # ── public API ─────────────────────────────────────────────────────
    def generate(self, target_id: str, num_molecules: int, *, seed: Optional[int] = None,
                 known_inchikeys: Optional[Set[str]] = None, max_attempts_per_molecule: int = 60) -> GenerationResult:
        stats = GenerationStats(requested=max(num_molecules, 0))
        params = {"method": METHOD_NAME, "seed": seed, "mw_window": [self.mw_min, self.mw_max],
                  "num_seed_molecules": len(self._seeds), "num_fragments": len(self._frag_mols),
                  "max_attempts_per_molecule": max_attempts_per_molecule, "edits": self._EDITS}
        if num_molecules <= 0 or not self._seeds:
            return GenerationResult([], stats, params)

        known = set(known_inchikeys or ())
        seen_keys: Set[str] = set()
        results: List[str] = []
        rng = random.Random(seed)
        cap = num_molecules * max_attempts_per_molecule

        with _GLOBAL_RANDOM_LOCK:
            random.seed(seed)
            while len(results) < num_molecules and stats.attempted < cap:
                if stats.attempted % 4 == 3:
                    candidates = self._recombine(2, rng) or [None]
                else:
                    candidates = [self._mutate(rng.choice(self._seeds), rng)]
                for cand in candidates:
                    stats.attempted += 1
                    if not cand:
                        continue
                    try:
                        std = chem.standardise(cand)
                    except chem.InvalidMolecule:
                        continue
                    stats.valid += 1
                    mol = Chem.MolFromSmiles(std.canonical_smiles)
                    if not (self.mw_min <= Descriptors.MolWt(mol) <= self.mw_max):
                        stats.filtered_size += 1
                        continue
                    if std.inchikey in seen_keys:
                        continue
                    seen_keys.add(std.inchikey)
                    stats.unique += 1
                    if std.inchikey in known:
                        continue
                    stats.novel += 1
                    results.append(std.canonical_smiles)
                    if len(results) >= num_molecules:
                        break
            stats.exhausted = len(results) < num_molecules
        stats.returned = len(results)
        return GenerationResult(results, stats, params)


_generator: Optional[MutationGenerator] = None


def get_generator(seed_smiles: Optional[Sequence[str]] = None) -> MutationGenerator:
    """Generator seeded with the given known compounds (defaults to the bundled reference library)."""
    global _generator
    if seed_smiles is not None:
        gen = MutationGenerator(seed_smiles)
        return gen
    if _generator is None:
        from ..data.candidate_library import CANDIDATE_LIBRARY
        _generator = MutationGenerator([e["smiles"] for e in CANDIDATE_LIBRARY if e.get("smiles")])
    return _generator
