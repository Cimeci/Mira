from __future__ import annotations

import asyncio
import json

from mira.events import StageEvent, Emit
from mira.types import Status

_STATUS_TO_EVENT_TYPE = {
    Status.LOCATED: "locate",
    Status.VERIFIED: "analyze_ok",
    Status.REJECTED: "analyze_reject",
    Status.ESCALATED: "analyze_escalate",
    Status.AWAITING_CONFIRM: "awaiting_confirm",
    Status.CONFIRMED: "confirmed",
    Status.DECLINED: "declined",
    Status.NOTIFIED: "notified",
    Status.REVOKED: "revoked",
    Status.FAILED: "failed",
    Status.MANDATED: "mandated",
}

def to_sse(event: StageEvent) -> str:
    """Série un StageEvent au format Server-Sent Events (SSE)."""
    # G-6 Guardrail: ne JAMAIS inclure phash/sha256/octets dans un event escalated
    if event.to_status == Status.ESCALATED:
        assert "perceptual_hash" not in event.payload, "G-6: phash interdit dans un event ESCALATED"
        assert "sha256_hash" not in event.payload, "G-6: sha256 interdit dans un event ESCALATED"
    
    event_type = _STATUS_TO_EVENT_TYPE.get(event.to_status, "message")
    
    # Règles L2: si le stage est "notice", on surcharge le type pour différencier de awaiting_confirm standard
    if event.stage == "notice":
        event_type = "notice_preview"
        
    data = json.dumps(event.to_dict())
    return f"event: {event_type}\ndata: {data}\n\n"

def make_logger(queue: asyncio.Queue) -> Emit:
    """Adaptateur qui transforme un StageEvent en item poussé dans la queue asynchrone."""
    def _emit(event: StageEvent) -> None:
        queue.put_nowait(event)
    return _emit

def to_sse_done() -> str:
    """Event terminal explicite autorisant le front à fermer l'EventSource."""
    return f"event: done\ndata: {{}}\n\n"
