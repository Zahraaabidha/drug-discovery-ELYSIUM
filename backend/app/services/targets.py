"""Supported drug targets. Unsupported targets are rejected, never substituted."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

_SEQ_FILE = Path(__file__).resolve().parents[1] / "data" / "target_sequences.json"


class UnsupportedTarget(ValueError):
    def __init__(self, target_id: str, supported: List[str]):
        super().__init__(f"Unsupported target {target_id!r}. Supported targets: {', '.join(supported)}")
        self.target_id = target_id
        self.supported = supported


@dataclass(frozen=True)
class Target:
    symbol: str
    uniprot_id: str
    sequence: str


def _load() -> Dict[str, Target]:
    raw = json.loads(_SEQ_FILE.read_text(encoding="utf-8"))
    return {k: Target(k, v["uniprot_id"], v["sequence"]) for k, v in raw.items()}


_TARGETS = _load()


def supported_targets() -> List[str]:
    return sorted(_TARGETS)


def all_targets() -> Dict[str, Target]:
    return dict(_TARGETS)


def resolve_target(target_id: str) -> Target:
    key = (target_id or "").strip().upper()
    if key not in _TARGETS:
        raise UnsupportedTarget(target_id, supported_targets())
    return _TARGETS[key]
