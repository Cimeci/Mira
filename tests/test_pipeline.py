"""Smoke tests du chemin de démo (spec G-13 : chaque stage testable avec mocks).

On teste UNE chose qui compte : les 3 beats de démo se comportent bien.
Le gate G-7 est async (contrat L2 : confirm attend un POST /confirm) — les confirms
de test sont donc des coroutines, jamais des lambdas sync.
"""

import asyncio

import pytest

from mira import config
from mira import mandate as mandate_mod
from mira.orchestrator import ConsentError, dispatch, run, run_until_gate
from mira.types import NotificationRecord, Status


async def _approve(notice: str) -> bool:
    return True


async def _decline(notice: str) -> bool:
    return False


def test_happy_path_dispatches_notice():
    m = mandate_mod.create_demo_mandate()
    results = asyncio.run(run(m, confirm=_approve))
    assert any(getattr(r, "status", None) is Status.NOTIFIED for r in results)


def test_no_active_mandate_refuses():
    m = mandate_mod.create_demo_mandate()
    m.active = False
    with pytest.raises(ConsentError):
        asyncio.run(run(m))


def test_suspected_minor_escalates_without_storage():
    m = mandate_mod.create_demo_mandate(case_id="minor")
    m.scope_urls = ["https://mock-host.local/minor-case"]
    results = asyncio.run(run(m, confirm=_approve))
    escalated = [r for r in results if getattr(r, "status", None) is Status.ESCALATED]
    assert escalated, "un flag mineur doit escalader"
    # Rien n'est stocké : pas de hash conservé.
    assert escalated[0].perceptual_hash == ""
    assert escalated[0].sha256_hash == ""


def test_victim_decline_holds_dispatch():
    m = mandate_mod.create_demo_mandate()
    results = asyncio.run(run(m, confirm=_decline))
    # Le refus produit un record DECLINED exact — jamais CONFIRMED sur un refus.
    notes = [r for r in results if isinstance(r, NotificationRecord)]
    assert notes, "le gate doit renvoyer un NotificationRecord même sur refus"
    assert all(n.status is Status.DECLINED for n in notes)
    assert not any(getattr(r, "status", None) is Status.NOTIFIED for r in results)


def test_confirm_timeout_fails_closed(monkeypatch):
    # Le notifier lit config.CONFIRM_TIMEOUT_S sur le module au moment de l'appel :
    # on patche l'attribut du module (pas une copie importée par valeur).
    monkeypatch.setattr(config, "CONFIRM_TIMEOUT_S", 0.05)

    async def never_answers(notice: str) -> bool:
        await asyncio.Event().wait()  # la victime ne répond jamais
        return True

    m = mandate_mod.create_demo_mandate()
    results = asyncio.run(run(m, confirm=never_answers))
    notes = [r for r in results if isinstance(r, NotificationRecord)]
    assert notes and all(n.status is Status.DECLINED for n in notes)
    assert not any(getattr(r, "status", None) is Status.NOTIFIED for r in results)


def test_run_until_gate_then_dispatch_split():
    """Contrat L2 : run_until_gate renvoie les VERIFIED sans rien envoyer,
    dispatch envoie APRÈS le verdict humain."""
    m = mandate_mod.create_demo_mandate()
    events = []
    records = asyncio.run(run_until_gate(m, log=lambda _msg: None, emit=events.append))
    verified = [r for r in records if r.status is Status.VERIFIED]
    assert verified, "le happy path doit produire au moins un record VERIFIED"
    # Rien n'a passé le gate : ni notice présentée, ni envoi.
    statuses = [e.to_status for e in events]
    assert Status.AWAITING_CONFIRM not in statuses
    assert Status.NOTIFIED not in statuses

    note = asyncio.run(
        dispatch(verified[0], m, confirm=_approve, log=lambda _msg: None, emit=events.append)
    )
    assert note.status is Status.NOTIFIED
    assert [e.to_status for e in events[-3:]] == [
        Status.AWAITING_CONFIRM,
        Status.CONFIRMED,
        Status.NOTIFIED,
    ]
