"""Reactome content service: pathways for a UniProt accession."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .http import get_json

URL = "https://reactome.org/ContentService/data/mapping/UniProt/{acc}/pathways"


@dataclass
class Pathway:
    st_id: str
    name: str
    species: str
    url: str


def parse_pathways(payload) -> List[Pathway]:
    out = []
    for p in payload or []:
        st_id = p.get("stId")
        if not st_id:
            continue
        out.append(Pathway(
            st_id=st_id, name=p.get("displayName") or st_id, species=p.get("speciesName", "Homo sapiens"),
            url=f"https://reactome.org/content/detail/{st_id}",
        ))
    return out


def fetch_pathways(uniprot_id: str, human_only: bool = True) -> List[Pathway]:
    paths = parse_pathways(get_json("Reactome", URL.format(acc=uniprot_id)))
    return [p for p in paths if p.species == "Homo sapiens"] if human_only else paths
