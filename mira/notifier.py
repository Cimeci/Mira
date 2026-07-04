"""Stage 3 — Le Notifier. Résout l'hébergeur, rédige la notice DSA, gate de confirmation, envoie.

Lane L3. Le vrai : RDAP (RFC 9083) -> point de contact DSA -> abuse@ ; LLM avec template
strict DSA art.16 ; dispatch Resend vers l'inbox de démo uniquement (G-12).
"""

from __future__ import annotations

import asyncio
import inspect
import os
import re
from collections.abc import Awaitable, Callable

from . import config
from .events import Emit, make_event, print_emitter
from .types import ForensicRecord, Mandate, NotificationRecord, Status, utcnow

# --- G-9 : verrou d'exactitude légale -----------------------------------------------------
# Citations JAMAIS générées par LLM — constantes figées, validées contre les textes
# officiels le 2026-07-04 (Légifrance : Code pénal art. 226-8-1 créé par la loi SREN
# n° 2024-449 du 21 mai 2024 ; EUR-Lex : règlement (UE) 2022/2065 « DSA » art. 16 ;
# LCEN loi n° 2004-575). Toute modification exige une relecture des sources officielles.
LEGAL_BASIS_CITATION = "Code pénal art. 226-8-1 (loi SREN n° 2024-449) ; DSA art. 16 ; LCEN."
GOOD_FAITH_DECLARATION = (  # exigence DSA art. 16(2)(d) (la LCEN renvoie au DSA depuis SREN)
    "Déclaration de bonne foi (DSA art. 16(2)(d)) : le notifiant estime de bonne foi "
    "ces informations exactes et complètes."
)
AI_TRANSPARENCY_LINE = (
    # Démarche VOLONTAIRE : l'AI Act art. 50 ne s'applique pas à une notification
    # bilatérale revue par un humain — ne pas affirmer une obligation qui n'existe pas.
    "Transparence (démarche volontaire) : cette notification a été préparée avec "
    "l'assistance d'un système d'IA, puis revue et validée par la personne concernée "
    "avant envoi."
)

# DSA art. 16(2)(c) : nom + adresse électronique du notifiant sont OBLIGATOIRES
# (l'exception d'anonymat ne couvre que le CSAM, pas les deepfakes visant des adultes).
# C'est le MANDATAIRE qui s'identifie — l'identité de la victime n'apparaît jamais.
# Adresse .example (RFC 2606) par défaut : inbox de démo uniquement (G-12).
NOTIFIER_NAME = os.getenv("MIRA_NOTIFIER_NAME", "Project Mira — mandataire de notification")
NOTIFIER_EMAIL = os.getenv("MIRA_NOTIFIER_EMAIL", "notices@project-mira.example")

# La notice ne mentionne JAMAIS de pénalité : citer une amende/peine (a fortiori
# l'inventer) est le risque G-9 disqualifiant. Ce motif barre toute sortie LLM.
# Frontières de mot sur les termes courts pour ne pas bloquer « européen » etc.
_PENALTY_PATTERN = re.compile(
    r"\bamendes?\b|\beuros?\b|€|\bprison\b|\bemprisonnement\b|\bréclusion\b"
    r"|\bdétention\b|condamn|pénalit|\bpeines?\b|\bsanctions?\b|\d[\d\s]*(?:€|euros?)",
    re.IGNORECASE,
)


def assert_no_invented_penalty(text: str) -> str:
    """Garde-fou G-9 : refuse tout texte qui parle de pénalité. À appliquer sur TOUTE
    sortie LLM (ex. l5-llm-cover-note) AVANT concaténation à la notice ; en cas d'échec,
    l'appelant retombe sur le template seul."""
    match = _PENALTY_PATTERN.search(text)
    if match:
        raise ValueError(f"Pénalité détectée dans le texte de notice (G-9) : {match.group(0)!r}")
    return text


def _resolve_host(url: str) -> str:
    """MOCK RDAP. Le vrai : RDAP -> contact DSA publié -> abuse@ en fallback."""
    return "abuse@mock-host.local"


# Ligne « Notifiant » par rôle de mandant : formulations FACTUELLES uniquement —
# on n'invente aucune base légale de représentation (G-9), on décrit le mandat reçu.
_NOTIFIER_LINE_BY_ROLE = {
    "victim": "agissant sur mandat de la personne concernée.",
    "legal_rep": "agissant sur mandat de son représentant légal mandaté.",
    "authorized_ngo": "agissant sur mandat d'une ONG autorisée.",
}


def _legal_core(record: ForensicRecord, host: str, mandate: Mandate) -> str:
    """Cœur légal de la notice DSA art. 16 — 100 % template déterministe.

    Aucune interpolation LLM sur les citations (G-9). Les seuls champs dynamiques
    sont factuels : hôte, URL, base légale et rôle portés par le mandat, bloc de
    preuve (phash/horodatage/score).
    """
    try:
        notifier_line = _NOTIFIER_LINE_BY_ROLE[mandate.requester_role]
    except KeyError:
        # Fail-fast : un rôle inconnu ici est un bug amont, pas une notice à improviser.
        raise KeyError(
            f"requester_role inconnu pour la notice : {mandate.requester_role!r} "
            f"(attendu : {sorted(_NOTIFIER_LINE_BY_ROLE)})"
        ) from None
    return (
        "Objet : Notification de contenu illicite (DSA, art. 16) — retrait demandé\n"
        f"Destinataire : {host}\n"
        f"Localisation exacte : {record.source_url}\n"
        f"Base légale : {mandate.legal_basis}\n"
        "Substantiation : deepfake sexuel non consenti d'une personne identifiée.\n"
        f"Notifiant : Project Mira, système assistif automatisé, {notifier_line}\n"
        f"Identification du notifiant (DSA art. 16(2)(c)) : {NOTIFIER_NAME} — "
        f"adresse électronique : {NOTIFIER_EMAIL}.\n"
        f"{GOOD_FAITH_DECLARATION}\n"
        f"Bloc de preuve : phash={record.perceptual_hash} ; "
        f"horodatage={record.discovery_ts_utc.isoformat()} ; "
        f"score détecteur={record.deepfake_score:.2f}.\n"
        f"{AI_TRANSPARENCY_LINE}\n"
    )


def _draft_dsa_notice(record: ForensicRecord, host: str, mandate: Mandate) -> str:
    """Notice complète = cœur légal figé. Si un LLM rédige un jour des parties
    NON légales (cover note), sa sortie passe par assert_no_invented_penalty
    avant concaténation — sinon template seul."""
    return _legal_core(record, host, mandate)


async def notify(
    record: ForensicRecord,
    mandate: Mandate,
    *,
    confirm: Callable[[str], Awaitable[bool]],
    log=print,
    emit: Emit = print_emitter,
) -> NotificationRecord:
    """Résout l'hôte, rédige, fait confirmer par la victime (G-7), puis envoie.

    `confirm` est OBLIGATOIREMENT async (jamais un callable sync — on l'await).
    Côté serveur (L2), l'implémentation attend un asyncio.Future/Event résolu par
    un POST /confirm ultérieur : c'est ce qui permet au gate de tenir sans bloquer
    l'event loop entre l'affichage de la notice et le verdict humain.
    Fail-closed : sans réponse sous CONFIRM_TIMEOUT_S, on traite comme un refus.
    """
    host = _resolve_host(record.source_url)
    notice = _draft_dsa_notice(record, host, mandate)
    log(f"[NOTIFY] hôte résolu : {host}")

    # Le texte de la notice ne va PAS dans le payload (règle events.py) — url seulement.
    emit(make_event(
        record.case_id,
        "notifier",
        Status.AWAITING_CONFIRM,
        from_status=Status.VERIFIED,
        payload={"url": record.source_url},
    ))

    # G-7 : gate de confirmation de la victime avant tout envoi externe.
    pending = confirm(notice)
    if not inspect.isawaitable(pending):
        # Fail-fast : un confirm sync bloquerait l'event loop (ou pire, un bool nu ici).
        raise TypeError(
            f"confirm doit être async (Awaitable[bool]), reçu {type(pending).__name__!r}"
        )
    try:
        # timeout lu sur le module (pas importé par valeur) : monkeypatchable en test.
        approved = await asyncio.wait_for(pending, timeout=config.CONFIRM_TIMEOUT_S)
    except TimeoutError:
        # Fail-closed : silence de la victime = refus. Jamais d'envoi par défaut.
        log("[NOTIFY] timeout de confirmation -> fail-closed, rien n'est envoyé")
        emit(make_event(
            record.case_id,
            "notifier",
            Status.DECLINED,
            from_status=Status.AWAITING_CONFIRM,
            detail="[NOTIFY] timeout de confirmation -> fail-closed, rien n'est envoyé",
            payload={"url": record.source_url, "reason": "confirm_timeout"},
        ))
        return _record(record, host, notice, Status.DECLINED)

    if not approved:
        emit(make_event(
            record.case_id,
            "notifier",
            Status.DECLINED,
            from_status=Status.AWAITING_CONFIRM,
            detail="[NOTIFY] victime décline -> hold/purge, rien n'est envoyé",
            payload={"url": record.source_url},
        ))
        return _record(record, host, notice, Status.DECLINED)

    emit(make_event(
        record.case_id,
        "notifier",
        Status.CONFIRMED,
        from_status=Status.AWAITING_CONFIRM,
        payload={"url": record.source_url},
    ))
    # MOCK dispatch. Le vrai : Resend/portail vers l'inbox de démo uniquement.
    emit(make_event(
        record.case_id,
        "notifier",
        Status.NOTIFIED,
        from_status=Status.CONFIRMED,
        detail=f"[NOTIFY] notice DSA envoyée à {host}",
        payload={"url": record.source_url},
    ))
    return _record(record, host, notice, Status.NOTIFIED)


def _record(r: ForensicRecord, host: str, notice: str, status: Status) -> NotificationRecord:
    return NotificationRecord(
        case_id=r.case_id,
        source_url=r.source_url,
        host_contact=host,
        notice_text=notice,
        dispatched_ts_utc=utcnow(),
        status=status,
    )
