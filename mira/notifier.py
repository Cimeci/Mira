"""Stage 3 — Le Notifier. Résout l'hébergeur, rédige la notice DSA, gate de confirmation, envoie.

Lane L3. Le vrai : RDAP (RFC 9083) -> point de contact DSA -> abuse@ ; LLM avec template
strict DSA art.16 ; dispatch Resend vers l'inbox de démo uniquement (G-12).
"""

from __future__ import annotations

from typing import Callable

from .types import ForensicRecord, Mandate, NotificationRecord, Status, utcnow


def _resolve_host(url: str) -> str:
    """MOCK RDAP. Le vrai : RDAP -> contact DSA publié -> abuse@ en fallback."""
    return "abuse@mock-host.local"


def _draft_dsa_notice(record: ForensicRecord, host: str) -> str:
    """Notice DSA art.16. Base légale exacte, JAMAIS de pénalité inventée (G-9).

    Ligne de transparence AI Act incluse. Déclaration de bonne foi (LCEN, G-8).
    """
    return (
        "Objet : Notification de contenu illicite (DSA, art. 16) — retrait demandé\n"
        f"Destinataire : {host}\n"
        f"Localisation exacte : {record.source_url}\n"
        "Base légale : Code pénal art. 226-8-1 (loi SREN n° 2024-449) ; DSA art. 16 ; LCEN.\n"
        "Substantiation : deepfake sexuel non consenti d'une personne identifiée.\n"
        "Notifiant : Project Mira, système assistif automatisé, agissant sur mandat de la personne concernée.\n"
        "Déclaration de bonne foi : le notifiant estime de bonne foi ces informations exactes et complètes.\n"
        f"Bloc de preuve : phash={record.perceptual_hash} ; "
        f"horodatage={record.discovery_ts_utc.isoformat()} ; score détecteur={record.deepfake_score:.2f}.\n"
        "Transparence (AI Act) : cette notification a été préparée par un système assisté par IA.\n"
    )


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
