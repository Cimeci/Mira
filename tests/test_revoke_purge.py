"""Révocation & purge (G-10, droit à l'effacement) — chemin de démo uniquement.

On teste ce qui compte pour la démo :
  1. un mandat révoqué -> event REVOKED + preuve/consentement effacés du disque ;
  2. une révocation EN COURS de pipeline (entre locate et le gate) -> aucun envoi ;
  3. un refus victime (DECLINE) -> la preuve retenue est purgée.
Le gate G-7 est async (contrat L2) : les confirms de test sont des coroutines.
"""

import asyncio

from mira import mandate as mandate_mod
from mira import orchestrator
from mira.locator import locate as real_locate
from mira.orchestrator import dispatch, purge, run_until_gate
from mira.types import ForensicRecord, Status, utcnow


async def _decline(notice: str) -> bool:
    return False


def _verified_record(case_id: str, evidence_path) -> ForensicRecord:
    return ForensicRecord(
        case_id=case_id,
        source_url="https://mock-host.local/target",
        deepfake_score=0.99,
        perceptual_hash="phash:x",
        sha256_hash="abc",
        discovery_ts_utc=utcnow(),
        status=Status.VERIFIED,
        minimal_ref=evidence_path,
    )


def test_revoke_sets_active_false_and_stamps_timestamp():
    """revoke() coupe l'autonomie ET horodate le retrait (source de vérité L1)."""
    m = mandate_mod.create_demo_mandate(case_id="revoke-flags")
    try:
        assert m.active is True and m.revoked_ts_utc is None
        mandate_mod.revoke(m)
        assert m.active is False
        assert m.revoked_ts_utc is not None
        # Idempotent : re-révoquer ne réécrit pas l'horodatage du premier retrait.
        first = m.revoked_ts_utc
        mandate_mod.revoke(m)
        assert m.revoked_ts_utc == first
    finally:
        if m.consent_artifact:
            m.consent_artifact.unlink(missing_ok=True)


def test_purge_erases_evidence_and_consent_and_emits_revoked(tmp_path):
    """Mandat révoqué -> statut REVOKED + toute référence de preuve effacée du disque."""
    m = mandate_mod.create_demo_mandate(case_id="revoke-purge")
    consent_path = m.consent_artifact
    assert consent_path is not None and consent_path.exists()

    # Simule une preuve chiffrée retenue (minimal_ref), telle que l'écrit l'analyzer.
    evidence = tmp_path / "revoke-purge_abc.enc"
    evidence.write_bytes(b"encrypted-evidence")
    record = _verified_record(m.case_id, evidence)

    mandate_mod.revoke(m)
    events = []
    purge(m, [record], log=lambda _m: None, emit=events.append)

    # Effacement physique : plus aucun octet retenu (G-5/G-10).
    assert not evidence.exists(), "la preuve chiffrée doit être supprimée du disque"
    assert not consent_path.exists(), "l'artefact de consentement doit être supprimé"
    assert record.minimal_ref is None and m.consent_artifact is None
    # Un unique event terminal REVOKED, source de vérité de la fin du case.
    assert [e.to_status for e in events] == [Status.REVOKED]
    assert events[0].payload == {"reason": "mandate_revoked"}


def test_purge_is_idempotent_on_missing_files(tmp_path):
    """Re-purger un case déjà purgé ne casse pas (fichiers absents = no-op, pas d'échec)."""
    m = mandate_mod.create_demo_mandate(case_id="revoke-twice")
    if m.consent_artifact:
        m.consent_artifact.unlink(missing_ok=True)  # artefact déjà disparu
    record = _verified_record(m.case_id, tmp_path / "does-not-exist.enc")
    events = []
    purge(m, [record], log=lambda _m: None, emit=events.append)  # ne doit pas lever
    assert [e.to_status for e in events] == [Status.REVOKED]


def test_revocation_between_locate_and_notify_sends_nothing(monkeypatch):
    """Révocation déclenchée ENTRE locate et notify -> checkpoint coopératif, aucun envoi.

    Distinct du gate d'entrée G-1 : le mandat est actif à l'ouverture, révoqué en cours.
    """
    m = mandate_mod.create_demo_mandate(case_id="revoke-midflight")

    async def locate_then_revoke(mandate, out, *, log=print, emit):
        await real_locate(mandate, out, log=log, emit=emit)
        mandate_mod.revoke(mandate)  # révoqué juste après la localisation, avant l'analyse

    monkeypatch.setattr(orchestrator.locator, "locate", locate_then_revoke)

    events = []
    records, notices = asyncio.run(
        run_until_gate(m, log=lambda _m: None, emit=events.append)
    )
    statuses = [e.to_status for e in events]
    assert Status.REVOKED in statuses, "un arrêt mid-flight doit émettre REVOKED"
    assert Status.AWAITING_CONFIRM not in statuses, "le gate G-7 ne doit jamais s'ouvrir"
    assert Status.CONFIRMED not in statuses and Status.NOTIFIED not in statuses
    assert notices == {}, "aucune notice ne survit à une révocation en cours de route"
    assert m.consent_artifact is None, "le consentement est purgé par le checkpoint"


def test_victim_decline_purges_retained_evidence(tmp_path):
    """Sur DECLINE victime : la minimal_ref retenue est purgée (rien conservé après refus)."""
    m = mandate_mod.create_demo_mandate(case_id="decline-purge")
    try:
        evidence = tmp_path / "decline_abc.enc"
        evidence.write_bytes(b"encrypted-evidence")
        record = _verified_record(m.case_id, evidence)

        note = asyncio.run(
            dispatch(record, m, notice="notice-texte", confirm=_decline,
                     log=lambda _m: None, emit=lambda _e: None)
        )
        assert note.status is Status.DECLINED
        assert not evidence.exists(), "un refus victime doit purger la preuve retenue"
        assert record.minimal_ref is None
    finally:
        if m.consent_artifact:
            m.consent_artifact.unlink(missing_ok=True)
