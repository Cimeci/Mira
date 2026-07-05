"""Nudity/intent phase in the analyzer: nudity GATES (must be explicit), the score is
STORED on the record either way, and the Grok intent verdict is attached. Deterministic:
the phase is monkeypatched, so no Sightengine/Grok keys or network are needed here.
"""

from __future__ import annotations

import asyncio

from mira import analyzer
from mira.types import MediaItem, Status


def _run(case_id: str):
    item = MediaItem(case_id=case_id, url="https://mock-host.local/target/x.jpg")
    return asyncio.run(analyzer.analyze(item, log=lambda *_: None, emit=lambda _e: None))


def test_not_explicit_rejects_and_stores_score(monkeypatch):
    async def _phase(item):
        return False, 0.12, None  # not explicit → gate rejects

    monkeypatch.setattr(analyzer, "_phase_nudity_intent", _phase)
    record = _run("nud-reject")
    assert record.status is Status.REJECTED
    assert record.nudity_score == 0.12  # stored even on rejection
    assert record.perceptual_hash == ""  # never touched bytes


def test_explicit_verified_stores_score_and_intent(monkeypatch):
    async def _phase(item):
        return True, 0.93, {"abusive_intent": True, "confidence": 0.8, "reason": "x"}

    monkeypatch.setattr(analyzer, "_phase_nudity_intent", _phase)
    record = _run("nud-verify")
    assert record.status is Status.VERIFIED
    assert record.nudity_score == 0.93
    assert record.intent["abusive_intent"] is True


def test_unconfigured_passes_through(monkeypatch):
    # No Sightengine keys → phase is a no-op → case proceeds on the other signals.
    monkeypatch.delenv("SIGHTENGINE_API_USER", raising=False)
    monkeypatch.delenv("SIGHTENGINE_API_SECRET", raising=False)
    proceed, score, intent = asyncio.run(
        analyzer._phase_nudity_intent(MediaItem(case_id="x", url="https://mock-host.local/y.jpg"))
    )
    assert proceed is True and score is None and intent is None
