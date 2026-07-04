"""Contrats de domaine — GELÉS.

Les 5 lanes codent contre ces types. Changer une signature ici se répercute sur
tout le monde : à discuter en équipe avant d'éditer. C'est ce qui garde le vibecode
propre à 5 (chacun code librement DANS son module, tant que l'interface tient).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path


def utcnow() -> datetime:
    """Horodatage UTC (ISO 8601). Une seule source de temps dans tout le système."""
    return datetime.now(timezone.utc)


class Status(str, Enum):
    """États de la state machine (voir spec §10)."""

    MANDATED = "MANDATED"    # Stage 0 — consentement + scope enregistrés
    LOCATED = "LOCATED"      # Stage 1 — média in-scope trouvé
    VERIFIED = "VERIFIED"    # Stage 2 — adulte, deepfake confirmé, preuve minimale
    REJECTED = "REJECTED"    # Stage 2 — sous le seuil, rien stocké
    ESCALATED = "ESCALATED"  # Stage 2 — mineur suspecté -> halt + signalement
    CONFIRMED = "CONFIRMED"  # Gate — victime a approuvé la notice
    NOTIFIED = "NOTIFIED"    # Stage 3 — notice DSA envoyée
    REVOKED = "REVOKED"      # Mandat retiré -> purge
    FAILED = "FAILED"        # Erreur non récupérable


@dataclass
class Mandate:
    """Stage 0 — la base légale. Sans mandat actif, aucun stage ne tourne (G-1)."""

    case_id: str                      # opaque, aucune PII dans l'id
    requester_role: str               # "victim" | "legal_rep" | "authorized_ngo"
    consent_ts_utc: datetime          # quand le consentement a été recueilli
    scope_urls: list[str]             # surfaces autorisées uniquement (pas le web ouvert)
    consent_artifact: Path | None = None  # preuve chiffrée du consentement
    active: bool = True               # False dès révocation


@dataclass
class MediaItem:
    """Sortie du Locator (Stage 1)."""

    case_id: str
    url: str
    status: Status = Status.LOCATED


@dataclass
class ForensicRecord:
    """Sortie de l'Analyzer (Stage 2). Preuve minimale : hash d'abord, jamais les octets bruts (G-5)."""

    case_id: str
    source_url: str
    deepfake_score: float             # confiance du détecteur 0.0-1.0
    perceptual_hash: str              # empreinte robuste = preuve primaire
    sha256_hash: str                  # hash exact de la capture
    discovery_ts_utc: datetime
    status: Status                    # VERIFIED | REJECTED | ESCALATED
    minimal_ref: Path | None = None   # chiffré, seulement si strictement requis


@dataclass
class NotificationRecord:
    """Sortie du Notifier (Stage 3)."""

    case_id: str
    source_url: str
    host_contact: str
    notice_text: str
    dispatched_ts_utc: datetime
    status: Status = Status.NOTIFIED
