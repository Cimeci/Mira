"""Live nudity/intent check against Sightengine + Grok on fixture images.

Like tests/test_face_recognition.py but for the content-safety stage: real API calls,
real images, real assertions — skipped unless the keys are in dev.env AND the fixtures
exist. Keys are read from dev.env and applied per-test (monkeypatch), so a normal
`pytest` run is unaffected and never hits the network.

Fixtures:
  tests/fixtures/faces/reference.jpg   — an existing SFW portrait (safe case)
  tests/fixtures/nudity/explicit.jpg   — provide your own (gitignored) for the positive case
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from mira import prompts, safety, vision

_ROOT = Path(__file__).resolve().parent.parent
_SAFE = _ROOT / "tests" / "fixtures" / "faces" / "reference.jpg"


def _fixture(*candidates: Path) -> Path:
    """First existing path, else the first candidate (for the skip check)."""
    return next((p for p in candidates if p.exists()), candidates[0])


_NUDITY_DIR = _ROOT / "tests" / "fixtures" / "nudity"
_EXPLICIT = _fixture(_NUDITY_DIR / "explicit.jpg", _NUDITY_DIR / "explicit.png")


def _dev_env() -> dict[str, str]:
    """Parse dev.env (gitignored) without mutating os.environ."""
    values: dict[str, str] = {}
    envfile = _ROOT / "dev.env"
    if envfile.exists():
        for line in envfile.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                if val.strip():
                    values[key.strip()] = val.strip()
    return values


_ENV = _dev_env()
_HAS_SIGHTENGINE = "SIGHTENGINE_API_USER" in _ENV and "SIGHTENGINE_API_SECRET" in _ENV
_HAS_XAI = "XAI_API_KEY" in _ENV


def _apply(monkeypatch, *keys: str) -> None:
    for key in keys:
        monkeypatch.setenv(key, _ENV[key])


@pytest.mark.skipif(
    not (_HAS_SIGHTENGINE and _SAFE.exists()), reason="needs Sightengine keys + SFW fixture"
)
def test_safe_image_not_flagged(monkeypatch):
    _apply(monkeypatch, "SIGHTENGINE_API_USER", "SIGHTENGINE_API_SECRET")
    nudity = safety.nudity_scores(_SAFE.read_bytes())
    assert "none" in nudity and "sexual_activity" in nudity  # nudity-2.1 response shape
    score = safety.explicitness(nudity)
    assert not safety.is_explicit(nudity), f"SFW portrait wrongly flagged ({score:.2f})"


@pytest.mark.skipif(
    not (_HAS_SIGHTENGINE and _EXPLICIT.exists() and _SAFE.exists()),
    reason="needs Sightengine keys + tests/fixtures/nudity/explicit.jpg",
)
def test_explicit_flagged_over_safe(monkeypatch):
    _apply(monkeypatch, "SIGHTENGINE_API_USER", "SIGHTENGINE_API_SECRET")
    explicit = safety.nudity_scores(_EXPLICIT.read_bytes())
    safe = safety.nudity_scores(_SAFE.read_bytes())
    ex_score = safety.explicitness(explicit)
    assert safety.is_explicit(explicit), f"explicit not flagged ({ex_score:.2f})"
    assert ex_score > safety.explicitness(safe)


@pytest.mark.skipif(
    not (_HAS_XAI and _SAFE.exists()), reason="needs XAI_API_KEY (+ xAI credits) + fixture"
)
def test_grok_intent_returns_valid_json(monkeypatch):
    _apply(monkeypatch, "XAI_API_KEY")
    try:
        raw = vision.ask_grok(_SAFE.read_bytes(), prompts.load("nudity_intent"))
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 403:  # xAI team has no credits/license yet
            pytest.skip(f"xAI not enabled: {exc.response.json().get('error', '')}")
        raise
    verdict = json.loads(raw)
    assert "abusive_intent" in verdict
    assert verdict["abusive_intent"] is False  # a plain portrait is not abusive intent
