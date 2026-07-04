"""Tests du flux d'événements structurés (mira/events.py) — le contrat SSE de L2/L3.

On teste les EVENTS ici ; les records (dont le DECLINED exact sur refus) sont
couverts par test_pipeline.py. Le gate G-7 étant async, les confirms sont des
coroutines.
"""

import asyncio

from mira import mandate as mandate_mod
from mira.events import StageEvent
from mira.orchestrator import run
from mira.types import Status


async def _approve(notice: str) -> bool:
    return True


async def _decline(notice: str) -> bool:
    return False


def _run_collecting(mandate, *, confirm) -> list[StageEvent]:
    events: list[StageEvent] = []
    asyncio.run(run(mandate, confirm=confirm, log=lambda _msg: None, emit=events.append))
    return events


def test_happy_path_emits_ordered_transitions():
    m = mandate_mod.create_demo_mandate()
    events = _run_collecting(m, confirm=_approve)
    assert [e.to_status for e in events] == [
        Status.MANDATED,
        Status.LOCATED,
        Status.VERIFIED,
        Status.AWAITING_CONFIRM,  # stage "notice" : aperçu pré-gate avec notice_text
        Status.AWAITING_CONFIRM,  # stage "notifier" : le gate G-7 standard
        Status.CONFIRMED,
        Status.NOTIFIED,
    ]
    assert [e.stage for e in events if e.to_status is Status.AWAITING_CONFIRM] == [
        "notice",
        "notifier",
    ]
    assert all(e.case_id == m.case_id for e in events)
    # MANDATED est la naissance du case : seul event sans état antérieur.
    assert events[0].from_status is None
    assert all(e.from_status is not None for e in events[1:])
    # Le dict canonique est JSON-friendly (StrEnum -> str, datetime -> ISO).
    as_dict = events[-1].to_dict()
    assert as_dict["to_status"] == "NOTIFIED"
    assert isinstance(as_dict["ts_utc"], str)


def test_notice_preview_event_precedes_gate_with_notice_text():
    """Contrat L3 : l'event stage='notice' porte le texte de la notice (exception
    documentée dans events.py) et arrive AVANT le gate AWAITING_CONFIRM standard —
    c'est lui qui remplit le panneau de confirmation avant le clic de la victime."""
    m = mandate_mod.create_demo_mandate()
    events = _run_collecting(m, confirm=_approve)
    notice_events = [e for e in events if e.stage == "notice"]
    assert len(notice_events) == 1
    preview = notice_events[0]
    assert preview.to_status is Status.AWAITING_CONFIRM
    assert preview.from_status is Status.VERIFIED
    assert preview.payload["url"]
    assert preview.payload["notice_text"].startswith("Objet :")
    gate_index = next(
        i for i, e in enumerate(events)
        if e.stage == "notifier" and e.to_status is Status.AWAITING_CONFIRM
    )
    assert events.index(preview) < gate_index


def test_suspected_minor_emits_minimal_escalated_event():
    m = mandate_mod.create_demo_mandate(case_id="minor-events")
    m.scope_urls = ["https://mock-host.local/minor-case"]
    events = _run_collecting(m, confirm=_approve)
    escalated = [e for e in events if e.to_status is Status.ESCALATED]
    assert escalated, "un flag mineur doit émettre ESCALATED"
    event = escalated[0]
    # G-6 : payload MINIMAL — case_id + raison uniquement, pas d'URL du média, pas de hash.
    assert event.payload == {"reason": "suspected_minor"}
    assert event.case_id == "minor-events"
    assert "minor-case" not in event.detail  # la ligne CLI n'expose pas l'URL non plus


def test_decline_emits_declined_and_never_notified():
    m = mandate_mod.create_demo_mandate()
    events = _run_collecting(m, confirm=_decline)
    statuses = [e.to_status for e in events]
    assert Status.DECLINED in statuses
    assert Status.NOTIFIED not in statuses
    # Le gate a bien été présenté avant le refus (G-7).
    assert statuses.index(Status.AWAITING_CONFIRM) < statuses.index(Status.DECLINED)
