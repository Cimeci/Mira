"""Couche d'orchestration. Applique le consent gate UNE fois, puis fait couler le pipeline.

Lane L1. C'est ici — et pas dans chaque stage — qu'on garantit G-1 : aucun stage ne
tourne sans mandat actif. La state machine vit ici.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from . import analyzer, escalation, locator, notifier
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
) -> tuple[list[ForensicRecord], dict[str, str]]:
    """Première moitié du pipeline : Mandate -> Locate -> Analyze -> Draft, STOP au gate G-7.

    Contrat L2 — renvoie `(records, notices)` :
      - records : tous les ForensicRecord produits ; ceux en Status.VERIFIED sont
        les candidats à dispatcher ;
      - notices : dict {record.source_url: notice pré-rédigée} pour chaque VERIFIED.
        À passer TEL QUEL à dispatch(record, mandate, notices[record.source_url])
        pour garantir que l'aperçu montré à la victime == la notice envoyée,
        octet pour octet (une seule rédaction).

    Pour chaque VERIFIED, la notice est rédigée ICI (notifier.draft, pur) et exposée
    à L3 via un StageEvent stage='notice' (payload {url, notice_text}) suivi du gate
    AWAITING_CONFIRM standard. RIEN n'est envoyé — appeler dispatch() APRÈS le
    verdict humain (résolu par POST /confirm).
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
    notices: dict[str, str] = {}

    # Stage 1 — Locate (in-scope only)
    await locator.locate(mandate, located, log=log, emit=emit)

    # Stage 2 — Analyze (+ pré-check mineur / seuil)
    while not located.empty():
        item = await located.get()
        record = await analyzer.analyze(item, log=log, emit=emit)
        records.append(record)
        if record.status is Status.ESCALATED:
            # G-6 : escalade AVANT toute tentative de stockage — garanti structurellement,
            # l'analyzer n'a rien téléchargé ni stocké sur ce cas. REJECTED s'arrête ici.
            escalation.escalate(record, mandate, log=log, emit=emit)
        elif record.status is Status.VERIFIED:
            # Pré-gate : la notice est rédigée UNE seule fois ici, montrée en aperçu
            # (event 'notice'), puis envoyée telle quelle par dispatch(notice=...).
            notice = notifier.draft(record, mandate)
            notices[record.source_url] = notice
            # Exception documentée dans events.py : notice_text est NOTRE texte
            # généré (template G-9), jamais du contenu victime ni des octets média.
            # C'est ce payload qui remplit le panneau de confirmation L3.
            emit(make_event(
                record.case_id,
                "notice",
                Status.AWAITING_CONFIRM,
                from_status=Status.VERIFIED,
                payload={"url": record.source_url, "notice_text": notice},
            ))
            # Puis le gate G-7 standard (payload url seulement, règle events.py).
            emit(make_event(
                record.case_id,
                "notifier",
                Status.AWAITING_CONFIRM,
                from_status=Status.VERIFIED,
                payload={"url": record.source_url},
            ))

    return records, notices


async def dispatch(
    record: ForensicRecord,
    mandate: Mandate,
    notice: str | None = None,
    *,
    confirm: Callable[[str], Awaitable[bool]],
    log=print,
    emit: Emit = print_emitter,
) -> NotificationRecord:
    """Seconde moitié : envoie la notice DÉJÀ rédigée pour UN record VERIFIED (gate G-7).

    `notice` : le texte pré-rédigé renvoyé par run_until_gate — le passer garantit
    que ce qui part est exactement l'aperçu validé par la victime. Si None (compat
    appel direct), on re-rédige via notifier.draft() — pur et déterministe, donc le
    texte reste identique à ce que le pré-gate aurait montré.
    `confirm` est OBLIGATOIRE (pas de défaut) : un appel L2 qui l'oublie doit
    échouer en TypeError, jamais auto-envoyer (G-7). Seul run() — la CLI — garde
    _auto_confirm et le transmet explicitement. Fail-closed : refus ou timeout ->
    record DECLINED, rien n'est envoyé (voir notifier.send).
    """
    # G-1 re-vérifié : du temps humain s'écoule entre le gate et le verdict,
    # le mandat a pu être révoqué entre-temps.
    _require_active(mandate)
    if record.status is not Status.VERIFIED:
        # Fail-fast : dispatcher un record non vérifié est un bug appelant.
        raise ValueError(
            f"dispatch attend un record VERIFIED, reçu {record.status} ({record.case_id})"
        )
    # Défense en profondeur avant envoi externe : le record doit appartenir AU mandat
    # qui autorise l'envoi — un mismatch = notifier au nom d'une autre victime.
    if record.case_id != mandate.case_id:
        raise ValueError(
            f"dispatch refusé : record {record.case_id!r} n'appartient pas au mandat "
            f"{mandate.case_id!r} (authorization mismatch)"
        )
    # G-2 re-vérifié au dernier point de sortie : rien ne part pour une URL hors du
    # périmètre consenti, même si le Locator reste le garant principal.
    if not locator.is_in_scope(record.source_url, mandate.scope_urls):
        raise ValueError(
            f"dispatch refusé : {record.source_url} hors scope du mandat (G-2)"
        )
    if notice is None:
        notice = notifier.draft(record, mandate)
    return await notifier.send(notice, record, mandate, confirm=confirm, log=log, emit=emit)


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
    records, notices = await run_until_gate(mandate, log=log, emit=emit)
    results: list = list(records)
    for record in records:
        if record.status is Status.VERIFIED:
            # La notice pré-rédigée est transmise : une seule rédaction par record,
            # preview == envoi garanti aussi sur le chemin CLI.
            results.append(
                await dispatch(
                    record,
                    mandate,
                    notices[record.source_url],
                    confirm=confirm,
                    log=log,
                    emit=emit,
                )
            )
    return results
