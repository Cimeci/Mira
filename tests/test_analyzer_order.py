"""Verrou d'ordre G-6 : le pré-check mineur tourne AVANT tout octet, prouvé par bombe.

On remplace `mira.analyzer._fetch_bytes` (le SEUL point d'accès aux octets) par une
fonction qui explose : si un chemin escaladé ou rejeté la déclenche, c'est un bug
G-6 disqualifiant — le test le rend impossible à réintroduire silencieusement.
"""

import asyncio
import json

import pytest

from mira import analyzer, escalation, notifier
from mira.types import ForensicRecord, MediaItem, Status, utcnow


def _boom(item):
    raise RuntimeError("G-6 violé : _fetch_bytes appelé avant/malgré le pré-check")


def _minor_item() -> MediaItem:
    return MediaItem(case_id="t-minor", url="https://mock-host.local/minor-case")


def test_minor_item_never_touches_bytes(monkeypatch):
    monkeypatch.setattr(analyzer, "_fetch_bytes", _boom)
    record = asyncio.run(analyzer.analyze(_minor_item(), log=lambda *_: None))
    # Pas d'exception = _fetch_bytes jamais appelé ; l'escalade est structurelle.
    assert record.status is Status.ESCALATED


def test_rejected_item_stores_nothing_and_never_touches_bytes(monkeypatch):
    monkeypatch.setattr(analyzer, "_fetch_bytes", _boom)

    async def low_score(item):
        return 0.10

    monkeypatch.setattr(analyzer, "_cv_score", low_score)
    item = MediaItem(case_id="t-reject", url="https://mock-host.local/fake-a")
    record = asyncio.run(analyzer.analyze(item, log=lambda *_: None))
    assert record.status is Status.REJECTED
    assert record.perceptual_hash == ""
    assert record.sha256_hash == ""


def test_escalation_emits_minimal_event_and_structured_authority_log():
    events, logs = [], []
    record = asyncio.run(
        analyzer.analyze(_minor_item(), log=logs.append, emit=events.append)
    )
    # Record minimal : aucune empreinte, aucune ref disque (G-6).
    assert record.perceptual_hash == ""
    assert record.sha256_hash == ""
    assert record.minimal_ref is None
    # Event ESCALATED minimal : reason seulement, jamais d'URL ni de hash (G-6/G-12).
    escalated = [e for e in events if e.to_status is Status.ESCALATED]
    assert len(escalated) == 1
    assert escalated[0].payload == {"reason": "suspected_minor"}
    # La raison (token détecté) est loggée.
    assert any("token 'minor'" in line for line in logs)

    # Le sink autorité mock logge une ligne JSON structurée SANS contenu ni URL du média.
    sink_logs = []
    escalation.escalate(record, mandate=None, log=sink_logs.append)
    assert len(sink_logs) == 1
    report = json.loads(sink_logs[0].split(" : ", 1)[1])
    assert report["case_id"] == "t-minor"
    assert report["reason"] == "suspected_minor"
    assert report["authority"] == "mock-ofmin-inbox"
    assert "url" not in report and "minor-case" not in sink_logs[0]


def test_notify_refuses_non_verified_record():
    escalated = ForensicRecord(
        case_id="t-minor",
        source_url="https://mock-host.local/minor-case",
        deepfake_score=0.0,
        perceptual_hash="",
        sha256_hash="",
        discovery_ts_utc=utcnow(),
        status=Status.ESCALATED,
    )
    with pytest.raises(ValueError, match="G-6/G-7"):
        asyncio.run(notifier.notify(escalated, mandate=None, confirm=lambda n: True))
