"""Couche d'orchestration. Applique le consent gate UNE fois, puis fait couler le pipeline.

Lane L1. C'est ici — et pas dans chaque stage — qu'on garantit G-1 : aucun stage ne
tourne sans mandat actif. La state machine vit ici.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from . import analyzer, locator, notifier
from .events import Emit, make_event, print_emitter
from .types import ForensicRecord, Mandate, MediaItem, NotificationRecord, Status


class ConsentError(RuntimeError):
    """Levée quand on tente de traiter un case sans mandat actif (G-1)."""


def _require_active(mandate: Mandate) -> None:
    if not mandate.active:
        raise ConsentError(
            f"Aucun mandat actif pour {mandate.case_id} ; traitement refusé (G-1)."
        )


async def _auto_confirm(notice: str) -> bool:
    """Confirm par défaut (CLI/tests) : approuve immédiatement.

    En production (L2), confirm attend un asyncio.Future/Event résolu par un
    POST /confirm — jamais un callable sync (voir notifier.notify).
    """
    return True


async def run_until_gate(
    mandate: Mandate,
    *,
    log=print,
    emit: Emit = print_emitter,
) -> list[ForensicRecord]:
    """Première moitié du pipeline : Mandate -> Locate -> Analyze, STOP avant le gate G-7.

    Renvoie tous les ForensicRecord produits ; ceux en Status.VERIFIED sont les
    candidats à dispatcher. RIEN n'est envoyé ici — c'est le point d'arrêt naturel
    pour L2 : appeler run_until_gate, montrer la notice à la victime, puis appeler
    dispatch() APRÈS son verdict humain (résolu par POST /confirm).
    """
    _require_active(mandate)  # consent gate G-1, vérifié à l'entrée du pipeline
    # from_status=None : MANDATED est la naissance du case, il n'y a pas d'état antérieur.
    emit(make_event(
        mandate.case_id,
        "mandate",
        Status.MANDATED,
        payload={"requester_role": mandate.requester_role, "scope_urls": mandate.scope_urls},
    ))

    located: asyncio.Queue[MediaItem] = asyncio.Queue()
    records: list[ForensicRecord] = []

    # Stage 1 — Locate (in-scope only)
    await locator.locate(mandate, located, log=log, emit=emit)

    # Stage 2 — Analyze (+ pré-check mineur / seuil)
    while not located.empty():
        item = await located.get()
        records.append(await analyzer.analyze(item, log=log, emit=emit))
        # ESCALATED / REJECTED s'arrêtent ici, par design ; VERIFIED attend dispatch().

    return records


async def dispatch(
    record: ForensicRecord,
    mandate: Mandate,
    *,
    confirm: Callable[[str], Awaitable[bool]] = _auto_confirm,
    log=print,
    emit: Emit = print_emitter,
) -> NotificationRecord:
    """Seconde moitié : Notify pour UN record VERIFIED, derrière le gate G-7.

    `confirm` est async ; côté L2 il attend le verdict humain (POST /confirm) sans
    bloquer l'event loop. Fail-closed : refus ou timeout -> record DECLINED, rien
    n'est envoyé (voir notifier.notify).
    """
    # G-1 re-vérifié : du temps humain s'écoule entre le gate et le verdict,
    # le mandat a pu être révoqué entre-temps.
    _require_active(mandate)
    if record.status is not Status.VERIFIED:
        # Fail-fast : dispatcher un record non vérifié est un bug appelant.
        raise ValueError(
            f"dispatch attend un record VERIFIED, reçu {record.status} ({record.case_id})"
        )
    return await notifier.notify(record, mandate, confirm=confirm, log=log, emit=emit)


async def run(
    mandate: Mandate,
    *,
    confirm: Callable[[str], Awaitable[bool]] = _auto_confirm,
    log=print,
    emit: Emit = print_emitter,
) -> list:
    """Pipeline complet Mandate -> Locate -> Analyze -> Notify. Renvoie tous les records.

    Point d'entrée CLI/tests : enchaîne run_until_gate() puis dispatch() pour chaque
    VERIFIED. Le web (L2) appelle plutôt les deux moitiés séparément pour tenir le
    gate G-7 ouvert entre deux requêtes HTTP.
    `emit` reçoit un StageEvent à chaque transition d'état (contrat : mira/events.py).
    `log` reste le canal texte legacy des messages hors transition (ex. rejet G-2).
    """
    records = await run_until_gate(mandate, log=log, emit=emit)
    results: list = list(records)
    for record in records:
        if record.status is Status.VERIFIED:
            results.append(
                await dispatch(record, mandate, confirm=confirm, log=log, emit=emit)
            )
    return results
