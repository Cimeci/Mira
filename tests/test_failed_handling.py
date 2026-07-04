"""Tests l1-failed-handling : une panne d'infra devient un FAILED propre, jamais un crash.

Politique testée (orchestrateur) : les exceptions IMPRÉVUES (réseau, API externe, bug
interne d'un mock remplacé par du réel) sont converties en Status.FAILED + StageEvent
sans le message d'origine (il peut contenir URL/PII) ; les erreurs de CONTRAT
(ConsentError, ValueError/TypeError/KeyError des gates fail-fast) remontent TOUJOURS
à l'appelant — les avaler masquerait un bug ou un refus de consentement.
"""

import asyncio

import pytest

from mira import analyzer, notifier
from mira import mandate as mandate_mod
from mira.orchestrator import ConsentError, dispatch, run, run_until_gate
from mira.types import NotificationRecord, Status

# Sentinelle : si cette chaîne fuit dans un event, le message d'exception (URL/PII
# potentielle) sort du process — exactement ce que l1-failed-handling interdit.
_SECRET = "SECRET https://pii.example/ne-doit-jamais-fuiter"


async def _approve(notice: str) -> bool:
    return True


def _silent(_msg: str) -> None:
    pass


def _two_item_mandate():
    """Mandat à 2 scope_urls : un item sain + un item 'boom' piégé dans le même run."""
    m = mandate_mod.create_demo_mandate(case_id="failed-handling")
    m.scope_urls = [
        "https://mock-host.local/target",
        "https://mock-host.local/boom",
    ]
    return m


def test_analyze_failure_yields_failed_record_and_run_survives(monkeypatch):
    async def exploding_cv_score(item):
        if "boom" in item.url:
            raise RuntimeError(_SECRET)
        return 0.94

    monkeypatch.setattr(analyzer, "_cv_score", exploding_cv_score)
    events = []
    results = asyncio.run(
        run(_two_item_mandate(), confirm=_approve, log=_silent, emit=events.append)
    )

    # L'item piégé produit un record FAILED : score nul, aucune empreinte retenue.
    failed = [r for r in results if getattr(r, "status", None) is Status.FAILED]
    assert len(failed) == 1 and "boom" in failed[0].source_url
    assert failed[0].deepfake_score == 0.0
    assert failed[0].perceptual_hash == "" and failed[0].sha256_hash == ""
    assert failed[0].minimal_ref is None

    # Un event FAILED est émis avec le TYPE d'exception seulement — jamais le message.
    failed_events = [e for e in events if e.to_status is Status.FAILED]
    assert len(failed_events) == 1
    assert failed_events[0].payload == {"stage": "analyzer", "error_type": "RuntimeError"}
    assert _SECRET not in failed_events[0].detail

    # L'item sain du même run aboutit quand même : le pipeline termine proprement.
    assert any(getattr(r, "status", None) is Status.NOTIFIED for r in results)


def test_send_failure_returns_failed_notification(monkeypatch):
    async def exploding_send(notice, record, mandate, *, confirm, log, emit):
        raise ConnectionError(_SECRET)

    m = mandate_mod.create_demo_mandate(case_id="failed-send")
    records, notices = asyncio.run(run_until_gate(m, log=_silent, emit=lambda _e: None))
    record = next(r for r in records if r.status is Status.VERIFIED)
    monkeypatch.setattr(notifier, "send", exploding_send)

    events = []
    note = asyncio.run(
        dispatch(record, m, notices[record.source_url],
                 confirm=_approve, log=_silent, emit=events.append)
    )
    # dispatch renvoie un NotificationRecord FAILED au lieu de propager : rien n'est parti.
    assert isinstance(note, NotificationRecord)
    assert note.status is Status.FAILED
    assert note.host_contact == ""
    failed_events = [e for e in events if e.to_status is Status.FAILED]
    assert len(failed_events) == 1
    assert failed_events[0].payload == {"stage": "notifier", "error_type": "ConnectionError"}
    assert _SECRET not in failed_events[0].detail


def test_consent_error_still_raises():
    m = mandate_mod.create_demo_mandate(case_id="failed-consent")
    m.active = False
    with pytest.raises(ConsentError):
        asyncio.run(run(m, confirm=_approve, log=_silent, emit=lambda _e: None))


def test_dispatch_case_mismatch_still_raises():
    """Le ValueError des gates fail-fast de dispatch n'est jamais converti en FAILED."""
    m = mandate_mod.create_demo_mandate(case_id="failed-gate")
    records, notices = asyncio.run(run_until_gate(m, log=_silent, emit=lambda _e: None))
    record = next(r for r in records if r.status is Status.VERIFIED)
    other = mandate_mod.create_demo_mandate(case_id="failed-gate-other")
    with pytest.raises(ValueError, match="authorization mismatch"):
        asyncio.run(
            dispatch(record, other, notices[record.source_url],
                     confirm=_approve, log=_silent, emit=lambda _e: None)
        )
