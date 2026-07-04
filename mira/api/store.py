from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from mira.types import Mandate

# POURQUOI 1 SEUL WORKER UVICORN EST REQUIS :
# L'état des cas (CaseState) est maintenu in-memory dans le dictionnaire global _cases.
# Si l'API tournait avec plusieurs workers (processus séparés), chaque worker aurait sa propre
# copie de la mémoire. Un POST /confirm pourrait être routé vers un worker qui n'a pas
# la tâche asynchrone (task) ou la queue d'événements (queue) correspondante, causant
# une erreur 404 introuvable en plein milieu du flow. 
# -> uvicorn.run(..., workers=1) est obligatoire pour ce design in-memory simple.

@dataclass
class CaseState:
    mandate: Mandate
    queue: asyncio.Queue[Any] = field(default_factory=asyncio.Queue)
    confirm_future: asyncio.Future[bool] = field(default_factory=lambda: asyncio.get_running_loop().create_future())
    records: list[Any] = field(default_factory=list)
    task: asyncio.Task[Any] | None = None
    status: str = "INIT"

_cases: dict[str, CaseState] = {}

class CaseAlreadyExists(Exception):
    pass

class CaseNotFound(Exception):
    pass

def create_case(case_id: str, mandate: Mandate) -> CaseState:
    if case_id in _cases:
        raise CaseAlreadyExists(f"Case {case_id} is already active.")
    state = CaseState(mandate=mandate)
    _cases[case_id] = state
    return state

def get_case(case_id: str) -> CaseState:
    if case_id not in _cases:
        raise CaseNotFound(f"Case {case_id} not found.")
    return _cases[case_id]

def drop_case(case_id: str) -> None:
    _cases.pop(case_id, None)

def purge(case_id: str) -> None:
    if case_id in _cases:
        case = _cases[case_id]
        case.records.clear()
        drop_case(case_id)
