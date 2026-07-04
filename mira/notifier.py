"""Stage 3 — Le Notifier. Résout l'hébergeur, rédige la notice DSA, gate de confirmation, envoie.

Lane L3. Le vrai : RDAP (RFC 9083) -> point de contact DSA -> abuse@ ; LLM avec template
strict DSA art.16 ; dispatch Resend vers l'inbox de démo uniquement (G-12).
"""

from __future__ import annotations

import re
from collections.abc import Callable

from .types import ForensicRecord, Mandate, NotificationRecord, Status, utcnow

# --- G-9 : verrou d'exactitude légale -----------------------------------------------------
# Citations JAMAIS générées par LLM — constantes figées, validées contre les textes
# officiels (Légifrance : Code pénal art. 226-8-1 créé par la loi SREN n° 2024-449 du
# 21 mai 2024 ; EUR-Lex : règlement (UE) 2022/2065 « DSA » art. 16 ; LCEN loi n° 2004-575).
# Toute modification de ces constantes exige une relecture des sources officielles.
LEGAL_BASIS_CITATION = "Code pénal art. 226-8-1 (loi SREN n° 2024-449) ; DSA art. 16 ; LCEN."
GOOD_FAITH_DECLARATION = (  # G-8, exigence LCEN
    "Déclaration de bonne foi : le notifiant estime de bonne foi "
    "ces informations exactes et complètes."
)
AI_TRANSPARENCY_LINE = (  # AI Act
    "Transparence (AI Act) : cette notification a été préparée par un système assisté par IA."
)

# La notice ne mentionne JAMAIS de pénalité : citer une amende/peine (a fortiori
# l'inventer) est le risque G-9 disqualifiant. Ce motif barre toute sortie LLM.
_PENALTY_PATTERN = re.compile(
    r"amende|euros|€|prison|emprisonnement|peine|sanction|\d[\d\s]*(?:€|euros)",
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


def _legal_core(record: ForensicRecord, host: str) -> str:
    """Cœur légal de la notice DSA art. 16 — 100 % template déterministe.

    Aucune interpolation LLM sur les citations (G-9). Les seuls champs dynamiques
    sont factuels : hôte, URL, bloc de preuve (phash/horodatage/score).
    """
    return (
        "Objet : Notification de contenu illicite (DSA, art. 16) — retrait demandé\n"
        f"Destinataire : {host}\n"
        f"Localisation exacte : {record.source_url}\n"
        f"Base légale : {LEGAL_BASIS_CITATION}\n"
        "Substantiation : deepfake sexuel non consenti d'une personne identifiée.\n"
        "Notifiant : Project Mira, système assistif automatisé, "
        "agissant sur mandat de la personne concernée.\n"
        f"{GOOD_FAITH_DECLARATION}\n"
        f"Bloc de preuve : phash={record.perceptual_hash} ; "
        f"horodatage={record.discovery_ts_utc.isoformat()} ; "
        f"score détecteur={record.deepfake_score:.2f}.\n"
        f"{AI_TRANSPARENCY_LINE}\n"
    )


def _draft_dsa_notice(record: ForensicRecord, host: str) -> str:
    """Notice complète = cœur légal figé. Si un LLM rédige un jour des parties
    NON légales (cover note), sa sortie passe par assert_no_invented_penalty
    avant concaténation — sinon template seul."""
    return _legal_core(record, host)


async def notify(
    record: ForensicRecord,
    mandate: Mandate,
    *,
    confirm: Callable[[str], bool],
    log=print,
) -> NotificationRecord:
    """Résout l'hôte, rédige, fait confirmer par la victime, puis envoie."""
    host = _resolve_host(record.source_url)
    notice = _draft_dsa_notice(record, host)
    log(f"[NOTIFY] hôte résolu : {host}")

    # G-7 : gate de confirmation de la victime avant tout envoi externe.
    if not confirm(notice):
        log("[NOTIFY] victime décline -> hold/purge, rien n'est envoyé")
        return _record(record, host, notice, Status.CONFIRMED)

    # MOCK dispatch. Le vrai : Resend/portail vers l'inbox de démo uniquement.
    log(f"[NOTIFY] notice DSA envoyée à {host}")
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
