"""Stage 0 — Le Mandat. Établit la base légale et le périmètre AVANT tout le reste.

Lane L1. Décision d'équipe : l'identité du demandeur est une ATTESTATION DÉCLARATIVE
(case à cocher « je certifie être la personne concernée / son représentant »), jamais
un vrai login/OAuth/KYC/OCR — zéro point jury, grosse surface de casse, et new-work-only
interdit de réimporter une stack d'auth existante. Le mandat ne peut pas exister sans
consentement explicite : c'est ce qui matérialise « consent unlocks autonomy ».
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path
from urllib.parse import urlparse

from .types import DEFAULT_LEGAL_BASIS, Mandate, utcnow

# Qui peut mandater Mira (spec §5). Un rôle inconnu est une erreur de programmation
# côté appelant -> ValueError, pas un refus de consentement.
ALLOWED_REQUESTER_ROLES = frozenset({"victim", "legal_rep", "authorized_ngo"})

# Preuves de consentement (G-5) : hors du code source, dossier gitignoré — le repo
# est public, AUCUNE preuve ne doit être committable. Nom de fichier = case_id
# (opaque par contrat de types), jamais de PII.
CONSENT_ARTIFACT_DIR = Path(".mira_consent")

# Clé HMAC : env MIRA_CONSENT_HMAC_KEY si fournie, sinon clé éphémère par process (dev).
# Stdlib uniquement — pas de dépendance `cryptography` pour un hackathon 15h.
_ENV_KEY = os.environ.get("MIRA_CONSENT_HMAC_KEY")
_HMAC_KEY: bytes = _ENV_KEY.encode("utf-8") if _ENV_KEY else secrets.token_bytes(32)


def _consent_payload(mandate: Mandate) -> bytes:
    """Sérialisation canonique (JSON trié) : même mandat -> mêmes octets -> même HMAC."""
    return json.dumps(
        {
            "case_id": mandate.case_id,
            "requester_role": mandate.requester_role,
            "scope_urls": mandate.scope_urls,
            "consent_ts_utc": mandate.consent_ts_utc.isoformat(),
            "legal_basis": mandate.legal_basis,
            "attestation": True,  # capture_consent refuse tout mandat non attesté
        },
        sort_keys=True,
    ).encode("utf-8")


def _sign(payload: bytes) -> str:
    return hmac.new(_HMAC_KEY, payload, hashlib.sha256).hexdigest()


def _write_consent_artifact(mandate: Mandate) -> Path:
    """Écrit la preuve signée de consentement sous .mira_consent/<case_id>.json."""
    payload = _consent_payload(mandate)
    artifact = {
        "payload_b64": base64.b64encode(payload).decode("ascii"),
        "signature": _sign(payload),
        "ts": utcnow().isoformat(),
    }
    CONSENT_ARTIFACT_DIR.mkdir(exist_ok=True)
    path = CONSENT_ARTIFACT_DIR / f"{mandate.case_id}.json"
    path.write_text(json.dumps(artifact, sort_keys=True), encoding="utf-8")
    return path


def verify_consent_artifact(mandate: Mandate) -> bool:
    """Recalcule le HMAC de l'artefact de consentement et le compare à la signature stockée.

    Modèle de sécurité honnête : l'artefact est SIGNÉ (intégrité + provenance vis-à-vis
    de la clé du process), il n'est PAS chiffré — le chiffrement au repos reste hors
    périmètre de la démo. Retourne False si l'artefact manque, est illisible ou altéré.
    """
    if mandate.consent_artifact is None or not mandate.consent_artifact.exists():
        return False
    try:
        data = json.loads(mandate.consent_artifact.read_text(encoding="utf-8"))
        payload = base64.b64decode(data["payload_b64"])
        stored_signature = data["signature"]
    except (json.JSONDecodeError, KeyError, ValueError):
        # Artefact corrompu/illisible = preuve invalide : c'est le verdict, pas un échec caché.
        return False
    return hmac.compare_digest(_sign(payload), stored_signature)


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
    mandate = Mandate(
        case_id=case_id,
        requester_role=requester_role,
        consent_ts_utc=utcnow(),
        scope_urls=scope_urls,
        legal_basis=legal_basis,
        active=True,
    )
    # G-5 : la preuve de consentement est signée et persistée hors du repo committable.
    mandate.consent_artifact = _write_consent_artifact(mandate)
    return mandate


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
