"""Couche d'orchestration. Applique le consent gate UNE fois, puis fait couler le pipeline.

Lane L1. C'est ici — et pas dans chaque stage — qu'on garantit G-1 : aucun stage ne
tourne sans mandat actif. La state machine vit ici.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from . import analyzer, locator, notifier
from .events import Emit, make_event, print_emitter
from .types import Mandate, MediaItem, NotificationRecord, Status


class ConsentError(RuntimeError):
    """Levée quand on tente de traiter un case sans mandat actif (G-1)."""


def _require_active(mandate: Mandate) -> None:
    if not mandate.active:
        raise ConsentError(
            f"Aucun mandat actif pour {mandate.case_id} ; traitement refusé (G-1)."
        )


async def run(
    mandate: Mandate,
    *,
    confirm: Callable[[str], bool] = lambda notice: True,
    log=print,
    emit: Emit = print_emitter,
) -> list:
    """Pipeline Mandate -> Locate -> Analyze -> Notify. Renvoie tous les records produits.

    `emit` reçoit un StageEvent à chaque transition d'état (contrat : mira/events.py).
    `log` reste le canal texte legacy des messages hors transition (ex. rejet G-2).
    """
    _require_active(mandate)  # le seul endroit où le consent gate est vérifié
    # from_status=None : MANDATED est la naissance du case, il n'y a pas d'état antérieur.
    emit(make_event(
        mandate.case_id,
        "mandate",
        Status.MANDATED,
        payload={"requester_role": mandate.requester_role, "scope_urls": mandate.scope_urls},
    ))

    located: asyncio.Queue[MediaItem] = asyncio.Queue()
    results: list = []

    # Stage 1 — Locate (in-scope only)
    await locator.locate(mandate, located, log=log, emit=emit)

    # Stage 2 — Analyze (+ pré-check mineur / seuil)
    to_notify = []
    while not located.empty():
        item = await located.get()
        record = await analyzer.analyze(item, log=log, emit=emit)
        results.append(record)
        if record.status is Status.VERIFIED:
            to_notify.append(record)
        # ESCALATED / REJECTED s'arrêtent ici, par design.

    # Stage 3 — Notify (gate de confirmation victime)
    for record in to_notify:
        note: NotificationRecord = await notifier.notify(
            record, mandate, confirm=confirm, log=log, emit=emit
        )
        results.append(note)

    return results
