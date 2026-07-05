"""Stage 3 dispatch — takedown SKILLS, one per target channel.

A skill is a takedown route: a channel, a target, and a Gemini Computer Use task
(Agents/prompts/takedown_{name}.md). submit() dispatches by the resolved skill's channel:

  - email           → send the DSA notice to the (demo) inbox via Resend.
  - platform_form   → Gemini Computer Use fills AND submits the platform's form (Meta/X/…).
  - official_portal → Gemini Computer Use fills the government portal (PHAROS) but does
                      NOT submit — a human sends any real report.

Which skill runs comes from the victim's chosen action paths (wireframe) — for now
MIRA_TAKEDOWN_SKILL selects it, defaulting to the EU/FR legal route.

Computer Use drives the skill's REAL URL, so the jury sees the real site. Use
MIRA_CU_HEADFUL=1 to show the browser window when you want to watch the run.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from . import prompts
from .types import ForensicRecord, Mandate

_RESEND_ENDPOINT = "https://api.resend.com/emails"


@dataclass(frozen=True)
class Skill:
    name: str
    label: str    # human label shown in the notice/event
    channel: str  # official_portal | platform_form | email
    target: str   # real URL to drive (portal/form), or "abuse@" for the email channel

    @property
    def task(self) -> str:
        """The Gemini Computer Use task for this skill (Agents/prompts/takedown_{name}.md)."""
        return prompts.load(f"takedown_{self.name}")


_SKILLS: dict[str, Skill] = {
    "legal_fr": Skill(
        "legal_fr", "Signalement légal France/UE", "official_portal",
        "https://www.internet-signalement.gouv.fr",
    ),
    "pharos": Skill(
        "pharos", "PHAROS (signalement France)", "official_portal",
        "https://www.internet-signalement.gouv.fr",
    ),
    "meta": Skill(
        "meta", "Meta (Facebook/Instagram)", "platform_form",
        "https://www.facebook.com/help/1753719584844061",
    ),
    "google": Skill(
        "google", "Google (removal)", "platform_form",
        "https://support.google.com/websearch/troubleshooter/3111061",
    ),
    "x": Skill("x", "X (Twitter)", "platform_form", "https://help.x.com/forms"),
    "host": Skill("host", "Hébergeur / abuse", "email", "abuse@"),
}

DEFAULT_SKILL = "legal_fr"

# Detected-host substrings → the platform's form skill (Computer Use).
_HOST_SKILL: tuple[tuple[tuple[str, ...], str], ...] = (
    (("facebook.com", "instagram.com", "fb.com", "fb.watch"), "meta"),
    (("x.com", "twitter.com", "t.co"), "x"),
)


def skills() -> dict[str, Skill]:
    return dict(_SKILLS)


def resolve_skill(record: ForensicRecord, mandate: Mandate) -> Skill:
    """Route the takedown from what we have:
      1. explicit override (MIRA_TAKEDOWN_SKILL), else
      2. the detected host — a known platform → its form (Computer Use), else
      3. an unknown host → email its abuse contact.
    The legal-complaint route (PHAROS) is the victim's choice — select it via the
    override for now, later via the action paths captured at consent.
    """
    override = os.getenv("MIRA_TAKEDOWN_SKILL")
    if override:
        return _SKILLS.get(override, _SKILLS[DEFAULT_SKILL])
    host = (urlparse(record.source_url).hostname or "").lower()
    for needles, name in _HOST_SKILL:
        if any(n in host for n in needles):
            return _SKILLS[name]
    return _SKILLS["host"]  # unknown host → email the abuse contact


def is_configured() -> bool:
    """True when the email channel can dispatch (Resend key + a demo inbox)."""
    return bool(os.getenv("RESEND_API_KEY") and os.getenv("DEMO_TARGET_INBOX"))


async def submit(notice: str, record: ForensicRecord, mandate: Mandate) -> tuple[bool, Skill]:
    """Dispatch the confirmed takedown by the resolved skill's channel. Returns
    (done, skill). Never raises — any failure returns (False, skill) so the caller can
    fall back to a mock NOTIFIED and the demo stays green."""
    skill = resolve_skill(record, mandate)
    try:
        if skill.channel == "email":
            done = await _dispatch_email(notice, record, skill)
        else:
            done = await _dispatch_cu(record, skill)
    except Exception:  # noqa: BLE001 - a dispatch failure must not crash the pipeline
        done = False
    return done, skill


async def _dispatch_email(notice: str, record: ForensicRecord, skill: Skill) -> bool:
    """Host abuse@ route: send the DSA notice to the demo inbox via Resend."""
    if not is_configured():
        return False
    subject = f"[{skill.label}] Retrait de contenu illicite — {record.source_url}"
    await asyncio.to_thread(_send_email, subject, notice)
    return True


async def _dispatch_cu(record: ForensicRecord, skill: Skill) -> bool:
    """Gemini Computer Use drives the skill's REAL form. Government portals
    (official_portal) are fill-only — never auto-submit a report; platform forms submit."""
    from .cu.agent import stream_takedown_cu  # lazy: pulls playwright/genai only here

    do_submit = skill.channel != "official_portal"
    completed = False
    async for event in stream_takedown_cu(
        skill.target, record.source_url, f"takedown_{skill.name}", submit=do_submit
    ):
        if event["type"] == "error":
            return False
        if event["type"] == "done":
            completed = True
    return completed


def _send_email(subject: str, body: str) -> None:
    key = os.getenv("RESEND_API_KEY")
    inbox = os.getenv("DEMO_TARGET_INBOX")
    # Resend requires a verified sender domain; onboarding@resend.dev works in test mode.
    sender = os.getenv("NOTICE_SENDER_EMAIL") or "onboarding@resend.dev"
    resp = httpx.post(
        _RESEND_ENDPOINT,
        headers={"Authorization": f"Bearer {key}"},
        json={"from": sender, "to": [inbox], "subject": subject, "text": body},
        timeout=30,
    )
    resp.raise_for_status()
