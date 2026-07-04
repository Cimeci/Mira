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
from mira.types import ForensicRecord, NotificationRecord, Status, utcnow


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
    """Contrat L2 : run_until_gate rédige et présente la notice (pré-gate) sans RIEN
    envoyer ; dispatch envoie la notice pré-rédigée APRÈS le verdict humain."""
    m = mandate_mod.create_demo_mandate()
    events = []
    records, notices = asyncio.run(
        run_until_gate(m, log=lambda _msg: None, emit=events.append)
    )
    verified = [r for r in records if r.status is Status.VERIFIED]
    assert verified, "le happy path doit produire au moins un record VERIFIED"
    # La notice pré-rédigée est disponible pour l'aperçu L3, indexée par source_url.
    assert notices[verified[0].source_url].startswith("Objet :")
    # Le gate est présenté (AWAITING_CONFIRM) mais rien n'a été confirmé ni envoyé.
    statuses = [e.to_status for e in events]
    assert Status.AWAITING_CONFIRM in statuses
    assert Status.CONFIRMED not in statuses
    assert Status.NOTIFIED not in statuses

    note = asyncio.run(
        dispatch(
            verified[0],
            m,
            notices[verified[0].source_url],
            confirm=_approve,
            log=lambda _msg: None,
            emit=events.append,
        )
    )
    assert note.status is Status.NOTIFIED
    # dispatch ne ré-émet PAS AWAITING_CONFIRM (déjà émis pré-gate) : verdict puis envoi.
    assert [e.to_status for e in events[-2:]] == [Status.CONFIRMED, Status.NOTIFIED]


def _verified_record_and_mandate():
    """Fabrique (record VERIFIED, mandat, notices) via le vrai pipeline pré-gate."""
    m = mandate_mod.create_demo_mandate()
    records, notices = asyncio.run(
        run_until_gate(m, log=lambda _msg: None, emit=lambda _e: None)
    )
    verified = [r for r in records if r.status is Status.VERIFIED]
    assert verified
    return verified[0], m, notices


def test_preview_notice_is_byte_identical_to_sent_notice():
    """Garantie centrale du split : la notice montrée en aperçu pré-gate (event
    'notice') est EXACTEMENT — octet pour octet — celle qui part après confirmation."""
    m = mandate_mod.create_demo_mandate()
    events = []
    records, notices = asyncio.run(
        run_until_gate(m, log=lambda _msg: None, emit=events.append)
    )
    record = next(r for r in records if r.status is Status.VERIFIED)
    preview = next(e for e in events if e.stage == "notice").payload["notice_text"]
    assert preview == notices[record.source_url]

    note = asyncio.run(
        dispatch(record, m, preview, confirm=_approve, log=lambda _msg: None,
                 emit=events.append)
    )
    assert note.status is Status.NOTIFIED
    assert note.notice_text == preview  # une seule rédaction, zéro divergence


def test_dispatch_rejects_case_id_mismatch():
    """Fix sécurité (a) : un record dispatché sous le mandat d'un AUTRE case est refusé
    — sinon on notifierait au nom d'une autre victime."""
    record, _m, notices = _verified_record_and_mandate()
    other = mandate_mod.create_demo_mandate(case_id="other-case")
    with pytest.raises(ValueError, match="authorization mismatch"):
        asyncio.run(
            dispatch(record, other, notices[record.source_url],
                     confirm=_approve, log=lambda _msg: None, emit=lambda _e: None)
        )


def test_dispatch_rejects_out_of_scope_record():
    """Fix sécurité (a) : G-2 re-vérifié au dernier point de sortie — un record forgé
    hors du périmètre consenti ne part jamais, même VERIFIED et même case_id."""
    m = mandate_mod.create_demo_mandate()
    forged = ForensicRecord(
        case_id=m.case_id,
        source_url="https://evil-mirror.example/leak.jpg",
        deepfake_score=0.99,
        perceptual_hash="phash:forged",
        sha256_hash="deadbeef",
        discovery_ts_utc=utcnow(),
        status=Status.VERIFIED,
    )
    with pytest.raises(ValueError, match="G-2"):
        asyncio.run(
            dispatch(forged, m, confirm=_approve, log=lambda _msg: None,
                     emit=lambda _e: None)
        )


def test_dispatch_requires_explicit_confirm():
    """Fix sécurité (b) : confirm est OBLIGATOIRE — un appel L2 qui l'oublie doit
    échouer en TypeError, jamais auto-envoyer (G-7)."""
    record, m, notices = _verified_record_and_mandate()
    with pytest.raises(TypeError):
        dispatch(record, m, notices[record.source_url])  # pas de confirm -> refus
