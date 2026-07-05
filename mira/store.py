"""Supabase persistence for cases (lane L2) — a durable mirror, NEVER blocking.

The demo does not depend on the DB: without credentials (mira.db.is_configured() False)
everything is a no-op; a DB failure logs an ERROR and the pipeline continues. Writes go
onto a queue drained by a single background task (asyncio.to_thread), so event order is
preserved and the SSE stream never waits on the network.

What is stored (schema supabase/migrations/0001_init.sql) — the pipeline audit trail:
opaque ids, demo URLs, hashes, notice text. NEVER media bytes or PII.

Wiring (mira/api.py, 2 points):
    store.case_created(mandate)                    # POST /cases
    store.event_published(case_id, seq, msg)       # _publish, every SSE message
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from . import db
from .types import Mandate

log = logging.getLogger("mira.store")

# Gate verdicts derived from the timeline (payload.url set by the notifier).
_VERDICT_STATUS = {"CONFIRMED": True, "DECLINED": False}

_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
_worker: asyncio.Task | None = None


def case_created(mandate: Mandate) -> None:
    """Record the case header at creation (POST /cases)."""
    _enqueue(
        {
            "op": "case",
            "case_id": mandate.case_id,
            "row": {
                "case_id": mandate.case_id,
                "requester_role": mandate.requester_role,
                "scope_urls": mandate.scope_urls,
                "last_status": "MANDATED",
            },
        }
    )


def event_published(case_id: str, seq: int, msg: dict) -> None:
    """Mirror an SSE message: timeline + derived state (case, notice)."""
    _enqueue({"op": "event", "case_id": case_id, "seq": seq, "msg": msg})


def save_reference_embedding(case_id: str, embedding: list[float]) -> None:
    """Persist the victim's 512-d ArcFace reference (enrollment). Fire-and-forget like
    the rest of this mirror; no-op when Supabase isn't configured."""
    _enqueue(
        {
            "op": "embedding",
            "case_id": case_id,
            "row": {"case_id": case_id, "embedding": embedding},
        }
    )


async def get_reference_embedding(case_id: str) -> list[float] | None:
    """Read the victim's reference embedding for the face match. Returns None when
    Supabase isn't configured (demo/tests) OR on any DB failure — the analyzer then
    passes through rather than rejecting, so persistence never breaks the pipeline."""
    if not db.is_configured():
        return None

    def _read() -> list[float] | None:
        client = db.get_client()
        res = (
            client.table("victim_embeddings")
            .select("embedding")
            .eq("case_id", case_id)
            .limit(1)
            .execute()
        )
        return res.data[0]["embedding"] if res.data else None

    try:
        return await asyncio.to_thread(_read)
    except Exception:  # noqa: BLE001 - a DB failure must never break the pipeline
        log.exception("reading victim_embeddings failed for %s — treating as no reference", case_id)
        return None


def _enqueue(item: dict[str, Any]) -> None:
    """No-op without credentials. Otherwise: queue + lazy start of the worker.

    Always called from the loop (endpoints / background pipeline of mira.api), so
    get_running_loop() cannot fail in real use."""
    if not db.is_configured():
        return
    global _worker
    _queue.put_nowait(item)
    if _worker is None or _worker.done():
        _worker = asyncio.get_running_loop().create_task(_drain())


async def _drain() -> None:
    """Drain the queue serially — a single writer, write order guaranteed."""
    while not _queue.empty():
        item = _queue.get_nowait()
        try:
            await asyncio.to_thread(_write, item)
        except Exception:  # noqa: BLE001 — persistence must never kill the pipeline
            log.exception(
                "Supabase write failed (op=%s case=%s) — pipeline unaffected",
                item.get("op"),
                item.get("case_id"),
            )


def _write(item: dict[str, Any]) -> None:
    """Synchronous write (runs off the loop, via to_thread)."""
    client = db.get_client()
    case_id = item["case_id"]

    if item["op"] == "case":
        client.table("cases").upsert(item["row"]).execute()
        return

    if item["op"] == "embedding":
        client.table("victim_embeddings").upsert(item["row"], on_conflict="case_id").execute()
        return

    msg = item["msg"]
    # Append-only timeline; replayable after a restart -> duplicates are ignored.
    client.table("case_events").upsert(
        {"case_id": case_id, "seq": item["seq"], "kind": msg["kind"], "payload": msg},
        on_conflict="case_id,seq",
        ignore_duplicates=True,
    ).execute()

    # Derived state — the case header and the notice follow the timeline.
    if msg["kind"] == "stage":
        event = msg["event"]
        patch: dict[str, Any] = {"last_status": event["to_status"]}
        client.table("cases").update(patch).eq("case_id", case_id).execute()
        _apply_verdict(client, case_id, event)
    elif msg["kind"] == "notice":
        client.table("notices").upsert(
            {"case_id": case_id, "source_url": msg["url"], "notice_text": msg["text"]},
            on_conflict="case_id,source_url",
        ).execute()
    elif msg["kind"] == "done":
        client.table("cases").update(
            {"statuses": msg["statuses"], "finished": True}
        ).eq("case_id", case_id).execute()


def _apply_verdict(client: Any, case_id: str, event: dict) -> None:
    """Reflect the confirmation gate on the notice: approved (CONFIRMED/DECLINED),
    dispatched (NOTIFIED). The notifier always sets payload.url on these events."""
    to_status = event["to_status"]
    url = event.get("payload", {}).get("url")
    if url is None:
        return
    if to_status in _VERDICT_STATUS:
        client.table("notices").update(
            {"approved": _VERDICT_STATUS[to_status]}
        ).eq("case_id", case_id).eq("source_url", url).execute()
    elif to_status == "NOTIFIED":
        client.table("notices").update(
            {"dispatched": True}
        ).eq("case_id", case_id).eq("source_url", url).execute()
