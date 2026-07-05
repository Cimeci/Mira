"""Takedown dispatch (Stage 3): skill registry + real email to the demo inbox only
(G-12), mock fallback when unconfigured. The live send is skipped unless RESEND_API_KEY
+ DEMO_TARGET_INBOX are in dev.env (it sends a real email to the demo inbox).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from mira import takedown
from mira.mandate import create_demo_mandate
from mira.types import ForensicRecord, Status, utcnow


def _verified(
    case_id: str = "td-1", url: str = "https://mock-host.local/target/x.jpg"
) -> ForensicRecord:
    return ForensicRecord(
        case_id=case_id,
        source_url=url,
        deepfake_score=0.94,
        perceptual_hash="phash:x",
        sha256_hash="sha",
        discovery_ts_utc=utcnow(),
        status=Status.VERIFIED,
    )


def test_unknown_host_routes_to_email(monkeypatch):
    monkeypatch.delenv("MIRA_TAKEDOWN_SKILL", raising=False)
    skill = takedown.resolve_skill(_verified(), create_demo_mandate("td-1"))
    assert skill.name == "host" and skill.channel == "email"


def test_platform_host_routes_to_cu(monkeypatch):
    monkeypatch.delenv("MIRA_TAKEDOWN_SKILL", raising=False)
    rec = _verified("td-fb", url="https://www.facebook.com/some/posts/123")
    skill = takedown.resolve_skill(rec, create_demo_mandate("td-fb"))
    assert skill.name == "meta" and skill.channel == "platform_form"


def test_override_wins(monkeypatch):
    monkeypatch.setenv("MIRA_TAKEDOWN_SKILL", "pharos")
    assert takedown.resolve_skill(_verified(), create_demo_mandate("td-1")).name == "pharos"


def test_every_skill_has_a_task():
    for name, skill in takedown.skills().items():
        assert skill.task.strip(), f"skill {name} has no task"


def test_unconfigured_returns_false_with_skill(monkeypatch):
    monkeypatch.delenv("MIRA_TAKEDOWN_SKILL", raising=False)
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.delenv("DEMO_TARGET_INBOX", raising=False)
    sent, skill = asyncio.run(takedown.submit("notice", _verified(), create_demo_mandate("td-1")))
    assert sent is False
    assert skill.channel == "email"  # mock-host is unknown → email route


def _local_env() -> dict[str, str]:
    values: dict[str, str] = {}
    envfile = Path(__file__).resolve().parent.parent / ".env.local"
    if envfile.exists():
        for line in envfile.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                if val.strip():
                    values[key.strip()] = val.strip()
    return values


_ENV = _local_env()
_HAS_RESEND = "RESEND_API_KEY" in _ENV and "DEMO_TARGET_INBOX" in _ENV


@pytest.mark.skipif(
    not _HAS_RESEND, reason="needs RESEND_API_KEY + DEMO_TARGET_INBOX (sends a real email)"
)
def test_live_dispatch_to_demo_inbox(monkeypatch):
    monkeypatch.setenv("MIRA_TAKEDOWN_SKILL", "host")  # host = the email channel
    for key in ("RESEND_API_KEY", "DEMO_TARGET_INBOX", "NOTICE_SENDER_EMAIL"):
        if _ENV.get(key):
            monkeypatch.setenv(key, _ENV[key])
    mandate = create_demo_mandate("td-1")
    sent, skill = asyncio.run(
        takedown.submit("Test DSA notice from Mira (takedown smoke).", _verified(), mandate)
    )
    assert sent is True and skill.channel == "email"
