"""Phase face-match (services/face-verifier, mock ici) : ordre G-6 + gate de correspondance.

Deux verrous prouvés par bombe, même technique que tests/test_analyzer_order.py :
le face-match ne tourne JAMAIS sur un mineur suspecté (analyser le visage d'un
mineur est déjà le mal qu'on évite), et un média qui ne correspond pas au visage
du mandat est REJECTED sans jamais toucher un octet.
"""

import asyncio

from mira import analyzer
from mira.types import MediaItem, Status


def _boom_bytes(item):
    raise RuntimeError("G-6 violé : _fetch_bytes appelé malgré un face-match négatif")


async def _boom_face_match(item):
    raise AssertionError("G-6 violé : face-match exécuté sur un mineur suspecté")


def test_face_match_never_runs_on_suspected_minor(monkeypatch):
    monkeypatch.setattr(analyzer, "_face_match", _boom_face_match)
    item = MediaItem(case_id="t-minor", url="https://mock-host.local/minor-case")
    # Pas d'exception = _face_match jamais appelé ; l'escalade précède la phase 2.
    record = asyncio.run(
        analyzer.analyze(item, log=lambda *_: None, emit=lambda e: None)
    )
    assert record.status is Status.ESCALATED


def test_face_mismatch_rejects_without_touching_bytes(monkeypatch):
    monkeypatch.setattr(analyzer, "_fetch_bytes", _boom_bytes)

    async def no_match(item):
        return False, 0.12

    monkeypatch.setattr(analyzer, "_face_match", no_match)
    events = []
    item = MediaItem(case_id="t-mismatch", url="https://mock-host.local/fake-b")
    record = asyncio.run(
        analyzer.analyze(item, log=lambda *_: None, emit=events.append)
    )
    assert record.status is Status.REJECTED
    assert record.perceptual_hash == ""
    assert record.sha256_hash == ""
    rejected = [e for e in events if e.to_status is Status.REJECTED]
    assert len(rejected) == 1
    assert rejected[0].payload["reason"] == "face_mismatch"


def test_face_match_none_score_does_not_crash_logging(monkeypatch):
    # Le service renvoie similarityScore=None quand aucun visage n'est détecté ;
    # un hook réel peut donc légitimement renvoyer (True/False, None).
    async def match_without_score(item):
        return True, None

    monkeypatch.setattr(analyzer, "_face_match", match_without_score)
    logs = []
    item = MediaItem(case_id="t-noscore", url="https://mock-host.local/fake-c")
    record = asyncio.run(
        analyzer.analyze(item, log=logs.append, emit=lambda e: None)
    )
    assert record.status is Status.VERIFIED
    assert any("face-match" in line and "n/a" in line for line in logs)


def test_face_match_passes_through_to_verified():
    item = MediaItem(case_id="t-match", url="https://mock-host.local/fake-a")
    record = asyncio.run(
        analyzer.analyze(item, log=lambda *_: None, emit=lambda e: None)
    )
    assert record.status is Status.VERIFIED
