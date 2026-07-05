"""Real ArcFace wired into the analyzer's face-match phase.

Skipped unless insightface + the fixture photos exist (see tests/fixtures/faces/).
Proves the victim is VERIFIED even when she's not the largest face in the candidate
(group shot), and a stranger is REJECTED — through the real analyze() pipeline.
"""

from __future__ import annotations

import asyncio
from importlib.util import find_spec
from pathlib import Path

import pytest

from mira import analyzer
from mira.types import MediaItem, Status

_FIX = Path(__file__).parent / "fixtures" / "faces"
_PHOTOS = ("reference.jpg", "same_person.jpg", "other_person.jpg")
_ready = find_spec("insightface") is not None and all((_FIX / p).exists() for p in _PHOTOS)


def _run(item: MediaItem):
    return asyncio.run(analyzer.analyze(item, log=lambda *_: None, emit=lambda _e: None))


def _enroll_and_serve(monkeypatch, candidate: str) -> None:
    from mira import face

    reference = face.embed((_FIX / "reference.jpg").read_bytes())  # victim's solo signature

    async def _ref(case_id: str):
        return reference

    async def _fetch(url: str):
        return (_FIX / candidate).read_bytes()

    monkeypatch.setattr(analyzer.store, "get_reference_embedding", _ref)
    monkeypatch.setattr(analyzer, "_fetch_candidate", _fetch)


@pytest.mark.skipif(not _ready, reason="needs insightface + fixtures/faces/*.jpg")
def test_analyzer_verifies_victim_in_group_shot(monkeypatch):
    _enroll_and_serve(monkeypatch, "same_person.jpg")  # victim present, not the largest face
    record = _run(MediaItem(case_id="c1", url="https://mock-host.local/target/a.jpg"))
    assert record.status is Status.VERIFIED


@pytest.mark.skipif(not _ready, reason="needs insightface + fixtures/faces/*.jpg")
def test_analyzer_rejects_stranger(monkeypatch):
    _enroll_and_serve(monkeypatch, "other_person.jpg")  # different person
    record = _run(MediaItem(case_id="c2", url="https://mock-host.local/target/b.jpg"))
    assert record.status is Status.REJECTED
    assert record.perceptual_hash == "" and record.sha256_hash == ""  # never touched bytes
