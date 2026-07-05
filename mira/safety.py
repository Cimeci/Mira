"""Content-safety classifiers (not identity, not an LLM).

nudity_scores: Sightengine nudity-2.1 — a purpose-built NSFW classifier returning
structured 0-1 scores. The nudity signal for the analyzer's nudity/intent phase;
deterministic and fast. The *intent* side is an LLM call (mira/vision.ask_grok),
prompted from Agents/prompts/nudity_intent.md.
"""

from __future__ import annotations

import os

import httpx

_ENDPOINT = "https://api.sightengine.com/1.0/check.json"

# Top intensity classes that mean "sexually explicit", not merely suggestive.
_EXPLICIT_CLASSES = ("sexual_activity", "sexual_display", "erotica")


def nudity_scores(image: bytes) -> dict:
    """Sightengine nudity-2.1 → the raw 'nudity' object (0-1 per class:
    sexual_activity, sexual_display, erotica, very_suggestive, ..., none)."""
    user = os.getenv("SIGHTENGINE_API_USER")
    secret = os.getenv("SIGHTENGINE_API_SECRET")
    if not (user and secret):
        raise RuntimeError("SIGHTENGINE_API_USER/SECRET unset — set them in dev.env")
    resp = httpx.post(
        _ENDPOINT,
        data={"models": "nudity-2.1", "api_user": user, "api_secret": secret},
        files={"media": image},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["nudity"]


def explicitness(nudity: dict) -> float:
    """Top-line explicit score = the strongest of the explicit intensity classes."""
    return max((nudity.get(c, 0.0) for c in _EXPLICIT_CLASSES), default=0.0)


def is_explicit(nudity: dict, threshold: float = 0.5) -> bool:
    """True if the image is sexually explicit (not merely suggestive)."""
    return explicitness(nudity) >= threshold
