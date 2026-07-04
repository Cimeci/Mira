"""Persistance Supabase des cases (lane L2) — miroir durable, JAMAIS bloquant.

La démo ne dépend pas de la DB : sans credentials (mira.db.is_configured() False)
tout est no-op ; une panne DB fait un log ERROR et le pipeline continue. Les
écritures partent dans une file consommée par une tâche de fond unique
(asyncio.to_thread), donc l'ordre des events est préservé et le flux SSE n'attend
jamais le réseau.

Ce qui est stocké (schéma supabase/migrations/0001_init.sql) — audit trail du
pipeline, aligné G-5 : ids opaques, URLs de démo, hashes, texte de notice.
JAMAIS d'octets média ni de PII.

Câblage (mira/api.py, 2 points) :
    store.case_created(mandate)                    # POST /cases
    store.event_published(case_id, seq, msg)       # _publish, chaque message SSE
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from . import db
from .types import Mandate

log = logging.getLogger("mira.store")

# Verdicts du gate G-7 dérivés de la timeline (payload.url posé par le notifier).
_VERDICT_STATUS = {"CONFIRMED": True, "DECLINED": False}

_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
_worker: asyncio.Task | None = None


def case_created(mandate: Mandate) -> None:
    """Enregistre le chapeau du case à sa création (POST /cases)."""
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
    """Miroir d'un message SSE : timeline + état dérivé (case, notice)."""
    _enqueue({"op": "event", "case_id": case_id, "seq": seq, "msg": msg})


def _enqueue(item: dict[str, Any]) -> None:
    """No-op sans credentials. Sinon : file + démarrage lazy du worker.

    Toujours appelé depuis la boucle (endpoints / pipeline de fond de mira.api),
    donc get_running_loop() ne peut pas échouer en usage réel.
    """
    if not db.is_configured():
        return
    global _worker
    _queue.put_nowait(item)
    if _worker is None or _worker.done():
        _worker = asyncio.get_running_loop().create_task(_drain())


async def _drain() -> None:
    """Vide la file en série — un seul writer, ordre des écritures garanti."""
    while not _queue.empty():
        item = _queue.get_nowait()
        try:
            await asyncio.to_thread(_write, item)
        except Exception:  # noqa: BLE001 — la persistance ne doit jamais tuer le pipeline
            log.exception(
                "écriture Supabase échouée (op=%s case=%s) — pipeline non affecté",
                item.get("op"),
                item.get("case_id"),
            )


def _write(item: dict[str, Any]) -> None:
    """Écriture synchrone (exécutée hors boucle, via to_thread)."""
    client = db.get_client()
    case_id = item["case_id"]

    if item["op"] == "case":
        client.table("cases").upsert(item["row"]).execute()
        return

    msg = item["msg"]
    # Timeline append-only ; rejouable après restart -> les doublons sont ignorés.
    client.table("case_events").upsert(
        {"case_id": case_id, "seq": item["seq"], "kind": msg["kind"], "payload": msg},
        on_conflict="case_id,seq",
        ignore_duplicates=True,
    ).execute()

    # État dérivé — le chapeau du case et la notice suivent la timeline.
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
    """Reflète le gate G-7 sur la notice : approved (CONFIRMED/DECLINED), dispatched
    (NOTIFIED). Le notifier pose toujours payload.url sur ces events."""
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
