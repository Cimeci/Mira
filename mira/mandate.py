"""Stage 0 — Le Mandat. Établit la base légale et le périmètre AVANT tout le reste.

Lane L1. Décision d'équipe : l'identité du demandeur est une ATTESTATION DÉCLARATIVE
(case à cocher « je certifie être la personne concernée / son représentant »), jamais
un vrai login/OAuth/KYC/OCR — zéro point jury, grosse surface de casse, et new-work-only
interdit de réimporter une stack d'auth existante. Le mandat ne peut pas exister sans
consentement explicite : c'est ce qui matérialise « consent unlocks autonomy ».
"""

from __future__ import annotations

from urllib.parse import urlparse

from .types import DEFAULT_LEGAL_BASIS, Mandate, utcnow

# Qui peut mandater Mira (spec §5). Un rôle inconnu est une erreur de programmation
# côté appelant -> ValueError, pas un refus de consentement.
ALLOWED_REQUESTER_ROLES = frozenset({"victim", "legal_rep", "authorized_ngo"})


def _validate_scope(urls: list[str]) -> None:
    """G-2 : le scope est la SEULE surface autorisée — il doit être précis et absolu."""
    if not urls:
        raise ValueError("scope_urls vide : un mandat sans périmètre n'autorise rien (G-2).")
    for url in urls:
        if "*" in url:
            raise ValueError(f"Wildcard interdit dans le scope (G-2) : {url!r}")
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(
                f"URL de scope invalide (attendu http(s)://host/... absolu, G-2) : {url!r}"
            )


def capture_consent(
    *,
    case_id: str,
    requester_role: str,
    scope_urls: list[str],
    legal_basis: str = DEFAULT_LEGAL_BASIS,
    attestation: bool,
) -> Mandate:
    """Fabrique LE mandat : consentement explicite requis, rôle et scope validés (fail-fast).

    Seul point du système où consent_ts_utc est stampé (source de temps unique).
    """
    if requester_role not in ALLOWED_REQUESTER_ROLES:
        raise ValueError(
            f"requester_role inconnu : {requester_role!r} "
            f"(attendu : {sorted(ALLOWED_REQUESTER_ROLES)})"
        )
    _validate_scope(scope_urls)
    if attestation is not True:
        # Import local : évite un import circulaire si l'orchestrateur venait à importer mandate.
        from .orchestrator import ConsentError

        raise ConsentError("consentement requis avant création du mandat (G-1/G-7).")
    return Mandate(
        case_id=case_id,
        requester_role=requester_role,
        consent_ts_utc=utcnow(),
        scope_urls=scope_urls,
        legal_basis=legal_basis,
        active=True,
    )


def create_demo_mandate(case_id: str = "demo-001") -> Mandate:
    """MOCK — mandat de démo pré-autorisé, scoped sur un mock host contrôlé (G-12)."""
    return capture_consent(
        case_id=case_id,
        requester_role="victim",
        scope_urls=["https://mock-host.local/target"],
        attestation=True,
    )


def revoke(mandate: Mandate) -> Mandate:
    """Révocation -> déclenche la purge en aval (G-10, droit à l'effacement)."""
    mandate.active = False
    return mandate
