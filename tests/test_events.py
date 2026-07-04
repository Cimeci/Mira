"""Tests du flux d'événements structurés (mira/events.py) — le contrat SSE de L2/L3.

On teste les EVENTS, pas les records : le record retourné sur decline porte encore le
statut CONFIRMED (bug connu, corrigé par la tâche l1-failed-handling suivante).
"""

import asyncio

from mira import mandate as mandate_mod
from mira.events import StageEvent
from mira.orchestrator import run
from mira.types import Status


def _run_collecting(mandate, *, confirm) -> list[StageEvent]:
    events: list[StageEvent] = []
    asyncio.run(run(mandate, confirm=confirm, log=lambda _msg: None, emit=events.append))
    return events


def test_happy_path_emits_ordered_transitions():
    m = mandate_mod.create_demo_mandate()
    events = _run_collecting(m, confirm=lambda notice: True)
    assert [e.to_status for e in events] == [
        Status.MANDATED,
        Status.LOCATED,
        Status.VERIFIED,
        Status.AWAITING_CONFIRM,
        Status.CONFIRMED,
        Status.NOTIFIED,
    ]
    assert all(e.case_id == m.case_id for e in events)
    # MANDATED est la naissance du case : seul event sans état antérieur.
    assert events[0].from_status is None
    assert all(e.from_status is not None for e in events[1:])
    # Le dict canonique est JSON-friendly (StrEnum -> str, datetime -> ISO).
    as_dict = events[-1].to_dict()
    assert as_dict["to_status"] == "NOTIFIED"
    assert isinstance(as_dict["ts_utc"], str)


def test_suspected_minor_emits_minimal_escalated_event():
    m = mandate_mod.create_demo_mandate(case_id="minor-events")
    m.scope_urls = ["https://mock-host.local/minor-case"]
    events = _run_collecting(m, confirm=lambda notice: True)
    escalated = [e for e in events if e.to_status is Status.ESCALATED]
    assert escalated, "un flag mineur doit émettre ESCALATED"
    event = escalated[0]
    # G-6 : payload MINIMAL — case_id + raison uniquement, pas d'URL du média, pas de hash.
    assert event.payload == {"reason": "suspected_minor"}
    assert event.case_id == "minor-events"
    assert "minor-case" not in event.detail  # la ligne CLI n'expose pas l'URL non plus


def test_decline_emits_declined_and_never_notified():
    m = mandate_mod.create_demo_mandate()
    events = _run_collecting(m, confirm=lambda notice: False)
    statuses = [e.to_status for e in events]
    assert Status.DECLINED in statuses
    assert Status.NOTIFIED not in statuses
    # Le gate a bien été présenté avant le refus (G-7).
    assert statuses.index(Status.AWAITING_CONFIRM) < statuses.index(Status.DECLINED)
