"""Stage 0 — Le Mandat. Établit la base légale et le périmètre AVANT tout le reste.

Lane L1. Le vrai : vérifier l'identité de la victime / représentant / ONG autorisée,
recueillir le consentement explicite, chiffrer la preuve de consentement.
"""

from __future__ import annotations

from .types import Mandate, utcnow


def create_demo_mandate(case_id: str = "demo-001") -> Mandate:
    """MOCK — mandat de démo pré-autorisé, scoped sur un mock host contrôlé (G-12)."""
    return Mandate(
        case_id=case_id,
        requester_role="victim",
        consent_ts_utc=utcnow(),
        scope_urls=["https://mock-host.local/target"],
        active=True,
    )


def revoke(mandate: Mandate) -> Mandate:
    """Révocation -> déclenche la purge en aval (G-10, droit à l'effacement)."""
    mandate.active = False
    return mandate
